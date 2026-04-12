import pygame, random, math
from settings import *

class Terrain:
    def __init__(self):
        self.width  = SCREEN_WIDTH
        self.height = SCREEN_HEIGHT
        self.image  = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.dirt_tex = pygame.image.load("assets/images/gravelly_sand_diff_1k.png").convert_alpha()
        self.grass_tex = pygame.image.load("assets/images/Grass005_1K-PNG_Color.png").convert_alpha()
        self.rect   = (0, 0)
        self.points = []
        self.mask   = None
        self.generate_terrain()

    def generate_terrain(self):
        self.image.fill((0, 0, 0, 0))
        self.points = self._perlin_noise()

        poly = [(0, SCREEN_HEIGHT)] + self.points + [(SCREEN_WIDTH, SCREEN_HEIGHT)]

        terrain_mask = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(terrain_mask, (255, 255, 255), poly)

        base_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for x in range(0, SCREEN_WIDTH, self.dirt_tex.get_width()):
            for y in range(0, SCREEN_HEIGHT, self.dirt_tex.get_height()):
                base_surface.blit(self.dirt_tex, (x, y))
        base_surface.blit(terrain_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        grass_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for x in range(0, SCREEN_WIDTH, self.grass_tex.get_width()):
            for y in range(0, SCREEN_HEIGHT, self.grass_tex.get_height()):
                grass_surface.blit(self.grass_tex, (x, y))

        grass_mask = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        blend_height = 90
        for x in range(SCREEN_WIDTH):
            top_y = self._terrain_height_at(x)
            for dy in range(blend_height):
                y = top_y + dy
                if y >= SCREEN_HEIGHT:
                    break
                alpha = 255 - int(255 * (dy / blend_height))
                grass_mask.set_at((x, y), (255, 255, 255, alpha))

        grass_mask.blit(terrain_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        grass_surface.blit(grass_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        base_surface.blit(grass_surface, (0, 0))

        shadow_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        shadow_height = 16
        max_shadow_alpha = 150      # higher = darker shadow
        for x in range(SCREEN_WIDTH):
            top_y = self._terrain_height_at(x)
            for dy in range(shadow_height):
                y = top_y + dy
                if y >= SCREEN_HEIGHT:
                    break
                alpha = max_shadow_alpha - int(max_shadow_alpha * (dy / shadow_height))
                shadow_surface.set_at((x, y), (*BROWN, alpha))

        base_surface.blit(shadow_surface, (0, 0))
        self.image = base_surface
        self.mask = pygame.mask.from_surface(self.image)

    def _perlin_noise(self):
        segments = 500      # Increased for smoother drawing of large curves
        gradients = [random.uniform(-1.0, 1.0) for _ in range(segments * 5)]
        result = []

        vertical_scale = 350    # Higher = taller mountains/deeper valleys
        base_freq = 8.0         # Lower = wider, more majestic hills
        persistance = 0.4      # How much the smaller "bumps" affect the shape

        for i in range(segments + 1):
            x = i * SCREEN_WIDTH / segments
            noise = 0.0
            amplitude = 1.0
            frequency = 1.0
            max_amplitude = 0.0

            for _ in range(3):
                sample_x = (i / segments) * frequency * base_freq
                noise += amplitude * self._perlin_1d(sample_x, gradients)

                max_amplitude += amplitude
                amplitude *= persistance
                frequency *= 2.0

            noise /= max_amplitude

            if noise > 0:
                noise = pow(noise, 1.2)

            y = int(SCREEN_HEIGHT * 0.5 + noise * vertical_scale)
            y = max(100, min(SCREEN_HEIGHT - 50, y))
            result.append((int(x), y))

        return result

    def _terrain_height_at(self, x):
        if not self.points:
            return SCREEN_HEIGHT

        x = max(0, min(x, SCREEN_WIDTH))
        for i in range(len(self.points) - 1):
            x0, y0 = self.points[i]
            x1, y1 = self.points[i + 1]
            if x0 <= x <= x1:
                if x1 == x0:
                    return y0
                t = (x - x0) / (x1 - x0)
                return int(y0 + (y1 - y0) * t)

        return self.points[-1][1]

    def _perlin_1d(self, x, gradients):
        x0 = int(math.floor(x))
        x1 = x0 + 1
        sx = x - x0
        u = sx * sx * sx * (sx * (sx * 6 - 15) + 10)
        g0 = gradients[x0 % len(gradients)]
        g1 = gradients[x1 % len(gradients)]
        return (1 - u) * (x - x0) * g0 + u * (x - x1) * g1

    def destroy(self, impact_pos, radius):
        pygame.draw.circle(self.image, (0, 0, 0, 0),
                           (int(impact_pos.x), int(impact_pos.y)),
                           int(radius))
        # Re-blit with SRCALPHA to cut hole, then update mask
        self.mask = pygame.mask.from_surface(self.image)

    def get_y_at(self, x):
        x = max(0, min(x, self.width - 1))
        for y in range(self.height):
            if self.mask.get_at((int(x), y)):
                return y
        return self.height

    def draw(self, screen):
        screen.blit(self.image, self.rect)
