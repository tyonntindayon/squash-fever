import pyxel
import math
import asyncio
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

WIDTH = 160
HEIGHT = 120
JST = timezone(timedelta(hours=9))

HUD_HEIGHT = 12
CEILING_Y = HUD_HEIGHT + 2
BALL_MIN_X = 4
BALL_MAX_X = WIDTH - 4

BASE_PADDLE_W = 30
GIANT_PADDLE_W = 42
MAX_HEARTS = 3
MAX_BALLS = 7

INITIAL_BALL_SPEED = 1.5
MAX_BALL_SPEED = 7.5
TIME_ACCELERATION = 0.00035

SUPABASE_URL = "https://hxjzgilnqxnnxlpqyasu.supabase.co"
SUPABASE_KEY = "sb_publishable_sae6J_mLG2NpvPFf2MI-kQ_ozswuMhR"
TABLE_URL = SUPABASE_URL + "/rest/v1/squash_scores"

SAVE_FILE = "dopaball_save.json"
GAME_TITLE = "DOPABALL"
TITLE_BYLINE = "created by TugumuKudo"

pyxel.init(WIDTH, HEIGHT, title=GAME_TITLE + " - " + TITLE_BYLINE)

COLORS = [1, 2, 5, 6, 9, 12, 13]

paddle_x = 55.0
paddle_y = 100
paddle_w = BASE_PADDLE_W

ball_x = 70.0
ball_y = 55.0
ball_dx = 0.0
ball_dy = -1.0
ball_speed = INITIAL_BALL_SPEED
ball_attached = False

extra_balls = []

score = 0
high_score = 0
combo = 0
max_combo = 0
max_speed = INITIAL_BALL_SPEED
game_frames = 0
game_over = False
new_record = False

hearts = MAX_HEARTS

flash_timer = 0
shake_timer = 0
fever_timer = 0
slow_timer = 0
shield_timer = 0
score_boost_timer = 0
music_level = -1
particles = []
score_popups = []

power_items = []
spawn_timer = 180
power_spawning_started = False
giant_timer = 0
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

save_data = {
    "high_score": 0,
    "max_combo": 0,
    "max_speed": INITIAL_BALL_SPEED,
    "last_score": 0
}

keyboard_rows = [
    "ABCDEFGHIJ",
    "KLMNOPQRST",
    "UVWXYZ0123",
    "456789_-<"
]

NAME_INPUT_X = 8
NAME_INPUT_Y = 64
NAME_INPUT_W = 144
NAME_INPUT_H = 8

KEYBOARD_START_X = 8
KEYBOARD_START_Y = 70
KEYBOARD_KEY_W = 12
KEYBOARD_KEY_H = 7
KEYBOARD_KEY_GAP = 1
KEYBOARD_ROW_GAP = 1

DELETE_BUTTON = (8, 103, 56, 10)
SUBMIT_BUTTON = (92, 103, 60, 10)


def get_name_input_rect():
    return (NAME_INPUT_X, NAME_INPUT_Y, NAME_INPUT_W, NAME_INPUT_H)


def get_keyboard_key_rect(row_index, key_index):
    x = KEYBOARD_START_X + key_index * (KEYBOARD_KEY_W + KEYBOARD_KEY_GAP)
    y = KEYBOARD_START_Y + row_index * (KEYBOARD_KEY_H + KEYBOARD_ROW_GAP)
    return (x, y, KEYBOARD_KEY_W, KEYBOARD_KEY_H)


def get_delete_button_rect():
    return DELETE_BUTTON


def get_submit_button_rect():
    return SUBMIT_BUTTON


def submit_current_name():
    global screen_mode, submitted_this_round, submit_status

    name = str(player_name or "").strip()[:12]
    if not name or submitted_this_round or submit_task_running:
        return False

    submitted_this_round = True
    screen_mode = "leaderboard"
    submit_status = "SENDING"
    try:
        asyncio.ensure_future(submit_and_refresh(name, score))
        return True
    except Exception:
        submitted_this_round = False
        submit_status = "LOCAL SAVE"
        return False


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


def play_hit_sound(combo_value):
    if combo_value >= 10:
        pyxel.play(3, 7)
    elif combo_value >= 5:
        pyxel.play(3, 6)
    else:
        pyxel.play(3, 9 if combo_value % 3 == 0 else 6)


def make_particles(x, y, amount=12, color=None):
    for _ in range(amount):
        angle = pyxel.rndf(0, math.pi * 2)
        speed = pyxel.rndf(0.5, 2.5)
        particle_color = color if color is not None else pyxel.rndi(8, 15)

        particles.append([
            float(x), float(y),
            math.cos(angle) * speed,
            math.sin(angle) * speed,
            pyxel.rndi(10, 20),
            particle_color
        ])


