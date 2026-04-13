"""
stress_test.py
==============
Stress test: Totodile fires Bubble Beam projectiles.

Controls
--------
  Arrow keys  — move
  Z           — fire Bubble Beam (single shot)
  HOLD Z      — rapid-fire stress mode (auto-fire every 120 ms)
  ESC         — quit

Stress metrics shown on screen:
  • Active projectile count
  • Total fired this session
  • Current FPS
"""

import pygame
import math
import random
from constants.settings import WIDTH, HEIGHT, FPS
from player import Player

B_RIM = (160, 220, 255)  # main rim colour
B_SHINE = (230, 248, 255)  # specular dot
B_INNER = (80, 160, 240)  # faint inner fill tint
B_IRID = [  # iridescent rim accent colours (cycled per bubble)
    (180, 200, 255),
    (200, 180, 255),
    (160, 240, 220),
    (200, 230, 255),
]

FACING_VELOCITY = {
    "down": (0, 1),
    "up": (0, -1),
    "left": (1, 0),
    "right": (-1, 0),
    "down_right": (-0.707, 0.707),
    "down_left": (0.707, 0.707),
    "up_right": (-0.707, -0.707),
    "up_left": (0.707, -0.707),
}


def draw_bubble(surface, cx, cy, r, irid_index=0, alpha_scale=1.0):
    """
    Draw a single translucent bubble directly onto `surface`.
    Uses only pygame.draw — no per-call Surface allocation.
    Simulates translucency by blending colours toward the background manually.

    cx, cy  — centre in screen coords
    r       — radius in pixels
    irid_index — which iridescent accent to use (cycles 0-3)
    alpha_scale — 0.0 (invisible) .. 1.0 (full)
    """
    if r < 1 or alpha_scale <= 0:
        return

    bg = (18, 22, 30)  # must match screen fill colour

    def blend(c, a):
        return (
            int(c[0] * a + bg[0] * (1 - a)),
            int(c[1] * a + bg[1] * (1 - a)),
            int(c[2] * a + bg[2] * (1 - a)),
        )

    # Faint inner fill (gives a "glass sphere" look)
    fill_a = 0.12 * alpha_scale
    pygame.draw.circle(surface, blend(B_INNER, fill_a), (cx, cy), r)

    # Outer rim — one or two concentric circles
    rim_a = 0.75 * alpha_scale
    pygame.draw.circle(surface, blend(B_RIM, rim_a), (cx, cy), r, 2)
    if r > 5:
        irid = B_IRID[irid_index % len(B_IRID)]
        pygame.draw.circle(surface, blend(irid, rim_a * 0.6), (cx, cy), r - 1, 1)

    # Specular highlight — top-left arc (just two small circles)
    if r >= 3:
        hx = cx - r // 3
        hy = cy - r // 3
        hr = max(1, r // 4)
        pygame.draw.circle(surface, blend(B_SHINE, 0.9 * alpha_scale), (hx, hy), hr)
        if r >= 6:
            pygame.draw.circle(
                surface,
                blend(B_SHINE, 0.5 * alpha_scale),
                (hx + 2, hy + 2),
                max(1, hr - 1),
            )


class TrailBubble:
    """A single bubble left in the wake of the projectile."""

    def __init__(self, x, y, vx_base, vy_base, irid_index):
        self.x = float(x)
        self.y = float(y)
        # Drift: slight random perpendicular wobble + slow forward momentum
        perp_angle = math.atan2(vy_base, vx_base) + math.pi / 2
        drift_mag = random.uniform(5, 25)
        side = random.choice((-1, 1))
        self.vx = math.cos(perp_angle) * drift_mag * side + vx_base * 0.04
        self.vy = math.sin(perp_angle) * drift_mag * side + vy_base * 0.04
        self.r = random.randint(3, 7)
        self.life = random.uniform(0.25, 0.55)
        self.max_life = self.life
        self.irid = irid_index
        # Gentle wobble oscillation
        self.wobble_phase = random.uniform(0, math.pi * 2)
        self.wobble_speed = random.uniform(3, 6)

    def update(self, dt):
        self.wobble_phase += self.wobble_speed * dt
        wobble = math.sin(self.wobble_phase) * 0.4
        self.x += (self.vx + wobble) * dt
        self.y += (self.vy + wobble * 0.5) * dt
        self.life -= dt

    @property
    def alive(self):
        return self.life > 0

    def draw(self, surface):
        a = max(0.0, self.life / self.max_life)
        draw_bubble(surface, int(self.x), int(self.y), self.r, self.irid, a)


class BubbleBeamProjectile:
    SPEED = 340  # bubbles travel a bit slower than a water jet
    TRAIL_INTERVAL = 0.04  # seconds between spawning trail bubbles
    HEAD_RADII = [9, 6, 4]  # cluster of 3 bubbles at the head
    HEAD_OFFSETS = [  # (dx, dy) offsets from centre for each head bubble
        (0, 0),
        (6, -5),
        (-5, 5),
    ]
    FRAME_SPEED = 2.5  # head wobble speed (radians/sec)

    def __init__(self, origin_x, origin_y, facing):
        self.facing = facing
        vx, vy = FACING_VELOCITY.get(facing, (0, 1))
        self.vx = vx * self.SPEED
        self.vy = vy * self.SPEED

        self.x = float(origin_x)
        self.y = float(origin_y)

        self.alive = True
        self.trail: list[TrailBubble] = []
        self._trail_timer = 0.0
        self._irid_cycle = 0
        self._wobble = 0.0  # head wobble accumulator

    def _spawn_trail(self):
        self._irid_cycle = (self._irid_cycle + 1) % len(B_IRID)
        # Spawn 1-2 trail bubbles slightly behind the head
        for _ in range(random.randint(1, 2)):
            ox = random.uniform(-4, 4)
            oy = random.uniform(-4, 4)
            self.trail.append(
                TrailBubble(
                    self.x + ox, self.y + oy, self.vx, self.vy, self._irid_cycle
                )
            )

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self._wobble += self.FRAME_SPEED * dt

        self._trail_timer += dt
        if self._trail_timer >= self.TRAIL_INTERVAL:
            self._trail_timer = 0.0
            self._spawn_trail()

        for b in self.trail:
            b.update(dt)
        self.trail = [b for b in self.trail if b.alive]

        if self.x > WIDTH + 80 or self.x < -80 or self.y > HEIGHT + 80 or self.y < -80:
            self.alive = False

    def draw(self, surface):
        # Trail bubbles drawn first (behind head)
        for b in self.trail:
            b.draw(surface)

        # Head cluster — 3 bubbles with a gentle wobble offset
        for i, (base_dx, base_dy) in enumerate(self.HEAD_OFFSETS):
            r = self.HEAD_RADII[i]
            # Wobble each bubble slightly independently
            phase = self._wobble + i * (math.pi * 2 / 3)
            wdx = math.cos(phase) * 1.5
            wdy = math.sin(phase) * 1.5
            cx = int(self.x + base_dx + wdx)
            cy = int(self.y + base_dy + wdy)
            irid = (self._irid_cycle + i) % len(B_IRID)
            draw_bubble(surface, cx, cy, r, irid, 1.0)


class HUD:
    def __init__(self):
        self.font_small = pygame.font.SysFont(None, 22)
        self.total_fired = 0
        self._fps_samples: list = []

    def record_shot(self):
        self.total_fired += 1

    def update_fps(self, fps):
        self._fps_samples.append(fps)
        if len(self._fps_samples) > 60:
            self._fps_samples.pop(0)

    @property
    def avg_fps(self):
        return sum(self._fps_samples) / max(1, len(self._fps_samples))

    def draw(self, surface, active_count, current_fps):
        lines = [
            f"FPS:          {current_fps:5.1f}  (avg {self.avg_fps:5.1f})",
            f"Active shots: {active_count}",
            f"Total fired:  {self.total_fired}",
            "",
            "Z = fire  (hold = rapid-fire stress)",
            "Arrows = move   ESC = quit",
        ]
        pad = 10
        for i, line in enumerate(lines):
            color = (255, 220, 80) if i == 0 else (200, 200, 200)
            surf = self.font_small.render(line, True, color)
            surface.blit(surf, (pad, pad + i * 20))


def run():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Totodile - Bubble Beam Stress Test")
    clock = pygame.time.Clock()

    all_sprites = pygame.sprite.Group()
    player = Player(
        (WIDTH // 2, HEIGHT // 2), all_sprites, lambda *args: None, pokemon="totodile"
    )

    projectiles: list[BubbleBeamProjectile] = []
    hud = HUD()

    RAPID_FIRE_INTERVAL = 120
    last_fire_time = 0

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        current_fps = clock.get_fps()
        hud.update_fps(current_fps)

        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        keys = pygame.key.get_pressed()
        now = pygame.time.get_ticks()
        if keys[pygame.K_z]:
            if now - last_fire_time >= RAPID_FIRE_INTERVAL:
                facing = player.get_facing()
                cx, cy = player.rect.center
                projectiles.append(BubbleBeamProjectile(cx, cy, facing))
                hud.record_shot()
                last_fire_time = now

        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_z:
                facing = player.get_facing()
                cx, cy = player.rect.center
                projectiles.append(BubbleBeamProjectile(cx, cy, facing))
                hud.record_shot()
                last_fire_time = now

        player.update(dt, events)
        for p in projectiles:
            p.update(dt)
        projectiles = [p for p in projectiles if p.alive]

        screen.fill((18, 22, 30))

        grid_color = (30, 36, 48)
        for gx in range(0, WIDTH, 64):
            pygame.draw.line(screen, grid_color, (gx, 0), (gx, HEIGHT))
        for gy in range(0, HEIGHT, 64):
            pygame.draw.line(screen, grid_color, (0, gy), (WIDTH, gy))

        for p in projectiles:
            p.draw(screen)

        all_sprites.draw(screen)

        facing = player.get_facing()
        vx, vy = FACING_VELOCITY.get(facing, (0, 1))
        VISUAL_OFFSET_X = 5
        px, py = player.rect.centerx + VISUAL_OFFSET_X, player.rect.centery
        arrow_end = (px + int(vx * 30), py + int(vy * 30))
        pygame.draw.line(screen, (255, 255, 100), (px, py), arrow_end, 2)
        pygame.draw.circle(screen, (255, 255, 100), arrow_end, 4)

        hud.draw(screen, len(projectiles), current_fps)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    run()
