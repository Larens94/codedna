"""run_game.py — Quick launcher for condition A game using PygameRenderer."""
import sys
import pygame
pygame.init()
import logging
logging.basicConfig(level=logging.INFO, format='%(name)s: %(message)s')

sys.path.insert(0, '.')

# Patch render module to expose PygameRenderer as Renderer
import render.pygame_renderer as _pr
import render as _render_mod
_render_mod.Renderer = _pr.PygameRenderer

# Patch Game to use pygame event loop for window_should_close
from render.pygame_renderer import PygameRenderer

class PatchedRenderer(PygameRenderer):
    def window_should_close(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return True
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return True
        return False
    def set_window_should_close(self, val):
        pass

_render_mod.Renderer = PatchedRenderer

from gameplay.game import Game

def main():
    game = Game()
    if not game.initialize():
        print("Init failed — check logs above")
        return

    print("Game running — press ESC or close window to quit")
    clock = pygame.time.Clock()
    while True:
        if not game.update():
            break
        game.render()
        clock.tick(60)

    game.shutdown()
    pygame.quit()

if __name__ == "__main__":
    main()
