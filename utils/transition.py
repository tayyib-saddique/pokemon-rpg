import pygame


class FadeTransition:
    SPEED = 300  # alpha per second

    def __init__(self, screen_size):
        self._surface = pygame.Surface(screen_size)
        self._surface.fill((0, 0, 0))
        self._alpha = 0
        self._dir = 1
        self.active = False
        self.on_midpoint = None  # called once when fully black

    def start(self, on_midpoint):
        self.active = True
        self._alpha = 0
        self._dir = 1
        self.on_midpoint = on_midpoint

    def update(self, dt):
        if not self.active:
            return

        self._alpha += self.SPEED * dt * self._dir

        if self._dir == 1 and self._alpha >= 255:
            self._alpha = 255
            self._dir = -1
            if self.on_midpoint:
                self.on_midpoint()

        elif self._dir == -1 and self._alpha <= 0:
            self._alpha = 0
            self.active = False

    def draw(self, surface):
        if not self.active:
            return
        self._surface.set_alpha(int(self._alpha))
        surface.blit(self._surface, (0, 0))
