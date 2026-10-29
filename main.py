import pyxel
import math
import asyncio
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

WIDTH = 160
HEIGHT = 120
JST = timezone(timedelta(hours=9))

SUPABASE_URL = "https://hxjzgilnqxnnxlpqyasu.supabase.co"
SUPABASE_KEY = "sb_publishable_sae6J_mLG2NpvPFf2MI-kQ_ozswuMhR"
TABLE_URL = SUPABASE_URL + "/rest/v1/squash_scores"

pyxel.init(WIDTH, HEIGHT, title="DOPABALL")

COLORS = [1, 2, 5, 6, 9, 12, 13]

paddle_x = 65.0
paddle_y = 105
BASE_PADDLE_W = 30
GIANT_PADDLE_W = 45
paddle_w = BASE_PADDLE_W

ball_x = 80.0
ball_y = 60.0
ball_dx = 1.0
ball_dy = 1.0
ball_speed = 1.5
extra_balls = []

score = 0
high_score = 0
combo = 0
game_over = False

flash_timer = 0
shake_timer = 0
fever_timer = 0
music_level = -1
particles = []

power_items = []
spawn_timer = 180
power_spawning_started = False
giant_timer = 0
triple_timer = 0
power_message_timer = 0
power_message = ""

player_name = ""
leaderboard = []
leaderboard_status = "LOADING"
leaderboard_error = ""
submit_status = ""

screen_mode = "title"
title_timer = 0
selected_period = "DAILY"

fetch_task_running = False
submit_task_running = False
submitted_this_round = False
initial_fetch_started = False

keyboard_rows = [
    "ABCDEFGHIJ",
    "KLMNOPQRST",
    "UVWXYZ0123",
    "456789_-<"
]


# -----------------------------
# Sound
# -----------------------------

pyxel.sounds[0].set("c3e3g3e3c3e3g3e3", "p", "6", "n", 12)
pyxel.sounds[1].set("c2c2g2g2a2a2g2g2", "t", "4", "n", 12)
pyxel.sounds[2].set("c3e3g3c4g3e3g3c4", "p", "7", "n", 9)
pyxel.sounds[3].set("c2g2c3g2f2g2a2g2", "t", "6", "n", 9)
pyxel.sounds[4].set("c4g3e3g3c4g3e3g3", "p", "7", "n", 6)
pyxel.sounds[5].set("c2c3g2c3a2c3g2c3", "t", "7", "n", 6)
pyxel.sounds[6].set("c3g3c4", "p", "7", "s", 8)
pyxel.sounds[7].set("c3e3g3c4", "p", "7", "s", 6)
pyxel.sounds[8].set("g3e3c3", "t", "7", "f", 10)
pyxel.sounds[9].set("c3e3g3c4", "p", "7", "s", 8)

pyxel.musics[0].set([0], [1], [], [])
pyxel.musics[1].set([2], [3], [], [])
pyxel.musics[2].set([4], [5], [], [])


def change_music(level):
    global music_level

    if level != music_level:
        music_level = level
        pyxel.playm(level, loop=True)


def make_particles(x, y, amount=12, color=None):
    for _ in range(amount):
        angle = pyxel.rndf(0, math.pi * 2)
        speed = pyxel.rndf(0.5, 2.5)

        particle_color = (
            color if color is not None
            else pyxel.rndi(8, 15)
        )

        particles.append([
            x, y,
            math.cos(angle) * speed,
            math.sin(angle) * speed,
            15, particle_color
        ])


# -----------------------------
# Pixel logo
# -----------------------------

LOGO_FONT = {
    "D": ["1110", "1001", "1001", "1001", "1110"],
    "O": ["0110", "1001", "1001", "1001", "0110"],
    "P": ["1110", "1001", "1110", "1000", "1000"],
    "A": ["0110", "1001", "1111", "1001", "1001"],
    "B": ["1110", "1001", "1110", "1001", "1110"],
    "L": ["1000", "1000", "1000", "1000", "1111"],
}