def add_score_popup(x, y, points, multiplier):
    score_popups.append({
        "x": float(x),
        "y": float(y),
        "text": "+" + str(points),
        "timer": 42,
        "color": 10 if multiplier >= 3 else 7
    })


# -----------------------------
# Local save
# -----------------------------

def load_save():
    global save_data, high_score, max_combo, max_speed

    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as file:
            loaded = json.load(file)

        save_data["high_score"] = max(0, int(loaded.get("high_score", 0)))
        save_data["max_combo"] = max(0, int(loaded.get("max_combo", 0)))
        save_data["max_speed"] = max(INITIAL_BALL_SPEED, float(loaded.get("max_speed", INITIAL_BALL_SPEED)))
        save_data["last_score"] = max(0, int(loaded.get("last_score", 0)))
    except Exception:
        pass

    high_score = save_data["high_score"]
    max_combo = save_data["max_combo"]
    max_speed = save_data["max_speed"]


def save_records():
    global save_data

    save_data["high_score"] = max(save_data["high_score"], high_score)
    save_data["max_combo"] = max(save_data["max_combo"], max_combo)
    save_data["max_speed"] = max(save_data["max_speed"], max_speed)
    save_data["last_score"] = max(save_data["last_score"], score)

    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as file:
            json.dump(save_data, file)
    except Exception:
        pass


load_save()


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
        if char not in LOGO_FONT:
            continue

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
# Ranking
# -----------------------------

def draw_period_tabs(y):
    daily_color = 10 if selected_period == "DAILY" else 5
    pyxel.rect(22, y, 52, 9, daily_color)
    pyxel.rectb(22, y, 52, 9, 7)
    pyxel.text(32, y + 2, "DAILY", 0 if selected_period == "DAILY" else 7)

    monthly_color = 10 if selected_period == "MONTHLY" else 5
    pyxel.rect(86, y, 52, 9, monthly_color)
    pyxel.rectb(86, y, 52, 9, 7)
    pyxel.text(94, y + 2, "MONTHLY", 0 if selected_period == "MONTHLY" else 7)


def period_tab_clicked(mx, my, y):
    global selected_period

    if not (y <= my < y + 10):
        return False

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
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
    else:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
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
    logo_color = 10 if pyxel.frame_count // 12 % 2 == 0 else 11

    draw_logo(logo, start_x + 2, 6, scale, 8)
    draw_logo(logo, start_x, 4, scale, logo_color)

    pyxel.line(12, 23, 148, 23, 10)
    pyxel.line(24, 25, 136, 25, 12)
    pyxel.text(52, 29, "TYON GAMES", 7)
    pyxel.text(30, 35, TITLE_BYLINE, 6)

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

            pyxel.text(14, y, str(i + 1) + ".", 10 if i == 0 else 7)
            pyxel.text(29, y, name, 7)
            pyxel.text(112, y, points, 10 if i == 0 else 11)

    if title_timer < 120:
        pyxel.text(54, 100, "GET READY...", 7)
    elif pyxel.frame_count // 20 % 2 == 0:
        pyxel.text(45, 100, "TAP TO START", 10)

    pyxel.text(25, 109, "    created by Tugumu Kudo", 6)
    pyxel.text(38, 115, "BEST:" + str(high_score), 7)


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

    name = str(name).strip()
    if not name:
        raise ValueError("empty player name")

    response = await pyfetch(
        TABLE_URL,
        method="POST",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": "Bearer " + SUPABASE_KEY,
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        },
        body=json.dumps([{"player_name": name, "score": int(points)}])
    )

    if response.status >= 400:
        raise RuntimeError("HTTP " + str(response.status))


async def refresh_leaderboard():
    global leaderboard, leaderboard_status, leaderboard_error
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
        if not isinstance(rows, list):
            rows = []

        best_by_player = {}

        for item in rows:
            name = str(item.get("player_name", "PLAYER")).strip()
            points = int(item.get("score", 0))

            if not name:
                name = "PLAYER"

            key = name.upper()

            if key not in best_by_player or points > int(best_by_player[key].get("score", 0)):
                best_by_player[key] = {
                    "player_name": name,
                    "score": points,
                    "created_at": item.get("created_at", "")
                }

        leaderboard = sorted(best_by_player.values(), key=lambda item: (-int(item.get("score", 0)), item.get("created_at", "")))
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
    global submit_task_running, submit_status
    global leaderboard_status, leaderboard_error

    if submit_task_running:
        return

    submit_task_running = True
    submit_status = "SENDING"
    save_data["last_score"] = max(save_data["last_score"], int(points))
    save_records()

    try:
        await send_score(name, points)
        submit_status = "SAVED"
        leaderboard_error = ""
        leaderboard_status = "OK"
        await refresh_leaderboard()

    except Exception as error:
        submit_status = "LOCAL SAVE"
        leaderboard_status = "ERROR"
        leaderboard_error = str(error)[:25]
        save_data["last_score"] = max(save_data["last_score"], int(points))
        save_records()

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

