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


class BaseProjectile(pygame.sprite.Sprite):
    MAX_RANGE = 400
    # seconds the caster freezes when projectile is fired; overrided per subclass
    FREEZE_DURATION = 0.10

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

        self.collision_sprites = collision_sprites
        self.combat_sprites = combat_sprites
        self.active = True
        self.map_width, self.map_height = map_size
        self.max_range = max_range

        # Up-facing projectiles render in the depth pass (behind the player).
        # All others render in the overlay pass (in front of everything).
        self.overlay = facing not in _UP_FACINGS
        self.ground_y = origin_y  # updated each frame for depth sorting

    def update(self, dt, *args, **kwargs):
        if not self.active:
            return

        self.pos += self.velocity * dt

        if hasattr(self, "rect"):
            self.rect.center = (round(self.pos.x), round(self.pos.y))
            if not self.overlay:
                self.ground_y = self.rect.bottom

            hitbox = getattr(self, "hitbox", self.rect)
            hitbox.center = self.rect.center

            if self.collision_sprites:
                for sprite in self.collision_sprites:
                    if hitbox.colliderect(sprite.rect):
                        self.on_collision()
                        self.active = False
                        self.kill()
                        return

            if self.combat_sprites:
                for sprite in self.combat_sprites:
                    if hitbox.colliderect(sprite.rect):
                        self.on_hit(sprite)
                        self.active = False
                        self.kill()
                        return

        if self._origin.distance_to(self.pos) > self.max_range:
            self.active = False
            self.kill()

        if not (
            0 <= self.pos.x <= self.map_width and 0 <= self.pos.y <= self.map_height
        ):
            self.active = False
            self.kill()

    def on_collision(self):
        """Override this in subclasses for explosion animations or sounds."""
        pass

    def on_hit(self, target):
        """Called when the projectile hits a combat sprite. Override to deal damage."""
        if hasattr(target, "health"):
            target.health.take_damage(10)

    def draw(self, surface, offset=(0, 0)):
        raise NotImplementedError("Subclasses must implement draw method")
