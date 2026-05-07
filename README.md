# YOUR_PROJECT_NAME

## Project Description

- Project by: Suppamok Tosranon
- Game Genre: Physics Sandbox, Simulation

TankHell is a physics based simulation game where two or more tanks shoot at each other in a 2D plane. Inspired by the game ShellShock Live, players have access to many types of shells and ammo to choose from, such as splash shells, napalm strikes, and orbital strikes. The game builds upon this by implementing a progression and unlocking system for various tank shells, giving players a long-term objective. Additionally, to make the gameplay more dynamic and exciting, the terrain can be destroyed when a shell hits the ground and explodes.

---

## Installation
To Clone this project:
```sh
git clone https://github.com/TheII-Jimmy/TankHell
```

To create and run Python Environment for This project:

Window:
```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Mac:
```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Running Guide
After activate Python Environment of this project, you can process to run the game by:

Window:
```bat
python game.py
```

Mac:
```sh
python3 game.py
```

---

## Tutorial / Usage
Use the following controls and menus to play the game:
- **Aiming:** Use the Up/Down arrow keys to adjust the angle of your tank's barrel.
- **Movement:** Use the Left/Right arrow keys to move your tank across the terrain, which is limited by the amount of fuel/oil you have left.
- **Power:** Use the W/S keys to adjust the shot strength or power.
- **Shell Selection:** Open the shell menu to choose your ammunition.
- **Menu Navigation:** Navigate the game menus (like the main menu and the shell selection menu) using your mouse to click and select your desired options.

---

## Game Features
- **PvP and Single Player Modes:** Play against friends in a two player mode, or play solo in a single player mode.
- **Player vs. Bots (AI Logic):** Fight against enemy AI tanks that use rule-based logic to evaluate fuel limits for movement, and calculate the necessary barrel angle and shot power to hit you.
- **Procedural Terrain Generation:** Maps are generated programmatically using Perlin noise algorithms to create random, natural-looking hilly landscapes.
- **Destructible Environment:** The terrain is fully destructible; when a shell explodes, it cuts a circle out of the image and dynamically updates the collision mask.
- **Projectile Kinematics:** Shells travel using realistic physics calculations that update frame-by-frame, factoring in a constant downward gravity force and global wind resistance.
- **Varied Type of Shells:** Access a wide dictionary of shell types with unique attributes, including splash damage, specific explosion radius, and damage falloff.
- **Progression System:** An integrated unlocking system for different tank shells provides a continuous, long-term objective.
- **Visual Particle Effects:** Includes a particle system that renders visual effects for explosions.
- **Data and Stat Tracking:** Automatically tracks detailed player statistics (such as accuracy, distance moved, and time taken per turn) and exports this tracked data into a CSV file at the end of each match.

---

## Known Bugs
- When the barrel is too close the terrain, it can clip through and shoot thorugh the terrain.
    - reason: when the tank shoot, its shell will spawn at the tip of the barrel, so if the tip is not in the terrain but the barrel is, the shell will be able to shoot thorugh it.
- If the width of terrain is too small, there's a chance that the shell will travel through it.
    - reason: the shell travel too fast and collosion detection doesn't activate

---

## Unfinished Works
- The scatter shell could be chnage to falling from the sky instead

---

## External sources
Acknowledge to:

1. **Dirt texture** — "gravelly_sand_diff_1k.png"
   Source: [https://polyhaven.com/a/gravelly_sand](https://polyhaven.com/a/gravelly_sand)
   License: CC0 (Public Domain)

2. **Grass texture** — "Grass005_1K-PNG_Color.png"
   Source: [https://ambientcg.com/view?id=Grass005](https://ambientcg.com/view?id=Grass005)
   License: CC0 (Public Domain)

3. **Tank shooting sound effect** — "tanks_shooting.wav"
   Creator: qubodup
   Source: [https://freesound.org/people/qubodup/sounds/189344/](https://freesound.org/people/qubodup/sounds/189344/)
   License: CC BY 3.0

4. **Pygame** — Game framework used for rendering, input handling, and collision detection.
   Source: [https://www.pygame.org](https://www.pygame.org) | License: LGPL

5. **Matplotlib** — Used for rendering statistical charts in the post-game dashboard.
   Source: [https://matplotlib.org](https://matplotlib.org) | License: PSF-based

6. **Pandas** — Used for reading and aggregating CSV data in the statistics module.
   Source: [https://pandas.pydata.org](https://pandas.pydata.org) | License: BSD 3-Clause

