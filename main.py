#!/usr/bin/env python3
"""The World in One Day -- Saturday 21 November 2026.

Pure Python 3 stdlib. Reads fonts.bin (a DejaVu glyph atlas generated at
build time by gen_atlas.py) and draws one dense newspaper front page
summing up 21 November 2026 world news to /output/entry.png.

Layout (1024x1024): masthead, kicker, 6-number stat strip, region strip,
3 hero stories with drawn pictures, 10 feature stories with drawn
pictures, a world map with numbered pins, an ALSO list of 22 one-liners,
and a DATE CHECK box that keeps 20 November's news out of the 21st.
"""
import math
import os
import struct
import sys
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER = (247, 241, 222)
PAPER2 = (241, 234, 210)
INK = (26, 23, 18)
INK_SOFT = (58, 52, 44)
RED = (178, 39, 30)
RED_DARK = (140, 28, 22)
NAVY = (31, 58, 95)
BLUE = (47, 99, 158)
SKY = (135, 190, 220)
TEAL = (23, 120, 110)
GREEN = (46, 125, 50)
GOLD = (198, 142, 26)
ORANGE = (214, 110, 30)
CREAM = (255, 248, 225)
WHITE = (255, 255, 255)
GREY = (120, 114, 100)
LINE = (26, 23, 18)

# soft tints behind the ten feature panels
TINTS = [
    (210, 226, 240),  # Kyiv: pale blue
    (206, 232, 228),  # Hormuz: pale teal
    (214, 222, 238),  # Trump: pale slate blue
    (240, 216, 214),  # China-Japan: pale rose
    (205, 233, 240),  # Davao: pale sky
    (220, 236, 214),  # Canberra: pale green
    (232, 222, 196),  # Bitcoin: pale gold
    (228, 226, 232),  # Russell: pale lavender grey
    (214, 232, 200),  # Rahul: pale grass green
    (210, 208, 224),  # BepiColombo: pale violet
]

