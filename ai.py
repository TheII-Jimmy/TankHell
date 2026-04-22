import math
import random
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, SHELL_GRAVITY, SHELLS, TANK_MOVE_SPEED


def _simulate_shell(start_x, start_y, angle_deg, power, wind,
                    shell_type="standard", target_x=None, target_y=None,
                    max_steps=600, dt=0.016):

    stats  = SHELLS.get(shell_type, SHELLS["standard"])
    speed  = power * 10.0 * stats.get("speed_multiplier", 1.0)
    grav   = SHELL_GRAVITY * stats.get("gravity_multiplier", 1.0)
    wr     = stats.get("wind_resistance", 1.0)

    rad = math.radians(angle_deg)
    vx  = math.cos(rad) * speed
    vy  = -math.sin(rad) * speed
    x, y = float(start_x), float(start_y)
    best_err = float("inf")

    for _ in range(max_steps):
        vy += grav * dt
        vx += wind*25 * wr * dt
        x  += vx * dt
        y  += vy * dt
        if target_x is not None and target_y is not None:
            best_err = min(best_err, math.hypot(x - target_x, y - target_y))
        if x < 0 or x > SCREEN_WIDTH:
            return None
        if y > SCREEN_HEIGHT:
            return x, y, best_err
    return x, y, best_err


def _solve_angle_and_power(src_x, src_y, tgt_x, tgt_y, wind,
                            shell_type="standard", facing_left=False):

    best_angle = 45.0
    best_power = 50.0
    best_err   = float("inf")

    for angle in range(5, 86, 1):        # 5° … 85° local angle
        for power in range(20, 101, 2):
            # Replicate exactly what tank.shoot() does when building the angle:
            # shell_angle = angle if not facing_left else 180 - angle
            world_angle = angle if not facing_left else 180 - angle
            result = _simulate_shell(src_x, src_y, world_angle, power, wind,
                                     shell_type, tgt_x, tgt_y)
            if result is None:
                continue
            _, _, err = result
            if err < best_err:
                best_err   = err
                best_angle = angle
                best_power = power

    # Fine-grained refinement: fix the best angle, sweep power in steps of 1
    # across a +-10 window around the coarse best to eliminate step-size error.
    world_angle = best_angle if not facing_left else 180 - best_angle
    for power in range(max(1, best_power - 10), min(100, best_power + 10) + 1):
        result = _simulate_shell(src_x, src_y, world_angle, power, wind,
                                 shell_type, tgt_x, tgt_y)
        if result is None:
            continue
        _, _, err = result
        if err < best_err:
            best_err   = err
            best_power = power

    return best_angle, best_power


_PHASE_MOVE  = "move"
_PHASE_AIM   = "aim"
_PHASE_SHOOT = "shoot"


