#include "game_renderer.h"

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <unordered_map>

using json = nlohmann::json;
namespace fs = std::filesystem;

void GameRenderer::Initialize() {
    EnsureSharedDirectory();
    const int screen_width = 1280;
    const int screen_height = 720;
    InitWindow(screen_width, screen_height, "Rogue-like Prototype");
    SetTargetFPS(60);

    current_state_ = json::object();
}

void GameRenderer::Shutdown() {
    CloseWindow();
}

void GameRenderer::EnsureSharedDirectory() {
    try {
        fs::create_directories(shared_dir_);
    } catch (const std::exception& e) {
        TraceLog(LOG_WARNING, "Failed to ensure shared directory: %s", e.what());
    }
}

void GameRenderer::UpdateFromPython() {
    const fs::path state_path = fs::path(shared_dir_) / "game_state.json";
    std::ifstream file(state_path);
    if (!file.is_open()) {
        return;
    }

    try {
        json state;
        file >> state;
        current_state_ = std::move(state);
        if (current_state_.contains("tilemap")) {
            const json& tilemap = current_state_["tilemap"];
            tile_size_ = tilemap.value("tile_size", 32.0f);
            room_width_ = tilemap.value("width", 0);
            room_height_ = tilemap.value("height", 0);
        }
    } catch (const std::exception& e) {
        TraceLog(LOG_WARNING, "Failed to parse game_state.json: %s", e.what());
    }
}

void GameRenderer::HandleInput() {
    Vector2 move{0.0f, 0.0f};
    if (IsKeyDown(KEY_W)) move.y -= 1.0f;
    if (IsKeyDown(KEY_S)) move.y += 1.0f;
    if (IsKeyDown(KEY_A)) move.x -= 1.0f;
    if (IsKeyDown(KEY_D)) move.x += 1.0f;

    Vector2 attack{0.0f, 0.0f};
    if (IsKeyDown(KEY_UP)) attack.y -= 1.0f;
    if (IsKeyDown(KEY_DOWN)) attack.y += 1.0f;
    if (IsKeyDown(KEY_LEFT)) attack.x -= 1.0f;
    if (IsKeyDown(KEY_RIGHT)) attack.x += 1.0f;

    const bool bomb = IsKeyPressed(KEY_SPACE);
    const bool use_item = IsKeyPressed(KEY_E);
    const bool pause = IsKeyPressed(KEY_P);
    const bool quit = IsKeyPressed(KEY_ESCAPE);

    json input = json::object();
    input["move"] = { {"x", move.x}, {"y", move.y} };
    input["attack"] = { {"x", attack.x}, {"y", attack.y} };
    input["bomb"] = bomb;
    input["use_item"] = use_item;
    input["pause"] = pause;
    input["quit"] = quit;

    WriteInput(input);

    if (quit) {
        quit_requested_ = true;
    }
}

bool GameRenderer::ShouldClose() {
    if (WindowShouldClose()) {
        quit_requested_ = true;
        return true;
    }
    return quit_requested_;
}

void GameRenderer::SignalQuit() {
    json quit_payload = {
        {"move", { {"x", 0}, {"y", 0} }},
        {"attack", { {"x", 0}, {"y", 0} }},
        {"bomb", false},
        {"use_item", false},
        {"pause", false},
        {"quit", true}
    };
    WriteInput(quit_payload);
}

void GameRenderer::WriteInput(const json& input) {
    const fs::path input_path = fs::path(shared_dir_) / "input.json";
    std::ofstream file(input_path);
    if (!file.is_open()) {
        TraceLog(LOG_WARNING, "Unable to write input.json");
        return;
    }
    file << input.dump(2);
}

void GameRenderer::RenderFrame() {
    BeginDrawing();
    ClearBackground(Color{16, 16, 24, 255});

    DrawTilemap();
    DrawPickups();
    DrawActors();
    DrawProjectiles();
    DrawEffects();
    DrawHud();

    EndDrawing();
}

void GameRenderer::DrawTilemap() {
    if (!current_state_.contains("tilemap")) {
        return;
    }

    const json& tilemap = current_state_["tilemap"];
    if (!tilemap.contains("tiles")) {
        return;
    }

    const auto& tiles = tilemap["tiles"];
    const float offset_x = (GetScreenWidth() - room_width_ * tile_size_) * 0.5f;
    const float offset_y = (GetScreenHeight() - room_height_ * tile_size_) * 0.5f;

    for (size_t y = 0; y < tiles.size(); ++y) {
        const auto& row = tiles[y];
        for (size_t x = 0; x < row.size(); ++x) {
            std::string tile = row[x].get<std::string>();
            Rectangle rect{
                offset_x + static_cast<float>(x) * tile_size_,
                offset_y + static_cast<float>(y) * tile_size_,
                tile_size_,
                tile_size_
            };
            DrawRectangleRec(rect, TileFillColor(tile));
            Color outline = TileOutlineColor(tile);
            if (outline.a > 0) {
                DrawRectangleLinesEx(rect, 1.0f, outline);
            }
        }
    }
}

