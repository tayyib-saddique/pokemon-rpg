import random

import pygame

from pokemon_rpg.data.pokemon import SPRITE_SHEETS
from pokemon_rpg.gameplay.combat.health import Health
from pokemon_rpg.gameplay.combat.moves import MOVE_CLASSES, POKEMON_MOVES
from pokemon_rpg.gameplay.direction import direction_name
from pokemon_rpg.rendering.animation import Animator
from pokemon_rpg.resources.asset_store import load_pokemon_animations


class Enemy(pygame.sprite.Sprite):
    BASE_HP = 60
    HP_PER_TIER = 20
    BASE_SPEED = 90
    SPEED_PER_TIER = 8
    BASE_COOLDOWN = 3.0
    COOLDOWN_REDUCTION_PER_TIER = 0.25
    MIN_COOLDOWN = 1.0
    DETECTION_RANGE = 350
    ATTACK_RANGE = 140
    HIT_JITTER_DURATION = 0.3
    HIT_JITTER_MAGNITUDE = 3

    # Per-instance debug ID, assigned in spawn order
    _next_id = 0
    DEBUG_PRINT_INTERVAL = 1.0  # seconds between debug prints

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
        patrol_points=None,
        nav_grid=None,
    ):
        super().__init__(group)

        self.enemy_id = Enemy._next_id
        Enemy._next_id += 1
        self._debug_print_timer = 0.0

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

        # Patrol
        self.patrol_points = [pygame.math.Vector2(p) for p in (patrol_points or [])]
        self.patrol_index = 0

        # Pathfinding
        self.nav_grid = nav_grid
        self._path = []
        self._path_timer = 0.0
        self._nav_mode = "idle"

        # Stuck detection
        self._stuck_check_pos = pygame.math.Vector2(self.pos)
        self._stuck_check_timer = 0.0
        self._stuck_count = 0

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

    def _navigate_to(self, target_pos, dt, recalc_interval=0.5):
        """Set self.direction toward the next A* step to target_pos. Returns facing name."""
        if self.nav_grid is not None:
            self._path_timer -= dt
            if self._path_timer <= 0 or not self._path:
                self._path = self.nav_grid.find_path(
                    (self.pos.x, self.pos.y), (target_pos.x, target_pos.y)
                )
                self._path_timer = recalc_interval

            if self._path:
                next_wp = pygame.math.Vector2(self._path[0])
                diff = next_wp - self.pos
                if diff.length() < 12:
                    self._path.pop(0)

                    if not self._path:
                        diff = target_pos - self.pos
                        if diff.length() > 0:
                            self.direction = diff.normalize()
                            return direction_name(diff.x, diff.y, self.get_facing())
                        self.direction = pygame.math.Vector2()
                        return self.get_facing()

                    diff = pygame.math.Vector2(self._path[0]) - self.pos

                if diff.length() > 0:
                    self.direction = diff.normalize()
                    return direction_name(diff.x, diff.y, self.get_facing())

                self.direction = pygame.math.Vector2()
                return self.get_facing()

            # Path exhausted before reaching target — walk straight toward it
            diff = target_pos - self.pos
            if diff.length() > 0:
                self.direction = diff.normalize()
                return direction_name(diff.x, diff.y, self.get_facing())
            self.direction = pygame.math.Vector2()
            return self.get_facing()

        # Path empty but target not reached — straight line toward target
        diff = target_pos - self.pos
        if diff.length() > 0:
            self.direction = diff.normalize()
            return direction_name(diff.x, diff.y, self.get_facing())
        self.direction = pygame.math.Vector2()
        return self.get_facing()

    def _check_stuck(self, dt):
        """Simplified stuck detection that forces a standard path recalculation."""
        self._stuck_check_timer += dt
        if self._stuck_check_timer < 0.5:
            return
        self._stuck_check_timer = 0.0

        if self._nav_mode not in ("chase", "patrol") or self.shooting:
            self._stuck_check_pos = pygame.math.Vector2(self.pos)
            self._stuck_count = 0
            return

        if self.pos.distance_to(self.player.pos) <= self.ATTACK_RANGE:
            self._stuck_check_pos = pygame.math.Vector2(self.pos)
            self._stuck_count = 0
            return

        moved = self.pos.distance_to(self._stuck_check_pos)
        if moved < 6 and self.nav_grid is not None:
            # We are stuck. Clear the path to force A* to recalculate next frame.
            self._path = []
            self._path_timer = 0.0
        else:
            self._stuck_count = max(0, self._stuck_count - 1)

        self._stuck_check_pos = pygame.math.Vector2(self.pos)

    def _update_ai(self, dt):
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
            else:
                # Missing shoot animation for this facing — keep closing in
                if self._nav_mode != "chase":
                    self._nav_mode = "chase"
                    self._path = []
                    self._path_timer = 0.0
                nav_facing = self._navigate_to(self.player.pos, dt, recalc_interval=0.5)
                self.status = f"{nav_facing}_walk"

        elif dist <= self.ATTACK_RANGE:
            # Hold position only when we're roughly aligned with the player AND
            # have a clear line of sight — otherwise A* can route us around any
            # wall that's blocking the shot.
            aligned_x = abs(self.pos.x - self.player.pos.x) < 24
            aligned_y = abs(self.pos.y - self.player.pos.y) < 24

            # Temporary until true LoS logic is built into nav_grid
            has_los = True

            if (aligned_x or aligned_y) and has_los:
                self._nav_mode = "idle"
                self.direction = pygame.math.Vector2()
                idle_status = f"{facing}_idle"
                self.status = (
                    idle_status if idle_status in self.animations else f"{facing}_walk"
                )
            else:
                if self._nav_mode != "chase":
                    self._nav_mode = "chase"
                    self._path = []
                    self._path_timer = 0.0
                nav_facing = self._navigate_to(self.player.pos, dt, recalc_interval=0.5)
                self.status = f"{nav_facing}_walk"
        elif dist <= self.DETECTION_RANGE:
            if self._nav_mode != "chase":
                self._nav_mode = "chase"
                self._path = []
                self._path_timer = 0.0
            nav_facing = self._navigate_to(self.player.pos, dt, recalc_interval=0.5)
            self.status = f"{nav_facing}_walk"
        elif self.patrol_points:
            if self._nav_mode != "patrol":
                self._nav_mode = "patrol"
                self._path = []
                self._path_timer = 0.0
            target = self.patrol_points[self.patrol_index]
            if (target - self.pos).length() < 15:
                self.patrol_index = (self.patrol_index + 1) % len(self.patrol_points)
                self._path = []
                self._path_timer = 0.0
            nav_facing = self._navigate_to(
                self.patrol_points[self.patrol_index], dt, recalc_interval=5.0
            )
            self.status = f"{nav_facing}_walk"
        else:
            self._nav_mode = "idle"
            self.direction = pygame.math.Vector2()
            self.status = "down_idle" if "down_idle" in self.animations else "down_walk"

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
            wall = sprite.rect
            if not wall.colliderect(self.hitbox):
                continue
            if axis == "horizontal":
                push_left = self.hitbox.right - wall.left
                push_right = wall.right - self.hitbox.left
                if push_left < push_right:
                    self.hitbox.right = wall.left
                else:
                    self.hitbox.left = wall.right
                self.pos.x = self.hitbox.centerx
            else:
                push_up = self.hitbox.bottom - wall.top
                push_down = wall.bottom - self.hitbox.top
                if push_up < push_down:
                    self.hitbox.bottom = wall.top
                else:
                    self.hitbox.top = wall.bottom
                self.pos.y = self.hitbox.centery

    def _update_walk_status(self, dx: float, dy: float):
        if self.shooting or not self.status.endswith("_walk"):
            return
        # Use the intended direction vector, not the physics delta — collision
        # snapping produces floating-point noise that direction_name misreads as "down".
        if self.direction.length() > 0:
            facing = direction_name(
                self.direction.x, self.direction.y, self.get_facing()
            )
            self.status = f"{facing}_walk"

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

        self._check_stuck(dt)
        self._update_ai(dt)
        if not self.shooting:
            prev_x, prev_y = self.pos.x, self.pos.y
            self._move(dt)
            self._update_walk_status(self.pos.x - prev_x, self.pos.y - prev_y)
        self._animate(dt)

        self._debug_print_timer += dt
        if self._debug_print_timer >= self.DEBUG_PRINT_INTERVAL:
            self._debug_print_timer = 0.0
            dist = self.pos.distance_to(self.player.pos)
            wp = (
                f"({self._path[0][0]:.0f},{self._path[0][1]:.0f})"
                if self._path
                else "None"
            )
            print(
                f"[enemy {self.enemy_id} {self.pokemon}] "
                f"pos=({self.pos.x:.0f},{self.pos.y:.0f}) "
                f"dist={dist:.0f} mode={self._nav_mode} "
                f"cooldown={self.attack_cooldown:.1f} "
                f"stuck={self._stuck_count} next_wp={wp} "
                f"shooting={self.shooting} status={self.status} "
                f"PATH LEN: {len(self._path)}"
            )

    @property
    def ground_y(self):
        return self.hitbox.bottom