POWER_EFFECTS = {
    "giant": {"weight": 20, "label": "GIANT", "color": 12, "icon": "G"},
    "multi_ball": {"weight": 18, "label": "MULTI", "color": 11, "icon": "M"},
    "slow_time": {"weight": 20, "label": "SLOW", "color": 10, "icon": "S"},
    "shield": {"weight": 14, "label": "SHIELD", "color": 9, "icon": "H"},
    "score_boost": {"weight": 15, "label": "BOOST", "color": 13, "icon": "B"},
}


def pick_random_power_effect():
    total = sum(data["weight"] for data in POWER_EFFECTS.values())
    roll = pyxel.rndi(0, total - 1)
    cutoff = 0

    for key, data in POWER_EFFECTS.items():
        cutoff += data["weight"]
        if roll < cutoff:
            return key

    return "giant"


def spawn_power_item():
    effect = pick_random_power_effect()
    power_items.append({
        "x": float(pyxel.rndi(10, WIDTH - 10)),
        "y": float(CEILING_Y + 4),
        "type": effect,
        "speed": pyxel.rndf(0.6, 1.0),
        "color": POWER_EFFECTS[effect]["color"],
        "icon": POWER_EFFECTS[effect]["icon"],
    })


def activate_power_item(item_type):
    global giant_timer, paddle_w, paddle_x, power_message, power_message_timer
    global slow_timer, shield_timer, score_boost_timer

    if item_type == "giant":
        giant_timer = 360
        paddle_w = GIANT_PADDLE_W
        paddle_x = max(0, min(WIDTH - paddle_w, paddle_x))
        power_message = "GIANT PADDLE!"
        make_particles(ball_x, ball_y, 24, 12)

    elif item_type == "multi_ball":
        current_ball_count = 1 + len(extra_balls)
        balls_to_add = max(0, min(2, MAX_BALLS - current_ball_count))

        for _ in range(balls_to_add):
            angle = pyxel.rndf(-0.8, 0.8)
            extra_balls.append({
                "x": ball_x,
                "y": ball_y,
                "dx": math.sin(angle),
                "dy": -abs(math.cos(angle))
            })

        power_message = "MULTI BALL!" if balls_to_add > 0 else "BALL LIMIT!"
        make_particles(ball_x, ball_y, 30, 11)

    elif item_type == "slow_time":
        slow_timer = 420
        power_message = "SLOW MOTION!"
        make_particles(ball_x, ball_y, 18, 10)

    elif item_type == "shield":
        shield_timer = 480
        power_message = "SHIELD UP!"
        make_particles(ball_x, ball_y, 22, 9)

    elif item_type == "score_boost":
        score_boost_timer = 420
        power_message = "SCORE BOOST!"
        make_particles(ball_x, ball_y, 22, 13)

    power_message_timer = 90
    pyxel.play(3, 9)


def update_power_items():
    global spawn_timer, power_spawning_started

    if pyxel.frame_count >= 180 and ball_speed >= 2.4:
        if not power_spawning_started:
            power_spawning_started = True
            spawn_timer = pyxel.rndi(120, 240)

        spawn_timer -= 1

        speed_factor = min(1.0, max(0.0, (ball_speed - 2.4) / (MAX_BALL_SPEED - 2.4)))
        min_interval = int(300 - speed_factor * 210)
        max_interval = int(420 - speed_factor * 300)

        if spawn_timer <= 0:
            spawn_power_item()
            min_interval = max(60, min_interval)
            max_interval = max(min_interval, max_interval)
            spawn_timer = pyxel.rndi(min_interval, max_interval)

    for item in power_items[:]:
        item["y"] += item["speed"]
        collected = False

        paddle_left = paddle_x
        paddle_right = paddle_x + paddle_w
        paddle_top = paddle_y
        paddle_bottom = paddle_y + 5

        if paddle_left <= item["x"] <= paddle_right and paddle_top <= item["y"] <= paddle_bottom:
            collected = True

        if collected:
            activate_power_item(item["type"])
            power_items.remove(item)
        elif item["y"] > HEIGHT + 8:
            power_items.remove(item)


