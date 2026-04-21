import math
from pathlib import Path

import pygame
from settings import *

ASSET_DIR = Path(__file__).resolve().parent / "assets" / "images"
TANK_SPRITES = {
    RED: pygame.image.load(str(ASSET_DIR / "red_tank.png")),
    BLUE: pygame.image.load(str(ASSET_DIR / "blue_tank.png")),
}

class Tank:
    def __init__(self, x, y, player_id, color):
        self.pos        = pygame.Vector2(x, y)
        self.player_id  = player_id
        self.color      = color
        self.health     = TANK_MAX_HEALTH
        self.armor      = 1.0        # multiplier: 1.0 = no reduction
        self.oil        = TANK_MAX_OIL
        self.angle      = 45.0       # barrel angle (0-90)
        self.power      = 50.0
        self.facing_left = False
        self.is_alive   = True
        self.current_shell = "standard"
        self.shell_list = {
            "standard": 5,
            "splash": 4,
            "shotgun": 3,
            "nuke": 1,
            "bouncy": 2,
            "triple_bounce": 2,
            "lazer": 3,
            "crazy_cluster": 2,
            "explosive": 2,
            "rapid": 3,
        }
        self.vel_y      = 0.0
        self.on_ground  = False

        self.sprite = TANK_SPRITES.get(self.color, TANK_SPRITES[RED])
        self.width, self.height = self.sprite.get_size()
        self.rect = self.sprite.get_rect(center=(x, y))
        self.prev_pos = pygame.Vector2(self.pos)
        # Adjustable barrel placement: edit this to align the barrel with the sprite.
        self.barrel_pivot = pygame.Vector2(self.width * 0.47, self.height * 0.25)
        self.barrel_length = 44
        self.barrel_width = 4

        # Stats tracking
        self.accuracy       = 0.0
        self.time_taken     = 0.0
        self.movedistance   = 0.0
        self._shots_fired   = 0
        self._shots_hit     = 0

    def draw(self, surface):
        image = self.sprite
        if self.facing_left:
            image = pygame.transform.flip(self.sprite, True, False)

        image_rect = image.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        surface.blit(image, image_rect)
        self._draw_barrel(surface, image_rect)

    def _draw_barrel(self, surface, image_rect):
        pivot = pygame.Vector2(self.barrel_pivot)
        if self.facing_left:
            pivot.x = self.width - pivot.x - 1

        pivot_pos = pygame.Vector2(image_rect.topleft) + pivot
        barrel_angle = self.angle if not self.facing_left else 180 - self.angle
        direction = pygame.Vector2(math.cos(math.radians(barrel_angle)),
                                   -math.sin(math.radians(barrel_angle)))
        barrel_end = pivot_pos + direction * self.barrel_length

        # Draw a black outline behind the barrel
        pygame.draw.line(surface,
                         BLACK,
                         (int(pivot_pos.x), int(pivot_pos.y)),
                         (int(barrel_end.x), int(barrel_end.y)),
                         self.barrel_width + 2)
        pygame.draw.line(surface,
                         self.color,
                         (int(pivot_pos.x), int(pivot_pos.y)),
                         (int(barrel_end.x), int(barrel_end.y)),
                         self.barrel_width)

    def update(self, terrain, dt):
        # Gravity always acts on the tank; it will land on terrain and fall through holes.
        self.vel_y += TANK_GRAVITY * dt
        self.pos.y += self.vel_y * dt

        self._resolve_terrain_collision(terrain)
        self._clamp_to_screen()
        self.rect.topleft = (int(self.pos.x) - self.width // 2,
                              int(self.pos.y) - self.height // 2)

    def _resolve_terrain_collision(self, terrain):
        surface_y = terrain.get_y_at(int(self.pos.x))
        bottom_y = self.pos.y + self.height / 2

        if bottom_y >= surface_y:
            target_y = surface_y - self.height / 2
            climb = max(0.0, self.prev_pos.y - target_y)
            if climb > 30:
                self.pos = pygame.Vector2(self.prev_pos)
                self.vel_y = 0.0
                self.on_ground = True
            else:
                self.pos.y = target_y
                self.vel_y = 0.0
                self.on_ground = True
        else:
            self.on_ground = False

    def _clamp_to_screen(self):
        half_width = TANK_WIDTH / 2
        self.pos.x = max(half_width, min(self.pos.x, SCREEN_WIDTH - half_width))

    def take_dmg(self, amount):
        actual = amount * self.armor
        self.health -= actual
        if self.health <= 0:
            self.health = 0
            self.is_alive = False

    def move(self, direction, dt, terrain=None):
        # direction: -1 = left, 1 = right
        self.facing_left = (direction == -1)
        if self.oil <= 0:
            return

        self.prev_pos = pygame.Vector2(self.pos)
        dist = TANK_MOVE_SPEED * dt
        target_x = self.pos.x + direction * dist
        half_width = self.width / 2
        clamped_x = max(half_width, min(target_x, SCREEN_WIDTH - half_width))
        movement = clamped_x - self.pos.x

        if abs(movement) < 1e-4:
            return

        if terrain is not None:
            current_x = max(0, min(int(self.pos.x), terrain.width - 1))
            next_x = max(0, min(int(clamped_x), terrain.width - 1))
            current_y = terrain.get_y_at(current_x)
            next_y = terrain.get_y_at(next_x)

            max_climb = 20
            if current_y - next_y > max_climb:
                return

        self.pos.x = clamped_x
        moved = abs(self.pos.x - self.prev_pos.x)
        self.oil = max(0, self.oil - moved)
        self.movedistance += moved

    def _get_shell_spawn_pos(self):
        pivot = pygame.Vector2(self.barrel_pivot)
        if self.facing_left:
            pivot.x = self.width - pivot.x - 1

        image_rect = self.sprite.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        pivot_pos = pygame.Vector2(image_rect.topleft) + pivot
        barrel_angle = self.angle if not self.facing_left else 180 - self.angle
        direction = pygame.Vector2(math.cos(math.radians(barrel_angle)),
                                   -math.sin(math.radians(barrel_angle)))
        return pivot_pos + direction * (self.barrel_length + 10)

    def get_aim_points(self, wind=0.0, steps=80, dt=0.04):
        stats = SHELLS.get(self.current_shell, SHELLS["standard"])
        speed_multiplier = stats.get("speed_multiplier", 1.0)
        gravity_multiplier = stats.get("gravity_multiplier", 1.0)
        wind_resistance = stats.get("wind_resistance", 1.0)

        start = self._get_shell_spawn_pos()
        shell_angle = self.angle if not self.facing_left else 180 - self.angle
        rad = math.radians(shell_angle)
        speed = self.power * 10.0 * speed_multiplier
        velocity = pygame.Vector2(math.cos(rad), -math.sin(rad)) * speed
        position = pygame.Vector2(start)
        points = []

        for i in range(steps):
            points.append(pygame.Vector2(position))
            velocity.y += SHELL_GRAVITY * gravity_multiplier * dt
            velocity.x += wind * wind_resistance * dt
            position += velocity * dt
            if position.y > SCREEN_HEIGHT:
                break
        return points

    def shoot(self):
        from shell import Shell

        # If the selected shell is out of ammo, use standard instead.
        if self.shell_list.get(self.current_shell, 0) <= 0:
            self.current_shell = "standard"

        stats = SHELLS.get(self.current_shell, SHELLS["standard"])
        count = stats.get("shell_count", 1)
        spread = stats.get("spread", 0)

        self.shell_list[self.current_shell] = max(
            0, self.shell_list.get(self.current_shell, 0) - 1
        )
        self._shots_fired += 1

        shell_angle = self.angle if not self.facing_left else 180 - self.angle
        shells = []
        for i in range(count):
            angle_offset = 0
            if count > 1:
                angle_offset = spread * ((i - (count - 1) / 2) / (count - 1))
            shells.append(
                Shell(
                    pos        = self._get_shell_spawn_pos(),
                    angle      = shell_angle + angle_offset,
                    power      = self.power,
                    shell_type = self.current_shell,
                    owner_id   = self.player_id,
                )
            )
        return shells
