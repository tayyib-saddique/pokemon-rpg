import pygame, sys
from settings import *
from level import Level


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Pokemon Mystery Dungeon Clone")
        self.clock = pygame.time.Clock()
        self.level = Level()

    def run(self):
        while True:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            dt = self.clock.tick() / 1000
            self.level.run(dt, events)
            pygame.display.update()


if __name__ == "__main__":
    game = Game()
    game.run()