class TankAI:
    # Offset range (pixels) applied to the target x position
    _AIM_OFFSET_RANGE = 0          # override in subclasses

    def __init__(self):
        self.reset()

    def reset(self):
        """Call at the start of each AI turn."""
        self._phase          = _PHASE_MOVE
        self._move_target_x  = None   # x to move to (or None = stay)
        self._move_direction = 0
        self._move_time_left = 0.0
        self._aim_angle      = 45.0
        self._aim_power      = 50.0
        self._aim_done       = False
        self._shoot_ready    = False

    def _choose_shell(self, tank):
        """Randomly pick an available shell (non-empty)."""
        available = [name for name, count in tank.shell_list.items() if count > 0]
        if not available:
            return "standard"
        return random.choice(available)

    def _is_perfect_shot(self, tank):
        """Return True when the upcoming shot should be 100% accurate."""
        return False

    def _apply_accuracy_offset(self, tank):
        """
        Return a random x-pixel offset to introduce inaccuracy.
        Override in subclasses.
        """
        return 0.0

    def _plan_turn(self, tank, enemy, wind):
        """Compute the desired shell, angle, and power for this turn."""
        # Pick shell
        tank.current_shell = self._choose_shell(tank)

        # Decide facing direction first so the solver uses the right world angle
        tank.facing_left = enemy.pos.x < tank.pos.x

        # Target position with accuracy offset
        target_x = enemy.pos.x + self._apply_accuracy_offset(tank)
        target_y = enemy.pos.y

        # Use the actual barrel spawn position as the simulation origin so the
        # solved trajectory matches what tank.shoot() will produce exactly.
        spawn = tank._get_shell_spawn_pos()

        # Solve aim — pass facing_left so the solver mirrors the angle the same
        # way tank.shoot() will, preventing the angle from being flipped twice.
        self._aim_angle, self._aim_power = _solve_angle_and_power(
            spawn.x,     spawn.y,
            target_x,    target_y,
            wind,         tank.current_shell,
            facing_left=tank.facing_left,
        )

    def update(self, tank, enemy, terrain, wind, dt):
        if self._phase == _PHASE_MOVE:
            return self._update_move(tank, terrain, dt)

        if self._phase == _PHASE_AIM:
            return self._update_aim(tank, enemy, wind, dt)

        if self._phase == _PHASE_SHOOT:
            return True      # caller fires the shell

        return False

    def _update_move(self, tank, terrain, dt):
        """Movement logic, if tank is near screen border -> it move in opposite direciton"""
        # On the very first frame of this phase, decide whether to move.
        if self._move_target_x is None:
            # If close to the screen edge, always move away from it.
            if tank.pos.x < 200:
                # Move right to get away from left edge
                move_dist = 300
                direction = 1
                self._move_direction = direction
                self._move_time_left = move_dist / TANK_MOVE_SPEED
                self._move_target_x = 0
                return False
            elif tank.pos.x > SCREEN_WIDTH - 200:
                # Move left to get away from right edge
                move_dist = 300
                direction = -1
                self._move_direction = direction
                self._move_time_left = move_dist / TANK_MOVE_SPEED
                self._move_target_x = 0
                return False
            else:
                # Normal logic: only 40% of AI turns will move; otherwise go straight to aiming.
                if random.random() >= 0.4:
                    self._phase = _PHASE_AIM
                    return False
                # Move a random distance (0 – 300 px) in a random direction
                move_dist = random.uniform(0, 300)
                direction = random.choice([-1, 1])
                self._move_direction = direction
                self._move_time_left = move_dist / TANK_MOVE_SPEED
                self._move_target_x = 0   # just a sentinel so we don't re-init

        if self._move_time_left > 0:
            tank.move(self._move_direction, dt, terrain)
            self._move_time_left -= dt
        else:
            # Moving done → plan the shot, then go to aim phase
            self._phase = _PHASE_AIM
        return False

    def _update_aim(self, tank, enemy, wind, dt):
        if not self._aim_done:
            self._plan_turn(tank, enemy, wind)
            self._aim_done = True

        # Smoothly adjust angle and power over ~0.5 s so it looks natural
        angle_diff = self._aim_angle - tank.angle
        power_diff = self._aim_power - tank.power

        step_angle = 120 * dt   # degrees per second
        step_power = 80  * dt

        if abs(angle_diff) > step_angle:
            tank.angle += math.copysign(step_angle, angle_diff)
        else:
            tank.angle = self._aim_angle

        if abs(power_diff) > step_power:
            tank.power += math.copysign(step_power, power_diff)
        else:
            tank.power = self._aim_power

        # When both are settled move to shoot
        if abs(tank.angle - self._aim_angle) < 0.5 and abs(tank.power - self._aim_power) < 0.5:
            self._phase = _PHASE_SHOOT
        return False

class EasyAI(TankAI):
    """~50 % hit rate: large random offset on the target x."""
    _AIM_OFFSET_RANGE = 260   # +- pixels

    def _is_perfect_shot(self, tank):
        next_shot = tank._shots_fired + 1
        return next_shot % 6 == 0

    def _apply_accuracy_offset(self, tank):
        if self._is_perfect_shot(tank):
            return 0.0
        return random.uniform(-self._AIM_OFFSET_RANGE, self._AIM_OFFSET_RANGE)


class MediumAI(TankAI):
    """~75 % hit rate: medium random offset."""
    _AIM_OFFSET_RANGE = 120   # +- pixels

    def _is_perfect_shot(self, tank):
        next_shot = tank._shots_fired + 1
        return next_shot % 3 == 0

    def _apply_accuracy_offset(self, tank):
        if self._is_perfect_shot(tank):
            return 0.0
        # 75 % of the time use a small offset, 25 % use a large miss
        if random.random() < 0.75:
            return random.uniform(-40, 40)
        return random.uniform(-self._AIM_OFFSET_RANGE, self._AIM_OFFSET_RANGE)


class HardAI(TankAI):
    """100 % hit rate: no offset, perfect aim."""
    _AIM_OFFSET_RANGE = 0

    def _apply_accuracy_offset(self, tank):
        return 0.0


def create_ai(difficulty: str) -> TankAI:
    """
    difficulty: "easy" | "medium" | "hard"
    Returns a fresh AI instance.
    """
    mapping = {
        "easy":   EasyAI,
        "medium": MediumAI,
        "hard":   HardAI,
    }
    cls = mapping.get(difficulty.lower(), MediumAI)
    return cls()
