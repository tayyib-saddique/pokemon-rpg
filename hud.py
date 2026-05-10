import pygame

BAR_W = 200
BAR_H = 18
PADDING = 20
BORDER = 2

BOSS_BAR_W = 500
BOSS_BAR_H = 22
BOSS_BAR_PADDING = 60  # distance from bottom of screen


class HUD:
    def __init__(self):
        self.surface = pygame.display.get_surface()
        self.font = pygame.font.SysFont("monospace", 13, bold=True)
        self.boss_font = pygame.font.SysFont("monospace", 13, bold=True)

    def draw(self, player, enemies=None, camera_offset=None):
        if enemies and camera_offset is not None:
            regular = [e for e in enemies if not e.is_boss]
            bosses = [e for e in enemies if e.is_boss]
            if regular:
                self._draw_enemy_bars(regular, camera_offset)
            for boss in bosses:
                self._draw_boss_bar(boss)

        sw, sh = self.surface.get_size()
        x = PADDING
        y = sh - PADDING - BAR_H

        ratio = player.health.ratio
        fill_w = int(BAR_W * ratio)

        pygame.draw.rect(
            self.surface,
            (10, 10, 10),
            (x - BORDER, y - BORDER, BAR_W + BORDER * 2, BAR_H + BORDER * 2),
            border_radius=4,
        )
        pygame.draw.rect(
            self.surface, (40, 40, 40), (x, y, BAR_W, BAR_H), border_radius=3
        )
        if fill_w > 0:
            pygame.draw.rect(
                self.surface,
                self._hp_colour(ratio),
                (x, y, fill_w, BAR_H),
                border_radius=3,
            )

        text = self.font.render(
            f"{player.pokemon.capitalize()}  {player.health.current}/{player.health.max_hp}",
            True,
            (255, 255, 255),
        )
        self.surface.blit(text, (x + 6, y + BAR_H // 2 - text.get_height() // 2))

    def _draw_enemy_bars(self, enemies, camera_offset):
        enemy_bar_h = 4
        gap = 6
        border = 1
        for enemy in enemies:
            bar_w = enemy.rect.width
            sx = int(enemy.rect.x - camera_offset.x)
            sy = int(enemy.rect.y - camera_offset.y) - gap - enemy_bar_h
            pygame.draw.rect(
                self.surface,
                (10, 10, 10),
                (
                    sx - border,
                    sy - border,
                    bar_w + border * 2,
                    enemy_bar_h + border * 2,
                ),
            )
            pygame.draw.rect(self.surface, (40, 40, 40), (sx, sy, bar_w, enemy_bar_h))
            fill_w = int(bar_w * enemy.health.ratio)
            if fill_w > 0:
                pygame.draw.rect(
                    self.surface,
                    self._hp_colour(enemy.health.ratio),
                    (sx, sy, fill_w, enemy_bar_h),
                )

    def _draw_boss_bar(self, boss):
        sw, sh = self.surface.get_size()
        x = (sw - BOSS_BAR_W) // 2
        y = sh - BOSS_BAR_PADDING - BOSS_BAR_H

        ratio = boss.health.ratio
        fill_w = int(BOSS_BAR_W * ratio)

        # Label above the bar
        label = self.boss_font.render(
            f"{boss.pokemon.capitalize()}  {boss.health.current}/{boss.health.max_hp}",
            True,
            (255, 220, 220),
        )
        self.surface.blit(label, (x, y - label.get_height() - 4))

        pygame.draw.rect(
            self.surface,
            (10, 10, 10),
            (x - BORDER, y - BORDER, BOSS_BAR_W + BORDER * 2, BOSS_BAR_H + BORDER * 2),
            border_radius=4,
        )
        pygame.draw.rect(
            self.surface, (40, 40, 40), (x, y, BOSS_BAR_W, BOSS_BAR_H), border_radius=3
        )
        if fill_w > 0:
            pygame.draw.rect(
                self.surface,
                self._hp_colour(ratio),
                (x, y, fill_w, BOSS_BAR_H),
                border_radius=3,
            )

    @staticmethod
    def _hp_colour(ratio):
        if ratio > 0.5:
            return (60, 200, 80)
        if ratio > 0.1:
            return (220, 180, 0)
        return (220, 50, 50)
