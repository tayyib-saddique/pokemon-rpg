import pygame

BAR_W   = 200
BAR_H   = 18
PADDING = 20
BORDER  = 2

class HUD:
    def __init__(self):
        self.surface = pygame.display.get_surface()
        self.font    = pygame.font.SysFont('monospace', 13, bold=True)

    def draw(self, player):
        sw, sh = self.surface.get_size()
        x = PADDING
        y = sh - PADDING - BAR_H

        ratio  = player.health.ratio
        fill_w = int(BAR_W * ratio)

        pygame.draw.rect(self.surface, (10, 10, 10),
                         (x - BORDER, y - BORDER,
                          BAR_W + BORDER * 2, BAR_H + BORDER * 2), border_radius=4)

        pygame.draw.rect(self.surface, (40, 40, 40),
                         (x, y, BAR_W, BAR_H), border_radius=3)

        if fill_w > 0:
            pygame.draw.rect(self.surface, self._hp_colour(ratio),
                             (x, y, fill_w, BAR_H), border_radius=3)

        text = self.font.render(
            f'{player.pokemon.capitalize()}  {player.health.current}/{player.health.max_hp}',
            True, (255, 255, 255)
        )
        self.surface.blit(text, (x + 6, y + BAR_H // 2 - text.get_height() // 2))

    @staticmethod
    def _hp_colour(ratio):
        if ratio > 0.5: return (60,  200,  80)
        if ratio > 0.1: return (220, 180,   0)
        return                 (220,  50,  50)