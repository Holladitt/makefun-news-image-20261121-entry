"""news-image-20261121 v4 — "The day as a map".

A structural redesign: instead of a dense text newspaper, the page is built
around a world map. The three lead stories get a stacked-headline treatment,
every other story is a numbered pin on the map, and the numbered list below
the map is the map's legend. 23 verified 21 Nov 2026 stories, 5 regions.
Pure Python 3.13 stdlib only, no network, deterministic: two runs write
identical bytes.
"""
import os
import struct
import zlib

W = 1024
H = 1024

PAPER = (245, 239, 224)
PANEL = (255, 253, 247)
INK = (22, 34, 46)
NAVY = (29, 53, 87)
RED = (179, 39, 30)
GOLD = (201, 154, 43)
SEA = (169, 199, 216)
LAND = (227, 211, 168)
LAND_EDGE = (150, 130, 90)
GREY = (90, 100, 110)
WHITE = (255, 255, 255)
DARKRED = (140, 28, 22)

# ---------------------------------------------------------------- PNG writer
def _chunk(kind, data):
    c = struct.pack(">I", len(data)) + kind + data
    c += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return c


def write_png(path, fb, w, h):
    # Sub filter (type 1) per scanline: each byte minus the byte 3 left.
    raw = bytearray()
    for y in range(h):
        row = fb[y * w * 3:(y + 1) * w * 3]
        raw.append(1)
        prev = 0
        out = bytearray(len(row))
        for i, b in enumerate(row):
            left = row[i - 3] if i >= 3 else 0
            out[i] = (b - left) & 0xFF
        raw += out
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


# ---------------------------------------------------------------- framebuffer
FB = bytearray(W * H * 3)


def px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        FB[i] = c[0]
        FB[i + 1] = c[1]
        FB[i + 2] = c[2]


def fill_rect(x0, y0, x1, y1, c):
    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(W, x1)
    y1 = min(H, y1)
    for y in range(y0, y1):
        base = (y * W + x0) * 3
        for x in range(x0, x1):
            i = base + (x - x0) * 3
            FB[i] = c[0]
            FB[i + 1] = c[1]
            FB[i + 2] = c[2]


def hline(x0, x1, y, c):
    for x in range(max(0, x0), min(W, x1)):
        px(x, y, c)


def vline(x, y0, y1, c):
    for y in range(max(0, y0), min(H, y1)):
        px(x, y, c)


def line(x0, y0, x1, y1, c):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        px(x, y, c)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def circle(cx, cy, r, c, fill=False):
    if fill:
        for y in range(cy - r, cy + r + 1):
            dx = int((r * r - (y - cy) * (y - cy)) ** 0.5) if abs(y - cy) <= r else 0
            for x in range(cx - dx, cx + dx + 1):
                px(x, y, c)
        return
    x = 0
    y = r
    d = 3 - 2 * r
    while x <= y:
        for sx, sy in ((x, y), (y, x), (-x, y), (-y, x),
                       (x, -y), (y, -x), (-x, -y), (-y, -x)):
            px(cx + sx, cy + sy, c)
        if d < 0:
            d += 4 * x + 6
        else:
            d += 4 * (x - y) + 10
            y -= 1
        x += 1


def poly_fill(points, c):
    # Scanline fill of a simple polygon.
    if not points:
        return
    ys = [p[1] for p in points]
    for y in range(max(0, min(ys)), min(H, max(ys) + 1)):
        xs = []
        n = len(points)
        for i in range(n):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % n]
            if (y0 <= y < y1) or (y1 <= y < y0):
                t = (y - y0) / (y1 - y0)
                xs.append(int(x0 + t * (x1 - x0)))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            for x in range(xs[k], xs[k + 1] + 1):
                px(x, y, c)


def poly_outline(points, c):
    n = len(points)
    for i in range(n):
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % n]
        line(x0, y0, x1, y1, c)


