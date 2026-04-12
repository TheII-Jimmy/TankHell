import pygame
from settings import *
from game    import Game

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(TITLE)

    game = Game(screen)
    game.run()

if __name__ == "__main__":
    main()