def draw_logo(text, x, y, scale, color):
    cursor_x = x

    for char in text:
        pattern = LOGO_FONT[char]

        for row, line in enumerate(pattern):
            for col, pixel in enumerate(line):
                if pixel == "1":
                    pyxel.rect(
                        cursor_x + col * scale,
                        y + row * scale,
                        scale, scale, color
                    )

        cursor_x += 5 * scale


# -----------------------------
# Daily / Monthly ranking
# -----------------------------

def draw_period_tabs(y):
    daily_color = 10 if selected_period == "DAILY" else 5
    pyxel.rect(22, y, 52, 9, daily_color)
    pyxel.rectb(22, y, 52, 9, 7)
    pyxel.text(
        32, y + 2, "DAILY",
        0 if selected_period == "DAILY" else 7
    )

    monthly_color = 10 if selected_period == "MONTHLY" else 5
    pyxel.rect(86, y, 52, 9, monthly_color)
    pyxel.rectb(86, y, 52, 9, 7)
    pyxel.text(
        94, y + 2, "MONTHLY",
        0 if selected_period == "MONTHLY" else 7
    )


def period_tab_clicked(mx, my, y):
    global selected_period

    if y <= my < y + 10:
        new_period = None

        if 22 <= mx < 74:
            new_period = "DAILY"
        elif 86 <= mx < 138:
            new_period = "MONTHLY"

        if new_period is not None:
            if selected_period != new_period:
                selected_period = new_period
                launch_refresh()

            return True

    return False


def get_period_bounds(period):
    now = datetime.now(JST)

    if period == "MONTHLY":
        start = now.replace(
            day=1, hour=0, minute=0,
            second=0, microsecond=0
        )

        if start.month == 12:
            end = start.replace(
                year=start.year + 1, month=1
            )
        else:
            end = start.replace(month=start.month + 1)

    else:
        start = now.replace(
            hour=0, minute=0,
            second=0, microsecond=0
        )
        end = start + timedelta(days=1)

    return start, end


# -----------------------------
# Title screen
# -----------------------------

def draw_title():
    pyxel.cls(1)

    for i in range(9):
        x = (i * 21 + pyxel.frame_count) % WIDTH
        color = 5 if i % 2 == 0 else 8
        pyxel.line(x, 0, x - 25, HEIGHT, color)

    for i in range(5):
        x = (i * 37 + pyxel.frame_count // 2) % WIDTH
        y = 18 + (i % 3) * 30
        pyxel.circ(x, y, 2, 12)

    logo = "DOPABALL"
    scale = 3
    logo_width = len(logo) * 5 * scale - scale
    start_x = (WIDTH - logo_width) // 2

    logo_color = (
        10 if pyxel.frame_count // 12 % 2 == 0
        else 11
    )

    draw_logo(logo, start_x + 2, 6, scale, 8)
    draw_logo(logo, start_x, 4, scale, logo_color)

    pyxel.line(12, 23, 148, 23, 10)
    pyxel.line(24, 25, 136, 25, 12)
    pyxel.text(52, 29, "SQUASH FEVER", 7)

    pyxel.rect(8, 35, 144, 61, 0)
    pyxel.rectb(8, 35, 144, 61, 12)

    draw_period_tabs(39)
    pyxel.text(44, 50, "TOP 5 SCORES", 10)

    if leaderboard_status == "LOADING":
        pyxel.text(49, 64, "LOADING...", 7)

    elif leaderboard_status == "ERROR":
        pyxel.text(22, 64, "RANKING OFFLINE", 8)
        pyxel.text(13, 75, "CHECK CONNECTION", 6)

    elif not leaderboard:
        pyxel.text(28, 66, "NO SCORES YET", 7)

    else:
        for i, item in enumerate(leaderboard[:5]):
            y = 59 + i * 7
            name = str(item.get("player_name", "PLAYER"))[:10]
            points = str(item.get("score", 0))

            pyxel.text(
                14, y, str(i + 1) + ".",
                10 if i == 0 else 7
            )
            pyxel.text(29, y, name, 7)
            pyxel.text(
                112, y, points,
                10 if i == 0 else 11
            )

    if title_timer < 120:
        pyxel.text(54, 100, "GET READY...", 7)
    elif pyxel.frame_count // 20 % 2 == 0:
        pyxel.text(45, 100, "TAP TO START", 10)

    pyxel.text(25, 110, "MOVE: LEFT / RIGHT", 6)


# -----------------------------
# Supabase
# -----------------------------

async def get_json(url):
    from pyodide.http import pyfetch

    response = await pyfetch(
        url,
        method="GET",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": "Bearer " + SUPABASE_KEY
        }
    )

    if response.status >= 400:
        raise RuntimeError("HTTP " + str(response.status))

    return await response.json()


