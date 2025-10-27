#pragma once
#include "raylib.h"

struct GameState {
    float ball_x, ball_y;
    float ball_speed_x, ball_speed_y;
    float player1_y, player2_y;
    int player1_score, player2_score;
    bool game_running;
};

class GameRenderer {
public:
    void Initialize();
    void Shutdown();
    void UpdateFromPython();  // Читает game_state.json
    void HandleInput();       // Отправляет ввод в Python
    void RenderFrame();

private:
    GameState current_state;
};