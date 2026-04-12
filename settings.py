# settings.py
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TITLE = "TankHell"

SHELL_GRAVITY = 900.0
WIND_MAX = 5.0

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED   = (200, 50, 50)
GREEN = (50, 180, 50)
SKY_BLUE = (100, 160, 220)
BROWN = (69, 42, 6)

# Tank settings
TANK_WIDTH      = 54
TANK_HEIGHT     = 21
TANK_MAX_HEALTH = 100
TANK_MAX_OIL    = 200
TANK_MAX_POWER  = 100
TANK_MOVE_SPEED = 180.0   # pixels per second
TANK_GRAVITY    = 900.0   # pixels per second squared

BLUE = (60, 120, 220)
YELLOW = (255, 235, 80)
ORANGE = (255, 150, 0)
CYAN = (100, 220, 255)

# Shell types - expand this later
SHELLS = {
    "standard": {
        "damage": 30,
        "radius": 40,
        "wind_resistance": 1.0,
        "bounce": 0,
        "shell_count": 1,
        "spread": 0,
        "particle_count": 25,
        "particle_color": RED,
        "trail_color": BLACK,
    },
    "splash": {
        "damage": 20,
        "radius": 80,
        "wind_resistance": 0.8,
        "bounce": 0,
        "shell_count": 1,
        "spread": 0,
        "particle_count": 40,
        "particle_color": YELLOW,
        "trail_color": BLACK,
    },
    "shotgun": {
        "damage": 15,
        "radius": 25,
        "wind_resistance": 1.2,
        "bounce": 0,
        "shell_count": 3,
        "spread": 12,
        "particle_count": 20,
        "particle_color": YELLOW,
        "trail_color": BLACK,
    },
    "nuke": {
        "damage": 80,
        "radius": 120,
        "wind_resistance": 0.6,
        "bounce": 0,
        "shell_count": 1,
        "spread": 0,
        "particle_count": 80,
        "particle_color": ORANGE,
        "trail_color": ORANGE,
    },
    "bouncy": {
        "damage": 25,
        "radius": 50,
        "wind_resistance": 0.9,
        "bounce": 2,
        "shell_count": 1,
        "spread": 0,
        "particle_count": 35,
        "particle_color": CYAN,
        "trail_color": CYAN,
    },
}