async def send_score(name, points):
    from pyodide.http import pyfetch

    response = await pyfetch(
        TABLE_URL,
        method="POST",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": "Bearer " + SUPABASE_KEY,
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        },
        body=json.dumps([{
            "player_name": name,
            "score": int(points)
        }])
    )

    if response.status >= 400:
        raise RuntimeError("HTTP " + str(response.status))


async def refresh_leaderboard():
    global leaderboard
    global leaderboard_status
    global leaderboard_error
    global fetch_task_running

    if fetch_task_running:
        return

    fetch_task_running = True
    leaderboard_status = "LOADING"
    requested_period = selected_period

    try:
        start, end = get_period_bounds(requested_period)

        start_utc = start.astimezone(timezone.utc).isoformat()
        end_utc = end.astimezone(timezone.utc).isoformat()

        url = (
            TABLE_URL
            + "?select=player_name,score,created_at"
            + "&created_at=gte." + quote(start_utc, safe=":")
            + "&created_at=lt." + quote(end_utc, safe=":")
            + "&order=score.desc,created_at.asc"
            + "&limit=1000"
        )

        rows = await get_json(url)
        best_by_player = {}

        for item in rows:
            name = str(item.get("player_name", "PLAYER")).strip()
            points = int(item.get("score", 0))

            if not name:
                name = "PLAYER"

            key = name.upper()

            if (
                key not in best_by_player
                or points > int(best_by_player[key].get("score", 0))
            ):
                best_by_player[key] = {
                    "player_name": name,
                    "score": points,
                    "created_at": item.get("created_at", "")
                }

        leaderboard = sorted(
            best_by_player.values(),
            key=lambda item: (
                -int(item.get("score", 0)),
                item.get("created_at", "")
            )
        )

        leaderboard_status = "OK"
        leaderboard_error = ""

    except Exception as error:
        leaderboard_status = "ERROR"
        leaderboard_error = str(error)[:25]

    finally:
        fetch_task_running = False

    if selected_period != requested_period:
        await refresh_leaderboard()


async def submit_and_refresh(name, points):
    global submit_task_running
    global submit_status
    global leaderboard_status
    global leaderboard_error

    submit_task_running = True
    submit_status = "SENDING"

    try:
        await send_score(name, points)
        submit_status = "SAVED"
        await refresh_leaderboard()

    except Exception as error:
        submit_status = "SAVE FAILED"
        leaderboard_status = "ERROR"
        leaderboard_error = str(error)[:25]

    finally:
        submit_task_running = False


def launch_refresh():
    try:
        asyncio.ensure_future(refresh_leaderboard())
    except Exception:
        pass


# -----------------------------
# Power-up system
# -----------------------------

def spawn_power_item():
    # 0 = GIANT PADDLE
    # 1 = SCORE x3
    # 2 = MULTI BALL
    item_type = pyxel.rndi(0, 2)
    x = pyxel.rndi(10, WIDTH - 10)

    power_items.append({
        "x": float(x),
        "y": -5.0,
        "type": item_type,
        "speed": pyxel.rndf(0.6, 1.0)
    })


