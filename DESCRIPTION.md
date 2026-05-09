# Project Description

## 1. Project Overview

- **Project Name:** TankHell
- **Brief Description:**

  TankHell is a 2D physics-based artillery game in which two tanks face off on a procedurally generated landscape, taking turns to aim, adjust power, and fire a variety of shells at one another. Every shot is governed by real-time kinematic simulation — gravity, wind, and shell-specific physics. The terrain itself is fully destructible: each explosion carves a circular hole out of the landscape, permanently altering the landscape, and future trajectories. A match ends when one tank's health reaches zero.

  The game supports three modes of play: Player vs. Player, Player vs. AI, and AI vs. AI. The AI system uses an internal ballistic solver to calculate the optimal angle and power for any given shot, with tunable accuracy offsets to produce Easy, Medium, and Hard opponents. A built-in statistics module records per-match data — accuracy, time per shot, distance moved, damage dealt by shell type, and total match duration — and presents the results in an interactive Tkinter dashboard with Matplotlib visualizations.

- **Problem Statement:**
  Turn-based artillery games are compelling because they blend strategic thinking with physics intuition. However, many implementations use simplistic AI opponents or lack meaningful post-game feedback. TankHell aims to provide a complete, self-contained experience: a fair but challenging AI adversary, a rich ammunition system that rewards tactical selection, destructible terrain that creates an evolving battlefield, and a data pipeline that lets players review and improve their performance over time.

- **Target Users:**
  - Casual players who enjoy turn-based physics games
  - People who are interest in physics sandbox games
  - For anyone who like tanks

- **Key Features:**
  - Procedural Terrain Generation using Perlin noise
  - Destructible Environment with real-time mask updates
  - Player vs. Bots (AI logic with Easy, Medium, and Hard difficulties)
  - Varied Shell Types with unique physics and damage profiles
  - Projectile kinematics (gravity, wind resistance, bounce)
  - Visual particle effects for explosions
  - Data and statistics tracking exported to CSV with GUI dashboard

