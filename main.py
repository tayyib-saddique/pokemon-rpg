import pygame
import sys
import pytmx
from constants.settings import *
from level import Level
from utils.transition import FadeTransition
from constants.world import ENTRY_POSITIONS
from constants.settings import SCALE


GAME_OVER_OVERLAY = (0, 0, 0, 160)
START_MAP = "vertia_road"
START_POS = (500, 500)


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Pokemon Mystery Dungeon Clone")
        self.clock = pygame.time.Clock()
        self.level = Level(START_MAP, START_POS)
        self.transition = FadeTransition((WIDTH, HEIGHT))
        self.game_over = False
        self._font_large = pygame.font.SysFont("monospace", 48, bold=True)
        self._font_small = pygame.font.SysFont("monospace", 20)

    def _do_transition(self, edge, map_name):
        old_player = self.level.player
        self.level.player.frozen = True
        self.transition.start(lambda: self._swap_map(edge, map_name, old_player))

    def _swap_map(self, edge, map_name, old_player):
        tmx_data = pytmx.load_pygame(f"graphics/floor_maps/{map_name}.tmx")
        map_w = tmx_data.width * tmx_data.tilewidth * SCALE
        map_h = tmx_data.height * tmx_data.tileheight * SCALE

        new_pos = ENTRY_POSITIONS[edge](old_player, map_w, map_h)
        self.level = Level(map_name, player_pos=new_pos)
        new_pos = ENTRY_POSITIONS[edge](
            old_player, self.level.map_width, self.level.map_height
        )
        self.level.player.rect.center = new_pos
        self.level.player.hitbox.center = new_pos

    def _restart(self):
        self.level = Level(START_MAP, START_POS)
        self.transition = FadeTransition((WIDTH, HEIGHT))
        self.game_over = False

    def _draw_game_over(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill(GAME_OVER_OVERLAY)
        self.screen.blit(overlay, (0, 0))

        title = self._font_large.render("YOU FAINTED", True, (255, 255, 255))
        prompt = self._font_small.render("Press R to try again", True, (200, 200, 200))

        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 24)))
        self.screen.blit(prompt, prompt.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 36)))

    def run(self):
        while True:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if self.game_over and event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self._restart()

            dt = self.clock.tick(60) / 1000

            self.level.run(dt, events)

            if not self.game_over and self.level.player.dead:
                self.game_over = True

            if self.game_over:
                self._draw_game_over()

            if self.level.pending_transition and not self.transition.active:
                edge, map_name = self.level.pending_transition
                self.level.pending_transition = None
                self._do_transition(edge, map_name)

            self.transition.update(dt)
            self.transition.draw(self.screen)
            pygame.display.flip()


if __name__ == "__main__":
    game = Game()
    game.run()