def activate_power_item(item_type):
    global giant_timer, triple_timer
    global paddle_w, paddle_x
    global power_message, power_message_timer
    global extra_balls

    if item_type == 0:
        # GIANT PADDLE: width 30 -> 45 for 10 seconds
        giant_timer = 60 * 10
        paddle_w = GIANT_PADDLE_W

        # Keep the entire paddle inside the screen.
        paddle_x = max(
            0,
            min(WIDTH - paddle_w, paddle_x)
        )

        power_message = "GIANT PADDLE!"
        make_particles(ball_x, ball_y, 24, 12)

    elif item_type == 1:
        triple_timer = 60 * 8

        power_message = "SCORE x3!"
        make_particles(ball_x, ball_y, 24, 10)

    else:
        current_ball_count = 1 + len(extra_balls)
        balls_to_add = max(0, 3 - current_ball_count)

        for _ in range(balls_to_add):
            angle = pyxel.rndf(-0.8, 0.8)

            extra_balls.append({
                "x": ball_x,
                "y": ball_y,
                "dx": math.sin(angle),
                "dy": -abs(math.cos(angle)),
            })

        if balls_to_add > 0:
            power_message = "MULTI BALL!"
        else:
            power_message = "BALLS ALREADY x3!"

        make_particles(ball_x, ball_y, 30, 11)

    power_message_timer = 100
    pyxel.play(3, 9)


def update_power_items():
    global spawn_timer, power_spawning_started

    # Items do not appear at the beginning.
    if pyxel.frame_count >= 180 and ball_speed >= 2.4:

        if not power_spawning_started:
            power_spawning_started = True
            spawn_timer = pyxel.rndi(120, 240)

        spawn_timer -= 1

        speed_factor = min(
            1.0,
            max(0.0, (ball_speed - 2.4) / (7.5 - 2.4))
        )

        min_interval = int(300 - speed_factor * 210)
        max_interval = int(420 - speed_factor * 300)

        if spawn_timer <= 0:
            spawn_power_item()

            min_interval = max(60, min_interval)
            max_interval = max(min_interval, max_interval)

            spawn_timer = pyxel.rndi(
                min_interval, max_interval
            )

    for item in power_items[:]:
        item["y"] += item["speed"]
        collected = False

        # Main ball collision.
        dx = ball_x - item["x"]
        dy = ball_y - item["y"]

        if dx * dx + dy * dy <= 9 * 9:
            collected = True

        # Extra balls can collect items too.
        if not collected:
            for ball in extra_balls:
                dx = ball["x"] - item["x"]
                dy = ball["y"] - item["y"]

                if dx * dx + dy * dy <= 9 * 9:
                    collected = True
                    break

        if collected:
            activate_power_item(item["type"])
            power_items.remove(item)
            continue

        if item["y"] > HEIGHT + 8:
            power_items.remove(item)


def draw_power_items():
    for item in power_items:
        x = int(item["x"])
        y = int(item["y"])
        pulse = pyxel.frame_count // 5 % 2

        if item["type"] == 0:
            pyxel.circ(x, y, 5, 12)
            pyxel.circ(x, y, 3, 1)
            pyxel.text(x - 2, y - 3, "W", 7)

        elif item["type"] == 1:
            pyxel.circ(x, y, 5, 10)
            pyxel.circ(x, y, 3, 9)
            pyxel.text(x - 4, y - 3, "x3", 0)

        else:
            pyxel.circ(x, y, 5, 11)
            pyxel.circ(x, y, 3, 1)
            pyxel.text(x - 3, y - 3, "3", 7)

        if pulse:
            pyxel.pset(x, y - 6, 7)


# -----------------------------
# Reset
# -----------------------------

