"""Python gameplay simulation for the C++/raylib rogue-like renderer."""

from __future__ import annotations

import json
import math
import random
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple

import yaml


@dataclass
class Actor:
    id: str
    kind: str
    variant: str
    x: float
    y: float
    speed: float
    hp: int
    max_hp: int
    state: str = "idle"
    vx: float = 0.0
    vy: float = 0.0
    attack_cooldown: float = 0.0
    invulnerability: float = 0.0


@dataclass
class Projectile:
    id: str
    owner: str
    kind: str
    x: float
    y: float
    vx: float
    vy: float
    damage: int
    ttl: float
    radius: float = 0.2


@dataclass
class Pickup:
    id: str
    kind: str
    x: float
    y: float


@dataclass
class Effect:
    id: str
    kind: str
    x: float
    y: float
    ttl: float


class RogueGame:
    """Main gameplay loop that mirrors classic Isaac-style mechanics."""

    SOLID_TILES = {"wall", "rock", "pit"}
    HAZARD_TILES = {"spikes"}

    def __init__(self, config_path: str = "game_config.yaml", shared_dir: str = "shared") -> None:
        self.config_path = Path(config_path)
        self.shared_dir = Path(shared_dir)
        self.shared_dir.mkdir(parents=True, exist_ok=True)

        self.config = self._load_config()
        self.tick_rate = float(self.config["game"].get("tick_rate", 60))
        self.delta_time = 1.0 / self.tick_rate

        seed = self.config["game"].get("rng_seed")
        if seed is None:
            seed = int(time.time())
        self.rng = random.Random(seed)

        self.player_radius = 0.35
        self.enemy_radius = 0.45

        self._reset_run()

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------
    def _load_config(self) -> Dict:
        base_config = {
            "game": {
                "room_width": 20,
                "room_height": 12,
                "tile_size": 32,
                "tick_rate": 60,
                "rng_seed": None,
            },
            "player": {
                "hp": 6,
                "speed": 4.0,
                "fire_delay": 0.33,
                "projectile_speed": 9.0,
                "projectile_damage": 3,
            },
            "enemies": {
                "variants": ["charger", "hopper", "spitter"],
                "spawn_min": 3,
                "spawn_max": 6,
                "speed_min": 1.2,
                "speed_max": 2.4,
                "hp_min": 2,
                "hp_max": 5,
            },
            "pickups": {
                "chance_heart": 0.25,
                "chance_coin": 0.4,
                "chance_key": 0.2,
                "chance_bomb": 0.15,
            },
        }

        if self.config_path.exists():
            with self.config_path.open("r", encoding="utf-8") as fh:
                user_config = yaml.safe_load(fh) or {}
            base_config = self._deep_merge(base_config, user_config)

        return base_config

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        result = dict(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _reset_run(self) -> None:
        self.tick = 0
        self.inventory = {"coins": 0, "keys": 0, "bombs": 1}
        self.messages: List[str] = []

        self.room = self._generate_room()
        spawn_x = self.room["width"] / 2.0
        spawn_y = self.room["height"] / 2.0
        player_hp = int(self.config["player"]["hp"])
        self.player = Actor(
            id="player",
            kind="player",
            variant="isaac",
            x=spawn_x,
            y=spawn_y,
            speed=float(self.config["player"]["speed"]),
            hp=player_hp,
            max_hp=player_hp,
        )

        self.enemies: List[Actor] = self._spawn_enemies()
        self.projectiles: List[Projectile] = []
        self.pickups: List[Pickup] = self._spawn_pickups()
        self.effects: List[Effect] = []

        self.running = True
        self._refresh_meta()

    def _generate_room(self) -> Dict:
        width = int(self.config["game"]["room_width"])
        height = int(self.config["game"]["room_height"])

        tiles = [["floor" for _ in range(width)] for _ in range(height)]

        for x in range(width):
            tiles[0][x] = "wall"
            tiles[height - 1][x] = "wall"
        for y in range(height):
            tiles[y][0] = "wall"
            tiles[y][width - 1] = "wall"

        # Place doors at the center of each wall
        tiles[0][width // 2] = "door_up"
        tiles[height - 1][width // 2] = "door_down"
        tiles[height // 2][0] = "door_left"
        tiles[height // 2][width - 1] = "door_right"

        for y in range(1, height - 1):
            for x in range(1, width - 1):
                roll = self.rng.random()
                if roll < 0.06:
                    tiles[y][x] = "rock"
                elif roll < 0.1:
                    tiles[y][x] = "pit"
                elif roll < 0.14:
                    tiles[y][x] = "spikes"

        return {
            "width": width,
            "height": height,
            "tile_size": int(self.config["game"]["tile_size"]),
            "tiles": tiles,
        }

    def _spawn_enemies(self) -> List[Actor]:
        count = self.rng.randint(
            int(self.config["enemies"]["spawn_min"]), int(self.config["enemies"]["spawn_max"])
        )

        enemies: List[Actor] = []
        for index in range(count):
            for _ in range(32):
                x = self.rng.uniform(1.5, self.room["width"] - 1.5)
                y = self.rng.uniform(1.5, self.room["height"] - 1.5)
                if self._is_position_walkable(x, y, self.enemy_radius):
                    break
            else:
                x = self.room["width"] / 2.0
                y = 2.0

            variant = self.rng.choice(self.config["enemies"]["variants"])
            hp = self.rng.randint(int(self.config["enemies"]["hp_min"]), int(self.config["enemies"]["hp_max"]))
            speed = self.rng.uniform(float(self.config["enemies"]["speed_min"]), float(self.config["enemies"]["speed_max"]))

            enemies.append(
                Actor(
                    id=f"enemy_{variant}_{index}",
                    kind="enemy",
                    variant=variant,
                    x=x,
                    y=y,
                    speed=speed,
                    hp=hp,
                    max_hp=hp,
                    state="wander",
                )
            )
        return enemies

    def _spawn_pickups(self) -> List[Pickup]:
        pickups: List[Pickup] = []
        if self.rng.random() < 0.5:
            kind = self._roll_pickup_kind()
            x = self.room["width"] / 2.0 + self.rng.uniform(-2, 2)
            y = self.room["height"] / 2.0 + self.rng.uniform(-2, 2)
            if self._is_position_walkable(x, y, 0.3):
                pickups.append(Pickup(id=f"pickup_{kind}_0", kind=kind, x=x, y=y))
        return pickups

    def _roll_pickup_kind(self) -> str:
        roll = self.rng.random()
        if roll < self.config["pickups"]["chance_heart"]:
            return "heart"
        roll -= self.config["pickups"]["chance_heart"]
        if roll < self.config["pickups"]["chance_coin"]:
            return "coin"
        roll -= self.config["pickups"]["chance_coin"]
        if roll < self.config["pickups"]["chance_key"]:
            return "key"
        return "bomb"

    # ------------------------------------------------------------------
    # Simulation update
    # ------------------------------------------------------------------
    def step(self, input_data: Dict) -> None:
        if input_data.get("quit"):
            self.running = False
            return

        dt = self.delta_time
        self.tick += 1

        self._update_player(input_data, dt)
        self._update_enemies(dt)
        self._update_projectiles(dt)
        self._handle_pickups()
        self._update_effects(dt)

        self._refresh_meta()

        if self.player.hp <= 0:
            self.running = False

    def _update_player(self, input_data: Dict, dt: float) -> None:
        move_x, move_y = self._normalize_vector(input_data.get("move", {}))
        self.player.vx = move_x * self.player.speed
        self.player.vy = move_y * self.player.speed

        self._move_actor(self.player, self.player_radius, dt)

        if abs(move_x) + abs(move_y) > 0:
            self.player.state = "move"
        else:
            self.player.state = "idle"

        attack_dir = self._normalize_vector(input_data.get("attack", {}), normalize=True)
        self.player.attack_cooldown = max(0.0, self.player.attack_cooldown - dt)
        if attack_dir != (0.0, 0.0) and self.player.attack_cooldown <= 0.0:
            self._spawn_player_projectile(attack_dir)
            self.player.attack_cooldown = float(self.config["player"]["fire_delay"])

        # Hazards
        tile_under = self._tile_at(self.player.x, self.player.y)
        if tile_under in self.HAZARD_TILES and self.player.invulnerability <= 0.0:
            self._damage_player(1, source="spikes")
            self.player.invulnerability = 0.75

        self.player.invulnerability = max(0.0, self.player.invulnerability - dt)

    def _move_actor(self, actor: Actor, radius: float, dt: float) -> None:
        desired_x = actor.x + actor.vx * dt
        desired_y = actor.y + actor.vy * dt

        if self._is_position_walkable(desired_x, actor.y, radius):
            actor.x = desired_x
        else:
            actor.vx = 0.0

        if self._is_position_walkable(actor.x, desired_y, radius):
            actor.y = desired_y
        else:
            actor.vy = 0.0

    def _spawn_player_projectile(self, direction: Tuple[float, float]) -> None:
        proj_speed = float(self.config["player"]["projectile_speed"])
        damage = int(self.config["player"]["projectile_damage"])
        projectile = Projectile(
            id=f"tear_{self.tick}_{len(self.projectiles)}",
            owner="player",
            kind="player_projectile",
            x=self.player.x,
            y=self.player.y,
            vx=direction[0] * proj_speed,
            vy=direction[1] * proj_speed,
            damage=damage,
            ttl=2.0,
        )
        self.projectiles.append(projectile)

    def _update_enemies(self, dt: float) -> None:
        for enemy in list(self.enemies):
            dx = self.player.x - enemy.x
            dy = self.player.y - enemy.y
            dist = math.hypot(dx, dy)

            if dist > 0.01:
                enemy.vx = (dx / dist) * enemy.speed
                enemy.vy = (dy / dist) * enemy.speed
            else:
                enemy.vx = enemy.vy = 0.0

            self._move_actor(enemy, self.enemy_radius, dt)

            enemy.attack_cooldown = max(0.0, enemy.attack_cooldown - dt)
            if dist < 1.0 and enemy.attack_cooldown <= 0.0:
                self._damage_player(1, source=enemy.variant)
                enemy.attack_cooldown = 0.8

            if enemy.hp <= 0:
                self.enemies.remove(enemy)
                self._on_enemy_death(enemy)

    def _update_projectiles(self, dt: float) -> None:
        next_projectiles: List[Projectile] = []
        for projectile in self.projectiles:
            projectile.x += projectile.vx * dt
            projectile.y += projectile.vy * dt
            projectile.ttl -= dt

            if projectile.ttl <= 0:
                continue

            tile = self._tile_at(projectile.x, projectile.y)
            if tile in self.SOLID_TILES:
                self.effects.append(
                    Effect(
                        id=f"impact_{projectile.id}",
                        kind="impact",
                        x=projectile.x,
                        y=projectile.y,
                        ttl=0.2,
                    )
                )
                continue

            if projectile.owner == "player":
                hit_enemy = self._check_enemy_hit(projectile)
                if hit_enemy:
                    continue
            else:
                if self._check_player_hit(projectile):
                    continue

            next_projectiles.append(projectile)

        self.projectiles = next_projectiles

    def _check_enemy_hit(self, projectile: Projectile) -> bool:
        for enemy in self.enemies:
            if self._distance(enemy.x, enemy.y, projectile.x, projectile.y) < (self.enemy_radius + projectile.radius):
                enemy.hp -= projectile.damage
                self.effects.append(
                    Effect(
                        id=f"blood_{enemy.id}_{self.tick}",
                        kind="blood_splatter",
                        x=projectile.x,
                        y=projectile.y,
                        ttl=0.4,
                    )
                )
                if enemy.hp <= 0:
                    self.messages.append(f"{enemy.variant.title()} defeated!")
                return True
        return False

    def _check_player_hit(self, projectile: Projectile) -> bool:
        if self.player.invulnerability > 0.0:
            return False
        if self._distance(self.player.x, self.player.y, projectile.x, projectile.y) < (self.player_radius + projectile.radius):
            self._damage_player(1, source="projectile")
            return True
        return False

    def _handle_pickups(self) -> None:
        remaining: List[Pickup] = []
        for pickup in self.pickups:
            if self._distance(self.player.x, self.player.y, pickup.x, pickup.y) < 0.75:
                self._apply_pickup(pickup)
            else:
                remaining.append(pickup)
        self.pickups = remaining

    def _apply_pickup(self, pickup: Pickup) -> None:
        if pickup.kind == "heart" and self.player.hp < self.player.max_hp:
            self.player.hp = min(self.player.max_hp, self.player.hp + 1)
            self.messages.append("You feel healthier.")
        elif pickup.kind == "coin":
            self.inventory["coins"] += 1
        elif pickup.kind == "key":
            self.inventory["keys"] += 1
        elif pickup.kind == "bomb":
            self.inventory["bombs"] += 1
        else:
            self.messages.append(f"Picked up {pickup.kind}")

    def _update_effects(self, dt: float) -> None:
        remaining: List[Effect] = []
        for effect in self.effects:
            effect.ttl -= dt
            if effect.ttl > 0:
                remaining.append(effect)
        self.effects = remaining

    def _on_enemy_death(self, enemy: Actor) -> None:
        if self.rng.random() < 0.3:
            kind = self._roll_pickup_kind()
            self.pickups.append(Pickup(id=f"pickup_{kind}_{self.tick}", kind=kind, x=enemy.x, y=enemy.y))

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def _refresh_meta(self) -> None:
        self.meta = {
            "tick": self.tick,
            "delta_time": self.delta_time,
            "room_id": 0,
            "player_hp": self.player.hp,
            "player_max_hp": self.player.max_hp,
            "coins": self.inventory["coins"],
            "keys": self.inventory["keys"],
            "bombs": self.inventory["bombs"],
            "rng_seed": self.config["game"].get("rng_seed"),
            "room_cleared": not self.enemies,
            "messages": self.messages[-4:],
            "player_dead": self.player.hp <= 0,
        }

    def _tile_at(self, x: float, y: float) -> str:
        xi = max(0, min(self.room["width"] - 1, int(x)))
        yi = max(0, min(self.room["height"] - 1, int(y)))
        return self.room["tiles"][yi][xi]

    def _is_position_walkable(self, x: float, y: float, radius: float) -> bool:
        samples = [
            (x - radius, y - radius),
            (x + radius, y - radius),
            (x - radius, y + radius),
            (x + radius, y + radius),
        ]
        for sx, sy in samples:
            tile = self._tile_at(sx, sy)
            if tile in self.SOLID_TILES:
                return False
        return True

    def _damage_player(self, amount: int, source: str) -> None:
        if self.player.invulnerability > 0.0:
            return
        self.player.hp = max(0, self.player.hp - amount)
        self.player.invulnerability = 1.0
        self.messages.append(f"Took damage from {source}!")

    def _distance(self, ax: float, ay: float, bx: float, by: float) -> float:
        return math.hypot(ax - bx, ay - by)

    def _normalize_vector(self, data: Dict, normalize: bool = False) -> Tuple[float, float]:
        x = float(data.get("x", 0))
        y = float(data.get("y", 0))
        x = max(-1.0, min(1.0, x))
        y = max(-1.0, min(1.0, y))
        if normalize:
            length = math.hypot(x, y)
            if length > 0:
                return (x / length, y / length)
            return (0.0, 0.0)
        return (x, y)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    def serialise_state(self) -> Dict:
        return {
            "meta": self.meta,
            "tilemap": self.room,
            "actors": [
                {
                    "id": self.player.id,
                    "type": self.player.kind,
                    "variant": self.player.variant,
                    "x": self.player.x,
                    "y": self.player.y,
                    "dir_x": math.copysign(1.0, self.player.vx) if abs(self.player.vx) > 0.1 else 0.0,
                    "dir_y": math.copysign(1.0, self.player.vy) if abs(self.player.vy) > 0.1 else 0.0,
                    "hp": self.player.hp,
                    "max_hp": self.player.max_hp,
                    "state": self.player.state,
                    "speed": self.player.speed,
                    "items": [],
                    "invulnerable": self.player.invulnerability > 0.0,
                }
            ]
            + [
                {
                    "id": enemy.id,
                    "type": enemy.kind,
                    "variant": enemy.variant,
                    "x": enemy.x,
                    "y": enemy.y,
                    "hp": enemy.hp,
                    "max_hp": enemy.max_hp,
                    "state": enemy.state,
                }
                for enemy in self.enemies
            ],
            "projectiles": [asdict(p) for p in self.projectiles],
            "pickups": [asdict(p) for p in self.pickups],
            "effects": [asdict(e) for e in self.effects],
            "ui": {
                "messages": self.meta.get("messages", []),
                "boss_health": None,
            },
        }

    def write_state(self) -> None:
        state_path = self.shared_dir / "game_state.json"
        with state_path.open("w", encoding="utf-8") as fh:
            json.dump(self.serialise_state(), fh, indent=2)

    def read_input(self) -> Dict:
        input_path = self.shared_dir / "input.json"
        if not input_path.exists():
            return {}
        try:
            with input_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    return data
        except json.JSONDecodeError:
            pass
        return {}

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        try:
            while self.running:
                start = time.perf_counter()
                inputs = self.read_input()
                self.step(inputs)
                self.write_state()
                elapsed = time.perf_counter() - start
                sleep_time = max(0.0, self.delta_time - elapsed)
                time.sleep(sleep_time)
        except KeyboardInterrupt:
            self.running = False


def main() -> None:
    game = RogueGame()
    game.write_state()  # Initial snapshot for renderer start-up
    game.run()


if __name__ == "__main__":
    main()
