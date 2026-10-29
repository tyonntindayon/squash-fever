import pyxel

WIDTH = 160
HEIGHT = 120

leaderboard = []
leaderboard_status = "LOADING"
high_score = 0
title_timer = 0


def draw_logo(logo, x, y, scale, color):
    for i, ch in enumerate(logo):
        pyxel.text(x + i * 6 * scale, y, ch, color)


def draw_bold_text(x, y, text, color, scale=1):
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            if dx == 0 and dy == 0:
                continue
            pyxel.text(x + dx * scale, y + dy * scale, text, 0)
    pyxel.text(x, y, text, color)


def draw_period_tabs(offset=39):
    for i in range(3):
        x = 20 + i * 34
        pyxel.rect(x, 35, x + 16, 41, 0)
        pyxel.rectb(x, 35, x + 16, 41, 12)
    pyxel.rect(offset, 35, offset + 10, 41, 10)


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
    scale = 1
    logo_width = len(logo) * 5 * scale - scale
    start_x = (WIDTH - logo_width) // 2
    logo_color = 10 if pyxel.frame_count // 12 % 2 == 0 else 11

    draw_logo(logo, start_x + 1, 6, scale, 8)
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

            pyxel.text(14, y, str(i + 1) + ".", 10 if i == 0 else 7)
            pyxel.text(29, y, name, 7)
            pyxel.text(112, y, points, 10 if i == 0 else 11)

    if title_timer < 120:
        pyxel.text(54, 100, "GET READY...", 7)
    elif pyxel.frame_count // 20 % 2 == 0:
        pyxel.text(45, 100, "TAP TO START", 10)

    pyxel.text(62, 100, "created by", 6)
    draw_bold_text(60, 105, "Tugumu", 10, 1)
    draw_bold_text(90, 105, "Kudo", 10, 1)
    pyxel.text(103, 100, "BEST:" + str(high_score), 7)


def update():
    global title_timer
    title_timer += 1


def draw():
    draw_title()


pyxel.init(WIDTH, HEIGHT, title="SQUASH FEVER")
pyxel.run(update, draw)
