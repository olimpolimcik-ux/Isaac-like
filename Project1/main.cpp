#include "game_renderer.h"

int main() {
    GameRenderer renderer;
    renderer.Initialize();

    while (!WindowShouldClose()) {
        renderer.HandleInput();     // → пишет input.json
        renderer.UpdateFromPython(); // ← читает game_state.json  
        renderer.RenderFrame();
    }

    renderer.Shutdown();
    return 0;
}