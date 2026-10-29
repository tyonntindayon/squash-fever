import pyxel
import math
import asyncio
import json

WIDTH = 160
HEIGHT = 120

SUPABASE_URL = "https://hxjzgilnqxnnxlpqyasu.supabase.co"
SUPABASE_KEY = "sb_publishable_sae6J_mLG2NpvPFf2MI-kQ_ozswuMhR"
TABLE_URL = SUPABASE_URL + "/rest/v1/squash_scores"

pyxel.init(WIDTH, HEIGHT, title="SQUASH FEVER")

COLORS = [1, 2, 5, 6, 9, 12, 13]

paddle_x = 65
paddle_y = 105
paddle_w = 30

ball_x = 80.0
ball_y = 60.0
ball_dx = 1.0
ball_dy = 1.0
ball_speed = 1.5

score = 0
high_score = 0
combo = 0
game_over = False

flash_timer = 0
shake_timer = 0
fever_timer = 0
music_level = -1
particles = []

player_name = ""
leaderboard = []
leaderboard_status = "LOADING"
leaderboard_error = ""
submit_status = ""

screen_mode = "game"
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

# サウンド
pyxel.sounds[0].set(
    "c3e3g3e3c3e3g3e3", "p", "6", "n", 12
)
pyxel.sounds[1].set(
    "c2c2g2g2a2a2g2g2", "t", "4", "n", 12
)
pyxel.sounds[2].set(
    "c3e3g3c4g3e3g3c4", "p", "7", "n", 9
)
pyxel.sounds[3].set(
    "c2g2c3g2f2g2a2g2", "t", "6", "n", 9
)
pyxel.sounds[4].set(
    "c4g3e3g3c4g3e3g3", "p", "7", "n", 6
)
pyxel.sounds[5].set(
    "c2c3g2c3a2c3g2c3", "t", "7", "n", 6
)
pyxel.sounds[6].set(
    "c3g3c4", "p", "7", "s", 8
)
pyxel.sounds[7].set(
    "c3e3g3c4", "p", "7", "s", 6
)
pyxel.sounds[8].set(
    "g3e3c3", "t", "7", "f", 10
)

pyxel.musics[0].set([0], [1], [], [])
pyxel.musics[1].set([2], [3], [], [])
pyxel.musics[2].set([4], [5], [], [])


def change_music(level):
    global music_level

    if level != music_level:
        music_level = level
        pyxel.playm(level, loop=True)


def make_particles(x, y, amount=12):
    for i in range(amount):
        angle = pyxel.rndf(0, math.pi * 2)
        speed = pyxel.rndf(0.5, 2.5)
        color = pyxel.rndi(8, 15)

        particles.append([
            x, y,
            math.cos(angle) * speed,
            math.sin(angle) * speed,
            15, color
        ])


# -----------------------------
# オンラインランキング通信
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

    try:
        url = (
            TABLE_URL
            + "?select=player_name,score,created_at"
            + "&order=score.desc,created_at.asc"
            + "&limit=10"
        )

        leaderboard = await get_json(url)
        leaderboard_status = "OK"
        leaderboard_error = ""

    except Exception as error:
        leaderboard_status = "ERROR"
        leaderboard_error = str(error)[:25]

    finally:
        fetch_task_running = False


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
# ゲームリセット
# -----------------------------

def reset():
    global paddle_x, ball_x, ball_y
    global ball_dx, ball_dy, ball_speed
    global score, combo, game_over
    global flash_timer, shake_timer, fever_timer
    global particles, music_level
    global screen_mode, submitted_this_round

    paddle_x = 65

    ball_x = 80.0
    ball_y = 60.0
    ball_dx = 1.0
    ball_dy = 1.0
    ball_speed = 1.5

    score = 0
    combo = 0
    game_over = False

    flash_timer = 0
    shake_timer = 0
    fever_timer = 0

    particles.clear()
    music_level = -1

    screen_mode = "game"
    submitted_this_round = False

    change_music(0)


# -----------------------------
# 名前入力
# -----------------------------

def handle_name_tap(mx, my):
    global player_name
    global screen_mode
    global submitted_this_round

    # 4行のオンスクリーンキーボード
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

    # 名前を送信
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

    # 名前を消去
    if 7 <= mx <= 77 and 106 <= my <= 117:
        player_name = player_name[:-1]


# -----------------------------
# ゲーム更新
# -----------------------------

