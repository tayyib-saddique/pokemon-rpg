import random
import pygame
from constants.moves import MOVE_CLASSES, POKEMON_MOVES
from constants.sprite_sheets import SPRITE_SHEETS
from utils.assets import load_pokemon_animations
from utils.animator import Animator
from utils.direction import direction_name
from utils.health import Health


class Enemy(pygame.sprite.Sprite):
    BASE_HP = 60
    HP_PER_TIER = 20
    BASE_SPEED = 90
    SPEED_PER_TIER = 8
    BASE_COOLDOWN = 3.0
    COOLDOWN_REDUCTION_PER_TIER = 0.25
    MIN_COOLDOWN = 1.0
    DETECTION_RANGE = 350
    ATTACK_RANGE = 220
    HIT_JITTER_DURATION = 0.3
    HIT_JITTER_MAGNITUDE = 3

    def __init__(
        self,
        pos,
        group,
        pokemon,
        player,
        create_projectile_callback,
        collision_sprites=None,
        map_size=(1440, 1440),
        tier=1,
        is_boss=False,
    ):
        super().__init__(group)

        self.pokemon = pokemon
        self.player = player
        self.create_projectile_callback = create_projectile_callback
        self.is_boss = is_boss

        # Stats scaled by tier
        # TODO: extend scaling to damage output once the damage formula is in place
        scaled_hp = self.BASE_HP + self.HP_PER_TIER * (tier - 1)
        self.SPEED = self.BASE_SPEED + self.SPEED_PER_TIER * (tier - 1)
        self.ATTACK_COOLDOWN = max(
            self.MIN_COOLDOWN,
            self.BASE_COOLDOWN - self.COOLDOWN_REDUCTION_PER_TIER * (tier - 1),
        )

        # Health
        self.health = Health(max_hp=scaled_hp)

        # Animation
        self.animations = load_pokemon_animations(self.pokemon)
        self.animator = Animator(self.animations)
        self.status = "down_idle"

        self.image = self.animations[self.status][0]
        self.rect = self.image.get_rect(center=pos)
        self.hitbox = self.rect.inflate(-self.rect.width // 2, -self.rect.height // 2)

        # Movement
        self.pos = pygame.math.Vector2(self.rect.center)
        self.direction = pygame.math.Vector2()

        # Combat
        moves = POKEMON_MOVES.get(pokemon, {})
        shoot_data = moves.get("shoot", [])
        self.shoot_move = shoot_data[0] if isinstance(shoot_data, list) else shoot_data
        self.shooting = False
        self.attack_complete = False
        self.freeze_timer = 0.0
        self.attack_cooldown = 0.0

        # Hit feedback
        self.hit_timer = 0.0

        # Collision
        self.collision_sprites = collision_sprites or []
        self.map_width, self.map_height = map_size

    def get_facing(self):
        return self.status.rsplit("_", 1)[0]

    def get_mouth_position(self):
        facing = self.get_facing()
        fracs = SPRITE_SHEETS.get(self.pokemon, {}).get("mouth_fracs", {})
        fx, fy = fracs.get(facing, (0.50, 0.38))
        return (
            self.rect.left + self.rect.width * fx,
            self.rect.top + self.rect.height * fy,
        )

    def take_damage(self, amount):
        # TODO: replace flat damage with formula (type effectiveness, attack/defence stats)
        self.health.take_damage(amount)
        self.hit_timer = self.HIT_JITTER_DURATION
        if self.health.is_dead:
            self.kill()

    def trigger_projectile(self):
        if not self.shoot_move:
            return
        self.create_projectile_callback(
            self.get_mouth_position(),
            self.get_facing(),
            self.shoot_move,
        )
        cls = MOVE_CLASSES.get(self.shoot_move)
        self.freeze_timer = cls.FREEZE_DURATION if cls else 0.0
        self.attack_cooldown = self.ATTACK_COOLDOWN

    def _update_ai(self):
        if self.player.dead:
            self.direction = pygame.math.Vector2()
            facing = self.get_facing()
            self.status = (
                f"{facing}_idle"
                if f"{facing}_idle" in self.animations
                else f"{facing}_walk"
            )
            return

        # Don't interrupt an active shoot animation
        if self.shooting and not self.attack_complete:
            self.direction = pygame.math.Vector2()
            return

        self.shooting = False
        self.attack_complete = False

        dist = self.pos.distance_to(self.player.pos)
        diff = self.player.pos - self.pos
        facing = (
            direction_name(diff.x, diff.y, self.get_facing())
            if diff.length() > 0
            else self.get_facing()
        )

        if dist <= self.ATTACK_RANGE and self.attack_cooldown <= 0 and self.shoot_move:
            shoot_status = f"{facing}_shoot"
            if shoot_status in self.animations:
                self.status = shoot_status
                self.animator.reset()
                self.shooting = True
                self.attack_complete = False
                self.direction = pygame.math.Vector2()
        elif dist <= self.DETECTION_RANGE:
            self.direction = diff.normalize()
            self.status = f"{facing}_walk"
        else:
            self.direction = pygame.math.Vector2()
            idle = f"{facing}_idle"
            self.status = idle if idle in self.animations else f"{facing}_walk"

    def _move(self, dt):
        if self.direction.length() == 0:
            return

        self.pos.x += self.direction.x * self.SPEED * dt
        self.hitbox.centerx = round(self.pos.x)
        self._collide("horizontal")

        self.pos.y += self.direction.y * self.SPEED * dt
        self.hitbox.centery = round(self.pos.y)
        self._collide("vertical")

        self.rect.center = self.hitbox.center

    def _collide(self, axis):
        for sprite in self.collision_sprites:
            if not sprite.rect.colliderect(self.hitbox):
                continue
            if axis == "horizontal":
                if self.direction.x > 0:
                    self.hitbox.right = sprite.rect.left
                elif self.direction.x < 0:
                    self.hitbox.left = sprite.rect.right
                self.pos.x = self.hitbox.centerx
            else:
                if self.direction.y > 0:
                    self.hitbox.bottom = sprite.rect.top
                elif self.direction.y < 0:
                    self.hitbox.top = sprite.rect.bottom
                self.pos.y = self.hitbox.centery

    def _animate(self, dt):
        if self.status not in self.animations:
            self.status = f"{self.get_facing()}_idle"

        effective_dt = 0.0 if self.freeze_timer > 0 else dt
        result = self.animator.update(self.status, effective_dt)

        if result.triggered:
            self.trigger_projectile()

        if result.finished:
            self.shooting = False
            self.attack_complete = True

        if result.image:
            self.image = result.image

        self.rect = self.image.get_rect(center=self.hitbox.center)

        if self.hit_timer > 0:
            jitter = self.HIT_JITTER_MAGNITUDE
            self.rect.x += random.randint(-jitter, jitter)
            self.rect.y += random.randint(-jitter, jitter)

    def update(self, dt, events=None):
        if self.freeze_timer > 0:
            self.freeze_timer = max(0.0, self.freeze_timer - dt)
        if self.attack_cooldown > 0:
            self.attack_cooldown = max(0.0, self.attack_cooldown - dt)
        if self.hit_timer > 0:
            self.hit_timer = max(0.0, self.hit_timer - dt)

        self._update_ai()
        if not self.shooting:
            self._move(dt)
        self._animate(dt)

    @property
    def ground_y(self):
        return self.hitbox.bottom