def draw_power_items():
    for item in power_items:
        x = int(item["x"])
        y = int(item["y"])
        pulse = pyxel.frame_count // 5 % 2

        pyxel.circ(x, y, 5, item["color"])
        pyxel.circ(x, y, 3, 1)
        pyxel.text(x - 2, y - 2, item["icon"], 7)

        if pulse:
            pyxel.pset(x, y - 6, 7)


# -----------------------------
# Hearts UI
# -----------------------------

def draw_heart(x, y, filled=True):
    color = 8 if filled else 5

    pyxel.rect(x + 1, y, 3, 2, color)
    pyxel.rect(x + 6, y, 3, 2, color)
    pyxel.rect(x, y + 1, 10, 3, color)
    pyxel.rect(x + 1, y + 4, 8, 2, color)
    pyxel.rect(x + 2, y + 6, 6, 2, color)
    pyxel.rect(x + 3, y + 8, 4, 1, color)

    if not filled:
        pyxel.rect(x + 3, y + 2, 4, 3, 1)
        pyxel.pset(x + 2, y + 1, 1)
        pyxel.pset(x + 7, y + 1, 1)
        pyxel.rect(x + 3, y + 5, 4, 2, 1)
        pyxel.rect(x + 4, y + 7, 2, 1, 1)


# -----------------------------
# Ball control
# -----------------------------

def attach_ball_to_paddle():
    global ball_x, ball_y, ball_dx, ball_dy, ball_attached

    ball_x = paddle_x + paddle_w / 2
    ball_y = paddle_y - 8
    ball_dx = 0.0
    ball_dy = -1.0
    ball_attached = True


def launch_attached_ball():
    global ball_dx, ball_dy, ball_attached

    angle = pyxel.rndf(-0.55, 0.55)
    ball_dx = math.sin(angle)
    ball_dy = -abs(math.cos(angle))
    ball_attached = False

    pyxel.play(3, 6)


# -----------------------------
# Score and records
# -----------------------------

def award_hit(x, y, is_extra=False):
    global score, high_score, combo, max_combo
    global ball_speed, max_speed, flash_timer, shake_timer
    global fever_timer, new_record

    combo += 1
    max_combo = max(max_combo, combo)

    fever = combo >= 10
    fever_factor = 3 if fever else 1
    combo_factor = 1 + combo // 3
    speed_factor = 1 + int(ball_speed * 1.8)
    multi_factor = 1.5 if (is_extra or extra_balls) else 1.0

    points = int(2 * combo_factor * speed_factor * fever_factor * multi_factor)
    if score_boost_timer > 0:
        points = int(points * 1.5)
    score += points

    if score > high_score:
        high_score = score
        new_record = True
        save_records()

    combo_speed = min(MAX_BALL_SPEED, INITIAL_BALL_SPEED + combo * 0.12)
    ball_speed = min(MAX_BALL_SPEED, max(ball_speed, combo_speed))
    max_speed = max(max_speed, ball_speed)

    flash_timer = 3
    shake_timer = 4

    particle_amount = 12 + min(combo, 18)
    particle_color = 10 if fever else (11 if combo >= 5 else None)

    make_particles(x, y, particle_amount, particle_color)
    add_score_popup(x, y, points, combo_factor)

    play_hit_sound(combo)

    if combo == 10:
        fever_timer = 120
        make_particles(x, y, 35, 10)

    if combo >= 10:
        change_music(2)
    elif combo >= 5:
        change_music(1)
    else:
        change_music(0)


def lose_heart_and_continue():
    global hearts, extra_balls, combo, game_over
    global screen_mode, player_name, submitted_this_round
    global flash_timer, shake_timer, power_message
    global power_message_timer, ball_attached, shield_timer

    if shield_timer > 0:
        shield_timer = 0
        power_message = "SHIELD BLOCK!"
        power_message_timer = 70
        make_particles(ball_x, ball_y, 18, 9)
        return

    hearts -= 1
    extra_balls.clear()

    flash_timer = 8
    shake_timer = 8
    save_records()

    if hearts <= 0:
        hearts = 0
        game_over = True
        combo = 0
        ball_attached = False

        pyxel.stop(3)
        pyxel.play(3, 8)
        change_music(0)

        screen_mode = "name"
        player_name = ""
        submitted_this_round = False

    else:
        combo = 0
        attach_ball_to_paddle()
        power_message = "LIFE LOST!"
        power_message_timer = 70
        change_music(0)


# -----------------------------
# Reset
# -----------------------------

