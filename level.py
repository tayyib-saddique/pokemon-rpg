import pygame
import pytmx
from player import Player
from sprite import Generic
from constants.moves import MOVE_CLASSES, SPAWN_OFFSETS

SCALE = 3
FILL_COLOUR = (60, 55, 65)

class Level:
    def __init__(self):
        self.display_surface = pygame.display.get_surface()
        self.all_sprites = CameraGroup()
        self.collision_sprites = pygame.sprite.Group()
        self.projectiles = []
        self.setup()

    def setup(self):
        tmx = pytmx.load_pygame("graphics/floor_maps/vertia_road.tmx", pixelalpha=True)

        self.map_width  = tmx.width  * tmx.tilewidth  * SCALE
        self.map_height = tmx.height * tmx.tileheight * SCALE

        self._build_map(tmx)

        self.player = Player(
            pos=(500, 500),
            group=self.all_sprites,
            create_projectile_callback=self.spawn_projectile,
            pokemon='totodile',
            map_size=(self.map_width, self.map_height),
            collision_sprites=self.collision_sprites,
        )

    def _build_map(self, tmx):
        TILE_W = tmx.tilewidth  * SCALE
        TILE_H = tmx.tileheight * SCALE

        def get_depth_value(tile_y):
            return (tile_y * TILE_H) + (TILE_H * 3 // 4)

        layers = self._flatten_layers(tmx.layers)

        # collect ALL base tile positions
        # Stored as (tile_x, tile_y, ground_y) so Tips/Mid tiles can search
        # for the nearest base below them even when the column doesn't align
        # exactly (canopy wider than trunk, or adjacent trees).
        base_positions = {}

        for layer in layers:
            if isinstance(layer, pytmx.TiledTileLayer) and 'Base' in layer.name:
                for x, y, image in layer.tiles():
                    if image:
                        base_positions[(x, y)] = get_depth_value(y)

        def find_tree_depth(tile_x, tile_y):
            # search downwards from the current tile to find the nearest base tile
            for row in range(tile_y + 1, tile_y + 15):
                if (tile_x, row) in base_positions:
                    return base_positions[(tile_x, row)]
            
            # if not found, search adjacent columns in case the tree is wider than 1 tile or misaligned
            for row in range(tile_y + 1, tile_y + 15):
                for dx in [-1, 1]:
                    if (tile_x + dx, row) in base_positions:
                        return base_positions[(tile_x + dx, row)]
            
            # if still not found, search two tiles away to catch even wider/misaligned trees
            for row in range(tile_y + 1, tile_y + 15):
                for dx in [-2, 2]:
                    if (tile_x + dx, row) in base_positions:
                        return base_positions[(tile_x + dx, row)]
                    
            # if no base tile found within reasonable distance, return a default depth to avoid rendering issues
            return self.map_height + 100
            
        # build every sprite
        for layer in layers:
            if not isinstance(layer, pytmx.TiledTileLayer):
                continue

            for x, y, image in layer.tiles():
                if not image:
                    continue

                pos    = (x * TILE_W, y * TILE_H)
                scaled = pygame.transform.scale(image, (TILE_W, TILE_H))

                if layer.name == 'Collisions':
                    Generic(
                        pos=pos,
                        surface=pygame.Surface((TILE_W, TILE_H)),
                        groups=self.collision_sprites,
                    )
                    continue

                sprite = Generic(pos=pos, surface=scaled, groups=self.all_sprites)
                sprite.layer_name = layer.name

                if 'Base' in layer.name:
                    sprite.ground_y = get_depth_value(y)
                elif 'Tips' in layer.name or 'Mid' in layer.name:
                    sprite.ground_y = find_tree_depth(x, y)
                else:
                    sprite.ground_y = get_depth_value(y)

    @staticmethod
    def _flatten_layers(layers):
        result = []
        for layer in layers:
            if hasattr(layer, 'layers'):
                result.extend(Level._flatten_layers(layer.layers))
            else:
                result.append(layer)
        return result

    def spawn_projectile(self, pos, facing, move_type):
        move_class = MOVE_CLASSES.get(move_type)
        if not move_class: return
            
        hb = self.player.hitbox

        spawn_x = hb.centerx + 7.5 * (1 if 'right' in facing else -1)
        spawn_y = hb.top + 10
        p = move_class(spawn_x, spawn_y, facing,
                        collision_sprites=self.collision_sprites)
        
        p.ground_y   = self.player.ground_y

        p.MAP_WIDTH  = self.map_width
        p.MAP_HEIGHT = self.map_height

        self.all_sprites.add(p)
        self.projectiles.append(p)

    def run(self, dt, events):
        self.display_surface.fill(FILL_COLOUR)

        self.all_sprites.update(dt, events)

        # for p in self.projectiles:
        #     p.ground_y = p.rect.bottom

        self.all_sprites.draw(self.player)

        self.projectiles = [p for p in self.projectiles if p.active]

class CameraGroup(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.offset = pygame.math.Vector2()

    def draw(self, player):
        self.offset.x = player.rect.centerx - self.display_surface.get_width()  // 2
        self.offset.y = player.rect.centery - self.display_surface.get_height() // 2

        floor_sprites  = []
        shadow_sprites = []
        depth_sprites  = []

        for sprite in self.sprites():
            if sprite is player:
                continue
            layer = getattr(sprite, 'layer_name', '')
            if 'Floor' in layer or 'Terrain' in layer:
                floor_sprites.append(sprite)
            elif 'Shadow' in layer:
                shadow_sprites.append(sprite)
            else:
                depth_sprites.append(sprite)

        for sprite in floor_sprites + shadow_sprites:
            self._blit(sprite)

        depth_sprites.append(player)
        depth_sprites.sort(key=lambda s: getattr(s, 'ground_y', s.rect.bottom))
        for sprite in depth_sprites:
            self._blit(sprite)

    def _blit(self, sprite):
        if hasattr(sprite, 'draw'):
            sprite.draw(self.display_surface, self.offset)
        else:
            self.display_surface.blit(sprite.image, sprite.rect.topleft - self.offset)