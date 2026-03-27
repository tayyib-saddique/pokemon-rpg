import pygame
import player
from settings import *
from player import Player
from constants.moves import MOVE_CLASSES
from sprite import Generic
import pytmx

SCALE = 3
FILL_COLOUR = (60, 55, 65)

class Level:
    def __init__(self):
        # get display surface
        self.display_surface = pygame.display.get_surface()

        # sprite group setup
        self.all_sprites = CameraGroup()

        # projectile set up
        self.projectiles = []

        self.setup()

    def setup(self):
        tmx = pytmx.load_pygame("graphics/floor_maps/vertia_road.tmx", pixelalpha=True)

        # bake all tile layers into one surface
        self.map_width  = tmx.width  * tmx.tilewidth  * SCALE   # 1440
        self.map_height = tmx.height * tmx.tileheight * SCALE   # 1440

        self.collision_sprites = pygame.sprite.Group()
        self.map_surface = self._bake_map(tmx)

        self.player = Player(
            (500, 500),
            self.all_sprites,
            create_projectile_callback=self.spawn_projectile,
            pokemon='totodile',
            map_size=(self.map_width, self.map_height),
            collision_sprites=self.collision_sprites
        )

    def _bake_map(self, tmx):
        TILE_W = tmx.tilewidth  * SCALE
        TILE_H = tmx.tileheight * SCALE
        map_w  = tmx.width  * TILE_W
        map_h  = tmx.height * TILE_H

        surface = pygame.Surface((map_w, map_h))
        surface.fill((60, 55, 65))

        for layer in tmx.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, image in layer.tiles():
                    if image:
                        if layer.name == 'Collision':
                            Generic(
                                pos=(x * TILE_W, y * TILE_H),
                                surface=pygame.Surface((TILE_W, TILE_H)),
                                groups=self.collision_sprites
                            )
                        else:
                            if SCALE == 2:
                                scaled = pygame.transform.scale2x(image)
                            else:
                                scaled = pygame.transform.scale(image, (TILE_W, TILE_H))
                            surface.blit(scaled, (x * TILE_W, y * TILE_H))

        return surface
    
    def spawn_projectile(self, pos, facing, move_type):
        move_class = MOVE_CLASSES.get(move_type)
        if move_class:
            projectile = move_class(pos[0], pos[1], facing)
            projectile.MAP_WIDTH = self.map_width
            projectile.MAP_HEIGHT = self.map_height
            self.projectiles.append(projectile)

    def run(self, dt, events):
        self.display_surface.fill(FILL_COLOUR)

        # Draw baked map using camera offset
        offset = self.all_sprites.offset
        self.display_surface.blit(self.map_surface, (-offset.x, -offset.y))

        # Draw player and sprites
        self.all_sprites.customise_draw(self.player)
        self.all_sprites.update(dt, events)
    
        for p in self.projectiles:
            p.update(dt)
            p.draw(self.display_surface, self.all_sprites.offset)

        self.projectiles = [p for p in self.projectiles if p.active]
    
class CameraGroup(pygame.sprite.Group):
    def __init__(self):
          super().__init__()
          self.display_surface = pygame.display.get_surface()
          self.offset = pygame.math.Vector2()

    def customise_draw(self, player):
        self.offset.x = player.rect.centerx - self.display_surface.get_width()  // 2
        self.offset.y = player.rect.centery - self.display_surface.get_height() // 2

        for sprite in self.sprites():
            offset_pos = sprite.rect.topleft - self.offset
            self.display_surface.blit(sprite.image, offset_pos)
    