def reset():
    global paddle_x, paddle_y, paddle_w
    global ball_x, ball_y, ball_dx, ball_dy, ball_speed
    global ball_attached, score, combo, max_combo
    global game_over, hearts, flash_timer, shake_timer
    global fever_timer, particles, score_popups, music_level
    global screen_mode, submitted_this_round, new_record
    global power_items, spawn_timer, power_spawning_started
    global giant_timer, power_message_timer, power_message
    global extra_balls, game_frames, slow_timer, shield_timer, score_boost_timer

    paddle_x = 55.0
    paddle_y = 100
    paddle_w = BASE_PADDLE_W

    ball_x = 70.0
    ball_y = 55.0
    ball_dx = 0.0
    ball_dy = -1.0
    ball_speed = INITIAL_BALL_SPEED
    ball_attached = False

    extra_balls.clear()

    score = 0
    combo = 0
    max_combo = 0
    game_frames = 0
    game_over = False
    hearts = MAX_HEARTS
    new_record = False

    flash_timer = 0
    shake_timer = 0
    fever_timer = 0
    slow_timer = 0
    shield_timer = 0
    score_boost_timer = 0

    particles.clear()
    score_popups.clear()
    power_items.clear()

    spawn_timer = pyxel.rndi(120, 240)
    power_spawning_started = False

    giant_timer = 0
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
    global player_name, screen_mode, submitted_this_round
    global submit_status

    player_name = str(player_name or "")

    for row, chars in enumerate(keyboard_rows):
        row_y = KEYBOARD_START_Y + row * (KEYBOARD_KEY_H + KEYBOARD_ROW_GAP)
        if row_y <= my < row_y + KEYBOARD_KEY_H:
            for index, char in enumerate(chars):
                x, y, w, h = get_keyboard_key_rect(row, index)
                if x <= mx < x + w and y <= my < y + h:
                    if char == "<":
                        player_name = player_name[:-1]
                    elif len(player_name) < 12:
                        player_name += char
                    return

    delete_x, delete_y, delete_w, delete_h = get_delete_button_rect()
    if delete_x <= mx < delete_x + delete_w and delete_y <= my < delete_y + delete_h:
        player_name = player_name[:-1]
        return

    submit_x, submit_y, submit_w, submit_h = get_submit_button_rect()
    if submit_x <= mx < submit_x + submit_w and submit_y <= my < submit_y + submit_h:
        submit_current_name()
        return


# -----------------------------
# Update
# -----------------------------

