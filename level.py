import pygame
import pytmx
from player import Player
from constants.moves import MOVE_CLASSES
from hud import HUD
from utils.camera import CameraGroup
from utils.map import flatten_layers, collect_base_positions, build_sprites

SCALE = 3
FILL_COLOUR = (60, 55, 65)


class Level:
    def __init__(self):
        self.display_surface = pygame.display.get_surface()
        self.all_sprites = CameraGroup()
        self.collision_sprites = pygame.sprite.Group()
        self.projectiles = []
        self.setup()
        self.hud = HUD()

    def setup(self):
        tmx = pytmx.load_pygame("graphics/floor_maps/vertia_road.tmx", pixelalpha=True)

        self.map_width = tmx.width * tmx.tilewidth * SCALE
        self.map_height = tmx.height * tmx.tileheight * SCALE

        self._build_map(tmx)

        self.player = Player(
            pos=(500, 500),
            group=self.all_sprites,
            create_projectile_callback=self.spawn_projectile,
            pokemon="totodile",
            map_size=(self.map_width, self.map_height),
            collision_sprites=self.collision_sprites,
        )

    def _build_map(self, tmx):
        tile_w = tmx.tilewidth * SCALE
        tile_h = tmx.tileheight * SCALE

        layers = flatten_layers(tmx.layers)
        base_positions = collect_base_positions(layers, tile_h)

        build_sprites(
            layers,
            tile_w,
            tile_h,
            base_positions,
            self.map_height,
            self.all_sprites,
            self.collision_sprites,
        )

    def spawn_projectile(self, pos, facing, move_type):
        move_class = MOVE_CLASSES.get(move_type)
        if not move_class:
            return

        spawn_x, spawn_y = self._get_spawn_pos(facing)

        p = move_class(
            spawn_x, spawn_y, facing, collision_sprites=self.collision_sprites
        )
        p.ground_y = self.player.ground_y
        p.MAP_WIDTH = self.map_width
        p.MAP_HEIGHT = self.map_height

        self.all_sprites.add(p)
        self.projectiles.append(p)

    def _get_spawn_pos(self, facing):
        hb = self.player.hitbox
        spawn_x = hb.centerx + 7.5 * (1 if "right" in facing else -1)
        spawn_y = hb.top + 10
        return spawn_x, spawn_y

    def run(self, dt, events):
        self.display_surface.fill(FILL_COLOUR)
        self.all_sprites.update(dt, events)
        self.all_sprites.draw(self.player)
        self.hud.draw(self.player)
        self.projectiles = [p for p in self.projectiles if p.active]
