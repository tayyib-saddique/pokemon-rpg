import pygame
import math
import random
from projectiles.base import BaseProjectile

B_RIM = (160, 220, 255)
B_SHINE = (230, 248, 255)
B_INNER = (80, 160, 240)
B_MID = (120, 190, 255)
B_IRID = [
    (180, 200, 255),
    (200, 180, 255),
    (160, 240, 220),
    (200, 230, 255),
]

GRAVITY = 25  # pixels/s^2 — gentle arc so beam still feels directional


def draw_pixel_bubble(surface, cx, cy, r, color=B_RIM):
    """Crisp pixel-art bubble: hard circle outline + highlight pixel."""
    if r < 2:
        pygame.draw.rect(surface, color, (cx, cy, 2, 2))
        return
    pygame.draw.circle(surface, color, (cx, cy), r, 2)
    if r >= 5:
        pygame.draw.rect(surface, B_INNER, (cx - 1, cy - 1, 2, 2))
    # Highlight in upper-left quadrant
    hx = cx - max(1, r // 3)
    hy = cy - max(1, r // 3)
    pygame.draw.rect(surface, B_SHINE, (hx, hy, 2, 2))


class StreamBubble:
    """Beam segment: spawned at head, drifts forward slowly so it forms a tail in the beam path."""

    def __init__(self, x, y, beam_vx, beam_vy, irid_index):
        self.x, self.y = float(x), float(y)

        # Travel mostly forward at ~25 % of beam speed so the head pulls ahead
        # and these form a dense chain behind it
        fwd_frac = random.uniform(0.20, 0.30)
        self.vx = beam_vx * fwd_frac
        self.vy = beam_vy * fwd_frac

        # Tiny perpendicular wobble keeps things from looking perfectly rigid
        perp = math.atan2(beam_vy, beam_vx) + math.pi / 2
        side = random.uniform(-6, 6)
        self.vx += math.cos(perp) * side
        self.vy += math.sin(perp) * side

        self.r = random.randint(3, 6)
        self.life = random.uniform(0.22, 0.40)
        self.max_life = self.life
        self.irid = irid_index

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    @property
    def active(self):
        return self.life > 0

    def draw(self, surface, offset=(0, 0)):
        if self.life <= 0:
            return
        t = self.life / self.max_life
        # Shrink as it fades — pixel rect for older/smaller bubbles, circle for larger
        r = max(2, int(self.r * t + 0.5))
        color = B_IRID[self.irid % len(B_IRID)]
        cx = int(self.x - offset[0])
        cy = int(self.y - offset[1])
        if r <= 3:
            # Tiny pixel square
            pygame.draw.rect(surface, color, (cx - r // 2, cy - r // 2, r, r))
        else:
            draw_pixel_bubble(surface, cx, cy, r, color)


class BubbleBeam(BaseProjectile):
    # High emit rate so bubbles overlap and read as a continuous beam
    TRAIL_INTERVAL = 0.018
    BUBBLES_PER_EMIT = 2

    HEAD_RADII = [9, 6]
    HEAD_OFFSETS = [(0, 0), (-3, 3)]

    def __init__(self, origin_x, origin_y, facing, **kwargs):
        super().__init__(origin_x, origin_y, facing, speed=340, **kwargs)

        self.stream: list[StreamBubble] = []
        self._trail_timer = 0.0
        self._irid_cycle = 0

        self.rect = pygame.Rect(0, 0, 18, 18)
        self.rect.center = self.pos

    def _emit(self):
        self._irid_cycle = (self._irid_cycle + 1) % len(B_IRID)
        for _ in range(self.BUBBLES_PER_EMIT):
            self.stream.append(
                StreamBubble(
                    self.pos.x + random.randint(-2, 2),
                    self.pos.y + random.randint(-2, 2),
                    self.velocity.x,
                    self.velocity.y,
                    self._irid_cycle,
                )
            )

    def update(self, dt, *args, **kwargs):
        # Gravity arc — water beam should curve slightly downward
        self.velocity.y += GRAVITY * dt

        super().update(dt)
        self.rect.center = self.pos

        self._trail_timer += dt
        if self._trail_timer >= self.TRAIL_INTERVAL:
            self._trail_timer = 0.0
            self._emit()

        for b in self.stream:
            b.update(dt)
        self.stream = [b for b in self.stream if b.active]

    def draw(self, surface, offset=(0, 0)):
        # Stream drawn first (behind head)
        for b in self.stream:
            b.draw(surface, offset)

        # Head: two hard pixel circles
        for i, (dx, dy) in enumerate(self.HEAD_OFFSETS):
            r = self.HEAD_RADII[i]
            cx = int(self.pos.x - offset[0] + dx)
            cy = int(self.pos.y - offset[1] + dy)
            irid = (self._irid_cycle + i) % len(B_IRID)
            draw_pixel_bubble(surface, cx, cy, r, B_IRID[irid])