void GameRenderer::DrawPickups() {
    if (!current_state_.contains("pickups")) {
        return;
    }

    for (const json& pickup : current_state_["pickups"]) {
        const float x = pickup.value("x", 0.0f);
        const float y = pickup.value("y", 0.0f);
        const std::string kind = pickup.value("kind", std::string("coin"));
        Vector2 pos = WorldToScreen(x, y);
        DrawCircleV(pos, tile_size_ * 0.22f, PickupColor(kind));
    }
}

void GameRenderer::DrawActors() {
    if (!current_state_.contains("actors")) {
        return;
    }

    for (const json& actor : current_state_["actors"]) {
        const std::string type = actor.value("type", std::string("enemy"));
        const std::string variant = actor.value("variant", std::string("default"));
        const float x = actor.value("x", 0.0f);
        const float y = actor.value("y", 0.0f);
        Vector2 pos = WorldToScreen(x, y);

        if (type == "player") {
            Color fill = Color{120, 200, 255, 255};
            if (actor.value("invulnerable", false)) {
                fill = Color{255, 255, 180, 255};
            }
            DrawCircleV(pos, tile_size_ * 0.35f, fill);
            DrawCircleLines(pos.x, pos.y, tile_size_ * 0.35f, Color{30, 30, 60, 255});
        } else {
            Color fill = variant == "spitter" ? Color{220, 90, 90, 255} : Color{200, 120, 120, 255};
            DrawCircleV(pos, tile_size_ * 0.32f, fill);
            DrawCircleLines(pos.x, pos.y, tile_size_ * 0.32f, Color{60, 20, 20, 255});

            const int hp = actor.value("hp", 0);
            const int max_hp = std::max(1, actor.value("max_hp", 1));
            float bar_width = tile_size_ * 0.6f;
            Rectangle background{
                pos.x - bar_width / 2.0f,
                pos.y - tile_size_ * 0.5f,
                bar_width,
                4.0f
            };
            DrawRectangleRec(background, Color{30, 10, 10, 180});
            Rectangle foreground = background;
            foreground.width *= static_cast<float>(hp) / static_cast<float>(max_hp);
            DrawRectangleRec(foreground, Color{220, 40, 40, 200});
        }
    }
}

void GameRenderer::DrawProjectiles() {
    if (!current_state_.contains("projectiles")) {
        return;
    }

    for (const json& projectile : current_state_["projectiles"]) {
        const float x = projectile.value("x", 0.0f);
        const float y = projectile.value("y", 0.0f);
        const std::string owner = projectile.value("owner", std::string("player"));
        Vector2 pos = WorldToScreen(x, y);
        Color color = owner == "player" ? Color{150, 220, 255, 255} : Color{255, 150, 150, 255};
        DrawCircleV(pos, tile_size_ * 0.18f, color);
    }
}

void GameRenderer::DrawEffects() {
    if (!current_state_.contains("effects")) {
        return;
    }

    for (const json& effect : current_state_["effects"]) {
        const float x = effect.value("x", 0.0f);
        const float y = effect.value("y", 0.0f);
        const std::string kind = effect.value("kind", std::string("impact"));
        Vector2 pos = WorldToScreen(x, y);
        Color color = kind == "blood_splatter" ? Color{200, 40, 40, 180} : Color{220, 220, 255, 180};
        DrawCircleLines(pos.x, pos.y, tile_size_ * 0.28f, color);
    }
}

void GameRenderer::DrawHud() {
    DrawMessages();
    DrawBossHealth();

    if (!current_state_.contains("meta")) {
        return;
    }

    const json& meta = current_state_["meta"];
    const int hp = meta.value("player_hp", 0);
    const int max_hp = meta.value("player_max_hp", std::max(hp, 1));
    const int coins = meta.value("coins", 0);
    const int keys = meta.value("keys", 0);
    const int bombs = meta.value("bombs", 0);

    const float heart_size = 20.0f;
    const float start_x = 20.0f;
    const float start_y = 20.0f;

    for (int i = 0; i < max_hp; ++i) {
        Rectangle heart{
            start_x + i * (heart_size + 6.0f),
            start_y,
            heart_size,
            heart_size
        };
        Color fill = i < hp ? Color{220, 30, 60, 255} : Color{80, 40, 40, 255};
        DrawRectangleRec(heart, fill);
        DrawRectangleLinesEx(heart, 1.5f, Color{30, 10, 10, 255});
    }

    DrawText(TextFormat("Coins: %d  Keys: %d  Bombs: %d", coins, keys, bombs), 20, 50, 20, Color{235, 235, 235, 255});
}

