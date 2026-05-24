import pygame
import pytmx

from entities.player import Player
from entities.enemy import Enemy

from config.moves import MOVE_CLASSES
from config.world import MAPS
from config.settings import SCALE

from ui.hud import HUD
from world.camera import CameraGroup
from world.map import flatten_layers, collect_base_positions, build_sprites
from world.pathfinding import NavGrid


FILL_COLOUR = (60, 55, 65)


class Level:
    def __init__(self, map_name="vertia_road", player_pos=(500, 500)):
        self.display_surface = pygame.display.get_surface()

        self.map_name = map_name
        self.pending_transition = None
        self.door_rects: list = []
        self.door_cooldown_until = 0

        # Groups
        self.all_sprites = CameraGroup()
        self.collision_sprites = pygame.sprite.Group()
        self.combat_sprites = pygame.sprite.Group()
        self.player_sprites = pygame.sprite.Group()

        self.projectiles = []

        self._setup_map(player_pos)
        self.hud = HUD()

    # Setup
    def _setup_map(self, player_pos):
        tmx = pytmx.load_pygame(
            f"assets/floor_maps/{self.map_name}.tmx", pixelalpha=True
        )

        self.map_width = tmx.width * tmx.tilewidth * SCALE
        self.map_height = tmx.height * tmx.tileheight * SCALE

        self._build_map(tmx)

        tile_size = tmx.tilewidth * SCALE

        self.nav_grid = NavGrid(
            self.collision_sprites, self.map_width, self.map_height, tile_size
        )

        self._spawn_player(player_pos)
        self._spawn_enemies()

    def _build_map(self, tmx):
        tile_w = tmx.tilewidth * SCALE
        tile_h = tmx.tileheight * SCALE

        layers = flatten_layers(tmx.layers)

        tree_base_positions, building_base_positions, town_positions = (
            collect_base_positions(layers, tile_h)
        )

        self.door_rects = build_sprites(
            layers=layers,
            tile_w=tile_w,
            tile_h=tile_h,
            tree_base_positions=tree_base_positions,
            building_base_positions=building_base_positions,
            town_positions=town_positions,
            map_height=self.map_height,
            all_sprites=self.all_sprites,
            collision_sprites=self.collision_sprites,
        )

    def _spawn_player(self, player_pos):
        self.player = Player(
            pos=player_pos,
            group=self.all_sprites,
            create_projectile_callback=self.spawn_projectile,
            pokemon="totodile",
            map_size=(self.map_width, self.map_height),
            collision_sprites=self.collision_sprites,
        )

        self.player.can_attack = not MAPS[self.map_name].get("no_combat", False)
        self.player.entity_blockers = self.combat_sprites

        self.player_sprites.add(self.player)

    def _spawn_enemies(self):
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
                nav_grid=self.nav_grid,
            )
            self.combat_sprites.add(enemy)

    # Projectiles
    def spawn_enemy_projectile(self, pos, facing, move_type):
        move_class = MOVE_CLASSES.get(move_type)
        if not move_class:
            return

        p = move_class(
            pos[0],
            pos[1],
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

        p = move_class(
            pos[0],
            pos[1],
            facing,
            collision_sprites=self.collision_sprites,
            combat_sprites=self.combat_sprites,
        )

        p.ground_y = self.player.ground_y
        p.MAP_WIDTH = self.map_width
        p.MAP_HEIGHT = self.map_height

        self.all_sprites.add(p)
        self.projectiles.append(p)

    # Collision Safety
    def _resolve_entity_overlaps(self):
        for enemy in self.combat_sprites:
            ph = self.player.hitbox
            eh = enemy.hitbox

            if not ph.colliderect(eh):
                continue

            dx = enemy.pos.x - self.player.pos.x
            dy = enemy.pos.y - self.player.pos.y

            if abs(dx) < 0.1 and abs(dy) < 0.1:
                dx = 1.0

            x_pen = (ph.width + eh.width) / 2 - abs(dx)
            y_pen = (ph.height + eh.height) / 2 - abs(dy)

            if x_pen <= 0 or y_pen <= 0:
                continue

            if x_pen <= y_pen:
                sep = x_pen / 2
                sign = 1 if dx >= 0 else -1
                self.player.pos.x -= sign * sep
                enemy.pos.x += sign * sep
            else:
                sep = y_pen / 2
                sign = 1 if dy >= 0 else -1
                self.player.pos.y -= sign * sep
                enemy.pos.y += sign * sep

            self.player.hitbox.center = (
                round(self.player.pos.x),
                round(self.player.pos.y),
            )
            enemy.hitbox.center = (
                round(enemy.pos.x),
                round(enemy.pos.y),
            )

    # Transitions
    def _check_transition(self):
        if self.pending_transition:
            return

        if self._check_door_transition():
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

    def _check_door_transition(self) -> bool:
        if pygame.time.get_ticks() < self.door_cooldown_until:
            return False

        if not self.door_rects:
            return False

        if self.player.hitbox.collidelist(self.door_rects) == -1:
            return False

        self.pending_transition = ("door", None)
        return True

    # Main Loop
    def run(self, dt, events):
        self.display_surface.fill(FILL_COLOUR)

        if pygame.time.get_ticks() % 1000 < 16:  # ~once per second
            print(f"Player pos: ({int(self.player.pos.x)}, {int(self.player.pos.y)})")

        self.all_sprites.update(dt, events)

        self._resolve_entity_overlaps()

        self.all_sprites.draw(self.player)

        self.hud.draw(self.player, self.combat_sprites, self.all_sprites.offset)

        self.projectiles = [p for p in self.projectiles if p.active]

        self._check_transition()
