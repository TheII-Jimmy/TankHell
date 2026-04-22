import pygame, math
from settings import *

class Shell:
    def __init__(self, pos, angle, power, shell_type, owner_id):
        self.pos        = pygame.Vector2(pos)
        self.prev_pos   = pygame.Vector2(self.pos)
        self.shell_type = shell_type
        self.owner_id   = owner_id
        self.is_active  = True

        stats = SHELLS[shell_type]
        self.damage           = stats["damage"]
        self.explosion_radius = stats["radius"]
        self.wind_resistance  = stats["wind_resistance"]
        self.damage_falloff   = 0.5
        self.gravity          = SHELL_GRAVITY * stats.get("gravity_multiplier", 1.0)
        self.timer            = 0.0
        self.bounces_left     = stats.get("bounce", 0)
        self.particle_count   = stats.get("particle_count", 25)
        self.particle_color   = stats.get("particle_color", BLACK)
        self.trail_color      = stats.get("trail_color", BLACK)
        self.trail            = []
        self.trail_timer      = 0.0
        self.trail_duration   = 1.0
        self.trail_spacing    = 0.05

        # Physics: convert angle + power into a velocity vector
        rad = math.radians(angle)
        speed = power * 10.0 * stats.get("speed_multiplier", 1.0)
        self.velocity = pygame.Vector2(
            math.cos(rad) * speed,
           -math.sin(rad) * speed   # negative because y-axis is flipped
        )

    def update(self, dt, wind=0.0):
        self.prev_pos = pygame.Vector2(self.pos)
        self.velocity.y += self.gravity * dt
        self.velocity.x += wind*25 * self.wind_resistance * dt
        self.pos += self.velocity * dt
        self.timer += dt

        self.trail_timer += dt
        if self.trail_timer >= self.trail_spacing:
            self.trail_timer = 0.0
            self.trail.append([pygame.Vector2(self.prev_pos), 0.0])

        for trail_point in self.trail:
            trail_point[1] += dt
        self.trail = [p for p in self.trail if p[1] <= self.trail_duration]

    def _get_surface_normal(self, terrain, cx, cy, sample_radius=4):
        """
        Samples the terrain mask around the impact point to find the surface gradient.
        Returns a normalized Vector2 pointing perpendicular (away) from the surface.
        """
        nx = 0
        ny = 0
        w, h = terrain.mask.get_size()
        
        # Sample points in a grid around the impact point
        for dx in range(-sample_radius, sample_radius + 1):
            for dy in range(-sample_radius, sample_radius + 1):
                x = int(cx + dx)
                y = int(cy + dy)
                
                # Check bounds
                if 0 <= x < w and 0 <= y < h:
                    # If the pixel is solid ground, push the normal away from it
                    if terrain.mask.get_at((x, y)):
                        nx -= dx
                        ny -= dy
                        
        normal = pygame.Vector2(nx, ny)
        
        # Fallback if somehow hit a perfectly isolated pixel or flat ground
        if normal.length_squared() == 0:
            return pygame.Vector2(0, -1) # Default straight up
            
        return normal.normalize()

    def _bounce_off_terrain(self, terrain):
        self.pos = pygame.Vector2(self.prev_pos)
        
        # Back out of the collision slightly so we aren't stuck inside the mask
        if self.velocity.length_squared() > 0.0001:
            step = self.velocity.normalize() * 1
            for _ in range(20):
                x = int(self.pos.x)
                y = int(self.pos.y)
                if x < 0 or x >= terrain.width or y < 0 or y >= terrain.height:
                    break
                if not terrain.mask.get_at((x, y)):
                    break
                self.pos -= step

        # Get the angle (normal) of the sloped ground
        normal = self._get_surface_normal(terrain, self.pos.x, self.pos.y, sample_radius=4)
        
        # Reflect the shell's velocity across the ground's normal
        self.velocity = self.velocity.reflect(normal)
        
        # Apply energy loss (restitution/bounciness)
        bounciness = 0.67 # Adjust this (0.0 to 1.0) to make it more/less bouncy
        self.velocity *= bounciness
        
        self.bounces_left -= 1

    def check_collision(self, terrain, tanks):
        # Returns "terrain", "tank", or None
        x = int(self.pos.x)
        y = int(self.pos.y)
        w, h = terrain.mask.get_size()
        if 0 <= x < w and 0 <= y < h and terrain.mask.get_at((x, y)):
            if self.bounces_left > 0:
                self._bounce_off_terrain(terrain)
                return None
            self.is_active = False
            return "terrain"
        for tank in tanks:
            if tank.is_alive and tank.player_id != self.owner_id and tank.rect.collidepoint(self.pos):
                self.is_active = False
                return "tank"
        return None

    def draw(self, surface):
        for idx, (pos, age) in enumerate(self.trail):
            if idx % 2 != 0:
                continue
            fade = 1.0 - (age / self.trail_duration)
            alpha = max(80, int(255 * fade))
            radius = 2
            r, g, b = self.trail_color 
            trail_surf = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(trail_surf, (r, g, b, alpha), (radius + 1, radius + 1), radius)
            surface.blit(trail_surf, (int(pos.x) - radius - 1, int(pos.y) - radius - 1))

        pygame.draw.circle(surface, self.trail_color,
                           (int(self.pos.x), int(self.pos.y)), 6)