def update():
    global paddle_x, ball_x, ball_y
    global ball_dx, ball_dy, ball_speed
    global score, high_score, combo, game_over
    global flash_timer, shake_timer, fever_timer
    global player_name, screen_mode
    global submitted_this_round, initial_fetch_started

    if not initial_fetch_started:
        initial_fetch_started = True
        launch_refresh()

    if flash_timer > 0:
        flash_timer -= 1

    if shake_timer > 0:
        shake_timer -= 1

    if fever_timer > 0:
        fever_timer -= 1

    for particle in particles:
        particle[0] += particle[2]
        particle[1] += particle[3]
        particle[4] -= 1

    particles[:] = [
        particle for particle in particles
        if particle[4] > 0
    ]

    # ゲームオーバー画面
    if game_over:

        # 名前入力画面
        if screen_mode == "name":

            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                handle_name_tap(
                    pyxel.mouse_x,
                    pyxel.mouse_y
                )

            # 外付けキーボードにも対応
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

        # ランキング画面
        elif screen_mode == "leaderboard":

            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                reset()

            elif pyxel.btnp(pyxel.KEY_SPACE):
                reset()

            elif pyxel.btnp(pyxel.KEY_N):
                player_name = ""
                screen_mode = "name"

        return

    # パドル操作
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

    # ボール移動
    ball_speed = min(5.0, 1.5 + combo * 0.12)

    ball_x += ball_dx * ball_speed
    ball_y += ball_dy * ball_speed

    if ball_x <= 3:
        ball_x = 3
        ball_dx = 1

    elif ball_x >= WIDTH - 4:
        ball_x = WIDTH - 4
        ball_dx = -1

    if ball_y <= 3:
        ball_y = 3
        ball_dy = 1

    # パドルとの衝突
    if (
        ball_dy > 0
        and paddle_x - 3 <= ball_x <= paddle_x + paddle_w + 3
        and paddle_y - 4 <= ball_y <= paddle_y + 5
    ):
        ball_y = paddle_y - 4
        ball_dy = -1

        combo += 1

        multiplier = min(5, 1 + combo // 5)
        fever = combo >= 10

        score += multiplier * (2 if fever else 1)
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

    # ゲームオーバー
    if ball_y > HEIGHT:
        game_over = True
        combo = 0

        pyxel.stop(3)
        pyxel.play(3, 8)
        change_music(0)

        screen_mode = "name"
        player_name = ""
        submitted_this_round = False


# -----------------------------
# 描画
# -----------------------------

def draw():
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
            2,
            color
        )

    if combo >= 10:
        for i in range(10):
            x = i * 16
            color = COLORS[(i + phase) % len(COLORS)]
            pyxel.rect(x + sx, sy, 8, 3, color)

    pyxel.rect(
        int(paddle_x + sx),
        int(paddle_y + sy),
        paddle_w, 5, 11
    )

    pyxel.rectb(
        int(paddle_x + sx - 1),
        int(paddle_y + sy - 1),
        paddle_w + 2, 7, 7
    )

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

    for particle in particles:
        pyxel.pset(
            int(particle[0]),
            int(particle[1]),
            particle[5]
        )

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

    if combo >= 10:
        color = (
            8 if pyxel.frame_count // 5 % 2 == 0
            else 10
        )

        pyxel.text(49, 40, "F E V E R !", color)

        if fever_timer > 0:
            pyxel.text(35, 50, "FEVER x2 SCORE!", 7)

    # ゲームオーバー画面
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

                    pyxel.text(
                        x + 2, y + 3,
                        label, 7
                    )

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
            pyxel.text(42, 31, "TOP 10 SCORES", 10)

            if leaderboard_status == "LOADING":
                pyxel.text(43, 44, "LOADING...", 7)

            elif leaderboard_status == "ERROR":
                pyxel.text(12, 44, "RANKING OFFLINE", 8)
                pyxel.text(
                    7, 55,
                    leaderboard_error[:25],
                    7
                )

            elif not leaderboard:
                pyxel.text(29, 44, "NO SCORES YET", 7)

            else:
                for i, item in enumerate(leaderboard[:10]):
                    y = 42 + i * 6

                    name = str(
                        item.get("player_name", "PLAYER")
                    )[:10]

                    points = str(item.get("score", 0))

                    pyxel.text(
                        7, y,
                        str(i + 1) + ".",
                        10
                    )

                    pyxel.text(23, y, name, 7)

                    pyxel.text(
                        112, y,
                        points,
                        11
                    )

            pyxel.text(
                7, 104,
                submit_status[:22],
                6 if submit_status == "SAVED" else 8
            )

            pyxel.text(7, 112, "TAP / SPACE: RETRY", 10)


pyxel.run(update, draw)
