import pygame

from settings import HEIGHT, WIDTH

FACING_VELOCITY = {
    'down':       ( 0,    1   ),
    'up':         ( 0,   -1   ),
    'left':       ( 1,    0   ),
    'right':      (-1,    0   ),
    'down_right': (-0.707,  0.707),
    'down_left':  ( 0.707,  0.707),
    'up_right':   (-0.707, -0.707),
    'up_left':    ( 0.707, -0.707),
}

class BaseProjectile:    
    MAX_RANGE = 400

    def __init__(self, origin_x, origin_y, facing, 
                speed = 300, map_size=(1440, 1440), 
                max_range = 400):
        self.facing = facing
        self.pos = pygame.math.Vector2(origin_x, origin_y)
        self._origin = pygame.math.Vector2(origin_x, origin_y)
        vx, vy = FACING_VELOCITY.get(facing, (0, 1))
        self.velocity = pygame.math.Vector2(vx * speed, vy * speed)

        self.active = True

        self.map_width, self.map_height = map_size
        self.max_range = max_range

    def update(self, dt):
        self.pos += self.velocity * dt

        if self._origin.distance_to(self.pos) > self.max_range:
            self.active = False

        if (self.pos.x < 0 or self.pos.x > self.map_width or
            self.pos.y < 0 or self.pos.y > self.map_height):
            self.active = False

    def draw(self, surface, offset=(0,0)):
        raise NotImplementedError("Subclasses must implement draw method")
