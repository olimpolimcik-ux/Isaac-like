#include "game_renderer.h"
#include <fstream>
#include <nlohmann/json.hpp>  // Простая JSON библиотека

using json = nlohmann::json;

void GameRenderer::Initialize() {
    InitWindow(800, 600, "Pong C++/Python");
    SetTargetFPS(60);
}

void GameRenderer::UpdateFromPython() {
    // Читаем состояние игры из JSON (созданного Python)
    std::ifstream file("../shared/game_state.json");
    if (file) {
        json j;
        file >> j;

        current_state.ball_x = j["ball_x"];
        current_state.ball_y = j["ball_y"];
        current_state.ball_speed_x = j["ball_speed_x"];
        current_state.ball_speed_y = j["ball_speed_y"];
        current_state.player1_y = j["player1_y"];
        current_state.player2_y = j["player2_y"];
        current_state.player1_score = j["player1_score"];
        current_state.player2_score = j["player2_score"];
        current_state.game_running = j["game_running"];
    }
}

void GameRenderer::HandleInput() {
    // Записываем ввод в JSON для Python
    json input;
    input["player1_up"] = IsKeyDown(KEY_W);
    input["player1_down"] = IsKeyDown(KEY_S);
    input["player2_up"] = IsKeyDown(KEY_UP);
    input["player2_down"] = IsKeyDown(KEY_DOWN);
    input["pause"] = IsKeyPressed(KEY_SPACE);

    std::ofstream file("../shared/input.json");
    file << input.dump(4);
}

void GameRenderer::RenderFrame() {
    BeginDrawing();
    ClearBackground(BLACK);

    // Ракетки
    DrawRectangle(50, current_state.player1_y - 50, 10, 100, WHITE);
    DrawRectangle(740, current_state.player2_y - 50, 10, 100, WHITE);

    // Мяч
    DrawCircle(current_state.ball_x, current_state.ball_y, 5, WHITE);

    // Счет
    DrawText(TextFormat("%d", current_state.player1_score), 200, 50, 30, WHITE);
    DrawText(TextFormat("%d", current_state.player2_score), 600, 50, 30, WHITE);

    EndDrawing();
}

void GameRenderer::Shutdown() {
    CloseWindow();
}