import pygame, random
from settings import *
from tank    import Tank
from terrain import Terrain
from particle import Particle

class Game:
    def __init__(self, screen):
        self.screen     = screen
        self.clock      = pygame.time.Clock()
        self.terrain    = Terrain()
        self.wind       = self._random_wind()
        self.rounds     = 0
        self.matchduration     = 0.0
        self.game_state        = "main_menu"   # "playing" | "game_over"
        self.current_turn_index = 0
        self.active_shells = []
        self.particles     = []
        self.player_list   = []
        self._setup_players()

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
        self._setup_players()

    def _setup_players(self):
        y1 = self.terrain.get_y_at(200) - TANK_HEIGHT / 2
        y2 = self.terrain.get_y_at(SCREEN_WIDTH - 200) - TANK_HEIGHT / 2
        red_tank = Tank(200,              y1, player_id=1, color=RED)
        blue_tank = Tank(SCREEN_WIDTH-200, y2, player_id=2, color=BLUE)
        blue_tank.facing_left = True
        self.player_list = [red_tank, blue_tank]

    @property
    def current_tank(self):
        return self.player_list[self.current_turn_index]

    def next_turn(self):
        self.current_turn_index = (self.current_turn_index + 1) % len(self.player_list)
        if self.current_turn_index == 0:
            self.rounds += 1
            self._refuel_tanks()
            self.wind = self._random_wind()

    def _refuel_tanks(self):
        for tank in self.player_list:
            if tank.is_alive:
                tank.oil = TANK_MAX_OIL

    def _explode(self, shell):
        for _ in range(shell.particle_count):
            self.particles.append(Particle(shell.pos, shell.particle_color))

    def run(self):
        while True:
            dt_ms = self.clock.tick(FPS)
            dt = dt_ms / 1000.0
            self.matchduration += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit_game()
                self._handle_input(event)

            self.update(dt)
            self.draw()

    def _handle_input(self, event):
        if self.game_state == "main_menu":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self.game_state = "playing"
            return

        if self.game_state == "game_over":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self.reset()
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and not self.active_shells:
                new_shells = self.current_tank.shoot()
                self.active_shells.extend(new_shells)
                self.next_turn()

            if event.key == pygame.K_1:
                self.current_tank.current_shell = "standard"
            elif event.key == pygame.K_2:
                self.current_tank.current_shell = "splash"
            elif event.key == pygame.K_3:
                self.current_tank.current_shell = "shotgun"
            elif event.key == pygame.K_4:
                self.current_tank.current_shell = "nuke"
            elif event.key == pygame.K_5:
                self.current_tank.current_shell = "bouncy"

    def _handle_held_keys(self, dt):
        pressed = pygame.key.get_pressed()
        tank = self.current_tank

        if pressed[pygame.K_LEFT]:
            tank.move(-1, dt)
        if pressed[pygame.K_RIGHT]:
            tank.move(1, dt)
        if pressed[pygame.K_UP]:
            tank.angle = min(90, tank.angle + 120 * dt)
        if pressed[pygame.K_DOWN]:
            tank.angle = max(0, tank.angle - 120 * dt)
        if pressed[pygame.K_w]:
            tank.power = min(TANK_MAX_POWER, tank.power + 1)
        if pressed[pygame.K_s]:
            tank.power = max(0, tank.power - 1)

    def update(self, dt):
        if self.game_state != "playing":
            return

        self._handle_held_keys(dt)

        for tank in self.player_list:
            tank.update(self.terrain, dt)

        for shell in self.active_shells:
            shell.update(dt, self.wind)
            p = shell.pos
            if p.x < 0 or p.x > SCREEN_WIDTH or p.y > SCREEN_HEIGHT:
                shell.is_active = False
                continue

            result = shell.check_collision(self.terrain, self.player_list)
            if result == "terrain":
                self.terrain.destroy(shell.pos, shell.explosion_radius)
                self._explode(shell)
            elif result == "tank":
                for tank in self.player_list:
                    if tank.rect.collidepoint(shell.pos):
                        tank.take_dmg(shell.damage)
                self.terrain.destroy(shell.pos, shell.explosion_radius)
                self._explode(shell)

        self.active_shells = [s for s in self.active_shells if s.is_active]

        # Check win condition
        alive = [t for t in self.player_list if t.is_alive]
        if len(alive) == 1:
            self.game_state = "game_over"

        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if not p.is_dead]

    def draw(self):
        self.screen.fill(SKY_BLUE)

        if self.game_state == "main_menu":
            font = pygame.font.SysFont(None, 72)
            txt  = font.render("TANKHELL  —  Press ENTER", True, WHITE)
            self.screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, 300))

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

        if self.game_state == "game_over":
            font = pygame.font.SysFont(None, 72)
            txt  = font.render("GAME OVER", True, WHITE)
            self.screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, 300))

        pygame.display.flip()

    def _draw_aim_line(self, tank):
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

            title_txt = font.render(f"Player {tank.player_id}", True, WHITE)
            self.screen.blit(title_txt, (panel_x + 10, panel_y + 10))

            bar_x = panel_x + 10
            bar_y = panel_y + 44
            bar_w = panel_w - 20
            bar_h = 18
            pygame.draw.rect(self.screen, BLACK, (bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4), 2)
            pygame.draw.rect(self.screen, tank.color, (bar_x, bar_y, int(bar_w * tank.health / TANK_MAX_HEALTH), bar_h))
            hp_txt = font.render(f"HP: {int(tank.health)}", True, WHITE)
            self.screen.blit(hp_txt, (bar_x, bar_y + bar_h + 6))

            angle_txt = font.render(f"Angle: {int(tank.angle)}°", True, WHITE)
            power_txt = font.render(f"Power: {int(tank.power)} / {TANK_MAX_POWER}", True, WHITE)
            fuel_txt = font.render(f"Fuel: {int(tank.oil)}", True, WHITE)
            shell_count = tank.shell_list.get(tank.current_shell, 0)
            shell_txt = font.render(
                f"Shell: {tank.current_shell} ({shell_count})",
                True, WHITE
            )

            self.screen.blit(angle_txt, (panel_x + 10, panel_y + 100))
            self.screen.blit(power_txt, (panel_x + 10, panel_y + 100 + 28))
            self.screen.blit(fuel_txt, (panel_x + 140, panel_y + 100))
            self.screen.blit(shell_txt, (panel_x + 10, panel_y + 100 + (28*2)))

        # Show whose turn it is
        turn_txt = font.render(f"Player {self.current_tank.player_id}'s Turn", True, WHITE)
        wind_symbol = "<-" if self.wind < 0 else "->" if self.wind > 0 else "--"
        wind_txt = font.render(f"Wind {wind_symbol} {abs(self.wind):.1f}", True, WHITE)
        self.screen.blit(turn_txt, (SCREEN_WIDTH//2 - turn_txt.get_width()//2, 10))
        self.screen.blit(wind_txt, (SCREEN_WIDTH//2 - wind_txt.get_width()//2, 40))

    def quit_game(self):
        pygame.quit()
        raise SystemExit
