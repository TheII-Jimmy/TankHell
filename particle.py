import pygame, random
from settings import *

class Particle:
    def __init__(self, pos, color):
        self.pos      = pygame.Vector2(pos)
        self.color    = color
        self.size     = random.randint(3, 8)
        self.lifetime = random.uniform(20, 45)
        self.velocity = pygame.Vector2(
            random.uniform(-3, 3),
            random.uniform(-5, -1)
        )
        self.is_dead  = False

    def update(self):
        self.pos      += self.velocity
        self.velocity.y += 0.2   # gravity on particles
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.is_dead = True

    def draw(self, screen):
        pygame.draw.circle(screen, self.color,
                           (int(self.pos.x), int(self.pos.y)), self.size)
