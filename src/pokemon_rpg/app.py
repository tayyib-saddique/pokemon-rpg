import sys

import pygame

from pokemon_rpg.rendering.transition import FadeTransition
from pokemon_rpg.settings import HEIGHT, WIDTH
from pokemon_rpg.world.level import Level


GAME_OVER_OVERLAY = (0, 0, 0, 160)
START_MAP = "vertia_city"
START_POS = (500, 500)
DOOR_RETRIGGER_COOLDOWN_MS = 1500


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

    def _do_transition(self, edge, connection):
        self.level.player.frozen = True

        if edge == "door" and connection is None:
            self.transition.start(self._end_dead_door_transition)
            return

        self.transition.start(lambda: self._swap_map(connection))

    def _end_dead_door_transition(self):
        self.level.player.frozen = False
        self.level.door_cooldown_until = (
            pygame.time.get_ticks() + DOOR_RETRIGGER_COOLDOWN_MS
        )

    def _swap_map(self, connection):
        self.level = Level(connection["map"], player_pos=connection["entry_pos"])

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
                edge, connection = self.level.pending_transition
                self.level.pending_transition = None
                self._do_transition(edge, connection)

            self.transition.update(dt)
            self.transition.draw(self.screen)
            pygame.display.flip()


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
