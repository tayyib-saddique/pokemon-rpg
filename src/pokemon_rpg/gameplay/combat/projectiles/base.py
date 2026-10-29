import pygame

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

_UP_FACINGS = {"up", "up_left", "up_right"}


def hit_rect(sprite):
    """The rect damage is tested against: hitbox if the sprite has one."""
    return getattr(sprite, "hitbox", sprite.rect)


class BaseProjectile(pygame.sprite.Sprite):
    MAX_RANGE = 400
    # seconds the caster freezes when projectile is fired; overrided per subclass
    FREEZE_DURATION = 0.10
    # TODO: replace flat damage with formula (type effectiveness, attack/defence stats)
    DAMAGE = 10

    def __init__(
        self,
        origin_x,
        origin_y,
        facing,
        speed=300,
        map_size=(1440, 1440),
        max_range=400,
        collision_sprites=None,
        combat_sprites=None,
    ):

        # Initialize the Sprite parent class
        super().__init__()

        self.facing = facing
        self.pos = pygame.math.Vector2(origin_x, origin_y)
        self._origin = pygame.math.Vector2(origin_x, origin_y)
        vx, vy = FACING_VELOCITY.get(facing, (0, 1))
        self.velocity = pygame.math.Vector2(vx * speed, vy * speed)

        if self.velocity.length() > 0:
            self.velocity = self.velocity.normalize() * speed

        self.collision_sprites = collision_sprites or []
        self.combat_sprites = combat_sprites or []
        # active = the projectile can still move and hit things. Once inactive
        # it stays in its sprite groups until has_effects() is False, so
        # trails and impact bursts can finish playing.
        self.active = True
        self.map_width, self.map_height = map_size
        self.max_range = max_range

        # Up-facing projectiles render in the depth pass (behind the player).
        # All others render in the overlay pass (in front of everything).
        self.overlay = facing not in _UP_FACINGS
        self.ground_y = origin_y  # updated each frame for depth sorting

        # Walls we already overlap at spawn — the projectile rect can clip into
        # a neighbouring wall tile when fired from a sprite's mouth, and we
        # don't want to die instantly. Populated lazily on the first update
        # because subclasses build self.rect after super().__init__.
        self._spawn_ignore = None

    def update(self, dt, *args, **kwargs):
        if self.active:
            self._advance(dt)
        self.update_effects(dt)
        if not self.active and not self.has_effects():
            self.kill()

    def _advance(self, dt):
        """Move and resolve collisions. Only called while active."""
        self.pos += self.velocity * dt

        if hasattr(self, "rect"):
            self.rect.center = (round(self.pos.x), round(self.pos.y))
            if not self.overlay:
                self.ground_y = self.rect.bottom

            hitbox = getattr(self, "hitbox", self.rect)
            hitbox.center = self.rect.center

            if self._spawn_ignore is None:
                # Only ignore walls clipped from the side or behind; a wall
                # directly ahead (firing point-blank) must still block.
                self._spawn_ignore = {
                    s
                    for s in self.collision_sprites
                    if hitbox.colliderect(s.rect) and not self._is_ahead(hitbox, s.rect)
                }

            for sprite in self.collision_sprites:
                overlapping = hitbox.colliderect(sprite.rect)
                if sprite in self._spawn_ignore:
                    if not overlapping:
                        self._spawn_ignore.discard(sprite)
                    continue
                if overlapping:
                    self.on_collision()
                    self._deactivate()
                    return

            for sprite in self.combat_sprites:
                if hitbox.colliderect(hit_rect(sprite)):
                    self.on_hit(sprite)
                    self._deactivate()
                    return

        if self._origin.distance_to(self.pos) > self.max_range:
            self._deactivate()
            return

        if not (
            0 <= self.pos.x <= self.map_width and 0 <= self.pos.y <= self.map_height
        ):
            self._deactivate()

    def _is_ahead(self, hitbox, wall_rect):
        """True if the overlap with wall_rect sits on the leading edge of travel."""
        if self.velocity.length_squared() == 0:
            return True
        overlap = hitbox.clip(wall_rect)
        offset = pygame.math.Vector2(overlap.center) - hitbox.center
        d = self.velocity.normalize()
        along = offset.dot(d)
        lateral = abs(offset.x * d.y - offset.y * d.x)
        return along > lateral

    def _deactivate(self):
        if self.active:
            self.active = False
            self.on_deactivate()

    def update_effects(self, dt):
        """Advance particles/trails. Called every frame, active or not."""

    def has_effects(self):
        """True while visual effects are still playing after deactivation."""
        return False

    def on_deactivate(self):
        """Called once when the projectile stops (hit, wall, range or map edge)."""

    def on_collision(self):
        """Override this in subclasses for explosion animations or sounds."""

    def on_hit(self, target):
        """Called when the projectile hits a combat sprite. Override to deal damage."""
        if hasattr(target, "take_damage"):
            # Shots from one volley share a source so they can all land inside
            # the invincibility window the first shot starts
            source = getattr(self, "volley", None)
            if source is None:
                target.take_damage(self.DAMAGE)
            else:
                target.take_damage(self.DAMAGE, source=source)
        elif hasattr(target, "health"):
            target.health.take_damage(self.DAMAGE)

    def draw(self, surface, offset=(0, 0)):
        raise NotImplementedError("Subclasses must implement draw method")