# ---------------------------------------------------------------- PNG out
def write_png(path, img, w, h):
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += img[y * w * 3:(y + 1) * w * 3]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", ihdr))
        f.write(chunk(b"IDAT", comp))
        f.write(chunk(b"IEND", b""))


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg) * (w * h)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(c)

    def blend(self, x, y, c, a):
        """Blend colour c with alpha a (0..255) over the pixel."""
        if 0 <= x < self.w and 0 <= y < self.h and a:
            i = (y * self.w + x) * 3
            inv = 255 - a
            self.px[i] = (c[0] * a + self.px[i] * inv) // 255
            self.px[i + 1] = (c[1] * a + self.px[i + 1] * inv) // 255
            self.px[i + 2] = (c[2] * a + self.px[i + 2] * inv) // 255

    def rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:(x1 - x0) * 3 + i] = bytes(c) * (x1 - x0)

    def hline(self, x, y, w, c, t=1):
        for k in range(t):
            self.rect(x, y + k, w, 1, c)

    def vline(self, x, y, h, c, t=1):
        for k in range(t):
            self.rect(x + k, y, 1, h, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx, dy = x1 - x0, y1 - y0
        n = max(abs(dx), abs(dy), 1)
        for k in range(n + 1):
            x = x0 + dx * k // n
            y = y0 + dy * k // n
            r = t // 2
            self.rect(x - r, y - r, t, t, c)

    def circle(self, cx, cy, r, c, fill=True):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                d2 = (x - cx) ** 2 + (y - cy) ** 2
                if fill:
                    if d2 <= r * r:
                        self.set(x, y, c)
                else:
                    if r * r - 2 * r <= d2 <= r * r:
                        self.set(x, y, c)

    def disc(self, cx, cy, r, c):
        self.circle(cx, cy, r, c, fill=True)

    def ring(self, cx, cy, r, c, t=2):
        for k in range(t):
            self.circle(cx, cy, r - k, c, fill=False)

    def ellipse(self, cx, cy, rx, ry, c):
        for y in range(cy - ry, cy + ry + 1):
            for x in range(cx - rx, cx + rx + 1):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1:
                    self.set(x, y, c)

    def poly(self, pts, c):
        """Scanline polygon fill."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / (y1 - y0)
                    xs.append(int(x0 + t * (x1 - x0)))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.rect(xs[k], y, xs[k + 1] - xs[k], 1, c)

    def arc_dots(self, cx, cy, r, a0, a1, c, step=6, dot=2):
        for a in range(a0, a1, step):
            t = math.radians(a)
            self.disc(int(cx + r * math.cos(t)), int(cy + r * math.sin(t)), dot, c)

    def burst(self, cx, cy, r, c, spikes=10):
        for k in range(spikes):
            a = 2 * math.pi * k / spikes
            a2 = a + math.pi / spikes
            x1 = int(cx + r * math.cos(a))
            y1 = int(cy + r * math.sin(a))
            x2 = int(cx + r * 0.45 * math.cos(a2))
            y2 = int(cy + r * 0.45 * math.sin(a2))
            self.line(cx, cy, x1, y1, c, 2)
            self.line(cx, cy, x2, y2, c, 2)
        self.disc(cx, cy, max(2, r // 3), c)


# ---------------------------------------------------------------- fonts
class Font:
    def __init__(self, glyphs, size):
        self.glyphs = glyphs  # cp -> (adv, w, h, ox, oy, bytes)
        self.size = size

    def width(self, text):
        s = self.size / 80.0
        total = 0
        for ch in text:
            g = self.glyphs.get(ord(ch))
            if g is None:
                g = self.glyphs.get(ord("?"))
            total += g[0] * s
        return total

    def draw(self, cv, x, y, text, color):
        """Draw text with its top-left at (x, y). Returns width used."""
        s = self.size / 80.0
        cx = x
        for ch in text:
            g = self.glyphs.get(ord(ch))
            if g is None:
                g = self.glyphs.get(ord(" "))
            if g is None:
                continue
            adv, w, h, ox, oy, bmp = g
            if w and h:
                # nearest-neighbour scale of the coverage bitmap
                dw = max(1, int(round(w * s)))
                dh = max(1, int(round(h * s)))
                oxs = int(round(ox * s))
                oys = int(round(oy * s))
                for yy in range(dh):
                    sy = min(h - 1, int(yy / s))
                    for xx in range(dw):
                        sx = min(w - 1, int(xx / s))
                        a = bmp[sy * w + sx]
                        if a:
                            cv.blend(int(cx) + oxs + xx, int(y) + oys + yy, color, a)
            cx += adv * s
        return cx - x


def load_fonts(path):
    with open(path, "rb") as f:
        data = f.read()
    assert data[:4] == b"FNT1", "bad fonts.bin"
    off = 4
    n_fonts = struct.unpack_from("<H", data, off)[0]
    off += 2
    fonts = {}
    for _ in range(n_fonts):
        nl = data[off]
        off += 1
        name = data[off:off + nl].decode()
        off += nl
        n_chars = struct.unpack_from("<H", data, off)[0]
        off += 2
        glyphs = {}
        for _ in range(n_chars):
            cp, adv, w, h, ox, oy = struct.unpack_from("<IHHHhh", data, off)
            off += 14
            bmp = data[off:off + w * h]
            off += w * h
            glyphs[cp] = (adv, w, h, ox, oy, bmp)
        fonts[name] = glyphs
    return fonts


class Fonts:
    def __init__(self, table):
        self.t = table
        self.cache = {}

    def get(self, name, size):
        key = (name, size)
        if key not in self.cache:
            self.cache[key] = Font(self.t[name], size)
        return self.cache[key]


def wrap(font, text, maxw):
    """Greedy word wrap. Returns list of lines, each fitting maxw."""
    words = text.split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if font.width(trial) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def text_block(cv, fonts, name, size, x, y, text, color, maxw, lh=None):
    """Draw a wrapped block. Returns the y after the last line."""
    f = fonts.get(name, size)
    lh = lh or int(size * 1.22)
    for line in wrap(f, text, maxw):
        f.draw(cv, x, y, line, color)
        y += lh
    return y

# ---------------------------------------------------------------- illustrations
# Every picture is a literal scene built from flat shapes: big contrast,
# one clear subject, a red banner across the top naming the story.

def banner(cv, fonts, x, y, w, text, color=RED):
    f = fonts.get("sans_bold", 12)
    tw = f.width(text)
    bw = int(tw) + 16
    cv.rect(x, y, bw, 20, color)
    cv.rect(x + bw, y, 3, 20, RED_DARK)
    f.draw(cv, x + 8, y + 4, text, WHITE)


def scene_cop31(cv, x, y, w, h):
    """Antalya: a globe, a red thermometer and a clock running late."""
    cv.rect(x, y, w, h, (198, 222, 196))
    cv.rect(x, y, w, 8, GREEN)
    # globe
    cx, cy, r = x + w // 2 - 28, y + h // 2 + 6, 46
    cv.disc(cx, cy, r, BLUE)
    cv.disc(cx, cy, r, (38, 90, 145))
    cv.poly([(cx - 34, cy - 8), (cx - 12, cy - 26), (cx + 2, cy - 12),
             (cx - 8, cy + 4), (cx - 26, cy + 12)], GREEN)
    cv.poly([(cx + 12, cy + 6), (cx + 30, cy - 6), (cx + 34, cy + 14),
             (cx + 16, cy + 26), (cx + 4, cy + 18)], GREEN)
    cv.ring(cx, cy, r, NAVY, 2)
    # thermometer, right
    tx = x + w - 52
    cv.rect(tx, y + 12, 12, h - 40, WHITE)
    cv.rect(tx, y + 12, 12, h - 40, RED, )
    cv.rect(tx, y + 12, 12, int((h - 40) * 0.55), (200, 90, 80))
    cv.rect(tx, y + 12, 12, int((h - 40) * 0.25), RED)
    cv.disc(tx + 6, y + h - 26, 11, RED)
    cv.disc(tx + 6, y + h - 26, 11, RED)
    # clock, left
    kx, ky = x + 34, y + h - 30
    cv.disc(kx, ky, 16, WHITE)
    cv.ring(kx, ky, 16, INK, 2)
    cv.line(kx, ky, kx, ky - 11, INK, 2)
    cv.line(kx, ky, kx + 9, ky + 3, INK, 2)
    # sun
    cv.disc(x + w - 34, y + 22, 10, GOLD)


def scene_riyadh(cv, x, y, w, h):
    """Riyadh: night skyline, three dotted missile arcs, orange bursts."""
    cv.rect(x, y, w, h, (24, 30, 62))
    for bx, by in [(x + 20, y + 22), (x + 70, y + 34), (x + 130, y + 16),
                   (x + 190, y + 30), (x + 240, y + 20)]:
        cv.disc(bx, by, 1, WHITE)
    # skyline
    base = y + h
    heights = [58, 84, 46, 96, 62, 78, 52, 88]
    bw = w // 8
    for i, hh in enumerate(heights):
        bx = x + i * bw + 3
        cv.rect(bx, base - hh, bw - 6, hh, (52, 60, 92))
        for wy in range(base - hh + 8, base - 6, 12):
            for wx in range(bx + 3, bx + bw - 9, 9):
                if (wx * 7 + wy * 13) % 3 == 0:
                    cv.rect(wx, wy, 3, 5, GOLD)
    # tallest tower with a red hit flash at its top
    cv.rect(x + 3 * bw + 3, base - 96, bw - 6, 96, (70, 80, 118))
    cv.burst(x + 3 * bw + bw // 2, base - 96, 12, ORANGE, 8)
    # three dotted interceptor arcs
    cv.arc_dots(x + 60, base - 10, 62, 235, 315, WHITE, 7, 2)
    cv.arc_dots(x + 150, base - 10, 56, 230, 310, (255, 220, 120), 7, 2)
    cv.arc_dots(x + 235, base - 10, 48, 240, 320, WHITE, 7, 2)
    cv.burst(x + 60, base - 62, 10, ORANGE, 8)
    cv.burst(x + 150, base - 56, 10, GOLD, 8)
    cv.burst(x + 235, base - 48, 10, ORANGE, 8)


def scene_peru(cv, x, y, w, h):
    """Junin: red seismograph zigzag over shaking ground, one house."""
    cv.rect(x, y, w, h, (232, 214, 178))
    # mountains
    cv.poly([(x, y + h - 30), (x + 70, y + 28), (x + 130, y + h - 30)], (150, 122, 88))
    cv.poly([(x + 110, y + h - 30), (x + 190, y + 12), (x + 260, y + h - 30)], (122, 96, 66))
    cv.disc(x + 70, y + 28, 0, WHITE)
    # ground
    cv.rect(x, y + h - 30, w, 30, (120, 88, 58))
    cv.line(x + 40, y + h - 30, x + 90, y + h - 6, INK, 2)
    cv.line(x + 90, y + h - 6, x + 140, y + h - 30, INK, 2)
    # house
    hx, hy = x + 30, y + h - 62
    cv.rect(hx, hy, 40, 32, (245, 235, 210))
    cv.poly([(hx - 4, hy), (hx + 20, hy - 16), (hx + 44, hy)], RED)
    cv.rect(hx + 16, hy + 16, 9, 16, INK)
    # seismograph strip
    cv.rect(x, y + 10, w, 34, WHITE)
    cv.rect(x, y + 10, w, 34, (250, 248, 240))
    cv.line(x + 4, y + 27, x + 40, y + 27, RED, 2)
    cv.line(x + 40, y + 27, x + 55, y + 12, RED, 2)
    cv.line(x + 55, y + 12, x + 70, y + 42, RED, 2)
    cv.line(x + 70, y + 42, x + 85, y + 18, RED, 2)
    cv.line(x + 85, y + 18, x + 100, y + 36, RED, 2)
    cv.line(x + 100, y + 36, x + 120, y + 14, RED, 2)
    cv.line(x + 120, y + 14, x + 135, y + 40, RED, 2)
    cv.line(x + 135, y + 40, x + 160, y + 27, RED, 2)
    cv.line(x + 160, y + 27, x + w - 4, y + 27, RED, 2)


def scene_kyiv(cv, x, y, w, h):
    """Kyiv: blue sky, yellow field, bridge silhouette, one explosion."""
    cv.rect(x, y, w, h, SKY)
    cv.rect(x, y + h // 2, w, h // 2, GOLD)
    cv.disc(x + w - 30, y + 16, 11, (255, 235, 140))
    # bridge
    by = y + h - 26
    cv.rect(x, by, w, 6, INK)
    for bx in range(x + 14, x + w - 10, 26):
        cv.vline(bx, by - 18, 18, INK, 3)
    cv.burst(x + w // 2, by - 8, 13, ORANGE, 9)
    cv.burst(x + w // 2 + 26, by - 4, 8, RED, 7)


def scene_hormuz(cv, x, y, w, h):
    """Strait of Hormuz: sea, a tanker, a small drone, one burst."""
    cv.rect(x, y, w, h, SKY)
    cv.rect(x, y + h // 2 + 6, w, h // 2 - 6, BLUE)
    cv.rect(x, y + h // 2 + 6, w, 3, WHITE)
    # tanker
    cv.rect(x + 18, y + h - 34, w - 60, 16, (30, 34, 44))
    cv.rect(x + 30, y + h - 48, 26, 14, (60, 66, 80))
    cv.rect(x + 56, y + h - 44, 6, 10, RED)
    # drone
    dx, dy = x + w - 42, y + 22
    cv.disc(dx, dy, 5, INK)
    cv.line(dx - 10, dy - 8, dx + 10, dy + 8, INK, 2)
    cv.line(dx - 10, dy + 8, dx + 10, dy - 8, INK, 2)
    cv.burst(dx, dy + 16, 9, ORANGE, 7)
    # waves
    for wx in range(x + 8, x + w - 8, 24):
        cv.line(wx, y + h - 12, wx + 12, y + h - 12, WHITE, 2)


def scene_trump(cv, x, y, w, h):
    """Washington: dark blue, a white domed building, a glowing chip."""
    cv.rect(x, y, w, h, NAVY)
    cv.disc(x + w - 26, y + 18, 10, GOLD)
    # domed building
    bx, by = x + 14, y + h - 42
    cv.rect(bx, by, w - 70, 22, WHITE)
    cv.rect(bx + 4, by - 12, w - 78, 12, (235, 232, 220))
    cv.disc(bx + (w - 70) // 2, by - 12, 13, WHITE)
    for cx in range(bx + 10, bx + w - 80, 14):
        cv.rect(cx, by + 4, 3, 18, NAVY)
    # chip
    cx, cy = x + w - 44, y + h - 34
    cv.rect(cx, cy, 30, 24, INK)
    cv.rect(cx + 2, cy + 2, 26, 20, (20, 24, 32))
    cv.line(cx - 5, cy + 6, cx + 35, cy + 6, GOLD, 2)
    cv.line(cx - 5, cy + 18, cx + 35, cy + 18, GOLD, 2)
    f = None


def scene_china_japan(cv, x, y, w, h):
    """Two flags, Japan's white with red sun, China's red with stars."""
    cv.rect(x, y, w, h, (240, 234, 220))
    # Japan flag
    cv.rect(x + 12, y + 12, 76, 46, WHITE)
    cv.disc(x + 50, y + 35, 14, RED)
    cv.vline(x + 12, y + 12, h - 12, INK, 2)
    # China flag
    cv.rect(x + w - 88, y + 12, 76, 46, RED)
    cv.disc(x + w - 72, y + 28, 7, GOLD)
    for sx, sy in [(x + w - 58, y + 20), (x + w - 52, y + 30),
                   (x + w - 54, y + 40), (x + w - 64, y + 44)]:
        cv.disc(sx, sy, 3, GOLD)
    cv.vline(x + w - 88, y + 12, h - 12, INK, 2)
    # speech lines between
    cv.line(x + w // 2 - 8, y + h - 26, x + w // 2 + 8, y + h - 26, INK, 2)
    cv.line(x + w // 2 - 8, y + h - 18, x + w // 2 + 8, y + h - 18, INK, 2)
    cv.line(x + w // 2 - 8, y + h - 10, x + w // 2 + 8, y + h - 10, INK, 2)


def scene_davao(cv, x, y, w, h):
    """Davao: sky, white jet landing, runway, smoke puffs."""
    cv.rect(x, y, w, h, SKY)
    cv.disc(x + 26, y + 16, 11, (255, 235, 140))
    cv.rect(x, y + h - 16, w, 16, (90, 90, 88))
    cv.rect(x, y + h - 16, w, 2, WHITE)
    # runway stripes
    for rx in range(x + 8, x + w - 8, 28):
        cv.rect(rx, y + h - 9, 16, 2, (255, 220, 120))
    # jet
    jx, jy = x + w // 2 - 40, y + h - 52
    cv.ellipse(jx + 40, jy, 44, 10, WHITE)
    cv.poly([(jx + 70, jy - 6), (jx + 88, jy - 22), (jx + 84, jy - 4)], WHITE)
    cv.poly([(jx + 20, jy + 4), (jx + 34, jy + 18), (jx + 44, jy + 6)], WHITE)
    cv.rect(jx + 76, jy - 4, 10, 6, NAVY)
    cv.line(jx + 2, jy + 8, jx + 2, jy + 16, INK, 2)
    cv.line(jx + 60, jy + 8, jx + 60, jy + 16, INK, 2)
    # smoke puffs behind
    cv.disc(jx - 8, jy - 2, 6, (235, 235, 230))
    cv.disc(jx - 18, jy - 8, 4, (235, 235, 230))


def scene_canberra(cv, x, y, w, h):
    """Canberra: green and gold, two flags, a glowing AI chip."""
    cv.rect(x, y, w, h, (196, 222, 188))
    # Australia flag
    cv.rect(x + 12, y + 12, 66, 40, NAVY)
    cv.disc(x + 24, y + 24, 4, WHITE)
    cv.disc(x + 58, y + 34, 3, WHITE)
    cv.disc(x + 44, y + 20, 3, WHITE)
    cv.disc(x + 62, y + 20, 3, WHITE)
    cv.vline(x + 12, y + 12, h - 12, INK, 2)
    # China flag
    cv.rect(x + w - 78, y + 12, 66, 40, RED)
    cv.disc(x + w - 64, y + 26, 6, GOLD)
    cv.vline(x + w - 78, y + 12, h - 12, INK, 2)
    # AI chip
    cx, cy = x + w // 2 - 16, y + h - 34
    cv.rect(cx, cy, 32, 24, INK)
    cv.rect(cx + 2, cy + 2, 28, 20, (20, 24, 32))
    cv.line(cx - 4, cy + 6, cx + 36, cy + 6, GOLD, 2)
    cv.line(cx - 4, cy + 18, cx + 36, cy + 18, GOLD, 2)


def scene_bitcoin(cv, x, y, w, h):
    """Bitcoin: dark panel, gold coin, red falling chart."""
    cv.rect(x, y, w, h, (24, 26, 34))
    cx, cy = x + w // 2, y + h // 2 - 2
    cv.disc(cx, cy, 26, GOLD)
    cv.disc(cx, cy, 22, (230, 178, 60))
    cv.rect(cx - 2, cy - 14, 4, 28, (160, 110, 20))
    cv.rect(cx - 8, cy - 10, 16, 4, (160, 110, 20))
    cv.rect(cx - 8, cy + 6, 16, 4, (160, 110, 20))
    # falling line
    pts = [(x + 8, y + 14), (x + 40, y + 18), (x + 70, y + 12),
           (x + 100, y + 24), (x + 130, y + 30), (x + w - 8, y + 40)]
    for a, b in zip(pts, pts[1:]):
        cv.line(a[0], a[1], b[0], b[1], RED, 2)
    cv.line(x + w - 8, y + 40, x + w - 16, y + 34, RED, 2)
    cv.line(x + w - 8, y + 40, x + w - 18, y + 44, RED, 2)


def scene_russell(cv, x, y, w, h):
    """Las Vegas: dark track curve, a race car, a checkered flag."""
    cv.rect(x, y, w, h, (30, 34, 44))
    # track arc
    cv.arc_dots(x + w // 2, y + h + 30, 78, 200, 340, (120, 120, 120), 8, 3)
    cv.arc_dots(x + w // 2, y + h + 30, 62, 200, 340, WHITE, 8, 2)
    # car
    cx, cy = x + w // 2 - 20, y + h - 40
    cv.rect(cx, cy, 44, 10, RED)
    cv.rect(cx + 12, cy - 8, 20, 8, RED_DARK)
    cv.disc(cx + 8, cy + 12, 5, INK)
    cv.disc(cx + 36, cy + 12, 5, INK)
    cv.disc(cx + 8, cy + 12, 2, (200, 200, 200))
    cv.disc(cx + 36, cy + 12, 2, (200, 200, 200))
    # checkered flag
    fx, fy = x + w - 30, y + 10
    cv.rect(fx, fy, 20, 14, WHITE)
    for r in range(2):
        for c in range(4):
            if (r + c) % 2 == 0:
                cv.rect(fx + c * 5, fy + r * 7, 5, 7, INK)
    cv.vline(fx, fy, 24, INK, 2)


def scene_rahul(cv, x, y, w, h):
    """Wellington: green pitch, a bat, a ball, big 136."""
    cv.rect(x, y, w, h, (128, 190, 110))
    cv.rect(x, y + h - 14, w, 14, (96, 150, 84))
    # stumps
    sx, sy = x + 20, y + h - 34
    for k in range(3):
        cv.vline(sx + k * 6, sy, 20, (235, 220, 160), 3)
    # bat
    cv.line(x + w - 44, y + 16, x + w - 24, y + 46, (200, 170, 120), 5)
    cv.line(x + w - 24, y + 46, x + w - 16, y + 58, (120, 90, 60), 4)
    # ball
    cv.disc(x + w - 58, y + 22, 6, RED)
    cv.disc(x + w - 58, y + 22, 3, (255, 255, 255))
    # big 136
    f = FONTS.get("serif_bold", 34)
    f.draw(cv, x + w // 2 - 26, y + h - 46, "136", WHITE)


def scene_bepi(cv, x, y, w, h):
    """Mercury orbit: black space, cratered Mercury, a spacecraft."""
    cv.rect(x, y, w, h, (12, 12, 22))
    for bx, by in [(x + 14, y + 12), (x + 40, y + 28), (x + 90, y + 10),
                   (x + 130, y + 24), (x + w - 20, y + 40)]:
        cv.disc(bx, by, 1, WHITE)
    # Mercury
    cx, cy = x + w // 2 - 14, y + h // 2 + 4
    cv.disc(cx, cy, 24, (196, 140, 96))
    cv.disc(cx - 6, cy - 4, 4, (160, 108, 66))
    cv.disc(cx + 8, cy + 6, 3, (160, 108, 66))
    cv.disc(cx + 4, cy - 10, 2, (160, 108, 66))
    cv.disc(cx - 10, cy + 10, 2, (160, 108, 66))
    # orbit ring
    cv.ring(cx, cy, 34, (120, 120, 140), 1)
    # spacecraft
    sx, sy = cx + 30, cy - 26
    cv.rect(sx - 8, sy - 6, 16, 12, (200, 200, 200))
    cv.rect(sx - 22, sy - 3, 12, 6, NAVY)
    cv.rect(sx + 10, sy - 3, 12, 6, NAVY)
    cv.line(sx, sy + 6, sx, sy + 12, (200, 200, 200), 2)

# ---------------------------------------------------------------- story data
# Every fact below was verified against a live source on 21 Nov 2026.
# Parent-verified core facts (1-6) are used as given; the rest were
# verified by live web search in this build session.

HEROES = [
    dict(
        num=1, banner="COP31: OVERTIME", tag="1 \u00b7 ANTALYA, T\u00dcRKIYE \u00b7 CLIMATE",
        headline="Climate summit runs into Saturday with no deal",
        deck=("Plenary suspended at 22:29 local on Friday. A third draft is due "
              "on Saturday morning; it drops fossil fuels and the $120bn figure."),
        source="AFP \u00b7 AL JAZEERA",
        caption="No deal \u00b7 day 13 of a summit meant to close on day 12",
        scene=scene_cop31,
    ),
    dict(
        num=2, banner="RIYADH: MISSILES", tag="2 \u00b7 RIYADH \u00b7 JAZAN \u00b7 WAR",
        headline="Five Houthi missiles shot down over Saudi Arabia",
        deck=("Three ballistic missiles over Riyadh early on Saturday, two more "
              "over Jazan \u2014 days after Thursday's strike on the PIF Tower."),
        source="AFP \u00b7 DAWN",
        caption="Three over the capital \u00b7 two over Jazan",
        scene=scene_riyadh,
    ),
    dict(
        num=3, banner="PERU: QUAKE 6.7", tag="3 \u00b7 JUN\u00cdN, PERU \u00b7 EARTHQUAKE",
        headline="Magnitude 6.7 earthquake shakes central Peru",
        deck=("The quake struck at 00:09 UTC on Saturday, 108 km deep, and was "
              "felt across Lima. There were no deaths and no major damage in "
              "the first reports."),
        source="USGS \u00b7 IGP",
        caption="108 km deep \u00b7 felt in Lima \u00b7 no deaths",
        scene=scene_peru,
    ),
]

FEATURES = [
    dict(num=4, banner="KYIV: WARNING", tag="4 \u00b7 KYIV \u00b7 WAR",
         headline="Zelensky: the Crimea bridge \u2018will not stay\u2019",
         deck="Warns of more double-tap strikes in an NBC interview.",
         source="NBC \u00b7 REUTERS", caption="Crimea Bridge, hit 16\u201317 Nov",
         scene=scene_kyiv),
    dict(num=5, banner="HORMUZ: DRONE", tag="5 \u00b7 STRAIT OF HORMUZ \u00b7 WAR",
         headline="Iran says it shot down a US MQ-9 drone",
         deck="Tehran calls it the 58th MQ-9 downed. No US confirmation.",
         source="IRIB \u00b7 ANI", caption="Iran's claim \u00b7 58th MQ-9",
         scene=scene_hormuz),
    dict(num=6, banner="TRUMP: AI TAX", tag="6 \u00b7 WASHINGTON \u00b7 TECHNOLOGY",
         headline="Trump vows a tax on data centres abroad",
         deck="\u2018Tremendous tax\u2019 on firms building abroad, he said.",
         source="REUTERS", caption="Said after his Asia trip",
         scene=scene_trump),
    dict(num=7, banner="CHINA\u2013JAPAN", tag="7 \u00b7 BEIJING \u00b7 DIPLOMACY",
         headline="China tells Japan to \u2018correct\u2019 Taiwan words",
         deck="Beijing repeats its demand over Taiwan; Tokyo stands firm.",
         source="REUTERS \u00b7 AFP", caption="Beijing's demand, renewed Friday",
         scene=scene_china_japan),
    dict(num=8, banner="DAVAO: 146 SAFE", tag="8 \u00b7 DAVAO \u00b7 AVIATION",
         headline="Jet lands safely after an engine fire alert",
         deck="Air Niugini's 767 diverted to Davao; all 146 on board safe.",
         source="AP \u00b7 CAAP", caption="Hong Kong\u2013Port Moresby flight",
         scene=scene_davao),
    dict(num=9, banner="CANBERRA: AI", tag="9 \u00b7 CANBERRA \u00b7 DIPLOMACY",
         headline="Australia and China agree to AI talks",
         deck="Xi hails a \u2018turnaround\u2019 after an 11-day trip.",
         source="AAP \u00b7 ABC", caption="Annual leaders' meeting",
         scene=scene_canberra),
    dict(num=10, banner="BITCOIN: $58,810", tag="10 \u00b7 WORLD \u00b7 MARKETS",
         headline="Bitcoin slips early on Saturday",
         deck="Down 4.1% in 24 hours at 01:30 UTC; it fell further later.",
         source="COINGECKO", caption="At 01:30 UTC on Saturday",
         scene=scene_bitcoin),
    dict(num=11, banner="RUSSELL: P1", tag="11 \u00b7 LAS VEGAS \u00b7 FORMULA ONE",
         headline="Russell fastest in final practice",
         deck="1:34.041 in Las Vegas, then sent to stewards after a clash.",
         source="FORMULA 1", caption="Final practice \u00b7 Las Vegas GP",
         scene=scene_russell),
    dict(num=12, banner="RAHUL: 136", tag="12 \u00b7 WELLINGTON \u00b7 CRICKET",
         headline="Rahul hits a century against New Zealand",
         deck="13th Test hundred; first opener with SENA centuries.",
         source="CRICINFO", caption="First opener in all four SENA lands",
         scene=scene_rahul),
    dict(num=13, banner="BEPICOLOMBO: MERCURY", tag="13 \u00b7 SPACE \u00b7 SCIENCE",
         headline="BepiColombo enters Mercury orbit",
         deck="Launched 2018; second craft ever to orbit Mercury.",
         source="ESA \u00b7 JAXA", caption="Launched October 2018",
         scene=scene_bepi),
]

ALSO = [
    (14, "Kryvyi Rih", "Double strike kills 2, injures 58", "Kyiv Independent"),
    (15, "Kyiv", "Hit again; 2 injured in Podil fires", "Kyiv Independent"),
    (16, "Kharkiv", "Drone hits a 5-storey block; 11 injured", "Kyiv Independent"),
    (17, "Odisha", "Akvan weakens; 440,000+ sheltered, no deaths", "IMD"),
    (18, "Copenhagen", "Denmark expels Russian attach\u00e9 in plot row", "WSJ"),
    (19, "Antalya", "Third COP31 draft due Saturday morning", "AFP"),
    (20, "Addis Ababa", "COP32 to be held in Ethiopia in 2027", "AFP"),
    (21, "Jazan", "Two more missiles downed over Jazan", "AFP"),
    (22, "Hodeidah", "Coalition struck the port on Friday", "AFP"),
    (23, "Texas", "Execution of a man of 70 takes 63 minutes", "AP"),
    (24, "Missouri", "Judge approves $7.25bn Roundup deal", "Reuters"),
    (25, "Sejong", "Freight train derails; no one hurt", "Yonhap"),
    (26, "Bangkok", "Six-point plan on arsenic in two rivers", "The Nation"),
    (27, "Wellington", "Gill falls two short of a century on 98", "Cricinfo"),
    (28, "Las Vegas", "Verstappen sent to stewards after contact", "FIA"),
    (29, "Wellington", "India 486 for 4 at stumps, lead by 118", "Cricinfo"),
    (30, "Riyadh", "PIF Tower hit on Thursday; no injuries", "AFP"),
    (31, "Odisha", "2,316 safe deliveries recorded in shelters", "IMD"),
    (32, "Davao", "Airport closed for two hours after landing", "AP"),
    (33, "Shenzhen", "Xi hails China-Australia \u2018turnaround\u2019", "Xinhua"),
    (34, "Antalya", "Closing plenary suspended at 22:29 local", "AFP"),
    (35, "Lima", "Quake felt across the capital; no tsunami risk", "USGS"),
]

STATS = [
    ("13", "DAY OF COP31, DUE TO CLOSE DAY 12"),
    ("5", "MISSILES SHOT DOWN OVER RIYADH AND JAZAN"),
    ("6.7", "MAGNITUDE OF THE QUAKE IN CENTRAL PERU"),
    ("146", "PEOPLE SAFE AFTER A JET'S ENGINE FIRE ALERT"),
    ("$58,810", "BITCOIN AT 01:30 UTC, DOWN 4.1% IN A DAY"),
    ("136", "RUNS BY K L RAHUL AGAINST NEW ZEALAND"),
]

REGIONS = [("EUROPE", 8), ("ASIA", 8), ("MIDDLE EAST", 5), ("AFRICA", 1),
           ("AMERICAS", 7), ("OCEANIA", 4), ("GLOBAL", 2)]


# ---------------------------------------------------------------- layout
def draw_hero(cv, fonts, x, y, w, hero):
    pic_h = 112
    hero["scene"](cv, x, y, w, pic_h)
    cv.rect(x, y + pic_h - 2, w, 2, INK)
    banner(cv, fonts, x + 8, y + 8, w, hero["banner"])
    # tag
    ty = y + pic_h + 6
    f = fonts.get("sans_bold", 10)
    f.draw(cv, x + 2, ty, hero["tag"], RED)
    # headline, 2 lines max
    hy = ty + 15
    f = fonts.get("serif_bold", 19)
    lines = wrap(f, hero["headline"], w - 4)
    for ln in lines[:2]:
        f.draw(cv, x + 2, hy, ln, INK)
        hy += 22
    # deck, 3 lines max
    dy = hy + 2
    f = fonts.get("sans", 12)
    lines = wrap(f, hero["deck"], w - 4)
    for ln in lines[:3]:
        f.draw(cv, x + 2, dy, ln, INK)
        dy += 15
    # source
    f = fonts.get("sans_bold", 9)
    f.draw(cv, x + 2, dy + 2, hero["source"], INK_SOFT)
    return dy + 14


def draw_feature(cv, fonts, x, y, w, feat, tint):
    cv.rect(x, y, w, 172, tint)
    pic_h = 74
    feat["scene"](cv, x + 4, y + 4, w - 8, pic_h)
    cv.rect(x + 4, y + 4 + pic_h - 2, w - 8, 2, INK)
    banner(cv, fonts, x + 10, y + 10, w, feat["banner"])
    ty = y + 82
    f = fonts.get("sans_bold", 9)
    f.draw(cv, x + 6, ty, feat["tag"], RED)
    hy = ty + 12
    f = fonts.get("serif_bold", 14)
    lines = wrap(f, feat["headline"], w - 12)
    for ln in lines[:2]:
        f.draw(cv, x + 6, hy, ln, INK)
        hy += 16
    dy = hy + 1
    f = fonts.get("sans", 11)
    lines = wrap(f, feat["deck"], w - 12)
    for ln in lines[:2]:
        f.draw(cv, x + 6, dy, ln, INK)
        dy += 13
    f = fonts.get("sans_bold", 8)
    f.draw(cv, x + 6, dy + 1, feat["source"], INK_SOFT)
    return y + 172

# ---------------------------------------------------------------- map + also
def draw_map(cv, fonts, x, y, w, h):
    """Stylised world map: pale sea, tan continents, numbered red pins."""
    cv.rect(x, y, w, h, (198, 220, 234))
    land = (210, 196, 150)
    # North America
    cv.ellipse(x + 52, y + 26, 44, 17, land)
    cv.ellipse(x + 78, y + 40, 22, 12, land)
    # South America
    cv.ellipse(x + 82, y + 74, 15, 20, land)
    # Europe
    cv.ellipse(x + 168, y + 22, 13, 9, land)
    # Africa
    cv.ellipse(x + 178, y + 56, 17, 20, land)
    # Asia
    cv.ellipse(x + 232, y + 26, 52, 18, land)
    cv.ellipse(x + 258, y + 44, 22, 12, land)
    # Australia
    cv.ellipse(x + 268, y + 86, 14, 8, land)
    # pins: (story number, px, py)
    pins = [(1, 183, 28), (2, 188, 50), (3, 80, 68), (4, 170, 16),
            (5, 206, 36), (6, 52, 30), (7, 246, 26), (8, 258, 56),
            (9, 270, 84), (10, 118, 16), (11, 38, 36), (12, 282, 92)]
    f = fonts.get("sans_bold", 8)
    for num, px, py in pins:
        cv.disc(x + px, y + py, 7, RED)
        cv.ring(x + px, y + py, 7, WHITE, 1)
        tw = f.width(str(num))
        f.draw(cv, x + px - tw / 2, y + py - 4, str(num), WHITE)
    # 13 is in orbit, not on the map
    cv.burst(x + w - 16, y + 14, 6, GOLD, 6)
    f.draw(cv, x + w - 26, y + 24, "13", INK)


def draw_also(cv, fonts, x, y, w, h):
    f = fonts.get("sans_bold", 11)
    f.draw(cv, x, y, "ALSO ON SATURDAY 21 NOVEMBER \u2014 22 MORE STORIES", INK)
    y += 16
    cv.hline(x, y, w, INK, 2)
    y += 6
    col_w = (w - 8) // 2
    f_bold = fonts.get("sans_bold", 10)
    f_reg = fonts.get("sans", 10)
    lh = 11
    for i, (num, place, text, src) in enumerate(ALSO):
        col = 0 if i < 11 else 1
        row = i if i < 11 else i - 11
        cx = x + col * (col_w + 8)
        cy = y + row * lh
        lead = f"{num}. {place}: "
        lead_w = f_bold.width(lead)
        f_bold.draw(cv, cx, cy, lead, INK)
        # one line: bold lead + regular text + grey source
        rest = text + " (" + src + ")"
        # shrink the rest if it would overflow the column
        while f_reg.width(rest) > col_w - lead_w and len(rest) > 12:
            rest = rest[:len(rest) - 4] + "\u2026"
        f_reg.draw(cv, cx + lead_w, cy, rest, INK)


# ---------------------------------------------------------------- page
def draw():
    base = os.path.dirname(os.path.abspath(__file__))
    table = load_fonts(os.path.join(base, "fonts.bin"))
    global FONTS
    FONTS = Fonts(table)
    fonts = FONTS
    cv = Canvas(W, H, PAPER)

    # ---- top bar
    f = fonts.get("serif_bold", 15)
    f.draw(cv, 14, 10, "THE WORLD IN ONE DAY", INK)
    f = fonts.get("sans_bold", 9)
    right = "35 STORIES \u00b7 7 REGIONS \u00b7 EVERY ONE DATED SATURDAY 21 NOVEMBER 2026"
    f.draw(cv, W - 14 - f.width(right), 13, right, INK)
    cv.hline(14, 28, W - 28, INK, 2)

    # ---- masthead
    f = fonts.get("serif_bold", 56)
    title = "Saturday 21 November 2026"
    f.draw(cv, (W - f.width(title)) / 2, 34, title, INK)
    f = fonts.get("serif_italic", 15)
    kicker = ("Climate summit runs past its deadline \u00b7 Five missiles shot down "
              "over Saudi Arabia \u00b7 Strong quake shakes Peru")
    f.draw(cv, (W - f.width(kicker)) / 2, 98, kicker, INK_SOFT)
    cv.hline(14, 120, W - 28, INK, 1)

    # ---- stat strip
    sy = 128
    bw = (W - 28 - 5 * 5) // 6
    for i, (num, label) in enumerate(STATS):
        bx = 14 + i * (bw + 5)
        cv.rect(bx, sy, bw, 50, PAPER2)
        cv.rect(bx, sy, bw, 3, RED)
        f = fonts.get("serif_bold", 24)
        f.draw(cv, bx + 8, sy + 6, num, INK)
        f = fonts.get("sans_bold", 8)
        for j, ln in enumerate(wrap(f, label, bw - 16)):
            f.draw(cv, bx + 8, sy + 32 + j * 10, ln, INK_SOFT)
    # ---- region strip
    ry = sy + 58
    f = fonts.get("sans_bold", 10)
    f.draw(cv, 14, ry, "7 REGIONS:", INK)
    rx = int(14 + f.width("7 REGIONS: ") + 4)
    for name, count in REGIONS:
        chip = f"{name} {count}"
        cw = int(f.width(chip)) + 12
        cv.rect(rx, ry - 2, cw, 16, NAVY)
        f.draw(cv, rx + 6, ry + 1, chip, WHITE)
        rx += cw + 6
    cv.hline(14, ry + 20, W - 28, INK, 1)

    # ---- heroes
    hy = ry + 28
    hw = (W - 28 - 2 * 15) // 3
    for i, hero in enumerate(HEROES):
        draw_hero(cv, fonts, 14 + i * (hw + 15), hy, hw, hero)
    # ---- features
    fy = hy + 254
    fw = (W - 28 - 4 * 8) // 5
    for i, feat in enumerate(FEATURES):
        row, col = divmod(i, 5)
        draw_feature(cv, fonts, 14 + col * (fw + 8), fy + row * 172,
                     fw, feat, TINTS[i])

    # ---- map + ALSO
    my = fy + 2 * 172 + 6
    f = fonts.get("sans_bold", 11)
    f.draw(cv, 14, my, "WHERE IT HAPPENED", INK)
    draw_map(cv, fonts, 14, my + 16, 300, 100)
    f = fonts.get("sans", 9)
    f.draw(cv, 14, my + 120, "Each number is the story with that number on this page.", INK_SOFT)
    f.draw(cv, 14, my + 131, "13 is in orbit, not on the map.", INK_SOFT)
    draw_also(cv, fonts, 330, my, W - 330 - 14, 150)

    # ---- DATE CHECK
    dy = my + 146
    cv.rect(14, dy, W - 28, 42, (255, 250, 230))
    cv.rect(14, dy, 4, 42, RED)
    f = fonts.get("sans_bold", 11)
    f.draw(cv, 26, dy + 4, "DATE CHECK \u2014 WHAT WAS LEFT OUT", RED)
    f = fonts.get("sans", 11)
    dc = ("Left out as Friday 20 November's news: Wall Street's fall into a correction, "
          "the 111-missile barrage that hit Kyiv's three bridges, the missile that landed "
          "in Poland, the UK\u2013EU deal and Cyclone Akvan's landfall. Older still: Voyager 1's "
          "light-day (18 Nov). Everything here happened, or was first reported, "
          "on Saturday 21 November 2026.")
    yy = dy + 16
    for ln in wrap(f, dc, W - 28 - 24):
        f.draw(cv, 26, yy, ln, INK)
        yy += 12

    # ---- footer
    f = fonts.get("sans", 9)
    foot = ("Every story here happened, or was first reported, on Saturday 21 November 2026. "
            "Officials' counts and claims are attributed. \u00b7 Sources named beside each story "
            "\u00b7 Original drawings")
    f.draw(cv, (W - f.width(foot)) / 2, dy + 48, foot, INK_SOFT)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    cv = draw()
    write_png(os.path.join(out_dir, "entry.png"), cv.px, W, H)


if __name__ == "__main__":
    main()
