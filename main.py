
import pyxel
import math

# =====================================
# SQUASH FEVER
# =====================================

WIDTH = 160
HEIGHT = 120

pyxel.init(WIDTH, HEIGHT, title="SQUASH FEVER")

# 色が変わるネオン背景
COLORS = [1, 2, 5, 6, 9, 12, 13]

# ゲーム状態
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

# =====================================
# サウンド
# =====================================

# 通常BGM
pyxel.sounds[0].set(
    "c3e3g3e3c3e3g3e3",
    "p", "6", "n", 12
)
pyxel.sounds[1].set(
    "c2c2g2g2a2a2g2g2",
    "t", "4", "n", 12
)

# 盛り上がるBGM
pyxel.sounds[2].set(
    "c3e3g3c4g3e3g3c4",
    "p", "7", "n", 9
)
pyxel.sounds[3].set(
    "c2g2c3g2f2g2a2g2",
    "t", "6", "n", 9
)

# FEVER BGM
pyxel.sounds[4].set(
    "c4g3e3g3c4g3e3g3",
    "p", "7", "n", 6
)
pyxel.sounds[5].set(
    "c2c3g2c3a2c3g2c3",
    "t", "7", "n", 6
)

# 効果音
pyxel.sounds[6].set(
    "c3g3c4",
    "p", "7", "s", 8
)
pyxel.sounds[7].set(
    "c3e3g3c4",
    "p", "7", "s", 6
)
pyxel.sounds[8].set(
    "g3e3c3",
    "t", "7", "f", 10
)

# BGMチャンネル
pyxel.musics[0].set([0], [1], [], [])
pyxel.musics[1].set([2], [3], [], [])
pyxel.musics[2].set([4], [5], [], [])


# =====================================
# BGM切り替え
# =====================================

def change_music(level):
    global music_level

    if level != music_level:
        music_level = level
        pyxel.playm(level, loop=True)


# =====================================
# パーティクル
# =====================================

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


# =====================================
# リセット
# =====================================

def reset():
    global paddle_x, ball_x, ball_y
    global ball_dx, ball_dy, ball_speed
    global score, combo, game_over
    global flash_timer, shake_timer, fever_timer
    global particles

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

    change_music(0)


# =====================================
# 更新処理
# =====================================

def update():
    global paddle_x, ball_x, ball_y
    global ball_dx, ball_dy, ball_speed
    global score, high_score, combo, game_over
    global flash_timer, shake_timer, fever_timer

    if flash_timer > 0:
        flash_timer -= 1

    if shake_timer > 0:
        shake_timer -= 1

    if fever_timer > 0:
        fever_timer -= 1

    # パーティクルを動かす
    for p in particles:
        p[0] += p[2]
        p[1] += p[3]
        p[4] -= 1

    particles[:] = [p for p in particles if p[4] > 0]

    # ゲームオーバー
    if game_over:
        if pyxel.btnp(pyxel.KEY_SPACE):
            reset()
        return

    # パドル操作
if pyxel.btn(pyxel.KEY_LEFT):
    paddle_x -= 3
if pyxel.btn(pyxel.KEY_RIGHT):
    paddle_x += 3

# タッチ操作

if pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
    paddle_x = pyxel.mouse_x - paddle_w / 2

