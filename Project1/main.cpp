#include "game_renderer.h"

int main() {
    GameRenderer renderer;
    renderer.Initialize();

    while (true) {
        renderer.UpdateFromPython();
        renderer.HandleInput();
        renderer.RenderFrame();

        if (renderer.ShouldClose()) {
            break;
        }
    }

    renderer.SignalQuit();
    renderer.Shutdown();
    return 0;
}