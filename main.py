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

GAME_TITLE = "DOPABALL | DOPAMINE SUPPLY"
TITLE_BYLINE = "A Tgames Original"
SAVE_FILE = "dopaball_save.json"

pyxel.init(WIDTH, HEIGHT, title=GAME_TITLE)

COLORS = [1, 2, 5, 6, 9, 12, 13]

paddle_x = 55.0
paddle_y = 100
paddle_w = BASE_PADDLE_W