void GameRenderer::DrawMessages() {
    if (!current_state_.contains("ui")) {
        return;
    }
    const json& ui = current_state_["ui"];
    if (!ui.contains("messages")) {
        return;
    }
    const auto& messages = ui["messages"];
    int y = GetScreenHeight() - 20;
    for (auto it = messages.rbegin(); it != messages.rend(); ++it) {
        const std::string text = it->get<std::string>();
        y -= 22;
        DrawText(text.c_str(), 20, y, 18, Color{230, 230, 230, 255});
    }
}

void GameRenderer::DrawBossHealth() {
    if (!current_state_.contains("ui")) {
        return;
    }
    const json& ui = current_state_["ui"];
    if (!ui.contains("boss_health") || ui["boss_health"].is_null()) {
        return;
    }
    const json& boss = ui["boss_health"];
    const int hp = boss.value("hp", 0);
    const int max_hp = std::max(1, boss.value("max_hp", 1));
    const std::string name = boss.value("name", std::string("Boss"));

    const float width = GetScreenWidth() * 0.4f;
    const float height = 18.0f;
    const float x = (GetScreenWidth() - width) * 0.5f;
    const float y = GetScreenHeight() - 60.0f;

    Rectangle bg{x, y, width, height};
    DrawRectangleRec(bg, Color{40, 10, 10, 200});

    Rectangle fg = bg;
    fg.width *= static_cast<float>(hp) / static_cast<float>(max_hp);
    DrawRectangleRec(fg, Color{200, 40, 40, 255});

    DrawText(name.c_str(), static_cast<int>(x), static_cast<int>(y - 22), 20, Color{240, 240, 240, 255});
}

Color GameRenderer::TileFillColor(const std::string& tile) const {
    static const std::unordered_map<std::string, Color> colors = {
        {"floor", Color{60, 52, 65, 255}},
        {"wall", Color{90, 92, 112, 255}},
        {"pit", Color{20, 20, 32, 255}},
        {"rock", Color{120, 120, 140, 255}},
        {"spikes", Color{110, 40, 40, 255}},
        {"door_up", Color{150, 120, 60, 255}},
        {"door_down", Color{150, 120, 60, 255}},
        {"door_left", Color{150, 120, 60, 255}},
        {"door_right", Color{150, 120, 60, 255}},
        {"special", Color{100, 50, 130, 255}},
    };
    const auto it = colors.find(tile);
    if (it != colors.end()) {
        return it->second;
    }
    return Color{50, 48, 60, 255};
}

Color GameRenderer::TileOutlineColor(const std::string& tile) const {
    static const std::unordered_map<std::string, Color> outlines = {
        {"wall", Color{15, 15, 25, 180}},
        {"rock", Color{30, 30, 40, 200}},
        {"spikes", Color{200, 40, 60, 255}},
        {"door_up", Color{240, 190, 90, 255}},
        {"door_down", Color{240, 190, 90, 255}},
        {"door_left", Color{240, 190, 90, 255}},
        {"door_right", Color{240, 190, 90, 255}},
        {"special", Color{200, 120, 255, 255}},
    };
    const auto it = outlines.find(tile);
    if (it != outlines.end()) {
        return it->second;
    }
    return Color{0, 0, 0, 0};
}

Color GameRenderer::PickupColor(const std::string& pickup) const {
    static const std::unordered_map<std::string, Color> colors = {
        {"heart", Color{220, 60, 80, 255}},
        {"coin", Color{230, 200, 80, 255}},
        {"key", Color{180, 180, 200, 255}},
        {"bomb", Color{90, 90, 90, 255}},
    };
    const auto it = colors.find(pickup);
    if (it != colors.end()) {
        return it->second;
    }
    return Color{220, 220, 220, 255};
}

Vector2 GameRenderer::WorldToScreen(float x, float y) const {
    const float offset_x = (GetScreenWidth() - room_width_ * tile_size_) * 0.5f;
    const float offset_y = (GetScreenHeight() - room_height_ * tile_size_) * 0.5f;
    return {
        offset_x + (x + 0.5f) * tile_size_,
        offset_y + (y + 0.5f) * tile_size_
    };
}