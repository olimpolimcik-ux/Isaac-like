## Python ↔ C++ Data Contract

This document defines the JSON messages exchanged between the Python gameplay
simulation and the C++/raylib renderer for the rogue‑like engine.

### Coordinate System

- The world is a uniform grid.
- All coordinates use floating point tile units (e.g. `x = 3.5` means the
  object is centered half‑way across tile column `3`).
- The renderer converts tile coordinates to pixels via
  `pixel = tile_coord * tile_size`.

### `shared/game_state.json`

```jsonc
{
  "meta": {
    "tick": 1432,
    "delta_time": 0.016,
    "room_id": 2,
    "player_hp": 5,
    "player_max_hp": 6,
    "coins": 7,
    "keys": 1,
    "bombs": 2,
    "rng_seed": 12039481,
    "room_cleared": false
  },
  "tilemap": {
    "tile_size": 32,
    "width": 20,
    "height": 12,
    "tiles": [
      ["wall", "wall", "wall", "wall"],
      ["wall", "floor", "floor", "wall"],
      ["wall", "pit", "floor", "wall"],
      ["wall", "door_up", "floor", "wall"],
      ["wall", "wall", "wall", "wall"]
    ]
  },
  "actors": [
    {
      "id": "player",
      "type": "player",
      "x": 9.5,
      "y": 5.5,
      "dir_x": 0,
      "dir_y": -1,
      "hp": 5,
      "max_hp": 6,
      "speed": 3.5,
      "state": "idle",
      "items": ["tears_up", "damage_up"]
    },
    {
      "id": "enemy_bloat_0",
      "type": "enemy",
      "variant": "bloat",
      "x": 4.0,
      "y": 5.0,
      "hp": 12,
      "max_hp": 12,
      "state": "chasing"
    }
  ],
  "projectiles": [
    {
      "id": "tear_15",
      "type": "player_projectile",
      "x": 10.5,
      "y": 5.1,
      "vx": 0,
      "vy": -8,
      "ttl": 0.35
    }
  ],
  "pickups": [
    {
      "id": "pickup_key_0",
      "type": "key",
      "x": 7.0,
      "y": 3.0
    }
  ],
  "effects": [
    {
      "id": "effect_blood_0",
      "type": "blood_splatter",
      "x": 4.1,
      "y": 5.2,
      "ttl": 0.25
    }
  ],
  "ui": {
    "messages": ["You feel blessed"],
    "boss_health": {
      "name": "Monstro",
      "hp": 150,
      "max_hp": 300
    }
  }
}
```

#### Tile Codes

| Code        | Description                 | Render Hint             |
|-------------|-----------------------------|-------------------------|
| `floor`     | Walkable floor              | Dark brown rectangle    |
| `wall`      | Solid wall                  | Slate grey rectangle    |
| `pit`       | Pit / hole (no walk)        | Dark void rectangle     |
| `rock`      | Breakable obstacle          | Light grey block        |
| `spikes`    | Damage when stepped on      | Grey with red outline   |
| `door_up`   | Door to connected room      | Gold frame              |
| `door_down` |                             |                         |
| `door_left` |                             |                         |
| `door_right`|                             |                         |
| `special`   | Special room feature        | Purple highlight        |

The renderer colors these procedurally (no textures yet).

#### Actor Variants

- `player`: The main controllable character. Always present.
- `enemy`: `variant` further specifies AI preset (e.g. `charger`, `turret`,
  `flyer`).
- `npc`: Non-hostile interactive actor.
- `boss`: Boss enemies; may appear alongside `boss_health` UI data.

#### Projectile Types

- `player_projectile`: Player tears/shots.
- `enemy_projectile`: Enemy projectiles.
- `bomb`: Active bombs with fuse timers.

#### Pickup Types

- `heart`, `soul_heart`, `black_heart`
- `coin`, `nickel`, `dime`
- `key`, `bomb`, `chest`, `item_pedestal`

Renderer draws all pickups as colored circles/squares with basic icons.

### `shared/input.json`

```jsonc
{
  "move": { "x": 0, "y": -1 },
  "attack": { "x": 0, "y": 1 },
  "bomb": false,
  "use_item": false,
  "pause": false,
  "quit": false
}
```

- `move`: Discrete direction from WASD input (normalized to {-1, 0, 1}).
- `attack`: Independent shooting direction from arrow keys (cardinal only).
- `bomb`: Trigger active bomb (SPACE).
- `use_item`: Activate current usable item (E).
- `pause`: Toggle pause (P).
- `quit`: Set by C++ when window closes; Python loop reads it to exit cleanly.

### File Locations

All JSON files live in `Project1/shared/` and are relative to both binaries.

```
Project1/
  shared/
    input.json
    game_state.json
```

The Python loop must create the directory if it is absent.