def reset():
    global paddle_x, paddle_w, ball_x, ball_y
    global ball_dx, ball_dy, ball_speed
    global score, combo, game_over
    global flash_timer, shake_timer, fever_timer
    global particles, music_level
    global screen_mode, submitted_this_round
    global power_items, spawn_timer, power_spawning_started
    global giant_timer, triple_timer
    global power_message_timer, power_message
    global extra_balls

    paddle_x = 65.0
    paddle_w = BASE_PADDLE_W

    ball_x = 80.0
    ball_y = 60.0
    ball_dx = 1.0
    ball_dy = 1.0
    ball_speed = 1.5

    extra_balls.clear()

    score = 0
    combo = 0
    game_over = False

    flash_timer = 0
    shake_timer = 0
    fever_timer = 0

    particles.clear()
    power_items.clear()

    spawn_timer = pyxel.rndi(120, 240)
    power_spawning_started = False

    giant_timer = 0
    triple_timer = 0
    power_message_timer = 0
    power_message = ""

    music_level = -1
    screen_mode = "game"
    submitted_this_round = False

    change_music(0)


# -----------------------------
# Name entry
# -----------------------------

def handle_name_tap(mx, my):
    global player_name
    global screen_mode
    global submitted_this_round

    for row in range(4):
        y = 57 + row * 12

        if y <= my < y + 11:
            chars = keyboard_rows[row]

            for index, char in enumerate(chars):
                x = 7 + index * 15

                if x <= mx < x + 13:
                    if char == "<":
                        player_name = player_name[:-1]
                    elif len(player_name) < 12:
                        player_name += char

                    return

    if 83 <= mx <= 153 and 106 <= my <= 117:
        name = player_name.strip()[:12]

        if name and not submitted_this_round:
            submitted_this_round = True
            screen_mode = "leaderboard"

            try:
                asyncio.ensure_future(
                    submit_and_refresh(name, score)
                )
            except Exception:
                submitted_this_round = False

    if 7 <= mx <= 77 and 106 <= my <= 117:
        player_name = player_name[:-1]


# -----------------------------
# Update
# -----------------------------

