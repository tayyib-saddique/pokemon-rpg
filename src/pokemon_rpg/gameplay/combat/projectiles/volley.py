import pygame

from pokemon_rpg.gameplay.combat.projectiles.base import BaseProjectile


class Volley(BaseProjectile):
    """Stationary emitter that fires a burst of independent shots.

    Each shot is its own BaseProjectile, so it collides, deals damage and
    expires on its own. The volley stays active while it is still firing and
    stays in its sprite groups until every shot has finished playing.
    """

    SHOT_CLASS = None
    SHOT_COUNT = 1
    SHOT_INTERVAL = 0.0  # seconds between shots
    # Heading offset (degrees) for each shot, cycled if shorter than SHOT_COUNT
    SPREAD = (0,)

    def __init__(self, origin_x, origin_y, facing, **kwargs):
        super().__init__(origin_x, origin_y, facing, **kwargs)

        self._shot_kwargs = {
            "map_size": (self.map_width, self.map_height),
            "max_range": self.max_range,
            "collision_sprites": self.collision_sprites,
            "combat_sprites": self.combat_sprites,
        }
        self.shots: list[BaseProjectile] = []
        self._fired = 0
        # Primed so the first shot leaves on the first frame
        self._timer = self.SHOT_INTERVAL

        self.rect = pygame.Rect(0, 0, 20, 20)
        self.rect.center = self.pos

    def _advance(self, dt):
        self._timer += dt
        while self._fired < self.SHOT_COUNT and self._timer >= self.SHOT_INTERVAL:
            self._timer -= self.SHOT_INTERVAL
            self._fire(self._fired)
            self._fired += 1
        if self._fired >= self.SHOT_COUNT:
            self._deactivate()

    def _fire(self, index):
        shot = self.SHOT_CLASS(
            self.pos.x,
            self.pos.y,
            self.facing,
            spread=self.SPREAD[index % len(self.SPREAD)],
            index=index,
            **self._shot_kwargs,
        )
        shot.volley = self
        self.shots.append(shot)

    def depth_parts(self):
        """Shots the camera should depth-sort individually.

        Each shot keeps its own overlay flag and ground_y as it flies, so it
        layers correctly against sprites it passes instead of staying at the
        volley's spawn point.
        """
        return list(self.shots)

    def update_effects(self, dt):
        for shot in self.shots:
            shot.update(dt)
        self.shots = [s for s in self.shots if s.active or s.has_effects()]

    def has_effects(self):
        return bool(self.shots)

    def draw(self, surface, offset=(0, 0)):
        for shot in self.shots:
            shot.draw(surface, offset)
