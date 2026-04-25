import pygame
from constants.moves import MOVE_CLASSES, POKEMON_MOVES
from constants.sprite_sheets import SPRITE_SHEETS
from utils.assets import load_pokemon_animations
from utils.animator import Animator
from utils.direction import direction_name
from utils.health import Health


class Player(pygame.sprite.Sprite):
    def __init__(
        self,
        pos,
        group,
        create_projectile_callback,
        pokemon,
        map_size=(1440, 1440),
        collision_sprites=None,
    ):
        super().__init__(group)

        #  Core
        self.pokemon = pokemon
        self.create_projectile_callback = create_projectile_callback

        #  State
        self.attacking = False
        self.shooting = False
        self.attack_complete = False
        self.freeze_timer = 0.0
        self.can_attack = True
        self.frozen = False
        self.dead = False
        self.invincible_timer = 0.0

        #  Animation
        self.animations = load_pokemon_animations(pokemon)
        self.animator = Animator(self.animations)
        self.status = "down_walk"

        self.image = self.animations[self.status][0]
        self.rect = self.image.get_rect(center=pos)
        self.hitbox = self.rect.inflate(-self.rect.width // 2, -self.rect.height // 2)

        #  Movement
        self.direction = pygame.math.Vector2()
        self.pos = pygame.math.Vector2(self.rect.center)
        self.speed = 200

        #  Moves
        moves = POKEMON_MOVES.get(pokemon, {})
        shoot_data = moves.get("shoot", [])
        self.shoot_moves = (
            [shoot_data] if isinstance(shoot_data, str) else list(shoot_data)
        )
        self.shoot_index = 0
        self.strike_move = moves.get("strike")

        #  Map
        self.map_width, self.map_height = map_size
        self.collision_sprites = collision_sprites or []

        # Health
        self.health = Health(max_hp=100)

    def input(self):
        keys = pygame.key.get_pressed()
        self.direction.x = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
        self.direction.y = keys[pygame.K_DOWN] - keys[pygame.K_UP]

    def handle_events(self, events):
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue

            if (
                event.key == pygame.K_z
                and self.can_attack
                and not (self.attacking or self.shooting)
            ):
                self.attacking = True
                self.attack_complete = False

            elif (
                event.key == pygame.K_x
                and self.can_attack
                and not (self.attacking or self.shooting)
            ):
                self.shooting = True
                self.attack_complete = False

            elif event.key == pygame.K_q and self.shoot_moves:
                self.shoot_index = (self.shoot_index + 1) % len(self.shoot_moves)
                print(f"Switched to: {self.shoot_moves[self.shoot_index]}")

    def get_status(self):
        facing = self.get_facing()

        if (
            "_shoot" in self.status or "_strike" in self.status
        ) and not self.attack_complete:
            return

        self.attack_complete = False

        if self.attacking:
            self._set_action(facing, "strike")
            return

        if self.shooting:
            self._set_action(facing, "shoot")
            return

        if self.direction.length() == 0:
            idle = f"{facing}_idle"
            self.status = idle if idle in self.animations else f"{facing}_walk"
        else:
            self.status = (
                f"{direction_name(self.direction.x, self.direction.y, facing)}_walk"
            )

    def _set_action(self, facing, action):
        new_status = f"{facing}_{action}"
        if new_status in self.animations:
            self.status = new_status
            self.animator.reset()
        else:
            setattr(self, action + "ing", False)

    def get_facing(self):
        return self.status.rsplit("_", 1)[0]

    def get_mouth_position(self):
        rect = self.rect
        facing = self.get_facing()
        fracs = SPRITE_SHEETS.get(self.pokemon, {}).get("mouth_fracs", {})
        fx, fy = fracs.get(facing, (0.50, 0.38))
        return rect.left + rect.width * fx, rect.top + rect.height * fy

    def trigger_projectile(self):
        if not self.shoot_moves:
            return
        move = self.shoot_moves[self.shoot_index]
        self.create_projectile_callback(
            self.get_mouth_position(),
            self.get_facing(),
            move,
        )
        cls = MOVE_CLASSES.get(move)
        self.freeze_timer = cls.FREEZE_DURATION if cls else 0.0

    def animate(self, dt):
        if self.status not in self.animations:
            self.status = f"{self.get_facing()}_walk"

        effective_dt = 0.0 if self.freeze_timer > 0 else dt
        result = self.animator.update(self.status, effective_dt)

        if result.triggered:
            self.trigger_projectile()

        if result.finished:
            self.attacking = self.shooting = False
            self.attack_complete = True

        if result.image:
            if self.invincible_timer > 0 and int(self.invincible_timer * 10) % 2 == 0:
                img = result.image.copy()
                img.set_alpha(60)
                self.image = img
            else:
                self.image = result.image

        self.rect = self.image.get_rect(center=self.hitbox.center)
        self.clamp_to_map()

    def move(self, dt):
        if self.direction.length() > 0:
            self.direction = self.direction.normalize()

        self.pos.x += self.direction.x * self.speed * dt
        self.hitbox.centerx = round(self.pos.x)
        self._collide("horizontal")

        self.pos.y += self.direction.y * self.speed * dt
        self.hitbox.centery = round(self.pos.y)
        self._collide("vertical")

        self.rect.center = self.hitbox.center

    def _collide(self, direction):
        for sprite in self.collision_sprites:
            if not sprite.rect.colliderect(self.hitbox):
                continue

            if direction == "horizontal":
                if self.direction.x > 0:
                    self.hitbox.right = sprite.rect.left
                if self.direction.x < 0:
                    self.hitbox.left = sprite.rect.right
                self.pos.x = self.hitbox.centerx

            if direction == "vertical":
                if self.direction.y > 0:
                    self.hitbox.bottom = sprite.rect.top
                if self.direction.y < 0:
                    self.hitbox.top = sprite.rect.bottom
                self.pos.y = self.hitbox.centery

    def clamp_to_map(self):
        map_rect = pygame.Rect(0, 0, self.map_width, self.map_height)
        if not map_rect.contains(self.rect):
            self.rect.clamp_ip(map_rect)
            self.pos.update(self.rect.center)
            self.hitbox.center = self.rect.center

    def take_damage(self, amount):
        if self.invincible_timer > 0 or self.dead:
            return
        self.health.take_damage(amount)
        self.invincible_timer = 1.0
        if self.health.is_dead:
            self.dead = True

    def update(self, dt, events):
        if self.dead or self.frozen:
            return
        if self.freeze_timer > 0:
            self.freeze_timer = max(0.0, self.freeze_timer - dt)
        if self.invincible_timer > 0:
            self.invincible_timer = max(0.0, self.invincible_timer - dt)
        self.input()
        self.handle_events(events)
        self.get_status()
        if not (self.shooting or self.attacking):
            self.move(dt)
        self.animate(dt)

    @property
    def ground_y(self):
        return self.hitbox.bottom
