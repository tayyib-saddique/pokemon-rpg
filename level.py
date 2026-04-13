import pygame
import pytmx
from player import Player
from constants.moves import MOVE_CLASSES
from constants.world import MAPS
from constants.settings import SCALE
from hud import HUD
from utils.camera import CameraGroup
from utils.map import flatten_layers, collect_base_positions, build_sprites


FILL_COLOUR = (60, 55, 65)


class Level:
    def __init__(self, map_name="vertia_road", player_pos=(500, 500)):
        self.display_surface = pygame.display.get_surface()

        self.map_name = map_name
        self.pending_transition = None

        self.all_sprites = CameraGroup()
        self.collision_sprites = pygame.sprite.Group()
        self.projectiles = []
        self.setup(player_pos)
        self.hud = HUD()

    def _check_transition(self):
        if self.pending_transition:
            return

        connections = MAPS[self.map_name]["connections"]
        p = self.player

        hw = p.hitbox.width // 2
        hh = p.hitbox.height // 2
        margin = 48

        print(
            f"pos=({p.pos.x:.0f}, {p.pos.y:.0f})  west check: {p.pos.x - hw:.0f} <= {margin} = {p.pos.x - hw <= margin}"
        )

        checks = [
            (p.pos.y - hh <= margin, "north"),
            (p.pos.y + hh >= self.map_height - margin, "south"),
            (p.pos.x + hw >= self.map_width - margin, "east"),
            (p.pos.x - hw <= margin, "west"),
        ]
        for condition, edge in checks:
            if condition and connections.get(edge):
                self.pending_transition = (edge, connections[edge])
                break

    def setup(self, player_pos):
        tmx = pytmx.load_pygame(
            f"graphics/floor_maps/{self.map_name}.tmx", pixelalpha=True
        )

        self.map_width = tmx.width * tmx.tilewidth * SCALE
        self.map_height = tmx.height * tmx.tileheight * SCALE

        self._build_map(tmx)

        self.player = Player(
            pos=player_pos,
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
        tree_base_positions, building_base_positions = collect_base_positions(
            layers, tile_h
        )

        build_sprites(
            layers=layers,
            tile_w=tile_w,
            tile_h=tile_h,
            tree_base_positions=tree_base_positions,
            building_base_positions=building_base_positions,
            map_height=self.map_height,
            all_sprites=self.all_sprites,
            collision_sprites=self.collision_sprites,
        ),

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
        self._check_transition()
