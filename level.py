import pygame
import pytmx
from player import Player
from enemy import Enemy
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
        self.combat_sprites = pygame.sprite.Group()
        self.player_sprites = pygame.sprite.Group()
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
        self.player.can_attack = not MAPS[self.map_name].get("no_combat", False)
        self.player_sprites.add(self.player)

        for spawn in MAPS[self.map_name].get("enemy_spawns", []):
            enemy = Enemy(
                pos=spawn["pos"],
                group=self.all_sprites,
                pokemon=spawn["pokemon"],
                player=self.player,
                create_projectile_callback=self.spawn_enemy_projectile,
                collision_sprites=self.collision_sprites,
                map_size=(self.map_width, self.map_height),
                tier=spawn.get("tier", 1),
                is_boss=spawn.get("boss", False),
            )
            self.combat_sprites.add(enemy)

    def _build_map(self, tmx):
        tile_w = tmx.tilewidth * SCALE
        tile_h = tmx.tileheight * SCALE

        layers = flatten_layers(tmx.layers)
        tree_base_positions, building_base_positions = collect_base_positions(
            layers, tile_h
        )

        (
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
        )

    def spawn_enemy_projectile(self, pos, facing, move_type):
        move_class = MOVE_CLASSES.get(move_type)
        if not move_class:
            return
        spawn_x, spawn_y = pos
        p = move_class(
            spawn_x,
            spawn_y,
            facing,
            collision_sprites=self.collision_sprites,
            combat_sprites=self.player_sprites,
        )
        p.MAP_WIDTH = self.map_width
        p.MAP_HEIGHT = self.map_height
        self.all_sprites.add(p)
        self.projectiles.append(p)

    def spawn_projectile(self, pos, facing, move_type):
        move_class = MOVE_CLASSES.get(move_type)
        if not move_class:
            return

        spawn_x, spawn_y = pos

        p = move_class(
            spawn_x,
            spawn_y,
            facing,
            collision_sprites=self.collision_sprites,
            combat_sprites=self.combat_sprites,
        )
        p.ground_y = self.player.ground_y
        p.MAP_WIDTH = self.map_width
        p.MAP_HEIGHT = self.map_height

        self.all_sprites.add(p)
        self.projectiles.append(p)

    def _resolve_entity_overlaps(self):
        for enemy in self.combat_sprites:
            if not self.player.hitbox.colliderect(enemy.hitbox):
                continue
            dx = enemy.pos.x - self.player.pos.x
            dy = enemy.pos.y - self.player.pos.y
            dist = max(1.0, (dx**2 + dy**2) ** 0.5)
            push = 2.0
            nx, ny = dx / dist * push, dy / dist * push
            self.player.pos.x -= nx
            self.player.pos.y -= ny
            self.player.hitbox.center = (
                round(self.player.pos.x),
                round(self.player.pos.y),
            )
            enemy.pos.x += nx
            enemy.pos.y += ny
            enemy.hitbox.center = (round(enemy.pos.x), round(enemy.pos.y))

    def run(self, dt, events):
        self.display_surface.fill(FILL_COLOUR)
        self.all_sprites.update(dt, events)
        self._resolve_entity_overlaps()
        self.all_sprites.draw(self.player)
        self.hud.draw(self.player, self.combat_sprites, self.all_sprites.offset)
        self.projectiles = [p for p in self.projectiles if p.active]
        self._check_transition()