def update():
    global paddle_x, paddle_w
    global ball_x, ball_y, ball_dx, ball_dy, ball_speed
    global score, high_score, combo, game_over
    global flash_timer, shake_timer, fever_timer
    global player_name, screen_mode
    global submitted_this_round, initial_fetch_started
    global title_timer
    global giant_timer, triple_timer
    global power_message_timer, power_message

    if not initial_fetch_started:
        initial_fetch_started = True
        launch_refresh()

    # Title screen
    if screen_mode == "title":
        title_timer += 1

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if period_tab_clicked(
                pyxel.mouse_x, pyxel.mouse_y, 39
            ):
                return

            if title_timer >= 120:
                reset()

        if title_timer >= 120 and (
            pyxel.btnp(pyxel.KEY_SPACE)
            or pyxel.btnp(pyxel.KEY_RETURN)
        ):
            reset()

        return

    if flash_timer > 0:
        flash_timer -= 1

    if shake_timer > 0:
        shake_timer -= 1

    if fever_timer > 0:
        fever_timer -= 1

    if power_message_timer > 0:
        power_message_timer -= 1
    else:
        power_message = ""

    # Particles
    for particle in particles:
        particle[0] += particle[2]
        particle[1] += particle[3]
        particle[4] -= 1

    particles[:] = [
        p for p in particles if p[4] > 0
    ]

    # Game over screens
    if game_over:
        if screen_mode == "name":
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                handle_name_tap(pyxel.mouse_x, pyxel.mouse_y)

            if pyxel.btnp(pyxel.KEY_BACKSPACE):
                player_name = player_name[:-1]

            if pyxel.btnp(pyxel.KEY_RETURN):
                name = player_name.strip()[:12]

                if name and not submitted_this_round:
                    submitted_this_round = True
                    screen_mode = "leaderboard"

                    try:
                        asyncio.ensure_future(
                            submit_and_refresh(name, score)
                        )
                    except Exception:
                        submitted_this_round = False

            if pyxel.btnp(pyxel.KEY_L):
                screen_mode = "leaderboard"
                launch_refresh()

        elif screen_mode == "leaderboard":
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                if period_tab_clicked(
                    pyxel.mouse_x, pyxel.mouse_y, 38
                ):
                    return

                reset()

            elif pyxel.btnp(pyxel.KEY_SPACE):
                reset()

            elif pyxel.btnp(pyxel.KEY_N):
                player_name = ""
                screen_mode = "name"

        return

    # -------------------------
    # Power-up timers
    # -------------------------

    if giant_timer > 0:
        giant_timer -= 1

        if giant_timer == 0:
            # Return to the normal paddle width.
            paddle_w = BASE_PADDLE_W

            paddle_x = max(
                0,
                min(WIDTH - paddle_w, paddle_x)
            )

    if triple_timer > 0:
        triple_timer -= 1

    # Keep the paddle width synchronized with the active effect.
    # This also prevents the paddle from getting stuck at the wrong size.
    if giant_timer > 0:
        paddle_w = GIANT_PADDLE_W
    else:
        paddle_w = BASE_PADDLE_W

    # Paddle movement
    if pyxel.btn(pyxel.KEY_LEFT):
        paddle_x -= 3

    if pyxel.btn(pyxel.KEY_RIGHT):
        paddle_x += 3

    if pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
        paddle_x = pyxel.mouse_x - paddle_w / 2

    paddle_x = max(
        0,
        min(WIDTH - paddle_w, paddle_x)
    )

    # Ball acceleration
    ball_speed = min(7.5, 1.5 + combo * 0.18)

    # Main ball movement
    ball_x += ball_dx * ball_speed
    ball_y += ball_dy * ball_speed

    if ball_x <= 3:
        ball_x = 3
        ball_dx = abs(ball_dx)

    elif ball_x >= WIDTH - 4:
        ball_x = WIDTH - 4
        ball_dx = -abs(ball_dx)

    if ball_y <= 3:
        ball_y = 3
        ball_dy = abs(ball_dy)

    # Main ball / paddle collision
    if (
        ball_dy > 0
        and paddle_x - 3 <= ball_x <= paddle_x + paddle_w + 3
        and paddle_y - 4 <= ball_y <= paddle_y + 5
    ):
        ball_y = paddle_y - 4

        paddle_center = paddle_x + paddle_w / 2
        hit_offset = (
            (ball_x - paddle_center) / (paddle_w / 2)
        )
        hit_offset = max(-1.0, min(1.0, hit_offset))

        angle = hit_offset * math.radians(55)

        ball_dx = math.sin(angle)
        ball_dy = -math.cos(angle)

        combo += 1

        multiplier = min(5, 1 + combo // 5)
        fever = combo >= 10
        points = multiplier * (2 if fever else 1)

        if triple_timer > 0:
            points *= 3

        score += points
        high_score = max(high_score, score)

        flash_timer = 3
        shake_timer = 4

        make_particles(ball_x, ball_y, 16)

        pyxel.play(
            3,
            7 if combo % 5 == 0 else 6
        )

        if combo == 10:
            fever_timer = 90
            make_particles(ball_x, ball_y, 30)

        if combo >= 10:
            change_music(2)
        elif combo >= 5:
            change_music(1)
        else:
            change_music(0)

    # Extra ball movement and paddle collision
    for ball in extra_balls[:]:
        ball["x"] += ball["dx"] * ball_speed
        ball["y"] += ball["dy"] * ball_speed

        if ball["x"] <= 3:
            ball["x"] = 3
            ball["dx"] = abs(ball["dx"])

        elif ball["x"] >= WIDTH - 4:
            ball["x"] = WIDTH - 4
            ball["dx"] = -abs(ball["dx"])

        if ball["y"] <= 3:
            ball["y"] = 3
            ball["dy"] = abs(ball["dy"])

        if (
            ball["dy"] > 0
            and paddle_x - 3 <= ball["x"] <= paddle_x + paddle_w + 3
            and paddle_y - 4 <= ball["y"] <= paddle_y + 5
        ):
            ball["y"] = paddle_y - 4

            center = paddle_x + paddle_w / 2
            offset = (ball["x"] - center) / (paddle_w / 2)
            offset = max(-1.0, min(1.0, offset))

            angle = offset * math.radians(55)

            ball["dx"] = math.sin(angle)
            ball["dy"] = -math.cos(angle)

            combo += 1

            multiplier = min(5, 1 + combo // 5)
            points = multiplier * (2 if combo >= 10 else 1)

            if triple_timer > 0:
                points *= 3

            score += points
            high_score = max(high_score, score)

            make_particles(ball["x"], ball["y"], 10)
            pyxel.play(3, 6)

        if ball["y"] > HEIGHT:
            extra_balls.remove(ball)

    # Power-up items
    update_power_items()

    # Game over only after all balls are lost
    if ball_y > HEIGHT:
        if extra_balls:
            replacement = extra_balls.pop(0)

            ball_x = replacement["x"]
            ball_y = replacement["y"]
            ball_dx = replacement["dx"]
            ball_dy = replacement["dy"]

        else:
            game_over = True
            combo = 0

            pyxel.stop(3)
            pyxel.play(3, 8)
            change_music(0)

            screen_mode = "name"
            player_name = ""
            submitted_this_round = False


# -----------------------------
# Draw
# -----------------------------

def draw():
    if screen_mode == "title":
        draw_title()
        return

    interval = (
        4 if combo >= 10
        else 8 if combo >= 5
        else 14
    )

    phase = pyxel.frame_count // interval
    bg = COLORS[phase % len(COLORS)]

    if flash_timer > 0:
        bg = 7

    pyxel.cls(bg)

    sx = pyxel.rndi(-1, 1) if shake_timer > 0 else 0
    sy = pyxel.rndi(-1, 1) if shake_timer > 0 else 0

    for i in range(8):
        x = (
            i * 23
            + pyxel.frame_count * (i % 3 + 1)
        ) % WIDTH

        color = COLORS[(i + phase) % len(COLORS)]

        pyxel.line(
            x + sx, sy,
            x + sx, HEIGHT + sy,
            color
        )

    for i in range(6):
        y = (
            i * 20 + pyxel.frame_count // 2
        ) % HEIGHT

        color = COLORS[(i + phase + 2) % len(COLORS)]

        pyxel.circ(5 + sx, y + sy, 2, color)
        pyxel.circ(
            WIDTH - 6 + sx,
            HEIGHT - y + sy,
            2, color
        )

    if combo >= 10:
        for i in range(10):
            x = i * 16
            color = COLORS[(i + phase) % len(COLORS)]
            pyxel.rect(x + sx, sy, 8, 3, color)

    # Paddle: draw using the current paddle width.
    paddle_color = 12 if giant_timer > 0 else 11

    pyxel.rect(
        int(paddle_x + sx),
        int(paddle_y + sy),
        int(paddle_w),
        5,
        paddle_color
    )

    pyxel.rectb(
        int(paddle_x + sx - 1),
        int(paddle_y + sy - 1),
        int(paddle_w) + 2,
        7,
        7
    )

    # Main ball
    pyxel.circ(
        int(ball_x + sx),
        int(ball_y + sy),
        4, 10
    )

    pyxel.pset(
        int(ball_x + sx),
        int(ball_y + sy),
        7
    )

    # Extra balls
    for ball in extra_balls:
        pyxel.circ(
            int(ball["x"] + sx),
            int(ball["y"] + sy),
            4, 11
        )

        pyxel.pset(
            int(ball["x"] + sx),
            int(ball["y"] + sy),
            7
        )

    # Power-up items
    draw_power_items()

    # Particles
    for particle in particles:
        pyxel.pset(
            int(particle[0]),
            int(particle[1]),
            particle[5]
        )

    # HUD
    pyxel.text(5, 5, "SCORE:" + str(score), 7)
    pyxel.text(5, 15, "BEST:" + str(high_score), 10)
    pyxel.text(5, 25, "COMBO:" + str(combo), 11)

    multiplier = min(5, 1 + combo // 5)

    if combo >= 5:
        pyxel.text(
            85, 25,
            "x" + str(multiplier) + " BONUS!",
            10
        )

    ball_count = 1 + len(extra_balls)

    if ball_count > 1:
        pyxel.text(110, 5, "BALLS:" + str(ball_count), 11)

    # Active power-up indicators
    if giant_timer > 0:
        seconds = (giant_timer + 59) // 60
        pyxel.text(5, 36, "GIANT:" + str(seconds) + "s", 12)

    if triple_timer > 0:
        seconds = (triple_timer + 59) // 60
        pyxel.text(87, 36, "SCORE x3:" + str(seconds) + "s", 10)

    if combo >= 10:
        color = (
            8 if pyxel.frame_count // 5 % 2 == 0
            else 10
        )

        pyxel.text(49, 45, "F E V E R !", color)

        if fever_timer > 0:
            pyxel.text(35, 55, "FEVER x2 SCORE!", 7)

    # Power-up notification
    if power_message_timer > 0:
        if "GIANT" in power_message:
            color = 12
        elif "MULTI" in power_message or "BALLS" in power_message:
            color = 11
        else:
            color = 10

        pyxel.rect(29, 66, 102, 13, 0)
        pyxel.rectb(29, 66, 102, 13, color)
        pyxel.text(34, 70, power_message, color)

    # Game over overlay
    if game_over:
        pyxel.rect(3, 28, 154, 90, 0)
        pyxel.rectb(3, 28, 154, 90, 10)

        if screen_mode == "name":
            pyxel.text(45, 31, "GAME OVER", 8)
            pyxel.text(7, 41, "SCORE:" + str(score), 7)
            pyxel.text(7, 49, "TAP KEYS TO ENTER NAME", 11)

            for row, chars in enumerate(keyboard_rows):
                y = 57 + row * 12

                for index, char in enumerate(chars):
                    x = 7 + index * 15

                    pyxel.rect(x, y, 13, 11, 1)
                    pyxel.rectb(x, y, 13, 11, 10)

                    label = "BK" if char == "<" else char
                    pyxel.text(x + 2, y + 3, label, 7)

            pyxel.rect(7, 106, 70, 11, 8)
            pyxel.text(19, 109, "DELETE", 7)

            pyxel.rect(83, 106, 70, 11, 3)
            pyxel.text(96, 109, "SUBMIT", 7)

            pyxel.text(
                7, 100,
                "NAME:" + player_name[:12],
                7
            )

        elif screen_mode == "leaderboard":
            draw_logo("DOPABALL", 43, 29, 1, 8)
            draw_logo("DOPABALL", 42, 28, 1, 10)

            draw_period_tabs(38)
            pyxel.text(42, 49, "TOP 7 SCORES", 10)

            if leaderboard_status == "LOADING":
                pyxel.text(43, 59, "LOADING...", 7)

            elif leaderboard_status == "ERROR":
                pyxel.text(12, 59, "RANKING OFFLINE", 8)
                pyxel.text(7, 68, leaderboard_error[:25], 7)

            elif not leaderboard:
                pyxel.text(29, 59, "NO SCORES YET", 7)

            else:
                for i, item in enumerate(leaderboard[:7]):
                    y = 57 + i * 6

                    name = str(
                        item.get("player_name", "PLAYER")
                    )[:10]

                    points = str(item.get("score", 0))

                    pyxel.text(7, y, str(i + 1) + ".", 10)
                    pyxel.text(23, y, name, 7)
                    pyxel.text(112, y, points, 11)

            pyxel.text(
                7, 104,
                submit_status[:22],
                6 if submit_status == "SAVED" else 8
            )

            pyxel.text(7, 112, "TAP / SPACE: RETRY", 10)


pyxel.run(update, draw)