paddle_x = max(0, min(WIDTH - paddle_w, paddle_x))
    # コンボに応じてスピードアップ
    ball_speed = min(5.0, 1.5 + combo * 0.12)

    # ボール移動
    ball_x += ball_dx * ball_speed
    ball_y += ball_dy * ball_speed

    # 左右の壁
    if ball_x <= 3:
        ball_x = 3
        ball_dx = 1

    elif ball_x >= WIDTH - 4:
        ball_x = WIDTH - 4
        ball_dx = -1

    # 天井
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

        # コンボ倍率
        multiplier = min(5, 1 + combo // 5)

        # FEVER中は得点2倍
        fever = combo >= 10
        score += multiplier * (2 if fever else 1)
        high_score = max(high_score, score)

        # 演出
        flash_timer = 3
        shake_timer = 4
        make_particles(ball_x, ball_y, 16)

        if combo % 5 == 0:
            pyxel.play(3, 7)
        else:
            pyxel.play(3, 6)

        # FEVER達成時の大演出
        if combo == 10:
            fever_timer = 90
            make_particles(ball_x, ball_y, 30)

        # BGM切り替え
        if combo >= 10:
            change_music(2)
        elif combo >= 5:
            change_music(1)
        else:
            change_music(0)

    # ミス
    if ball_y > HEIGHT:
        game_over = True
        combo = 0
        pyxel.stop(3)
        pyxel.play(3, 8)
        change_music(0)


# =====================================
# 描画
# =====================================

def draw():
    # ネオン背景
    interval = 4 if combo >= 10 else 8 if combo >= 5 else 14
    phase = pyxel.frame_count // interval
    bg = COLORS[phase % len(COLORS)]

    if flash_timer > 0:
        bg = 7

    pyxel.cls(bg)

    # 画面揺れ
    sx = pyxel.rndi(-1, 1) if shake_timer > 0 else 0
    sy = pyxel.rndi(-1, 1) if shake_timer > 0 else 0

    # 流れるライト
    for i in range(8):
        x = (i * 23 + pyxel.frame_count * (i % 3 + 1)) % WIDTH
        color = COLORS[(i + phase) % len(COLORS)]
        pyxel.line(x + sx, sy, x + sx, HEIGHT + sy, color)

    # サイドランプ
    for i in range(6):
        y = (i * 20 + pyxel.frame_count // 2) % HEIGHT
        color = COLORS[(i + phase + 2) % len(COLORS)]
        pyxel.circ(5 + sx, y + sy, 2, color)
        pyxel.circ(WIDTH - 6 + sx, HEIGHT - y + sy, 2, color)

    # FEVERライト
    if combo >= 10:
        for i in range(10):
            x = i * 16
            color = COLORS[(i + phase) % len(COLORS)]
            pyxel.rect(x + sx, sy, 8, 3, color)

    # パドル
    pyxel.rect(
        int(paddle_x + sx), int(paddle_y + sy),
        paddle_w, 5, 11
    )
    pyxel.rectb(
        int(paddle_x + sx - 1), int(paddle_y + sy - 1),
        paddle_w + 2, 7, 7
    )

    # ボール
    pyxel.circ(int(ball_x + sx), int(ball_y + sy), 4, 10)
    pyxel.pset(int(ball_x + sx), int(ball_y + sy), 7)

    # 粒子
    for p in particles:
        pyxel.pset(int(p[0]), int(p[1]), p[5])

    # スコア
    pyxel.text(5, 5, "SCORE:" + str(score), 7)
    pyxel.text(5, 15, "BEST:" + str(high_score), 10)
    pyxel.text(5, 25, "COMBO:" + str(combo), 11)

    multiplier = min(5, 1 + combo // 5)

    if combo >= 5:
        pyxel.text(85, 25, "x" + str(multiplier) + " BONUS!", 10)

    if combo >= 10:
        color = 8 if pyxel.frame_count // 5 % 2 == 0 else 10
        pyxel.text(49, 40, "F E V E R !", color)

        if fever_timer > 0:
            pyxel.text(35, 50, "FEVER x2 SCORE!", 7)

    # ゲームオーバー
    if game_over:
        pyxel.rect(15, 38, 130, 45, 0)
        pyxel.rectb(15, 38, 130, 45, 10)
        pyxel.text(45, 45, "GAME OVER", 8)
        pyxel.text(35, 56, "SCORE:" + str(score), 7)
        pyxel.text(35, 67, "BEST:" + str(high_score), 10)
        pyxel.text(25, 76, "SPACE: RETRY", 11)


pyxel.run(update, draw)
