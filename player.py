import pygame
import os
from settings import *
from utils.support import *
from constants.moves import POKEMON_MOVES
from constants.sprite_sheets import SPRITE_SHEETS

class Player(pygame.sprite.Sprite):
    def __init__(self, pos, group, create_projectile_callback, 
                pokemon = 'totodile', map_size=(1440, 1440), collision_sprites = None):
        super().__init__(group)
        self.pokemon = pokemon

        self.attacking = False
        self.shooting = False
        self.attack_complete = False

        # animation setup
        self.import_assets()
        self.status = 'down_walk'
        self.frame_index = 0

        # general set up
        self.image = self.animations[self.status][self.frame_index]
        self.rect = self.image.get_rect(center=pos)
        self.hitbox = self.rect.inflate(-self.rect.width // 2, -self.rect.height // 2)

        # movement attributes
        self.direction = pygame.math.Vector2()
        self.pos = pygame.math.Vector2(self.rect.center)
        self.speed = 200

        # moves
        self.create_projectile_callback = create_projectile_callback
        moves = POKEMON_MOVES.get(pokemon, {})
        shoot_data = moves.get('shoot', [])
        if isinstance(shoot_data, str):
            self.shoot_moves = [shoot_data]
        else:
            self.shoot_moves = list(shoot_data)

        self.shoot_index = 0      
        self.strike_move = moves.get('strike')

        # map
        self.map_width, self.map_height = map_size
        self.collision_sprites = collision_sprites or []

    def import_assets(self):
        self.animations = {}
        scale = 3

        pokemon_data = SPRITE_SHEETS.get(self.pokemon, {})

        actions = ['walk', 'idle', 'shoot', 'strike']

        for action in actions:
            data = pokemon_data.get(action)
            sheet_path = f'graphics/pokemon/{self.pokemon}/{action}.png'
            
            if not os.path.exists(sheet_path):
                continue
            
            sheet = pygame.image.load(sheet_path).convert_alpha()
            
            frame_w = sheet.get_width() // data['cols'] # variable column count per action
            frame_h = sheet.get_height() // 8
            
            frames_by_direction = load_pmd_sheet(sheet_path, frame_w=frame_w, frame_h=frame_h)
            
            for direction, frames in frames_by_direction.items():
                scaled = [pygame.transform.scale(f, (int(frame_w * scale), int(frame_h * scale))) for f in frames]
                if 'trim' in data:
                    indices = data['trim']
                    scaled = [f for i, f in enumerate(scaled) if i in indices]
                    
                self.animations[f'{direction}_{action}'] = scaled

    def get_status(self):
        facing = self.status.rsplit('_', 1)[0]

        if ('_shoot' in self.status or '_strike' in self.status) and not self.attack_complete:
            return

        self.attack_complete = False

        if self.attacking:
            new_status = f'{facing}_strike'
            if new_status in self.animations:
                self.status = new_status
                self.frame_index = 0
                return
            else:
                self.attacking = False

        if self.shooting:
            new_status = f'{facing}_shoot'
            if new_status in self.animations:
                self.status = new_status
                self.frame_index = 0
                return
            else:
                self.shooting = False
        
        if self.direction.magnitude() == 0:
            idle_status = f'{facing}_idle'
            self.status = idle_status if idle_status in self.animations else f'{facing}_walk'

        # update status based on direction
        else:
            if self.direction.x < 0 and self.direction.y > 0:
                    self.status = 'down_right_walk'
            elif self.direction.x < 0 and self.direction.y < 0:
                self.status = 'up_right_walk'
            elif self.direction.x > 0 and self.direction.y > 0:
                self.status = 'down_left_walk'
            elif self.direction.x > 0 and self.direction.y < 0:
                self.status = 'up_left_walk'
            elif self.direction.y > 0:
                self.status = 'down_walk'
            elif self.direction.y < 0:
                self.status = 'up_walk'
            elif self.direction.x < 0:
                self.status = 'right_walk'
            elif self.direction.x > 0:
                self.status = 'left_walk'

    def input(self):
        keys = pygame.key.get_pressed()
        
        self.direction.y = -1 if keys[pygame.K_UP] else (1 if keys[pygame.K_DOWN] else 0)
        self.direction.x = -1 if keys[pygame.K_LEFT] else (1 if keys[pygame.K_RIGHT] else 0)

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_z and not self.attacking and not self.shooting:
                    self.attacking = True
                    self.attack_complete = False
                if event.key == pygame.K_x and not self.attacking and not self.shooting:
                    self.shooting = True
                    self.attack_complete = False
                if event.key == pygame.K_q and self.shoot_moves:
                    if len(self.shoot_moves) > 0:
                        self.shoot_index = (self.shoot_index + 1) % len(self.shoot_moves)
                        print(f"Switched to: {self.shoot_moves[self.shoot_index]}")
    
    def trigger_projectile(self, move_type):
        if '_shoot' in self.status and self.shoot_moves:
            current_move = self.shoot_moves[self.shoot_index]
            facing = self.get_facing()
            self.create_projectile_callback(self.rect.center, facing, current_move)
        
        # elif '_strike' in self.status:
        #     facing = self.get_facing()
        #     self.create_projectile_callback(self.rect.center, facing, self.strike_move)
        
    def switch_move(self):
        """Cycle through available shoot moves."""
        if len(self.shoot_moves) > 1:
            self.shoot_index = (self.shoot_index + 1) % len(self.shoot_moves)
            print('Switched to move:', self.shoot_moves[self.shoot_index])

    def animate(self, dt):
        if self.status not in self.animations:
            facing = self.get_facing()
            self.status = f'{facing}_walk' 

        if '_strike' in self.status:
            speed = 20
        elif '_shoot' in self.status:
            speed = 20
        else: 
            speed = 8
        
        old_frame = int(self.frame_index)
        self.frame_index += speed * dt 
        next_frame = int(self.frame_index)
        trigger_frame = len(self.animations[self.status]) // 2 # Fire at the midpoint

        if old_frame < trigger_frame <= next_frame:
            if '_shoot' in self.status:
                self.trigger_projectile(self.shoot_moves[self.shoot_index])
            # elif '_strike' in self.status:
            #     self.trigger_projectile(self.strike_move)

        if next_frame >= len(self.animations[self.status]):
            self.frame_index = 0
            if '_strike' in self.status or '_shoot' in self.status:
                self.attack_complete = True
                self.attacking = False
                self.shooting = False
        
        self.image = self.animations[self.status][int(self.frame_index)]

        self.rect = self.image.get_rect(center=self.hitbox.center)

        # dynamic clamping 
        map_rect = pygame.Rect(0, 0, self.map_width, self.map_height)
        if not map_rect.contains(self.rect):
            self.rect.clamp_ip(map_rect)
            self.pos.x = float(self.rect.centerx)
            self.pos.y = float(self.rect.centery)
            self.hitbox.center = self.rect.center

    def move(self, dt):
        # normalising vectors
        if self.direction.magnitude() > 0:
            self.direction = self.direction.normalize()
                
        # horizontal movement
        self.pos.x += self.direction.x * self.speed * dt
        self.rect.centerx = self.pos.x
        self.hitbox.centerx = round(self.pos.x)
        self._collide('horizontal')

        # vertical movement
        self.pos.y += self.direction.y * self.speed * dt
        self.rect.centery = self.pos.y
        self.hitbox.centery = round(self.pos.y)
        self._collide('vertical')

        self.rect.center = self.hitbox.center

    def get_facing(self):
            """
            Returns the current facing direction as a plain string, e.g.:
            'down', 'up', 'left', 'right',
            'down_right', 'down_left', 'up_right', 'up_left'

            Strips the trailing action suffix (_walk / _idle / _shoot / _strike)
            from self.status using rsplit so compound directions like
            'down_right' are preserved intact.
            """
            return self.status.rsplit('_', 1)[0]
    
    def _collide(self, direction):
        for sprite in self.collision_sprites:
            if sprite.rect.colliderect(self.hitbox):
                if direction == 'horizontal':
                    if self.direction.x > 0: self.hitbox.right = sprite.rect.left
                    elif self.direction.x < 0: self.hitbox.left = sprite.rect.right
                    self.pos.x = float(self.hitbox.centerx)

                elif direction == 'vertical':
                    if self.direction.y > 0: self.hitbox.bottom = sprite.rect.top
                    elif self.direction.y < 0: self.hitbox.top = sprite.rect.bottom
                    self.pos.y = float(self.hitbox.centery)

    def update(self, dt, events):
        self.input()
        self.handle_events(events)
        self.get_status()
        self.move(dt)
        self.animate(dt)