def update():
    global paddle_x, paddle_w
    global ball_x, ball_y, ball_dx, ball_dy, ball_speed
    global score, combo, game_over, flash_timer, shake_timer
    global fever_timer, player_name, screen_mode
    global initial_fetch_started, title_timer
    global giant_timer, power_message_timer, power_message
    global game_frames, max_speed, new_record
    global slow_timer, shield_timer, score_boost_timer

    if not initial_fetch_started:
        initial_fetch_started = True
        launch_refresh()

    if screen_mode == "title":
        title_timer += 1

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if period_tab_clicked(pyxel.mouse_x, pyxel.mouse_y, 39):
                return
            if title_timer >= 120:
                reset()

        if title_timer >= 120 and (pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN)):
            reset()

        return

    if flash_timer > 0:
        flash_timer -= 1

    if shake_timer > 0:
        shake_timer -= 1

    if fever_timer > 0:
        fever_timer -= 1

    if slow_timer > 0:
        slow_timer -= 1

    if shield_timer > 0:
        shield_timer -= 1

    if score_boost_timer > 0:
        score_boost_timer -= 1

    if power_message_timer > 0:
        power_message_timer -= 1
    else:
        power_message = ""

    for particle in particles:
        particle[0] += particle[2]
        particle[1] += particle[3]
        particle[4] -= 1

    particles[:] = [p for p in particles if p[4] > 0]

    for popup in score_popups:
        popup["y"] -= 0.35
        popup["timer"] -= 1

    score_popups[:] = [p for p in score_popups if p["timer"] > 0]

    if game_over:
        if screen_mode == "name":
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                handle_name_tap(pyxel.mouse_x, pyxel.mouse_y)

            if pyxel.btnp(pyxel.KEY_BACKSPACE):
                player_name = str(player_name or "")[:-1]

            if pyxel.btnp(pyxel.KEY_RETURN):
                submit_current_name()

            if pyxel.btnp(pyxel.KEY_L):
                screen_mode = "leaderboard"
                launch_refresh()

        elif screen_mode == "leaderboard":
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                if period_tab_clicked(pyxel.mouse_x, pyxel.mouse_y, 38):
                    return
                reset()

            elif pyxel.btnp(pyxel.KEY_SPACE):
                reset()

            elif pyxel.btnp(pyxel.KEY_N):
                player_name = ""
                screen_mode = "name"

        return

    if giant_timer > 0:
        giant_timer -= 1

    paddle_w = GIANT_PADDLE_W if giant_timer > 0 else BASE_PADDLE_W
    paddle_x = max(0, min(WIDTH - paddle_w, paddle_x))

    if pyxel.btn(pyxel.KEY_LEFT):
        paddle_x -= 3

    if pyxel.btn(pyxel.KEY_RIGHT):
        paddle_x += 3

    if pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
        paddle_x = pyxel.mouse_x - paddle_w / 2

    paddle_x = max(0, min(WIDTH - paddle_w, paddle_x))

    if ball_attached:
        ball_x = paddle_x + paddle_w / 2
        ball_y = paddle_y - 8

        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            launch_attached_ball()

        return

    game_frames += 1

    ball_speed = min(MAX_BALL_SPEED, ball_speed + TIME_ACCELERATION)

    combo_speed = min(MAX_BALL_SPEED, INITIAL_BALL_SPEED + combo * 0.12)
    ball_speed = max(ball_speed, combo_speed)
    max_speed = max(max_speed, ball_speed)

    speed_factor = 0.85 if slow_timer > 0 else 1.0
    movement_speed = ball_speed * speed_factor

    ball_x += ball_dx * movement_speed
    ball_y += ball_dy * movement_speed

    if ball_x <= BALL_MIN_X:
        ball_x = BALL_MIN_X
        ball_dx = abs(ball_dx)
        make_particles(ball_x, ball_y, 4, 7)
    elif ball_x >= BALL_MAX_X:
        ball_x = BALL_MAX_X
        ball_dx = -abs(ball_dx)
        make_particles(ball_x, ball_y, 4, 7)

    if ball_y <= CEILING_Y + 4:
        ball_y = CEILING_Y + 4
        ball_dy = abs(ball_dy)
        make_particles(ball_x, ball_y, 4, 7)

    if ball_dy > 0 and paddle_x - 3 <= ball_x <= paddle_x + paddle_w + 3 and paddle_y - 4 <= ball_y <= paddle_y + 5:
        ball_y = paddle_y - 4

        center = paddle_x + paddle_w / 2
        offset = (ball_x - center) / (paddle_w / 2)
        offset = max(-1.0, min(1.0, offset))

        angle = offset * math.radians(55)
        ball_dx = math.sin(angle)
        ball_dy = -math.cos(angle)

        award_hit(ball_x, ball_y, False)

    for ball in extra_balls[:]:
        ball["x"] += ball["dx"] * movement_speed
        ball["y"] += ball["dy"] * movement_speed

        if ball["x"] <= BALL_MIN_X:
            ball["x"] = BALL_MIN_X
            ball["dx"] = abs(ball["dx"])
        elif ball["x"] >= BALL_MAX_X:
            ball["x"] = BALL_MAX_X
            ball["dx"] = -abs(ball["dx"])

        if ball["y"] <= CEILING_Y + 4:
            ball["y"] = CEILING_Y + 4
            ball["dy"] = abs(ball["dy"])

        if ball["dy"] > 0 and paddle_x - 3 <= ball["x"] <= paddle_x + paddle_w + 3 and paddle_y - 4 <= ball["y"] <= paddle_y + 5:
            ball["y"] = paddle_y - 4

            center = paddle_x + paddle_w / 2
            offset = (ball["x"] - center) / (paddle_w / 2)
            offset = max(-1.0, min(1.0, offset))

            angle = offset * math.radians(55)
            ball["dx"] = math.sin(angle)
            ball["dy"] = -math.cos(angle)

            award_hit(ball["x"], ball["y"], True)

        if ball["y"] > HEIGHT:
            extra_balls.remove(ball)

    update_power_items()

    if ball_y > HEIGHT and extra_balls:
        replacement = extra_balls.pop(0)
        ball_x = replacement["x"]
        ball_y = replacement["y"]
        ball_dx = replacement["dx"]
        ball_dy = replacement["dy"]
    elif ball_y > HEIGHT and not extra_balls:
        lose_heart_and_continue()


# -----------------------------
# HUD
# -----------------------------

