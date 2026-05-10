import math
import time
from typing import Tuple, List
from utils.pathfinding import NavGrid

WorldPos = Tuple[float, float]


class Enemy:
    def __init__(self, pos: WorldPos, nav_grid: NavGrid, speed: float = 120):
        self.pos = list(pos)
        self.nav = nav_grid
        self.speed = speed

        self.path: List[WorldPos] = []
        self.target = None

        self.last_repath = 0
        self.repath_delay = 0.4  # seconds

    def update(self, player_pos: WorldPos, dt: float):
        now = time.time()

        # -------------------------
        # Repath only if needed
        # -------------------------
        if (
            now - self.last_repath > self.repath_delay
            or not self.path
            or self._target_moved(player_pos)
        ):
            self.path = self.nav.find_path(self.pos, player_pos)
            self.target = player_pos
            self.last_repath = now

        # -------------------------
        # Move along path
        # -------------------------
        self._follow_path(dt)

    def _follow_path(self, dt: float):
        if not self.path:
            return

        tx, ty = self.path[0]

        dx = tx - self.pos[0]
        dy = ty - self.pos[1]
        dist = math.hypot(dx, dy)

        if dist < 4:
            self.pos = [tx, ty]
            self.path.pop(0)
            return

        self.pos[0] += (dx / dist) * self.speed * dt
        self.pos[1] += (dy / dist) * self.speed * dt

    def _target_moved(self, player_pos: WorldPos) -> bool:
        if self.target is None:
            return True
        return (
            math.hypot(
                player_pos[0] - self.target[0],
                player_pos[1] - self.target[1],
            )
            > 32
        )
