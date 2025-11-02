#pragma once
#include "raylib.h"

#include <nlohmann/json.hpp>
#include <string>

class GameRenderer {
public:
    void Initialize();
    void Shutdown();
    void UpdateFromPython();
    void HandleInput();
    void RenderFrame();
    bool ShouldClose();
    void SignalQuit();

private:
    nlohmann::json current_state_;
    std::string shared_dir_ = "shared";
    float tile_size_ = 32.0f;
    int room_width_ = 0;
    int room_height_ = 0;
    bool quit_requested_ = false;

    void EnsureSharedDirectory();
    void WriteInput(const nlohmann::json& input);
    void DrawTilemap();
    void DrawPickups();
    void DrawActors();
    void DrawProjectiles();
    void DrawEffects();
    void DrawHud();
    void DrawMessages();
    void DrawBossHealth();
    Color TileFillColor(const std::string& tile) const;
    Color TileOutlineColor(const std::string& tile) const;
    Color PickupColor(const std::string& pickup) const;
    Vector2 WorldToScreen(float x, float y) const;
};