def draw_game_hud():
    pyxel.rect(0, 0, WIDTH, HUD_HEIGHT, 0)
    pyxel.line(0, HUD_HEIGHT, WIDTH - 1, HUD_HEIGHT, 7)

    pyxel.text(2, 2, "S:" + str(score), 7)
    pyxel.text(43, 2, "B:" + str(high_score), 10)

    pyxel.text(105, 2, "HP", 7)

    for i in range(MAX_HEARTS):
        draw_heart(123 + i * 11, 1, filled=(i < hearts))

    pyxel.text(2, 7, "C:" + str(combo), 11)

    ball_count = 1 + len(extra_balls)
    pyxel.text(56, 7, "BALL:" + str(ball_count), 11)

    multiplier = min(5, 1 + combo // 5)
    if combo >= 5:
        pyxel.text(111, 7, "x" + str(multiplier), 10)

    if slow_timer > 0:
        pyxel.text(130, 7, "SLOW", 10)
    if shield_timer > 0:
        pyxel.text(130, 7, "SHIELD", 9)
    if score_boost_timer > 0:
        pyxel.text(130, 7, "BOOST", 13)


# -----------------------------
# Draw
# -----------------------------

def draw():
    if screen_mode == "title":
        draw_title()
        return

    speed_phase = int(ball_speed * 2)
    combo_phase = combo // 3

    interval = 3 if combo >= 10 else 5 if combo >= 5 else max(4, 14 - int(ball_speed))
    phase = pyxel.frame_count // interval
    bg = COLORS[(phase + speed_phase + combo_phase) % len(COLORS)]

    if flash_timer > 0:
        bg = 7

    pyxel.cls(bg)

    sx = pyxel.rndi(-1, 1) if shake_timer > 0 else 0
    sy = pyxel.rndi(-1, 1) if shake_timer > 0 else 0

    for i in range(8):
        speed_factor = max(1, int(ball_speed))
        x = (i * 23 + pyxel.frame_count * (i % 3 + 1) * speed_factor) % WIDTH
        color = COLORS[(i + phase + combo_phase) % len(COLORS)]
        pyxel.line(x + sx, CEILING_Y + sy, x + sx, HEIGHT + sy, color)

    for i in range(6):
        y = CEILING_Y + (i * 20 + pyxel.frame_count * max(1, int(ball_speed))) % (HEIGHT - CEILING_Y)
        color = COLORS[(i + phase + 2) % len(COLORS)]
        pyxel.circ(5 + sx, y + sy, 2, color)
        pyxel.circ(WIDTH - 6 + sx, HEIGHT - y + sy, 2, color)

    if combo >= 10:
        for i in range(10):
            x = i * 16
            pyxel.rect(x + sx, CEILING_Y + sy, 8, 3, COLORS[(i + phase) % len(COLORS)])

    pyxel.line(0, CEILING_Y, WIDTH - 1, CEILING_Y, 7)

    paddle_color = 12 if giant_timer > 0 else 11
    pyxel.rect(int(paddle_x + sx), int(paddle_y + sy), int(paddle_w), 5, paddle_color)
    pyxel.rectb(int(paddle_x + sx - 1), int(paddle_y + sy - 1), int(paddle_w) + 2, 7, 7)

    if shield_timer > 0:
        pyxel.circ(int(paddle_x + paddle_w / 2 + sx), int(paddle_y + sy), 12, 9)
        pyxel.circ(int(paddle_x + paddle_w / 2 + sx), int(paddle_y + sy), 9, 1)

    pyxel.circ(int(ball_x + sx), int(ball_y + sy), 4, 10)
    pyxel.pset(int(ball_x + sx), int(ball_y + sy), 7)

    for ball in extra_balls:
        pyxel.circ(int(ball["x"] + sx), int(ball["y"] + sy), 4, 11)
        pyxel.pset(int(ball["x"] + sx), int(ball["y"] + sy), 7)

    draw_power_items()

    for particle in particles:
        pyxel.pset(int(particle[0]), int(particle[1]), particle[5])

    for popup in score_popups:
        color = popup["color"]
        if popup["timer"] < 12 and popup["timer"] // 2 % 2 == 0:
            color = 7
        pyxel.text(int(popup["x"]), int(popup["y"]), popup["text"], color)

    draw_game_hud()

    if ball_attached and not game_over:
        pyxel.text(43, 83, "SPACE / TAP", 7)

    if giant_timer > 0:
        seconds = (giant_timer + 59) // 60
        pyxel.text(5, 20, "GIANT:" + str(seconds) + "s", 12)
    if slow_timer > 0:
        seconds = (slow_timer + 59) // 60
        pyxel.text(62, 20, "SLOW:" + str(seconds) + "s", 10)
    if score_boost_timer > 0:
        seconds = (score_boost_timer + 59) // 60
        pyxel.text(103, 20, "BOOST:" + str(seconds) + "s", 13)
    if shield_timer > 0:
        seconds = (shield_timer + 59) // 60
        pyxel.text(103, 20, "SHIELD:" + str(seconds) + "s", 9)

    if combo >= 10:
        color = 8 if pyxel.frame_count // 5 % 2 == 0 else 10
        pyxel.text(49, 55, "F E V E R !", color)
        pyxel.text(35, 65, "FEVER x3 SCORE!", 7)

    if new_record and score > 0:
        color = 10 if pyxel.frame_count // 5 % 2 == 0 else 7
        pyxel.text(42, 36, "NEW HIGH SCORE!", color)

    if power_message_timer > 0:
        if "GIANT" in power_message:
            color = 12
        elif "MULTI" in power_message or "BALL" in power_message:
            color = 11
        elif "SLOW" in power_message:
            color = 10
        elif "SHIELD" in power_message:
            color = 9
        elif "BOOST" in power_message:
            color = 13
        else:
            color = 10

        pyxel.rect(29, 78, 102, 13, 0)
        pyxel.rectb(29, 78, 102, 13, color)
        pyxel.text(34, 82, power_message, color)

    if game_over:
        pyxel.rect(3, 28, 154, 90, 0)
        pyxel.rectb(3, 28, 154, 90, 10)

        if screen_mode == "name":
            pyxel.text(45, 31, "GAME OVER", 8)
            pyxel.text(7, 38, "SCORE:" + str(score), 7)
            pyxel.text(7, 45, "BEST:" + str(high_score), 10)
            pyxel.text(7, 52, "MAX COMBO:" + str(max_combo), 11)
            pyxel.text(7, 59, "MAX SPEED:" + str(round(max_speed, 1)), 12)

            pyxel.text(7, 66, "NAME:", 7)
            name_x, name_y, name_w, name_h = get_name_input_rect()
            pyxel.rect(name_x, name_y, name_w, name_h, 1)
            pyxel.rectb(name_x, name_y, name_w, name_h, 7)
            pyxel.text(name_x + 3, name_y + 1, str(player_name or "")[:12], 7)

            for row, chars in enumerate(keyboard_rows):
                for index, char in enumerate(chars):
                    x, y, w, h = get_keyboard_key_rect(row, index)
                    pyxel.rect(x, y, w, h, 1)
                    pyxel.rectb(x, y, w, h, 10)
                    label = "BK" if char == "<" else char
                    pyxel.text(x + 2, y + 1, label, 7)

            delete_x, delete_y, delete_w, delete_h = get_delete_button_rect()
            pyxel.rect(delete_x, delete_y, delete_w, delete_h, 8)
            pyxel.rectb(delete_x, delete_y, delete_w, delete_h, 7)
            pyxel.text(delete_x + 12, delete_y + 2, "DELETE", 7)

            submit_x, submit_y, submit_w, submit_h = get_submit_button_rect()
            pyxel.rect(submit_x, submit_y, submit_w, submit_h, 3)
            pyxel.rectb(submit_x, submit_y, submit_w, submit_h, 7)
            pyxel.text(submit_x + 13, submit_y + 2, "SUBMIT", 7)

        elif screen_mode == "leaderboard":
            draw_logo("DOPABALL", 43, 29, 1, 8)
            draw_logo("DOPABALL", 42, 28, 1, 10)

            draw_period_tabs(38)
            pyxel.text(42, 49, "TOP 7 SCORES", 10)

            if leaderboard_status == "LOADING":
                pyxel.text(43, 59, "LOADING...", 7)
            elif leaderboard_status == "ERROR":
                pyxel.text(12, 59, "RANKING OFFLINE", 8)
                pyxel.text(7, 68, "SCORE SAVED LOCALLY", 7)
                pyxel.text(7, 77, str(leaderboard_error or "")[:25], 7)
            elif not leaderboard:
                pyxel.text(29, 59, "NO SCORES YET", 7)
            else:
                for i, item in enumerate(leaderboard[:7]):
                    y = 57 + i * 6
                    name = str(item.get("player_name", "PLAYER"))[:10]
                    points = str(item.get("score", 0))
                    pyxel.text(7, y, str(i + 1) + ".", 10)
                    pyxel.text(23, y, name, 7)
                    pyxel.text(112, y, points, 11)

            if submit_status == "LOCAL SAVE":
                pyxel.text(7, 98, "LOCAL SAVE", 10)
            elif submit_status == "SAVED":
                pyxel.text(7, 98, "RANKED", 10)
            elif submit_status == "SENDING":
                pyxel.text(7, 98, "SENDING...", 11)

            pyxel.text(7, 104, str(submit_status or "")[:22], 6 if submit_status == "SAVED" else 8)
            pyxel.text(7, 112, "TAP / SPACE: RETRY", 10)


pyxel.run(update, draw)
