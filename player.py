import pygame
import os
from settings import *
from utils.support import *
from constants.moves import POKEMON_MOVES
from constants.sprite_sheets import SPRITE_SHEETS


class Player(pygame.sprite.Sprite):
    def __init__(self, pos, group, create_projectile_callback,
                 pokemon, map_size=(1440, 1440), collision_sprites=None):
        super().__init__(group)

        # --- Core ---
        self.pokemon = pokemon
        self.create_projectile_callback = create_projectile_callback

        # --- State ---
        self.attacking = False
        self.shooting = False
        self.attack_complete = False

        # --- Animation ---
        self.animations = {}
        self.import_assets()
        self.status = 'down_walk'
        self.frame_index = 0

        self.image = self.animations[self.status][0]
        self.rect = self.image.get_rect(center=pos)
        self.hitbox = self.rect.inflate(-self.rect.width // 2, -self.rect.height // 2)

        # --- Movement ---
        self.direction = pygame.math.Vector2()
        self.pos = pygame.math.Vector2(self.rect.center)
        self.speed = 200

        # --- Moves ---
        moves = POKEMON_MOVES.get(pokemon, {})
        shoot_data = moves.get('shoot', [])
        self.shoot_moves = [shoot_data] if isinstance(shoot_data, str) else list(shoot_data)

        self.shoot_index = 0
        self.strike_move = moves.get('strike')

        # --- Map ---
        self.map_width, self.map_height = map_size
        self.collision_sprites = collision_sprites or []

    # --------------------------------------------------
    # ASSETS
    # --------------------------------------------------
    def import_assets(self):
        scale = 3
        pokemon_data = SPRITE_SHEETS.get(self.pokemon, {})
        actions = ['walk', 'idle', 'shoot', 'strike']

        for action in actions:
            data = pokemon_data.get(action)
            path = f'graphics/pokemon/{self.pokemon}/{action}.png'

            if not data or not os.path.exists(path):
                continue

            sheet = pygame.image.load(path).convert_alpha()
            frame_w = sheet.get_width() // data['cols']
            frame_h = sheet.get_height() // 8

            frames = load_pmd_sheet(path, frame_w, frame_h)

            for direction, imgs in frames.items():
                scaled = [pygame.transform.scale(img, (frame_w * scale, frame_h * scale)) for img in imgs]

                if 'trim' in data:
                    scaled = [f for i, f in enumerate(scaled) if i in data['trim']]

                self.animations[f'{direction}_{action}'] = scaled

    # --------------------------------------------------
    # INPUT / EVENTS
    # --------------------------------------------------
    def input(self):
        keys = pygame.key.get_pressed()
        self.direction.x = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
        self.direction.y = keys[pygame.K_DOWN] - keys[pygame.K_UP]

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_z and not (self.attacking or self.shooting):
                    self.attacking = True
                    self.attack_complete = False

                elif event.key == pygame.K_x and not (self.attacking or self.shooting):
                    self.shooting = True
                    self.attack_complete = False

                elif event.key == pygame.K_q and self.shoot_moves:
                    self.shoot_index = (self.shoot_index + 1) % len(self.shoot_moves)
                    print(f"Switched to: {self.shoot_moves[self.shoot_index]}")

    # --------------------------------------------------
    # STATE / STATUS
    # --------------------------------------------------
    def get_status(self):
        facing = self.get_facing()

        if ('_shoot' in self.status or '_strike' in self.status) and not self.attack_complete:
            return

        self.attack_complete = False

        if self.attacking:
            self.set_action(facing, 'strike')
            return

        if self.shooting:
            self.set_action(facing, 'shoot')
            return

        if self.direction.length() == 0:
            self.status = f'{facing}_idle' if f'{facing}_idle' in self.animations else f'{facing}_walk'
        else:
            self.status = f'{self.get_direction_name()}_walk'

    def set_action(self, facing, action):
        new_status = f'{facing}_{action}'
        if new_status in self.animations:
            self.status = new_status
            self.frame_index = 0
        else:
            setattr(self, action + 'ing', False)

    def get_direction_name(self):
        dx, dy = self.direction.x, self.direction.y

        if dx < 0 and dy > 0: return 'down_right'
        if dx < 0 and dy < 0: return 'up_right'
        if dx > 0 and dy > 0: return 'down_left'
        if dx > 0 and dy < 0: return 'up_left'
        if dy > 0: return 'down'
        if dy < 0: return 'up'
        if dx < 0: return 'right'
        if dx > 0: return 'left'

        return self.get_facing()

    def get_facing(self):
        return self.status.rsplit('_', 1)[0]

    # --------------------------------------------------
    # PROJECTILES
    # --------------------------------------------------
    def get_mouth_position(self):
        x, y = self.rect.center

        offsets = {
            'up': (0, -20), 'down': (0, 20),
            'left': (-20, 0), 'right': (20, 0),
            'up_left': (-20, -20), 'up_right': (20, -20),
            'down_left': (-20, 20), 'down_right': (20, 20),
        }

        ox, oy = offsets.get(self.get_facing(), (0, 0))
        return x + ox, y + oy

    def trigger_projectile(self):
        if not self.shoot_moves:
            return

        move = self.shoot_moves[self.shoot_index]
        self.create_projectile_callback(
            self.get_mouth_position(),
            self.get_facing(),
            move
        )

    # --------------------------------------------------
    # ANIMATION
    # --------------------------------------------------
    def animate(self, dt):
        if self.status not in self.animations:
            self.status = f'{self.get_facing()}_walk'

        speed = 20 if ('_shoot' in self.status or '_strike' in self.status) else 8

        old = int(self.frame_index)
        self.frame_index += speed * dt
        new = int(self.frame_index)

        trigger = len(self.animations[self.status]) // 2

        if old < trigger <= new and '_shoot' in self.status:
            self.trigger_projectile()

        if new >= len(self.animations[self.status]):
            self.frame_index = 0
            if '_shoot' in self.status or '_strike' in self.status:
                self.attacking = self.shooting = False
                self.attack_complete = True

        self.image = self.animations[self.status][int(self.frame_index)]
        self.rect = self.image.get_rect(center=self.hitbox.center)

        self.clamp_to_map()

    # --------------------------------------------------
    # MOVEMENT
    # --------------------------------------------------
    def move(self, dt):
        if self.direction.length() > 0:
            self.direction = self.direction.normalize()

        self.pos.x += self.direction.x * self.speed * dt
        self.hitbox.centerx = round(self.pos.x)
        self._collide('horizontal')

        self.pos.y += self.direction.y * self.speed * dt
        self.hitbox.centery = round(self.pos.y)
        self._collide('vertical')

        self.rect.center = self.hitbox.center

    def _collide(self, direction):
        for sprite in self.collision_sprites:
            if sprite.rect.colliderect(self.hitbox):
                if direction == 'horizontal':
                    if self.direction.x > 0:
                        self.hitbox.right = sprite.rect.left
                    elif self.direction.x < 0:
                        self.hitbox.left = sprite.rect.right
                    self.pos.x = self.hitbox.centerx

                if direction == 'vertical':
                    if self.direction.y > 0:
                        self.hitbox.bottom = sprite.rect.top
                    elif self.direction.y < 0:
                        self.hitbox.top = sprite.rect.bottom
                    self.pos.y = self.hitbox.centery

    def clamp_to_map(self):
        map_rect = pygame.Rect(0, 0, self.map_width, self.map_height)
        if not map_rect.contains(self.rect):
            self.rect.clamp_ip(map_rect)
            self.pos.update(self.rect.center)
            self.hitbox.center = self.rect.center

    # --------------------------------------------------
    # UPDATE
    # --------------------------------------------------
    def update(self, dt, events):
        self.input()
        self.handle_events(events)
        self.get_status()
        self.move(dt)
        self.animate(dt)

    @property
    def ground_y(self):
        return self.hitbox.bottom