# ---------------------------------------------------------------- 5x7 font
# Each glyph: 7 rows of 5 bits, '#' = on.
FONT = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    'D': ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    'J': ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    '3': ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    '.': ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ',': ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ':': ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ';': ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '-': ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    '(': ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ')': ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    '/': ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    '%': ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    '+': ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    '&': ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    '!': ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    '?': ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    '=': ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    '*': ("00000", "10101", "01110", "11111", "01110", "10101", "00000"),
    '|': ("00100", "00100", "00100", "00100", "00100", "00100", "00100"),
}


def text_w(s, scale):
    return len(s) * 6 * scale


def draw_text(x, y, s, scale, c):
    s = s.upper()
    cx = x
    for ch in s:
        g = FONT.get(ch, FONT[' '])
        for r in range(7):
            row = g[r]
            for col in range(5):
                if row[col] == '1':
                    fill_rect(cx + col * scale, y + r * scale,
                              cx + (col + 1) * scale, y + (r + 1) * scale, c)
        cx += 6 * scale
    return cx


def draw_centered(cx, y, s, scale, c):
    draw_text(cx - text_w(s, scale) // 2, y, s, scale, c)


def wrap_lines(s, scale, max_w):
    words = s.upper().split(' ')
    lines = []
    cur = ''
    for wd in words:
        trial = (cur + ' ' + wd).strip()
        if text_w(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def draw_block(x, y, s, scale, c, max_w, leading=None):
    if leading is None:
        leading = 7 * scale + 4
    lines = wrap_lines(s, scale, max_w)
    for ln in lines:
        draw_text(x, y, ln, scale, c)
        y += leading
    return y

# ---------------------------------------------------------------- masthead
def draw_masthead():
    fill_rect(0, 0, W, 96, NAVY)
    fill_rect(0, 96, W, 100, GOLD)
    draw_centered(W // 2, 14, "SATURDAY 21 NOVEMBER 2026", 6, WHITE)
    draw_centered(W // 2, 62, "THE WORLD IN ONE DAY  |  23 STORIES  |  5 REGIONS  |  EVERY STORY DATE-CHECKED", 2, GOLD)


# ---------------------------------------------------------------- lead story
def draw_gulf_schematic(x0, y0, x1, y1):
    # Schematic of the Gulf / Strait of Hormuz: sea, land, two tankers,
    # blast rings at Bahrain and in the strait, arrow from Iran.
    fill_rect(x0, y0, x1, y1, SEA)
    # Iran landmass (top)
    poly_fill([(x0, y0), (x1, y0), (x1, y0 + 42), (x0 + 210, y0 + 58),
               (x0 + 120, y0 + 40), (x0, y0 + 46)], LAND)
    poly_outline([(x0, y0), (x1, y0), (x1, y0 + 42), (x0 + 210, y0 + 58),
                  (x0 + 120, y0 + 40), (x0, y0 + 46)], LAND_EDGE)
    # Arabian peninsula (bottom right)
    poly_fill([(x0 + 150, y1), (x1, y1), (x1, y0 + 96), (x0 + 250, y0 + 118),
               (x0 + 190, y0 + 150)], LAND)
    poly_outline([(x0 + 150, y1), (x1, y1), (x1, y0 + 96), (x0 + 250, y0 + 118),
                  (x0 + 190, y0 + 150)], LAND_EDGE)
    # Strait of Hormuz water channel between the two landmasses
    # Blast ring at Bahrain (left of the strait)
    bx, by = x0 + 128, y0 + 96
    circle(bx, by, 26, RED)
    circle(bx, by, 18, RED)
    circle(bx, by, 10, RED, fill=True)
    circle(bx, by, 4, WHITE, fill=True)
    # Blast ring in the strait (tankers)
    tx, ty = x0 + 232, y0 + 82
    circle(tx, ty, 22, DARKRED)
    circle(tx, ty, 14, DARKRED)
    circle(tx, ty, 7, RED, fill=True)
    # Two tanker glyphs: hull + bridge
    for sx, sy in ((x0 + 168, y0 + 128), (x0 + 252, y0 + 128)):
        fill_rect(sx, sy, sx + 44, sy + 10, INK)
        fill_rect(sx + 30, sy - 8, sx + 40, sy, INK)
        vline(sx + 35, sy - 16, sy - 8, INK)
    # Dashed arrow from Iran down toward Bahrain
    for k in range(0, 5):
        y = y0 + 46 + k * 9
        fill_rect(x0 + 96, y, x0 + 100, y + 5, DARKRED)
    draw_text(x0 + 8, y0 + 6, "IRAN", 2, INK)
    draw_text(x0 + 8, y0 + 88, "BAHRAIN", 2, DARKRED)
    draw_text(x0 + 196, y0 + 108, "HORMUZ", 2, INK)
    draw_text(x0 + 8, y1 - 16, "THE GULF - SCHEMATIC", 2, GREY)


def draw_lead():
    fill_rect(0, 100, W, 296, PANEL)
    fill_rect(0, 100, W, 108, RED)
    draw_text(32, 116, "LEAD STORY  -  THE GULF", 2, RED)
    draw_text(32, 136, "IRAN STRIKES", 7, INK)
    draw_text(32, 190, "BAHRAIN", 7, RED)
    draw_text(32, 246, "TWO TANKERS HIT IN HORMUZ", 3, INK)
    draw_text(32, 270, "TEHRAN: WE HIT US BASES  -  2 HURT", 3, INK)
    draw_gulf_schematic(672, 116, 992, 288)
    # thin rule under the lead
    fill_rect(0, 292, W, 296, INK)


# ---------------------------------------------------------------- second row
def draw_clock(cx, cy, r):
    circle(cx, cy, r, INK)
    circle(cx, cy, r - 3, PANEL, fill=True)
    circle(cx, cy, r, INK)
    line(cx, cy, cx, cy - r + 8, INK)
    line(cx, cy, cx + r - 10, cy + 6, RED)
    circle(cx, cy, 3, RED, fill=True)


def draw_star(cx, cy, r, c):
    import math
    pts = []
    for k in range(10):
        ang = -math.pi / 2 + k * math.pi / 5
        rr = r if k % 2 == 0 else r * 0.45
        pts.append((int(cx + rr * math.cos(ang)), int(cy + rr * math.sin(ang))))
    poly_fill(pts, c)
    poly_outline(pts, DARKRED)


def draw_row2():
    # Left: COP31
    fill_rect(16, 308, 504, 448, PANEL)
    fill_rect(16, 308, 504, 312, RED)
    draw_text(32, 322, "COP31 OVERTIME", 4, INK)
    draw_text(32, 356, "ANTALYA TALKS PASS", 3, INK)
    draw_text(32, 382, "THE DEADLINE", 3, INK)
    draw_text(32, 408, "SPLIT ON FOSSIL FUELS", 3, RED)
    draw_text(32, 434, "EU: GOOD DEAL OR NONE", 2, GREY)
    draw_clock(452, 388, 34)
    draw_text(420, 428, "DAY 17", 2, INK)
    # Right: El Chapo Isidro
    fill_rect(520, 308, 1008, 448, PANEL)
    fill_rect(520, 308, 1008, 312, RED)
    draw_text(536, 322, "CHAPO ISIDRO HELD", 4, INK)
    draw_text(536, 356, "MEXICAN FORCES SEIZE", 3, INK)
    draw_text(536, 382, "FBI MOST-WANTED BOSS", 3, INK)
    draw_text(536, 408, "GUASAVE, SINALOA - 11 DEAD", 3, RED)
    draw_text(536, 434, "US INTEL HELP - $5M REWARD", 2, GREY)
    circle(970, 330, 14, GOLD, fill=True)
    circle(970, 330, 14, DARKRED)
    draw_text(958, 323, "10", 2, DARKRED)

# ---------------------------------------------------------------- world map
MAP_X0, MAP_X1, MAP_Y0, MAP_Y1 = 16, 1008, 480, 636
MAP_LON0, MAP_LON1, MAP_LAT0, MAP_LAT1 = -180, 180, 75, -60


def map_xy(lon, lat):
    x = MAP_X0 + (lon - MAP_LON0) / (MAP_LON1 - MAP_LON0) * (MAP_X1 - MAP_X0)
    y = MAP_Y0 + (MAP_LAT0 - lat) / (MAP_LAT0 - MAP_LAT1) * (MAP_Y1 - MAP_Y0)
    return int(x), int(y)


CONTINENTS = [
    # North America
    [(-168, 66), (-145, 70), (-130, 71), (-120, 70), (-110, 68), (-100, 69),
     (-90, 68), (-85, 66), (-82, 70), (-75, 72), (-65, 60), (-60, 55),
     (-55, 52), (-60, 47), (-65, 44), (-70, 42), (-74, 39), (-76, 35),
     (-80, 32), (-81, 26), (-84, 30), (-89, 29), (-91, 19), (-97, 16),
     (-94, 17), (-97, 22), (-105, 20), (-110, 23), (-114, 29), (-120, 34),
     (-124, 40), (-124, 48), (-130, 55), (-140, 60), (-155, 58), (-162, 55),
     (-168, 60)],
    # Greenland
    [(-55, 60), (-45, 60), (-32, 65), (-25, 70), (-30, 74), (-45, 76),
     (-58, 76), (-60, 70), (-58, 64)],
    # South America
    [(-79, 9), (-77, 7), (-72, 11), (-64, 10), (-60, 8), (-54, 6),
     (-51, 4), (-50, 0), (-44, -3), (-38, -5), (-35, -8), (-37, -13),
     (-40, -20), (-41, -23), (-48, -27), (-52, -32), (-58, -35),
     (-62, -39), (-65, -41), (-68, -47), (-69, -52), (-71, -54),
     (-74, -50), (-73, -44), (-73, -37), (-72, -30), (-70, -20),
     (-75, -15), (-80, -6), (-81, -1), (-80, 4), (-79, 8)],
    # Europe
    [(-10, 36), (-9, 43), (-2, 44), (-1, 48), (2, 51), (5, 53), (8, 55),
     (8, 57), (11, 58), (18, 56), (21, 55), (24, 58), (26, 59), (30, 60),
     (30, 62), (28, 66), (25, 70), (20, 70), (15, 68), (12, 65), (8, 62),
     (5, 60), (5, 58), (0, 55), (-3, 53), (-5, 50), (-4, 48), (-10, 44),
     (-10, 38)],
    # Africa
    [(-17, 15), (-16, 20), (-14, 25), (-10, 30), (-6, 34), (-1, 35),
     (5, 37), (10, 37), (12, 34), (18, 33), (22, 33), (28, 31), (32, 31),
     (34, 28), (36, 24), (38, 20), (40, 15), (43, 11), (48, 11), (51, 12),
     (48, 8), (44, 3), (41, -2), (40, -8), (38, -15), (35, -20), (32, -26),
     (28, -32), (22, -35), (18, -34), (15, -30), (13, -24), (12, -18),
     (10, -12), (9, -2), (9, 4), (4, 6), (-3, 5), (-8, 5), (-13, 8),
     (-16, 11)],
    # Asia
    [(30, 62), (35, 66), (40, 68), (45, 68), (50, 69), (55, 69), (60, 69),
     (65, 70), (70, 72), (75, 73), (80, 73), (85, 74), (90, 75), (95, 76),
     (100, 77), (105, 77), (110, 76), (115, 74), (120, 73), (125, 72),
     (130, 71), (135, 71), (140, 72), (145, 71), (150, 70), (155, 69),
     (160, 69), (165, 67), (170, 66), (175, 65), (178, 64), (175, 60),
     (170, 60), (165, 58), (162, 55), (160, 52), (158, 50), (155, 53),
     (150, 59), (145, 59), (142, 55), (140, 50), (138, 46), (135, 43),
     (132, 40), (130, 38), (127, 36), (125, 33), (122, 30), (120, 27),
     (117, 24), (114, 22), (110, 20), (108, 18), (106, 10), (104, 9),
     (101, 7), (99, 9), (98, 12), (96, 15), (94, 17), (92, 21), (90, 22),
     (88, 22), (86, 20), (84, 18), (82, 16), (80, 13), (78, 8), (77, 8),
     (75, 11), (73, 16), (72, 20), (70, 21), (68, 23), (66, 25), (63, 25),
     (61, 25), (58, 26), (56, 27), (54, 27), (52, 28), (50, 29), (48, 30),
     (46, 29), (44, 29), (42, 30), (40, 31), (38, 32), (36, 36), (34, 36),
     (32, 36), (30, 36), (28, 37), (26, 38), (24, 37), (22, 37), (20, 39),
     (18, 41), (15, 44), (12, 44), (9, 44), (6, 43), (3, 42), (0, 40),
     (-2, 38), (-5, 36), (-8, 36)],
    # Australia
    [(113, -22), (114, -28), (115, -33), (118, -35), (122, -34), (126, -32),
     (129, -32), (132, -32), (135, -35), (138, -35), (140, -38),
     (144, -39), (147, -39), (150, -37), (153, -32), (153, -27),
     (151, -24), (148, -20), (146, -19), (143, -15), (142, -11),
     (140, -17), (137, -12), (135, -15), (132, -12), (129, -14),
     (126, -14), (123, -17), (120, -20), (117, -20), (114, -22)],
]

# (number, lon, lat, offset dx, dy) — offsets spread crowded pins apart.
PINS = [
    (1, 50.6, 26.2, -4, -26),    # Bahrain (lead)
    (2, 30.7, 36.9, -12, 28),    # Antalya / COP31 (lead)
    (3, -108.5, 25.6, 0, 0),     # Guasave (lead)
    (4, 30.5, 50.4, 0, 0),       # Kyiv
    (5, 33.4, 47.9, 28, 22),     # Kryvyi Rih
    (6, 26.0, 59.8, -14, -10),   # Gulf of Finland
    (7, 46.7, 24.7, -30, 18),    # Riyadh
    (8, 47.8, 30.5, 28, -10),    # Basra
    (9, 93.9, 24.7, 0, 0),       # Manipur
    (10, -81.5, 28.0, -16, 12),  # Florida
    (11, -77.0, 38.9, 0, 0),     # Washington
    (12, -72.3, 18.9, 0, 18),    # Haiti
    (13, -47.9, -15.8, 0, 0),    # Brasilia
    (14, -74.0, 40.7, 26, -16),  # New York
]


def draw_pin(num, lon, lat, dx, dy):
    tx, ty = map_xy(lon, lat)
    cx, cy = tx + dx, ty + dy
    if dx or dy:
        line(tx, ty, cx, cy, INK)
        circle(tx, ty, 3, DARKRED, fill=True)
    circle(cx, cy, 13, RED, fill=True)
    circle(cx, cy, 13, DARKRED)
    s = str(num)
    draw_text(cx - text_w(s, 2) // 2, cy - 7, s, 2, WHITE)


def draw_map():
    draw_text(16, 456, "AROUND THE WORLD", 3, INK)
    draw_text(636, 460, "EVERY NUMBER IS A STORY BELOW", 2, RED)
    fill_rect(MAP_X0, MAP_Y0, MAP_X1, MAP_Y1, SEA)
    for poly in CONTINENTS:
        pts = [map_xy(lon, lat) for lon, lat in poly]
        poly_fill(pts, LAND)
        poly_outline(pts, LAND_EDGE)
    for num, lon, lat, dx, dy in PINS:
        draw_pin(num, lon, lat, dx, dy)
    # 15: off the map — in orbit. Gold star badge, top right of the map.
    draw_star(958, 498, 14, GOLD)
    draw_text(951, 491, "15", 2, DARKRED)


# ---------------------------------------------------------------- grid
# (number, place, detail) — place in red scale 3, detail in ink scale 2.
GRID = [
    (4, "KYIV", "DRONE HITS FLAT, 14 MISSING"),
    (5, "KRYVYI", "DOUBLE-TAP, 2 DEAD"),
    (6, "FINLAND", "RUSSIAN CARGO SHIP BURNING"),
    (7, "RIYADH", "3 HOUTHI MISSILES STOPPED"),
    (8, "BASRA", "POWER PLANT FIRE, 4 DEAD"),
    (9, "MANIPUR", "TOXIC ALCOHOL KILLS 11"),
    (10, "FLORIDA", "RIVER HITS 73-YEAR RECORD"),
    (11, "WASHINGTON", "CYBER CHIEF FIRED"),
    (12, "HAITI", "TROOPS RETAKE GANG STADIUM"),
    (13, "BRASILIA", "BOLSONARO TAKEN TO ICU"),
    (14, "NEW YORK", "STOCKS FALL 3.7%"),
    (15, "MERCURY", "BEPICOLOMBO IN ORBIT"),
]


def draw_grid():
    rows = [644, 684, 724, 764, 804, 844]
    for i, (num, place, detail) in enumerate(GRID):
        col = 0 if i < 6 else 1
        row = i % 6
        x = 16 if col == 0 else 520
        y = rows[row]
        fill_rect(x, y + 7, x + 26, y + 33, RED)
        s = str(num)
        draw_text(x + 13 - text_w(s, 2) // 2, y + 12, s, 2, WHITE)
        tx = x + 34
        draw_text(tx, y + 9, place, 3, RED)
        tx += text_w(place, 3) + 8
        draw_text(tx, y + 12, detail, 2, INK)


# ---------------------------------------------------------------- ticker + footer
TICKER_LEFT = [
    "FBI PROBES POLICE DATABASE BREACH",
    "TRUMP BACKS 10% CARD-RATE CAP",
    "NATO REAFFIRMS POLAND DEFENCE",
    "PUGH SWIMS 15 KM ACROSS HORMUZ",
]
TICKER_RIGHT = [
    "ROMAN GOLD CHAIN FOUND ON DIG",
    "GAZA STRIKE KILLS 3 - AID LINK DISPUTED",
    "ZELENSKY OFFERS G20 TALKS WITH PUTIN",
    "DEA FINDS FIRST BIG NITAZENE LAB",
]


def draw_ticker_footer():
    draw_text(16, 892, "ALSO ON SATURDAY", 2, RED)
    for i, s in enumerate(TICKER_LEFT):
        draw_text(16, 910 + i * 16, s, 2, INK)
    for i, s in enumerate(TICKER_RIGHT):
        draw_text(520, 910 + i * 16, s, 2, INK)
    fill_rect(0, 980, W, 982, INK)
    draw_text(16, 988, "DATE CHECK - THE PERU QUAKE WAS FRIDAY 20 NOV, M6.7. IT IS NOT A 21 NOV STORY.", 2, DARKRED)
    draw_text(16, 1006, "23 STORIES - 5 REGIONS", 2, GREY)
    draw_text(1008 - text_w("SATURDAY 21 NOVEMBER 2026", 2), 1006, "SATURDAY 21 NOVEMBER 2026", 2, GREY)


# ---------------------------------------------------------------- main
def main():
    fill_rect(0, 0, W, H, PAPER)
    draw_masthead()
    draw_lead()
    draw_row2()
    draw_map()
    draw_grid()
    draw_ticker_footer()
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    write_png(os.path.join(out_dir, "entry.png"), FB, W, H)


if __name__ == "__main__":
    main()
