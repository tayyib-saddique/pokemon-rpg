import pygame

from settings import HEIGHT, WIDTH

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


class BaseProjectile(pygame.sprite.Sprite):
    MAX_RANGE = 400

    def __init__(
        self,
        origin_x,
        origin_y,
        facing,
        speed=300,
        map_size=(1440, 1440),
        max_range=400,
        collision_sprites=None,
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
        self.active = True
        self.map_width, self.map_height = map_size
        self.max_range = max_range

    def update(self, dt, *args, **kwargs):
        if not self.active:
            return

        self.pos += self.velocity * dt

        if hasattr(self, "rect"):
            self.rect.center = (round(self.pos.x), round(self.pos.y))

            hitbox = getattr(self, "hitbox", self.rect)
            hitbox.center = self.rect.center
            if self.collision_sprites:
                for sprite in self.collision_sprites:
                    if hitbox.colliderect(sprite.rect):
                        self.on_collision()
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

    def draw(self, surface, offset=(0, 0)):
        raise NotImplementedError("Subclasses must implement draw method")