- **Links:**
   - **Proposal:** [TankHell Project Proposal](TankHell_Project_Proposal.pdf)
   - **Github:** [TankHell Github Repositories](https://github.com/TheII-Jimmy/TankHell)
   - **Youtube Presentation:** [TankHell Presentation](https://youtube.com)
---

## 2. Concept

### 2.1 Background

While browsing the steam store page: a ditital distribution platform for PC games, I came across a game called ShellShock Live, a 2D physics based tank game where tanks shoot at each other with various types of shells and superpower, and I immediately got intrested in it. So when the opportunity to make a game I want to try to recreate this game. I do not want to just copy the game and summit it, so I add a few more fetures in my game such as; procedural terrain generation, AI system that challenges the player, and a data collection system to see your own improvement.

### 2.2 Objectives

- Implement a complete turn-based artillery game loop with realistic 2D projectile physics (gravity, wind, shell-specific speed and gravity multipliers, and terrain bounce).
- Generate unique, natural-looking battlefields procedurally for every match using layered 1D Perlin noise.
- Build a rule-based AI system capable of solving the ballistic equations for any shot and applying calibrated inaccuracy offsets to produce three distinct difficulty levels.
- Design a rich ammunition system with ten distinct shell types, each with unique attributes (explosion radius, damage, shell count, spread, bounce count, and visual trail).
- Record granular per-match statistics — accuracy, time per shot, damage per shell type, distance moved, and match duration — and display them as interactive charts in a post-game dashboard.
- Provide a fully destructible terrain system where every explosion updates both the rendered surface and the collision mask in real time.

---

## 3. UML Class Diagram

[UML Class Diagram](UML_classdiagram.pdf)

---

## 4. Object-Oriented Programming Implementation

- **Game:** The central controller and game-loop driver. Manages game state transitions (main menu → playing → game over), owns the list of active tanks, shells, and particles, coordinates turn progression, handles all user input events, delegates rendering to per-system draw methods, and invokes the `StatsManager` at match end to persist data.

- **Tank:** Represents a player-controlled or AI-controlled tank. Encapsulates position, health, fuel (oil), angle, power, facing direction, and the shell inventory. Provides movement with terrain-aware slope checking, gravity simulation, barrel drawing, shell spawning via `shoot()`, and a trajectory-preview helper `get_aim_points()`. Tracks per-turn statistics (`_shots_fired`, `_shots_hit`, `time_taken`, `movedistance`).

- **Shell:** A live projectile. Stores velocity, shell type, owner identity, remaining bounce count, and a fading trail buffer. On each frame, `update()` advances position using Euler integration with gravity and wind. `check_collision()` samples the terrain mask and tank rectangles; if a surface is struck and bounces remain, `_bounce_off_terrain()` reflects the velocity across the computed surface normal with energy loss.

- **Terrain:** Procedurally generated battlefield. `generate_terrain()` builds a height map from layered 1D Perlin noise and composites a textured surface (dirt + grass + shadow layers) before baking a collision mask. `destroy()` cuts a circle from the surface image and regenerates the mask, enabling real-time destructibility. `get_y_at(x)` scans the mask vertically to return the surface height at any column.

- **Particle:** A single spark in an explosion effect. Spawned in batches by `Game._explode()`, each particle has a random velocity, size, color, and lifetime. `update()` applies gravity and decrements lifetime; the particle marks itself dead when the timer expires.

- **TankAI (base) / EasyAI / MediumAI / HardAI:** A three-phase finite state machine (Move → Aim → Shoot). The base class drives movement with optional randomised repositioning and calls `_plan_turn()` to invoke the ballistic solver `_solve_angle_and_power()`, which performs a coarse grid search followed by a fine-grained refinement pass. Subclasses override `_apply_accuracy_offset()` to introduce calibrated error: `EasyAI` uses a ±260 px offset with a perfect shot every 6 turns; `MediumAI` uses ±120 px with a perfect shot every 3 turns; `HardAI` fires with zero offset.

- **StatsConfig:** A pure configuration class. Defines the output directory, CSV file names and headers for each data category, the UI colour theme, and font size constants.

- **StatsManager:** Handles all data persistence. Initialises CSV files on first run, appends rows via `append_row()`, reads data back as Pandas DataFrames via `read_csv()`, auto-increments `game_number` across sessions, and aggregates a full match's data in `record_match()`.

- **StatsGUI:** Constructs a Tkinter window with a tabbed `ttk.Notebook`. Each tab renders a Matplotlib chart embedded via `FigureCanvasTkAgg`: a dual pie chart for accuracy, line charts for time per shot and distance moved, a bar chart for average damage per shell type, and a filled area chart for match duration over time.

---

## 5. Statistical Data

### 5.1 Data Recording Method

Statistics are collected passively during gameplay. Each `Tank` instance maintains running counters (`_shots_fired`, `_shots_hit`, `time_taken`, `movedistance`) that are updated on every relevant event — a shot fired, a hit registered, a turn ended, a move step completed. The `Game` class maintains a `_shell_damage_log` dictionary that accumulates total damage dealt per shell type within the match.

At match end, `StatsManager.record_match()` is called with the list of tanks, the total match duration, and the damage log. The method computes derived statistics (accuracy percentage, average time per shot), assigns an auto-incremented game number by reading the existing CSV, and appends one row per relevant entity to each of five CSV files stored in the `data/` directory.

### 5.2 Data Features

| Dataset | Key Columns | Description |
|---|---|---|
| `stats_accuracy.csv` | `game_number`, `player_id`, `shots_fired`, `shots_hit`, `accuracy_pct` | Hit rate per player per match |
| `stats_time_per_shot.csv` | `game_number`, `player_id`, `avg_time_per_shot` | Average thinking time per shot |
| `stats_damage_per_shell.csv` | `game_number`, `shell_type`, `damage_dealt` | Total damage output per shell type |
| `stats_move_distance.csv` | `game_number`, `player_id`, `total_distance` | Total pixels moved per player per match |
| `stats_match_duration.csv` | `game_number`, `duration_seconds` | Total match length in seconds |

Data accumulates across sessions, enabling cross-match trend analysis in the statistics dashboard. All numeric fields are stored as plain numbers (integer or float rounded to two decimal places) to allow straightforward aggregation with Pandas.

---

## 6. Changed Proposed Features

- **Scatter shell rework:** The scatter / crazy-cluster shell was originally intended to deploy sub-munitions that fall vertically from above the target. In the final implementation it fires multiple shells in a horizontal spread from the barrel instead.

---

## 7. External Sources

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
