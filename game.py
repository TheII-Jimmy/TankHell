import math, pygame, random, sys
import multiprocessing
from settings import *
from tank    import Tank
from terrain import Terrain
from particle import Particle
from ai      import create_ai
from stats import StatsManager, StatsGUI


def run_stats_gui():
    """Helper to launch the stats window in an independent process."""
    manager = StatsManager()
    gui = StatsGUI(manager)
    gui.open_window()


_MODES = [
    ("PvP",    None),
    ("Easy",   "easy"),
    ("Medium", "medium"),
    ("Hard",   "hard"),
]


class Game:
    def __init__(self, screen):
        self.screen     = screen
        self.clock      = pygame.time.Clock()
        self.terrain    = Terrain()
        self.wind       = self._random_wind()

        try:
            self.shoot_sound = pygame.mixer.Sound("assets/tanks_shooting.wav")
            self.shoot_sound.set_volume(0.75)
        except FileNotFoundError:
            print("Warning: Audio file 'assets/tanks_shooting.wav' not found.")
            self.shoot_sound = None

        self.rounds     = 0
        self.matchduration     = 0.0
        self.game_state        = "main_menu"
        self.current_turn_index = 0
        self.active_shells = []
        self.particles     = []
        self.player_list   = []
        self.restart_button_rect = pygame.Rect(SCREEN_WIDTH - 150, 10, 140, 38)
        self.shell_menu_open = False
        self.shell_menu_button_rect = pygame.Rect(0, 0, 0, 0)
        self.shell_menu_item_rects = []
        
        # --- INIT STATS MANAGER ---
        self.stats_manager = StatsManager()

        self.cheat_sequence = []
        self.auto_loop_ai = None
        self.game_over_timer = 0.0

        self.ai_controllers = [None, None]
        self.ai_difficulties = [None, None]
        self.ai_turn_active = False

        self._mode_button_rects = []
        self._build_mode_buttons()
        
        self._ai_button_rects = []
        self._build_ai_menu_buttons()

        self._stats_button_rect = pygame.Rect(
            SCREEN_WIDTH // 2 - 100,
            SCREEN_HEIGHT // 2 + 110,
            200, 46,
        )

        self._shell_damage_log = {}
        self._turn_start_time  = 0.0
        self._stats_saved = False

        self._setup_players()

    def _build_mode_buttons(self):
        btn_w, btn_h = 200, 56
        gap          = 20
        total_w      = len(_MODES) * btn_w + (len(_MODES) - 1) * gap
        start_x      = SCREEN_WIDTH  // 2 - total_w // 2
        btn_y        = SCREEN_HEIGHT // 2 + 20

        self._mode_button_rects = []
        for i, (label, diff) in enumerate(_MODES):
            rect = pygame.Rect(start_x + i * (btn_w + gap), btn_y, btn_w, btn_h)
            self._mode_button_rects.append((label, diff, rect))

    def _build_ai_menu_buttons(self):
        btn_w, btn_h = 240, 56
        gap          = 20
        modes = [("Easy", "easy"), ("Medium", "medium"), ("Hard", "hard")]
        total_w      = len(modes) * btn_w + (len(modes) - 1) * gap
        start_x      = SCREEN_WIDTH  // 2 - total_w // 2
        btn_y        = SCREEN_HEIGHT // 2 + 20

        self._ai_button_rects = []
        for i, (label, diff) in enumerate(modes):
            rect = pygame.Rect(start_x + i * (btn_w + gap), btn_y, btn_w, btn_h)
            self._ai_button_rects.append((label, diff, rect))

    def _random_wind(self):
        return random.uniform(-WIND_MAX, WIND_MAX)

    def reset(self):
        self.terrain    = Terrain()
        self.wind       = self._random_wind()
        self.rounds     = 0
        self.matchduration = 0.0
        self.game_state = "main_menu"
        self.current_turn_index = 0
        self.active_shells = []
        self.particles     = []
        self.shell_menu_open = False
        self.shell_menu_item_rects = []
        
        self.ai_controllers  = [None, None]
        self.ai_difficulties = [None, None]
        self.ai_turn_active = False
        self.auto_loop_ai = None
        self.game_over_timer = 0.0
        self.end_reason = None

        self._shell_damage_log = {}
        self._turn_start_time  = 0.0
        self._stats_saved = False
        self.cheat_sequence = []
        
        self._setup_players()

    def _setup_players(self):
        y1 = self.terrain.get_y_at(200) - TANK_HEIGHT / 2
        y2 = self.terrain.get_y_at(SCREEN_WIDTH - 200) - TANK_HEIGHT / 2
        red_tank  = Tank(200,              y1, player_id=1, color=RED)
        blue_tank = Tank(SCREEN_WIDTH-200, y2, player_id=2, color=BLUE)
        blue_tank.facing_left = True
        self.player_list = [red_tank, blue_tank]

    @property
    def current_tank(self):
        return self.player_list[self.current_turn_index]

    def next_turn(self):
        tank = self.current_tank
        elapsed = self.matchduration - self._turn_start_time
        tank.time_taken += elapsed
        self._turn_start_time = self.matchduration

        self.shell_menu_open = False
        self.current_turn_index = (self.current_turn_index + 1) % len(self.player_list)
        if self.current_turn_index == 0:
            self.rounds += 1
            self._refuel_tanks()
            self.wind = self._random_wind()

        ai_controller = self.ai_controllers[self.current_turn_index]
        if ai_controller:
            ai_controller.reset()
            self.ai_turn_active = True
        else:
            self.ai_turn_active = False

    def _refuel_tanks(self):
        for tank in self.player_list:
            if tank.is_alive:
                tank.oil = TANK_MAX_OIL

    def _explode(self, shell):
        for _ in range(shell.particle_count):
            self.particles.append(Particle(shell.pos, shell.particle_color))

    def _apply_explosion_damage(self, shell):
        for tank in self.player_list:
            if not tank.is_alive:
                continue
            tank_center = pygame.Vector2(tank.rect.center)
            distance = tank_center.distance_to(shell.pos)
            if distance > shell.explosion_radius:
                continue
            damage_ratio = max(0.0, 1.0 - (distance / shell.explosion_radius))
            damage = shell.damage * damage_ratio
            tank.take_dmg(damage)

            if damage > 0:
                shooter = next(
                    (t for t in self.player_list if t.player_id == shell.owner_id), None
                )
                if shooter:
                    shooter._shots_hit += 1

                stype = shell.shell_type
                self._shell_damage_log[stype] = (
                    self._shell_damage_log.get(stype, 0.0) + damage
                )

    def _save_stats(self):
        if getattr(self, "_stats_saved", False):
            return
        if self.game_state not in ("playing", "game_over"):
            return
        if all(t._shots_fired == 0 for t in self.player_list):
            return

        self.stats_manager.record_match(self.player_list, self.matchduration, self._shell_damage_log)
        self._stats_saved = True

    def run(self):
        while True:
            dt_ms = self.clock.tick(FPS)
            dt = dt_ms / 1000.0
            self.matchduration += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if self.game_state == "game_over":
                        self._save_stats()
                    self.quit_game()
                self._handle_input(event)

            self.update(dt)
            self.draw()

    def _handle_input(self, event):
        # Catch the hidden cheat code to activate AI vs AI
        if event.type == pygame.KEYDOWN:
            if event.key in [pygame.K_UP, pygame.K_RIGHT, pygame.K_DOWN]:
                self.cheat_sequence.append(event.key)
                if len(self.cheat_sequence) > 5:
                    self.cheat_sequence.pop(0)

                target_seq = [pygame.K_UP, pygame.K_RIGHT, pygame.K_DOWN, pygame.K_DOWN, pygame.K_DOWN]
                if self.game_state == "main_menu" and self.cheat_sequence == target_seq:
                    self.game_state = "ai_menu"
                    self.cheat_sequence = []
                    return

        # General Restart Button Handling (Acts as 'Back' outside main menu)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.game_state in ("playing", "game_over", "ai_menu"):
                if self.restart_button_rect.collidepoint(event.pos):
                    self.reset()
                    return

        # Main Menu Controls
        if self.game_state == "main_menu":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for label, diff, rect in self._mode_button_rects:
                    if rect.collidepoint(event.pos):
                        self._start_game(diff)
                        return
                if self._stats_button_rect.collidepoint(event.pos):
                    # --- OOP UPDATE HERE ---
                    # Start the stats window using the new helper function
                    p = multiprocessing.Process(target=run_stats_gui)
                    p.daemon = True
                    p.start()
                    return

        # AI vs AI Menu Controls
        elif self.game_state == "ai_menu":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for label, diff, rect in self._ai_button_rects:
                    if rect.collidepoint(event.pos):
                        self._start_ai_vs_ai(diff)
                        return

        # In-Game Controls
        elif self.game_state == "playing" and not self.ai_turn_active:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.shell_menu_button_rect.collidepoint(event.pos):
                    self.shell_menu_open = not self.shell_menu_open
                    return

                if self.shell_menu_open:
                    if self._handle_shell_menu_click(event.pos):
                        return
                    self.shell_menu_open = False

            if event.type == pygame.KEYDOWN:
                if (event.key == pygame.K_SPACE
                        and not self.active_shells):
                    new_shells = self.current_tank.shoot()
                    self.active_shells.extend(new_shells)

                    if self.shoot_sound:
                        self.shoot_sound.play()

                    self.next_turn()

    def _start_game(self, difficulty):
        self.ai_difficulties = [None, difficulty]
        self.ai_controllers = [None, None]
        if difficulty is not None:
            self.ai_controllers[1] = create_ai(difficulty)
        self.ai_turn_active = False
        self._shell_damage_log = {}
        self._turn_start_time  = self.matchduration
        self._stats_saved = False
        self.game_state = "playing"

    def _start_ai_vs_ai(self, difficulty):
        self.auto_loop_ai = difficulty
        self.ai_difficulties = [difficulty, difficulty]
        self.ai_controllers = [create_ai(difficulty), create_ai(difficulty)]
        self._shell_damage_log = {}
        self._turn_start_time = self.matchduration
        self._stats_saved = False
        self.game_state = "playing"
        
        # Manually kick off the first AI's turn
        self.ai_turn_active = True
        self.ai_controllers[0].reset()

    def _handle_held_keys(self, dt):
        if self.active_shells or self.ai_turn_active:
            return

        pressed = pygame.key.get_pressed()
        tank = self.current_tank

        if pressed[pygame.K_LEFT]:
            tank.move(-1, dt, self.terrain)
        if pressed[pygame.K_RIGHT]:
            tank.move(1, dt, self.terrain)
        if pressed[pygame.K_UP]:
            tank.angle = min(90, tank.angle + 120 * dt)
        if pressed[pygame.K_DOWN]:
            tank.angle = max(0, tank.angle - 120 * dt)
        if pressed[pygame.K_w]:
            tank.power = min(TANK_MAX_POWER, tank.power + 1)
        if pressed[pygame.K_s]:
            tank.power = max(0, tank.power - 1)

    def _update_ai(self, dt):
        if not self.ai_turn_active or self.active_shells:
            return

        ai_tank = self.current_tank
        enemy_tank = self.player_list[(self.current_turn_index + 1) % len(self.player_list)]
        ai_controller = self.ai_controllers[self.current_turn_index]

        if not ai_tank.is_alive or not ai_controller:
            self.ai_turn_active = False
            return

        done = ai_controller.update(
            ai_tank, enemy_tank, self.terrain, self.wind, dt
        )
        if done:
            new_shells = ai_tank.shoot()
            self.active_shells.extend(new_shells)

            if self.shoot_sound:
                self.shoot_sound.play()

            self.ai_turn_active = False
            self.next_turn()

    def update(self, dt):
        # Handle auto-loop timer logic during game_over
        if self.game_state == "game_over":
            if self.auto_loop_ai:
                self.game_over_timer += dt
                if self.game_over_timer > 1.5:  # 1.5 second delay before restarting
                    diff = self.auto_loop_ai
                    self.reset()
                    self._start_ai_vs_ai(diff)
            
            # Still update particles so explosions fade
            for p in self.particles:
                p.update()
            self.particles = [p for p in self.particles if not p.is_dead]
            return

        if self.game_state != "playing":
            return

        self._handle_held_keys(dt)
        self._update_ai(dt)

        for tank in self.player_list:
            tank.update(self.terrain, dt)

        for shell in self.active_shells:
            shell.update(dt, self.wind)
            p = shell.pos
            if p.x < 0 or p.x > SCREEN_WIDTH or p.y > SCREEN_HEIGHT:
                shell.is_active = False
                continue

            result = shell.check_collision(self.terrain, self.player_list)
            if result in ("terrain", "tank"):
                self.terrain.destroy(shell.pos, shell.explosion_radius)
                self._explode(shell)
                self._apply_explosion_damage(shell)

        self.active_shells = [s for s in self.active_shells if s.is_active]

        alive = [t for t in self.player_list if t.is_alive]
        if len(alive) == 1:
            self._save_stats()
            self.game_state = "game_over"
            self.game_over_timer = 0.0
            self.end_reason = "win" if len(alive) == 1 else "draw"

        elif self.rounds >= 50:
            self._save_stats()
            self.game_state = "game_over"
            self.game_over_timer = 0.0
            self.end_reason = "draw" # Reached the 50 round limit

        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if not p.is_dead]

    def draw(self):
        self.screen.fill(SKY_BLUE)

        if self.game_state == "main_menu":
            self._draw_main_menu()
            
        elif self.game_state == "ai_menu":
            self._draw_ai_menu()

        elif self.game_state in ("playing", "game_over"):
            self.terrain.draw(self.screen)
            for tank in self.player_list:
                tank.draw(self.screen)

            if not self.active_shells:
                self._draw_aim_line(self.current_tank)

            for p in self.particles:
                p.draw(self.screen)
            for shell in self.active_shells:
                shell.draw(self.screen)
            self._draw_ui()
            self._draw_restart_button()

        if self.game_state == "game_over":
            font = pygame.font.SysFont(None, 72)
            msg = "DRAW" if getattr(self, 'end_reason', None) == "draw" else "GAME OVER"
            txt  = font.render(msg, True, WHITE)
            self.screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, 300))

        pygame.display.flip()

    def _draw_main_menu(self):
        font_big = pygame.font.SysFont(None, 80)
        title = font_big.render("TANKHELL", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 160))

        font_sub = pygame.font.SysFont(None, 36)
        sub = font_sub.render("Choose a game mode to start", True, (200, 220, 255))
        self.screen.blit(sub, (SCREEN_WIDTH//2 - sub.get_width()//2, 255))

        font_btn = pygame.font.SysFont(None, 38)
        mouse_pos = pygame.mouse.get_pos()

        colours = {
            "PvP":    ((80,  130, 200), (60,  110, 180)),
            "Easy":   ((60,  160,  70), (40,  130,  50)),
            "Medium": ((200, 150,  30), (170, 120,  20)),
            "Hard":   ((190,  50,  50), (160,  30,  30)),
        }

        for label, diff, rect in self._mode_button_rects:
            base, hover = colours.get(label, ((100,100,100),(80,80,80)))
            col = hover if rect.collidepoint(mouse_pos) else base
            pygame.draw.rect(self.screen, col,    rect, border_radius=10)
            pygame.draw.rect(self.screen, WHITE,  rect, 2, border_radius=10)

            txt = font_btn.render(label, True, WHITE)
            self.screen.blit(txt, txt.get_rect(center=rect.center))

            font_small = pygame.font.SysFont(None, 24)
            sublabels = {
                "PvP":    "2 Players",
                "Easy":   "50% hit rate",
                "Medium": "75% hit rate",
                "Hard":   "100% hit rate",
            }
            stxt = font_small.render(sublabels.get(label, ""), True, (220,220,220))
            self.screen.blit(stxt, stxt.get_rect(
                centerx=rect.centerx, top=rect.bottom + 6))

        s_hover = (80, 60, 160) if self._stats_button_rect.collidepoint(mouse_pos) else (60, 40, 140)
        pygame.draw.rect(self.screen, s_hover, self._stats_button_rect, border_radius=10)
        pygame.draw.rect(self.screen, WHITE,   self._stats_button_rect, 2, border_radius=10)
        s_lbl = font_btn.render("Statistics", True, WHITE)
        self.screen.blit(s_lbl, s_lbl.get_rect(center=self._stats_button_rect.center))

        font_hint = pygame.font.SysFont(None, 26)
        hints = [
            "Left / Right : Move    Up / Down : Aim angle    W / S : Power    SPACE : Fire",
            "Shell selector: click the shell button on your HUD panel",
            "Activate 500kg Bomb for automation",
        ]
        for i, h in enumerate(hints):
            ht = font_hint.render(h, True, (180, 200, 230))
            self.screen.blit(ht, (SCREEN_WIDTH//2 - ht.get_width()//2,
                                  SCREEN_HEIGHT - 80 + i * 28))

    def _draw_ai_menu(self):
        font_big = pygame.font.SysFont(None, 80)
        title = font_big.render("AI vs AI Simulator", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 160))

        font_sub = pygame.font.SysFont(None, 36)
        sub = font_sub.render("Select AI difficulty matchup", True, (200, 220, 255))
        self.screen.blit(sub, (SCREEN_WIDTH//2 - sub.get_width()//2, 255))

        font_btn = pygame.font.SysFont(None, 38)
        mouse_pos = pygame.mouse.get_pos()

        for label, diff, rect in self._ai_button_rects:
            base, hover = (100, 100, 100), (80, 80, 80)
            col = hover if rect.collidepoint(mouse_pos) else base
            pygame.draw.rect(self.screen, col,    rect, border_radius=10)
            pygame.draw.rect(self.screen, WHITE,  rect, 2, border_radius=10)

            txt = font_btn.render(label, True, WHITE)
            self.screen.blit(txt, txt.get_rect(center=rect.center))

        self._draw_restart_button()

    def _draw_aim_line(self, tank):
        if self.ai_turn_active:
            return
        points = tank.get_aim_points(self.wind, steps=80, dt=0.04)
        max_points = max(1, len(points) - 1)
        for idx, point in enumerate(points):
            fade = 1.0 - (idx / max_points) * 2
            if fade <= 0:
                break
            alpha = max(20, int(255 * fade))
            radius = 2
            dot = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(dot, (255, 255, 255, alpha), (radius + 1, radius + 1), radius)
            self.screen.blit(dot, (int(point.x) - radius - 1, int(point.y) - radius - 1))

    def _draw_ui(self):
        font = pygame.font.SysFont(None, 30)
        for i, tank in enumerate(self.player_list):
            panel_x = 20 if i == 0 else SCREEN_WIDTH - 320
            panel_y = SCREEN_HEIGHT - 210
            panel_w = 300
            panel_h = 200

            panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            panel_surf.fill((60, 60, 60, 180))
            self.screen.blit(panel_surf, (panel_x, panel_y))
            pygame.draw.rect(self.screen, BLACK, (panel_x, panel_y, panel_w, panel_h), 2)

            if self.ai_difficulties[i]:
                label = f"AI ({self.ai_difficulties[i].capitalize()})"
            else:
                label = f"Player {tank.player_id}"
            title_txt = font.render(label, True, WHITE)
            self.screen.blit(title_txt, (panel_x + 10, panel_y + 10))

            bar_x = panel_x + 10
            bar_y = panel_y + 44
            bar_w = panel_w - 20
            bar_h = 18
            pygame.draw.rect(self.screen, BLACK, (bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4), 2)
            pygame.draw.rect(self.screen, tank.color,
                             (bar_x, bar_y, int(bar_w * tank.health / TANK_MAX_HEALTH), bar_h))
            hp_txt = font.render(f"HP: {int(tank.health)}", True, WHITE)
            self.screen.blit(hp_txt, (bar_x, bar_y + bar_h + 6))

            angle_txt = font.render(f"Angle: {int(tank.angle)}°", True, WHITE)
            power_txt = font.render(f"Power: {int(tank.power)} / {TANK_MAX_POWER}", True, WHITE)
            fuel_txt  = font.render(f"Fuel: {int((tank.oil/TANK_MAX_OIL)*100)}%", True, WHITE)
            shell_count = tank.shell_list.get(tank.current_shell, 0)
            shell_label = f"{tank.current_shell} ({shell_count})"
            shell_txt   = font.render(f"Shell: {shell_label}", True, WHITE)

            self.screen.blit(angle_txt, (panel_x + 10, panel_y + 100))
            self.screen.blit(power_txt, (panel_x + 10, panel_y + 100 + 28))
            self.screen.blit(fuel_txt,  (panel_x + 140, panel_y + 100))

            if tank is self.current_tank and not self.ai_turn_active:
                self.shell_menu_button_rect = pygame.Rect(
                    panel_x + 10,
                    panel_y + 100 + (28 * 2),
                    shell_txt.get_width() + 16,
                    shell_txt.get_height() + 12,
                )
                pygame.draw.rect(self.screen, GRAY, self.shell_menu_button_rect)
                pygame.draw.rect(self.screen, BLACK, self.shell_menu_button_rect, 2)
                self.screen.blit(shell_txt,
                                 (self.shell_menu_button_rect.x + 8,
                                  self.shell_menu_button_rect.y + 6))
                if self.shell_menu_open and self.game_state == "playing":
                    self._draw_shell_menu(font)
            else:
                self.screen.blit(shell_txt, (panel_x + 10, panel_y + 100 + (28 * 2)))

        if self.ai_turn_active:
            diff = self.ai_difficulties[self.current_turn_index]
            if diff:
                turn_label = f"AI ({diff.capitalize()}) is thinking…"
            else:
                turn_label = "AI is thinking..."
        else:
            turn_label = f"Player {self.current_tank.player_id}'s Turn"
            
        turn_txt    = font.render(turn_label, True, WHITE)
        wind_symbol = "<-" if self.wind < 0 else "->" if self.wind > 0 else "--"
        wind_txt    = font.render(f"Wind {wind_symbol} {abs(self.wind):.1f}", True, WHITE)
        current_round = font.render(f"Current round: {self.rounds}", True, WHITE)
        self.screen.blit(turn_txt, (SCREEN_WIDTH//2 - turn_txt.get_width()//2, 10))
        self.screen.blit(wind_txt, (SCREEN_WIDTH//2 - wind_txt.get_width()//2, 40))
        self.screen.blit(current_round, (SCREEN_WIDTH//2 - current_round.get_width()//2, 70))

    def _handle_shell_menu_click(self, pos):
        for shell_name, rect in self.shell_menu_item_rects:
            if rect.collidepoint(pos):
                count = self.current_tank.shell_list.get(shell_name, 0)
                if count > 0 or (shell_name == "standard" and all(c <= 0 for c in self.current_tank.shell_list.values())):
                    self.current_tank.current_shell = shell_name
                    self.shell_menu_open = False
                    return True
        return False

    def _draw_shell_menu(self, font):
        shell_names = list(self.current_tank.shell_list.keys())
        rows    = min(4, len(shell_names))
        columns = max(1, (len(shell_names) + rows - 1) // rows)

        item_w = 185
        item_h = 28
        gap    = 8
        menu_width  = columns * item_w + (columns + 1) * gap
        menu_height = rows    * item_h + (rows    + 1) * gap

        menu_x = self.shell_menu_button_rect.left
        menu_y = self.shell_menu_button_rect.bottom + 6

        if menu_x + menu_width > SCREEN_WIDTH - 10:
            menu_x = SCREEN_WIDTH - menu_width - 10
        if menu_y + menu_height > SCREEN_HEIGHT - 10:
            menu_y = self.shell_menu_button_rect.top - 6 - menu_height

        pygame.draw.rect(self.screen, (50, 50, 50), (menu_x, menu_y, menu_width, menu_height))
        pygame.draw.rect(self.screen, WHITE,        (menu_x, menu_y, menu_width, menu_height), 2)

        self.shell_menu_item_rects = []
        for idx, shell_name in enumerate(shell_names):
            row  = idx % rows
            col  = idx // rows
            item_x = menu_x + gap + col * (item_w + gap)
            item_y = menu_y + gap + row * (item_h + gap)
            rect = pygame.Rect(item_x, item_y, item_w, item_h)

            count        = self.current_tank.shell_list.get(shell_name, 0)
            fill_color   = (90, 90, 90) if shell_name == self.current_tank.current_shell else (70, 70, 70)
            text_color   = WHITE if count > 0 else (180, 180, 180)
            border_color = YELLOW if shell_name == self.current_tank.current_shell else BLACK

            pygame.draw.rect(self.screen, fill_color,   rect)
            pygame.draw.rect(self.screen, border_color, rect, 2)
            item_txt = font.render(f"{shell_name} ({count})", True, text_color)
            self.screen.blit(item_txt, (rect.x + 8, rect.y + 4))
            self.shell_menu_item_rects.append((shell_name, rect))

    def _draw_restart_button(self):
        font = pygame.font.SysFont(None, 28)
        pygame.draw.rect(self.screen, RED,  self.restart_button_rect)
        pygame.draw.rect(self.screen, GRAY, self.restart_button_rect, 2)
        txt = font.render("Restart" if self.game_state != "ai_menu" else "Back", True, WHITE)
        txt_pos = txt.get_rect(center=self.restart_button_rect.center)
        self.screen.blit(txt, txt_pos)

    def quit_game(self):
        pygame.quit()
        sys.exit()
        raise SystemExit


if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(TITLE)
    game = Game(screen)
    game.run()
