#!/usr/bin/env python3
"""news-image-20261121 v5: Saturday 21 November 2026, broadsheet front page.

Pure Python 3 stdlib (zlib + struct). No network, no Pillow, no files read.
Draws a 1024x1024 cream broadsheet to /output/entry.png, byte-identical
on every run. All facts were checked against live news sources on
23 Nov 2026 (USGS, Reuters, EU Council, CNN, NPR).
"""
import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER = (247, 241, 222)
PAPER2 = (241, 233, 208)
INK = (17, 17, 17)
INK2 = (70, 70, 70)
RED = (179, 35, 27)
RED_DK = (140, 22, 18)
GREEN = (46, 125, 50)
GREEN_LT = (220, 237, 200)
TEAL = (14, 107, 107)
BLUE = (31, 78, 121)
SEA = (207, 224, 232)
SEA_DK = (168, 200, 214)
LAND = (232, 220, 195)
LAND_DK = (214, 198, 168)
GOLD = (178, 138, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREY = (120, 120, 120)
GREY_LT = (200, 200, 200)

REG_EUROPE = (31, 78, 121)
REG_MIDEAST = (179, 35, 27)
REG_AMERICAS = (46, 125, 50)
REG_AFRICA = (178, 106, 0)
REG_SASIA = (123, 31, 162)
REG_EASIA = (194, 24, 91)
REG_SEASIA = (0, 121, 107)
REG_OCEANIA = (93, 64, 55)
REG_GLOBAL = (55, 71, 79)

# ------------------------------------------------------- 5x7 bitmap font
# Each glyph: 7 rows, 5 bits each (bit 4 = leftmost pixel).
FONT = {
    ' ': (0, 0, 0, 0, 0, 0, 0),
    '!': (0x04, 0x04, 0x04, 0x04, 0x04, 0x00, 0x04),
    '"': (0x0A, 0x0A, 0x0A, 0x00, 0x00, 0x00, 0x00),
    '#': (0x0A, 0x0A, 0x1F, 0x0A, 0x1F, 0x0A, 0x0A),
    '$': (0x04, 0x0F, 0x14, 0x0E, 0x05, 0x1E, 0x04),
    '%': (0x18, 0x19, 0x02, 0x04, 0x08, 0x13, 0x03),
    '&': (0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D),
    "'": (0x04, 0x04, 0x08, 0x00, 0x00, 0x00, 0x00),
    '(': (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ')': (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    '*': (0x00, 0x04, 0x15, 0x0E, 0x15, 0x04, 0x00),
    '+': (0x00, 0x04, 0x04, 0x1F, 0x04, 0x04, 0x00),
    ',': (0x00, 0x00, 0x00, 0x00, 0x0C, 0x04, 0x08),
    '-': (0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00),
    '.': (0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C),
    '/': (0x01, 0x02, 0x02, 0x04, 0x08, 0x08, 0x10),
    '0': (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    '1': (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    '2': (0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F),
    '3': (0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E),
    '4': (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    '5': (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    '6': (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    '7': (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    '8': (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    '9': (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    ':': (0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x0C, 0x00),
    ';': (0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x04, 0x08),
    '<': (0x02, 0x04, 0x08, 0x10, 0x08, 0x04, 0x02),
    '=': (0x00, 0x00, 0x1F, 0x00, 0x1F, 0x00, 0x00),
    '>': (0x08, 0x04, 0x02, 0x01, 0x02, 0x04, 0x08),
    '?': (0x0E, 0x11, 0x01, 0x02, 0x04, 0x00, 0x04),
    '@': (0x0E, 0x11, 0x17, 0x15, 0x16, 0x10, 0x0E),
    'A': (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    'B': (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    'C': (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    'D': (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    'E': (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    'F': (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    'G': (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    'H': (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    'I': (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    'J': (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    'K': (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    'L': (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    'M': (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    'N': (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    'O': (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    'P': (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    'Q': (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    'R': (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    'S': (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    'T': (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    'U': (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    'V': (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    'W': (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11),
    'X': (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    'Y': (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    'Z': (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    '[': (0x0E, 0x08, 0x08, 0x08, 0x08, 0x08, 0x0E),
    '\\': (0x10, 0x08, 0x08, 0x04, 0x02, 0x02, 0x01),
    ']': (0x0E, 0x02, 0x02, 0x02, 0x02, 0x02, 0x0E),
    '^': (0x04, 0x0A, 0x11, 0x00, 0x00, 0x00, 0x00),
    '_': (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1F),
    '`': (0x08, 0x04, 0x02, 0x00, 0x00, 0x00, 0x00),
    'a': (0x00, 0x00, 0x0E, 0x01, 0x0F, 0x11, 0x0F),
    'b': (0x10, 0x10, 0x16, 0x19, 0x11, 0x11, 0x1E),
    'c': (0x00, 0x00, 0x0E, 0x11, 0x10, 0x11, 0x0E),
    'd': (0x01, 0x01, 0x0D, 0x13, 0x11, 0x11, 0x0F),
    'e': (0x00, 0x00, 0x0E, 0x11, 0x1F, 0x10, 0x0E),
    'f': (0x06, 0x08, 0x08, 0x1E, 0x08, 0x08, 0x08),
    'g': (0x00, 0x0F, 0x11, 0x11, 0x0F, 0x01, 0x0E),
    'h': (0x10, 0x10, 0x16, 0x19, 0x11, 0x11, 0x11),
    'i': (0x04, 0x00, 0x0C, 0x04, 0x04, 0x04, 0x0E),
    'j': (0x02, 0x00, 0x06, 0x02, 0x02, 0x12, 0x0C),
    'k': (0x10, 0x10, 0x12, 0x14, 0x18, 0x14, 0x12),
    'l': (0x0C, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    'm': (0x00, 0x00, 0x1A, 0x15, 0x15, 0x15, 0x15),
    'n': (0x00, 0x00, 0x16, 0x19, 0x11, 0x11, 0x11),
    'o': (0x00, 0x00, 0x0E, 0x11, 0x11, 0x11, 0x0E),
    'p': (0x00, 0x00, 0x1E, 0x11, 0x11, 0x1E, 0x10),
    'q': (0x00, 0x00, 0x0D, 0x13, 0x11, 0x0F, 0x01),
    'r': (0x00, 0x00, 0x16, 0x19, 0x10, 0x10, 0x10),
    's': (0x00, 0x00, 0x0F, 0x10, 0x0E, 0x01, 0x1E),
    't': (0x08, 0x08, 0x1E, 0x08, 0x08, 0x09, 0x06),
    'u': (0x00, 0x00, 0x11, 0x11, 0x11, 0x13, 0x0D),
    'v': (0x00, 0x00, 0x11, 0x11, 0x11, 0x0A, 0x04),
    'w': (0x00, 0x00, 0x11, 0x11, 0x15, 0x15, 0x0A),
    'x': (0x00, 0x00, 0x11, 0x0A, 0x04, 0x0A, 0x11),
    'y': (0x00, 0x00, 0x11, 0x11, 0x0F, 0x01, 0x0E),
    'z': (0x00, 0x00, 0x1F, 0x02, 0x04, 0x08, 0x1F),
    '{': (0x06, 0x08, 0x08, 0x1E, 0x08, 0x08, 0x06),
    '|': (0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    '}': (0x0C, 0x02, 0x02, 0x0F, 0x02, 0x02, 0x0C),
    '~': (0x00, 0x00, 0x0E, 0x15, 0x00, 0x00, 0x00),
    '\u2022': (0x00, 0x00, 0x04, 0x0E, 0x0E, 0x04, 0x00),  # bullet
    '\u2014': (0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00),  # em dash
    '\u2013': (0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00),  # en dash
    '\u2019': (0x04, 0x04, 0x08, 0x00, 0x00, 0x00, 0x00),  # right quote
    '\u201c': (0x0A, 0x0A, 0x0A, 0x00, 0x00, 0x00, 0x00),  # left dquote
    '\u201d': (0x0A, 0x0A, 0x0A, 0x00, 0x00, 0x00, 0x00),  # right dquote
    '\u00b0': (0x0E, 0x11, 0x11, 0x0E, 0x00, 0x00, 0x00),  # degree
    '\u00d7': (0x11, 0x0A, 0x04, 0x0A, 0x11, 0x00, 0x00),  # multiply
    '\u2713': (0x01, 0x02, 0x04, 0x0C, 0x14, 0x10, 0x00),  # check mark
}


def text_width(s, scale):
    """Pixel width of string s at scale (no trailing gap)."""
    if not s:
        return 0
    return len(s) * 6 * scale - scale


def wrap_text(s, scale, maxw):
    """Greedy word wrap; returns list of lines that fit maxw pixels."""
    lines = []
    for para in s.split('\n'):
        words = para.split(' ')
        cur = ''
        for wd in words:
            trial = wd if not cur else cur + ' ' + wd
            if text_width(trial, scale) <= maxw or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = wd
        if cur != '' or not lines:
            lines.append(cur)
    return lines


class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg * (w * h))

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def rect(self, x, y, w, h, c, fill=True):
        if w <= 0 or h <= 0:
            return
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if fill:
            for yy in range(y0, y1):
                base = (yy * self.w + x0) * 3
                for xx in range(x0, x1):
                    i = base + (xx - x0) * 3
                    self.px[i] = c[0]
                    self.px[i + 1] = c[1]
                    self.px[i + 2] = c[2]
        else:
            for xx in range(x0, x1):
                self.set(xx, y0, c)
                self.set(xx, y1 - 1, c)
            for yy in range(y0, y1):
                self.set(x0, yy, c)
                self.set(x1 - 1, yy, c)

    def hline(self, x, y, w, c, t=1):
        for k in range(t):
            for xx in range(x, x + w):
                self.set(xx, y + k, c)

    def vline(self, x, y, h, c, t=1):
        for k in range(t):
            for yy in range(y, y + h):
                self.set(x + k, yy, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            for a in range(t):
                for b in range(t):
                    self.set(x + a, y + b, c)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def dashed_line(self, x0, y0, x1, y1, c, dash=5, gap=4):
        dist = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
        if dist == 0:
            return
        steps = int(dist)
        on = True
        run = 0
        for i in range(steps + 1):
            t = i / steps
            x = int(round(x0 + (x1 - x0) * t))
            y = int(round(y0 + (y1 - y0) * t))
            if on:
                self.set(x, y, c)
            run += 1
            if on and run >= dash:
                on = False
                run = 0
            elif not on and run >= gap:
                on = True
                run = 0

    def disc(self, cx, cy, r, c):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self.set(xx, yy, c)

    def circle(self, cx, cy, r, c, t=1):
        import math
        for a in range(360):
            rad = math.radians(a)
            for k in range(t):
                self.set(int(round(cx + (r + k) * math.cos(rad))),
                         int(round(cy + (r + k) * math.sin(rad))), c)

    def poly(self, pts, c):
        """Scanline fill of a simple polygon."""
        if not pts:
            return
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                for x in range(int(xs[k]), int(xs[k + 1]) + 1):
                    self.set(x, y, c)

    def text(self, x, y, s, scale, c, bold=False, align='left'):
        """Draw string; (x,y) is top-left (or anchor per align). Returns width."""
        w = text_width(s, scale)
        if align == 'center':
            x = x - w // 2
        elif align == 'right':
            x = x - w
        offs = [(0, 0)]
        if bold:
            offs.append((max(1, scale // 3), 0))
        for ch in s:
            g = FONT.get(ch)
            if g is None:
                x += 6 * scale
                continue
            for (ox, oy) in offs:
                for row in range(7):
                    bits = g[row]
                    if not bits:
                        continue
                    for col in range(5):
                        if bits & (1 << (4 - col)):
                            bx = x + ox + col * scale
                            by = y + oy + row * scale
                            self.rect(bx, by, scale, scale, c)
            x += 6 * scale
        return w

    def text_block(self, x, y, lines, scale, c, bold=False, leading=None,
                   align='left'):
        lead = leading if leading is not None else 7 * scale + 2
        for ln in lines:
            self.text(x, y, ln, scale, c, bold=bold, align=align)
            y += lead
        return y

    def badge(self, x, y, s, scale, fg, bg):
        """Small filled badge with text; returns width used."""
        w = text_width(s, scale) + 8 * scale // 2 + 4
        h = 7 * scale + 4
        self.rect(x, y, w, h, bg)
        self.text(x + 4, y + 2, s, scale, fg, bold=True)
        return w


def png_bytes(c):
    raw = bytearray()
    stride = c.w * 3
    for y in range(c.h):
        raw.append(0)
        raw += c.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(typ, data):
        return (struct.pack('>I', len(data)) + typ + data +
                struct.pack('>I', zlib.crc32(typ + data) & 0xffffffff))

    ihdr = struct.pack('>IIBBBBB', c.w, c.h, 8, 2, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) +
            chunk(b'IDAT', comp) + chunk(b'IEND', b''))

# ------------------------------------------------------------------ layout
M = 14
CW = 1024 - 2 * M


def draw_top(c):
    # top bar
    c.text(M, 8, 'THE WORLD IN ONE DAY', 1, INK, bold=True)
    c.text(512, 8, 'DAY 325 OF 2026', 1, RED, bold=True, align='center')
    c.text(1024 - M, 8, 'ALL TIMES UTC \u2022 RANKED BY CONSEQUENCE', 1, INK,
           bold=True, align='right')
    c.hline(M, 20, CW, INK, 2)
    # masthead
    c.text(512, 24, 'Saturday 21 November 2026', 6, INK, bold=True,
           align='center')
    c.hline(M, 70, CW, INK, 2)
    c.text(512, 74, '37 STORIES, 9 REGIONS. EVERY ONE DATED SATURDAY 21 NOVEMBER 2026',
           2, RED, bold=True, align='center')
    c.text(512, 90,
           'Iran hits Bahrain \u2022 Sparta II ablaze off Finland \u2022 COP31 deadlocked in overtime',
           2, INK, align='center')
    c.hline(M, 108, CW, INK, 1)


def draw_timeline(c, y0):
    # label box
    c.rect(M, y0, 92, 44, BLACK)
    c.text(M + 46, y0 + 6, 'THE DAY', 2, WHITE, bold=True, align='center')
    c.text(M + 46, y0 + 24, 'IN UTC', 2, WHITE, bold=True, align='center')
    x0, x1 = 116, 1010
    axis_y = y0 + 26
    c.hline(x0, axis_y, x1 - x0, INK, 2)
    for h in range(0, 25, 4):
        x = x0 + int(round(h / 24.0 * (x1 - x0)))
        c.vline(x, axis_y - 4, 6, INK, 1)
    for h in (0, 8, 12, 16, 20, 24):
        x = x0 + int(round(h / 24.0 * (x1 - x0)))
        c.text(x, axis_y + 4, '%02d' % h, 1, INK2, align='center')
    pins = [
        ('00:09 Peru M6.7 quake', 0 * 60 + 9, 'up'),
        ('04:00 Geneva talks end', 4 * 60, 'down'),
        ('06:50 Sparta II alarm', 6 * 60 + 50, 'up'),
        ('09:42 Banda Sea M6.8', 9 * 60 + 42, 'down'),
        ('12:12 EU-Indonesia signed', 12 * 60 + 12, 'up'),
        ('18:24 BepiColombo orbit', 18 * 60 + 24, 'down'),
        ('22:00 COP31 talks pause', 22 * 60, 'up'),
    ]
    for label, mins, side in pins:
        x = x0 + int(round(mins / 1440.0 * (x1 - x0)))
        c.disc(x, axis_y, 4, RED)
        c.vline(x, axis_y - 8 if side == 'up' else axis_y + 2, 8, RED, 1)
        ly = y0 + 2 if side == 'up' else axis_y + 14
        # keep label inside the page and clear of the label box
        lw = text_width(label, 1)
        lx = max(112, min(x - lw // 2, 1024 - M - lw))
        c.text(lx, ly, label, 1, INK, bold=True)


def draw_numbers(c, y0):
    cells = [
        ('2', 'tankers attacked off Khasab, Strait of Hormuz'),
        ('130+', 'countries want fossil fuels named at COP31'),
        ('730m', 'people in the new EU-Indonesia trade area'),
        ('128', 'states at the Geneva AI-weapons talks'),
        ('$5m', "FBI reward for 'El Chapo Isidro'"),
        ('8 yrs', "BepiColombo's journey to Mercury"),
    ]
    cw = CW // 6
    for i, (num, lab) in enumerate(cells):
        x = M + i * cw
        if i:
            c.vline(x, y0, 46, GREY_LT, 1)
        c.text(x + cw // 2, y0, num, 4, RED, bold=True, align='center')
        lines = wrap_text(lab, 1, cw - 10)
        c.text_block(x + 5, y0 + 30, lines[:2], 1, INK, leading=8)


def draw_regions(c, y0):
    segs = [
        ('Europe', 9, REG_EUROPE), ('Middle East', 6, REG_MIDEAST),
        ('Americas', 4, REG_AMERICAS), ('Africa', 3, REG_AFRICA),
        ('South Asia', 3, REG_SASIA), ('East Asia', 3, REG_EASIA),
        ('South-East Asia', 3, REG_SEASIA), ('Oceania', 3, REG_OCEANIA),
        ('Global', 3, REG_GLOBAL),
    ]
    c.rect(M, y0, 118, 18, BLACK)
    c.text(M + 59, y0 + 5, 'STORIES BY REGION', 1, WHITE, bold=True,
           align='center')
    x = M + 122
    widths = [212, 141, 94, 71, 71, 71, 71, 71, 71]
    for (name, n, col), w in zip(segs, widths):
        c.rect(x, y0, w, 18, col)
        c.text(x + w // 2, y0 + 5, str(n), 2, WHITE, bold=True,
               align='center')
        x += w
    legend = ('Europe 9 \u2022 Middle East 6 \u2022 Americas 4 \u2022 Africa 3 '
              '\u2022 South Asia 3 \u2022 East Asia 3 \u2022 South-East Asia 3 '
              '\u2022 Oceania 3 \u2022 Global 3')
    c.text(512, y0 + 22, legend, 1, INK2, align='center')


# ------------------------------------------------------------ lead maps
def draw_gulf_map(c, x, y, w, h):
    c.rect(x, y, w, h, SEA)
    # Iran (top), Arabia (bottom), Qatar bump
    c.poly([(x, y), (x + w, y), (x + w, y + 34), (x + 150, y + 44),
            (x + 120, y + 30), (x + 60, y + 36), (x, y + 26)], LAND)
    c.poly([(x + 30, y + h), (x + w, y + h), (x + w, y + 78),
            (x + 250, y + 70), (x + 210, y + 92), (x + 120, y + 86),
            (x + 60, y + 96)], LAND)
    # Qatar peninsula
    c.poly([(x + 128, y + 62), (x + 138, y + 58), (x + 142, y + 72),
            (x + 132, y + 76)], LAND)
    # Strait of Hormuz gap + tankers
    c.rect(x + 268, y + 40, 26, 8, (40, 40, 40))
    c.rect(x + 272, y + 32, 14, 8, (40, 40, 40))
    c.rect(x + 236, y + 88, 26, 8, (40, 40, 40))
    c.rect(x + 240, y + 80, 14, 8, (40, 40, 40))
    c.disc(x + 281, y + 36, 3, RED)
    c.disc(x + 249, y + 84, 3, RED)
    # Bahrain island + blast
    c.disc(x + 96, y + 62, 5, LAND_DK)
    for dx, dy in ((-9, -7), (9, -7), (-10, 0), (10, 0), (-7, 8), (7, 8),
                   (0, -10), (0, 10)):
        c.line(x + 96, y + 62, x + 96 + dx, y + 62 + dy, RED, 2)
    c.disc(x + 96, y + 62, 4, RED)
    # dashed attack arrow Iran -> Bahrain
    c.dashed_line(x + 170, y + 30, x + 108, y + 56, RED)
    c.text(x + 8, y + 6, 'IRAN', 1, INK2, bold=True)
    c.text(x + 60, y + 74, 'BAHRAIN', 1, RED, bold=True)
    c.text(x + 8, y + h - 12, 'SAUDI ARABIA', 1, INK2)
    c.text(x + 118, y + 82, 'QATAR', 1, INK2)
    c.text(x + w - 52, y + h - 12, 'U.A.E.', 1, INK2)
    c.text(x + 196, y + 52, 'STRAIT OF', 1, INK2, bold=True)
    c.text(x + 196, y + 60, 'HORMUZ', 1, INK2, bold=True)
    # fire tag (left of Bahrain, clear of SAUDI ARABIA + QATAR labels)
    c.rect(x + 30, y + 86, 62, 12, RED)
    c.text(x + 61, y + 88, 'SITE ON FIRE', 1, WHITE, bold=True,
           align='center')


def draw_sparta_map(c, x, y, w, h):
    c.rect(x, y, w, h, PAPER2)
    # sky / sea
    c.rect(x, y + 62, w, h - 62, SEA)
    c.hline(x, y + 62, w, SEA_DK, 2)
    # Finland + Estonia land (top right)
    c.poly([(x + 210, y), (x + w, y), (x + w, y + 44), (x + 260, y + 52),
            (x + 220, y + 40)], LAND)
    c.poly([(x + 250, y + 52), (x + w, y + 52), (x + w, y + 62),
            (x + 262, y + 62)], LAND)
    c.text(x + 258, y + 8, 'FINLAND', 1, INK2, bold=True)
    c.text(x + 262, y + 54, 'ESTONIA', 1, INK2)
    c.text(x + w - 44, y + 66, 'RUSSIA', 1, INK2, bold=True)
    # ship hull + superstructure + containers
    hx, hy = x + 30, y + 84
    c.poly([(hx, hy), (hx + 220, hy), (hx + 206, hy + 16), (hx + 8, hy + 16)],
           BLACK)
    c.rect(hx + 150, hy - 22, 34, 22, WHITE)
    c.rect(hx + 150, hy - 22, 34, 22, INK, fill=False)
    for i, col in enumerate(((179, 35, 27), (31, 78, 121), (178, 138, 0),
                             (46, 125, 50))):
        c.rect(hx + 18 + i * 30, hy - 16, 26, 16, col)
    c.text(hx + 96, hy + 4, 'SPARTA II', 1, WHITE, bold=True, align='center')
    # smoke + flame
    for (sx, sy, r) in ((hx + 60, hy - 30, 7), (hx + 72, hy - 40, 9),
                        (hx + 88, hy - 50, 8), (hx + 118, hy - 58, 6)):
        c.disc(sx, sy, r, (150, 150, 150))
    c.poly([(hx + 52, hy - 16), (hx + 60, hy - 34), (hx + 68, hy - 16)],
           (255, 140, 0))
    c.poly([(hx + 58, hy - 16), (hx + 62, hy - 26), (hx + 66, hy - 16)],
           (255, 220, 0))
    # drones + dashed paths
    for (dx, dy) in ((hx + 40, hy - 58), (hx + 130, hy - 66)):
        c.disc(dx, dy, 3, INK)
        c.disc(dx, dy, 1, WHITE)
    c.dashed_line(hx + 40, hy - 58, hx + 58, hy - 30, INK)
    c.dashed_line(hx + 130, hy - 66, hx + 96, hy - 40, INK)
    c.text(x + 8, y + 6, '06:50 UTC', 1, INK, bold=True)
    c.text(x + 8, y + 16, 'two drones, taken off', 1, INK2)


def draw_cop31_map(c, x, y, w, h):
    c.rect(x, y, w, h, PAPER2)
    # COP31 badge
    c.rect(x + 10, y + 10, 96, 62, (0, 121, 107))
    c.text(x + 58, y + 18, 'COP31', 3, WHITE, bold=True, align='center')
    c.text(x + 58, y + 44, 'ANTALYA', 1, WHITE, bold=True, align='center')
    c.text(x + 58, y + 54, 'UN CLIMATE SUMMIT', 1, WHITE, align='center')
    for i in range(5):
        c.disc(x + 22 + i * 18, y + 88, 5, GREEN)
    c.text(x + 58, y + 100, 'talks paused for the night', 1, INK2,
           align='center')
    # draft text paper
    c.rect(x + 118, y + 10, 106, 62, WHITE)
    c.rect(x + 118, y + 10, 106, 62, INK, fill=False)
    c.text(x + 171, y + 14, 'DRAFT TEXT', 1, INK2, bold=True, align='center')
    c.text(x + 171, y + 34, 'fossil fuels', 1, RED, bold=True, align='center')
    c.line(x + 135, y + 43, x + 207, y + 43, RED, 2)
    c.text(x + 171, y + 50, 'not in the draft', 1, INK2, align='center')
    # clock
    import math
    cx, cy, r = x + 268, y + 40, 26
    c.disc(cx, cy, r, WHITE)
    c.circle(cx, cy, r, INK, 2)
    c.disc(cx, cy, 2, INK)
    for ang, ln in ((90, 18), (330, 22)):
        rad = math.radians(ang - 90)
        c.line(cx, cy, int(cx + ln * math.cos(rad)),
               int(cy + ln * math.sin(rad)), INK, 2)
    c.rect(x + 232, y + 74, 72, 12, RED)
    c.text(x + 268, y + 76, 'OVERTIME', 1, WHITE, bold=True, align='center')
    c.text(x + 268, y + 92, "a day past Friday's", 1, INK2, align='center')
    c.text(x + 268, y + 101, 'deadline', 1, INK2, align='center')


def draw_lead(c, x, y, w, num, kicker, badge, headline, body, source,
              map_fn, region_col):
    map_fn(c, x, y, w, 118)
    ky = y + 122
    c.text(x, ky, '%d %s' % (num, kicker), 1, INK, bold=True)
    bw = c.badge(x + w - 76, ky - 2, badge, 1, WHITE, GREEN)
    _ = bw
    lines = wrap_text(headline, 3, w)
    c.text_block(x, ky + 16, lines[:3], 3, INK, bold=True, leading=23)
    by = ky + 16 + 3 * 23
    blines = wrap_text(body, 1, w)
    c.text_block(x, by + 2, blines[:2], 1, INK, leading=9)
    c.text(x, by + 24, source, 1, INK2)

# -------------------------------------------------------------- grid cards
def draw_grid(c, y0):
    cards = [
        # num, kicker, badge, headline, body, picto(kind, big, sub)
        (4, 'BRUSSELS \u2022 TRADE', 'CONFIRMED',
         'EU and Indonesia sign trade pact',
         'After 10 years of talks; lifts 98.5% of lines.',
         ('pct', '98.5%', 'TARIFF LINES')),
        (5, 'SINALOA \u2022 SECURITY', 'CONFIRMED',
         "Mexico seizes 'El Chapo Isidro' in raid",
         'FBI most-wanted; 7 gunmen, 4 soldiers killed in Guasave.',
         ('dead', '11', 'DEAD')),
        (6, 'GENEVA \u2022 AI ARMS', 'CONFIRMED',
         'UN killer-robot talks end with no treaty',
         '128 states settle for two more years of talks; draft by 2028.',
         ('robot', '2028', 'DRAFT BY')),
        (7, 'MERCURY \u2022 SCIENCE', 'OFFICIAL',
         'BepiColombo enters orbit around Mercury',
         'Europe-Japan probe, 8 years out; 37-min burn.',
         ('orbit', '18:24', 'ORBIT BURN')),
        (8, 'BAYELSA \u2022 DISASTER', 'CONFIRMED',
         'Nigeria funeral boat toll reaches 24',
         'Capsized Fri, Ayama-Ukubie; toll given Sat (NEMA).',
         ('boat', '24', 'DEAD')),
        (9, 'BANDA SEA \u2022 QUAKE', 'CONFIRMED',
         'Deep quake shakes Timor-Leste',
         '122 km deep, 105 km north-east of Lospalos.',
         ('quake', 'M6.8', 'DEEP')),
        (10, 'MANIPUR \u2022 HEALTH', 'CONFIRMED',
         "Tainted alcohol kills 11 in India's Manipur",
         'More than 180 in hospital, chief minister says.',
         ('bottle', '11', 'DEAD')),
        (11, 'LONDON \u2022 RUGBY', 'CONFIRMED',
         'England beat All Blacks 37-12',
         '25 points: their biggest win over New Zealand.',
         ('rugby', '37-12', 'FULL TIME')),
        (12, 'OSAKA \u2022 MUSIC', 'CONFIRMED',
         'BTS take five MAMA awards',
         'Five wins, incl. Album of the Year.',
         ('trophy', '5', 'AWARDS')),
        (13, 'FRANCE \u2022 PROTEST', 'CONFIRMED',
         'Sixth Saturday of living-cost marches',
         'Ministry count; organisers say 150,000.',
         ('crowd', '82,500', 'MARCHERS')),
    ]
    cw, gap = 193, 8
    rh, rgap = 112, 6
    for i, (num, kicker, badge, head, body, picto) in enumerate(cards):
        row, col = divmod(i, 5)
        x = M + col * (cw + gap)
        y = y0 + row * (rh + rgap)
        c.rect(x, y, cw, rh, PAPER2)
        c.rect(x, y, cw, rh, INK, fill=False)
        draw_picto(c, x, y, cw, 34, picto)
        ky = y + 38
        c.text(x + 4, ky, '%d %s' % (num, kicker), 1, INK, bold=True)
        c.badge(x + cw - 66, ky - 2, badge, 1, WHITE, GREEN)
        lines = wrap_text(head, 2, cw - 8)
        c.text_block(x + 4, ky + 14, lines[:3], 2, INK, bold=True,
                     leading=14)
        blines = wrap_text(body, 1, cw - 8)
        c.text_block(x + 4, ky + 58, blines[:2], 1, INK, leading=8)


def draw_picto(c, x, y, w, h, picto):
    kind, big, sub = picto
    c.rect(x, y, w, h, SEA)
    if kind == 'pct':
        # EU + Indonesia mini flags
        c.rect(x + 8, y + 8, 26, 18, (0, 51, 153))
        for (sx, sy) in ((21, 13), (15, 19), (27, 19), (18, 24), (24, 24)):
            c.disc(x + sx, y + sy, 1, (255, 204, 0))
        c.rect(x + 38, y + 8, 26, 9, RED)
        c.rect(x + 38, y + 17, 26, 9, WHITE)
        c.text(x + w - 8, y + 4, big, 3, RED, bold=True, align='right')
        c.text(x + w - 8, y + 25, sub, 1, INK2, align='right')
    elif kind == 'dead':
        c.disc(x + 22, y + 17, 9, GOLD)
        c.rect(x + 16, y + 13, 12, 8, (60, 40, 0))
        c.text(x + 22, y + 15, '$', 1, GOLD, bold=True, align='center')
        c.text(x + 46, y + 4, big, 3, INK, bold=True)
        c.text(x + 46, y + 25, sub, 1, RED, bold=True)
    elif kind == 'robot':
        c.rect(x + 12, y + 8, 22, 18, (120, 120, 120))
        c.rect(x + 20, y + 3, 2, 5, INK)
        c.disc(x + 21, y + 3, 2, RED)
        c.disc(x + 19, y + 15, 2, INK)
        c.disc(x + 27, y + 15, 2, INK)
        c.hline(x + 17, y + 22, 12, INK, 1)
        c.text(x + 46, y + 4, big, 3, INK, bold=True)
        c.text(x + 46, y + 25, sub, 1, INK2, bold=True)
    elif kind == 'orbit':
        c.disc(x + 24, y + 17, 9, (150, 150, 150))
        c.disc(x + 24, y + 17, 4, (100, 100, 100))
        c.circle(x + 24, y + 17, 14, INK, 1)
        c.disc(x + 38, y + 8, 2, RED)
        c.text(x + 52, y + 4, big, 3, INK, bold=True)
        c.text(x + 52, y + 25, sub, 1, INK2, bold=True)
    elif kind == 'boat':
        c.poly([(x + 10, y + 20), (x + 40, y + 20), (x + 34, y + 28),
                (x + 16, y + 28)], INK)
        c.rect(x + 22, y + 10, 3, 10, INK)
        c.poly([(x + 25, y + 10), (x + 25, y + 19), (x + 34, y + 19)],
               WHITE)
        for wx in range(x + 8, x + 48, 8):
            c.line(wx, y + 31, wx + 4, y + 31, SEA_DK, 1)
        c.text(x + 56, y + 4, big, 3, INK, bold=True)
        c.text(x + 56, y + 25, sub, 1, RED, bold=True)
    elif kind == 'quake':
        pts = [(x + 8, y + 20), (x + 16, y + 20), (x + 20, y + 10),
               (x + 26, y + 28), (x + 32, y + 12), (x + 38, y + 20),
               (x + 46, y + 20)]
        for a, b in zip(pts, pts[1:]):
            c.line(a[0], a[1], b[0], b[1], RED, 2)
        c.text(x + 56, y + 4, big, 3, RED, bold=True)
        c.text(x + 56, y + 25, sub, 1, INK2, bold=True)
    elif kind == 'bottle':
        c.rect(x + 16, y + 6, 6, 6, INK)
        c.rect(x + 12, y + 12, 14, 16, (31, 78, 121))
        c.rect(x + 12, y + 18, 14, 6, WHITE)
        c.poly([(x + 38, y + 8), (x + 48, y + 26), (x + 28, y + 26)],
               GOLD)
        c.text(x + 38, y + 18, '!', 2, INK, bold=True, align='center')
        c.text(x + 56, y + 4, big, 3, INK, bold=True)
        c.text(x + 56, y + 25, sub, 1, RED, bold=True)
    elif kind == 'rugby':
        c.vline(x + 16, y + 6, 24, INK, 2)
        c.vline(x + 30, y + 6, 24, INK, 2)
        c.hline(x + 16, y + 18, 16, INK, 2)
        c.disc(x + 23, y + 26, 4, (120, 60, 20))
        c.text(x + 44, y + 4, big, 3, INK, bold=True)
        c.text(x + 44, y + 25, sub, 1, INK2, bold=True)
    elif kind == 'trophy':
        c.poly([(x + 14, y + 6), (x + 32, y + 6), (x + 29, y + 20),
                (x + 17, y + 20)], GOLD)
        c.rect(x + 12, y + 6, 4, 8, GOLD)
        c.rect(x + 30, y + 6, 4, 8, GOLD)
        c.rect(x + 20, y + 20, 6, 4, GOLD)
        c.rect(x + 14, y + 24, 18, 3, GOLD)
        c.text(x + 46, y + 4, big, 3, INK, bold=True)
        c.text(x + 46, y + 25, sub, 1, INK2, bold=True)
    elif kind == 'crowd':
        for r in range(2):
            for k in range(5):
                c.disc(x + 12 + k * 8, y + 10 + r * 11, 3, INK)
        c.text(x + 58, y + 4, big, 3, INK, bold=True)
        c.text(x + 58, y + 25, sub, 1, INK2, bold=True)


# -------------------------------------------------------------- world map
CONTINENTS = [
    # North America
    [(20, 18), (95, 8), (135, 22), (150, 38), (132, 62), (118, 88),
     (96, 92), (78, 74), (58, 66), (34, 52), (18, 34)],
    # South America
    [(98, 102), (128, 96), (146, 118), (140, 152), (122, 178),
     (106, 152), (96, 122)],
    # Europe
    [(164, 22), (196, 12), (214, 26), (208, 48), (188, 56),
     (170, 48), (160, 34)],
    # Africa
    [(168, 66), (204, 60), (222, 78), (224, 108), (208, 142),
     (190, 150), (176, 118), (164, 88)],
    # Asia
    [(216, 18), (286, 10), (322, 30), (326, 62), (306, 92),
     (276, 104), (246, 88), (224, 62), (214, 38)],
    # Australia
    [(272, 140), (308, 134), (322, 152), (306, 172), (280, 162)],
]


def lonlat_to_xy(lon, lat, mx, my, mw, mh):
    x = mx + int(round((lon + 180.0) / 360.0 * mw))
    y = my + int(round((75.0 - lat) / 130.0 * mh))
    return x, y


def draw_worldmap(c, x, y, w, h):
    c.rect(x, y, w, h, SEA)
    c.rect(x, y, w, h, INK, fill=False)
    # continents (map area inset by 4px)
    mx, my, mw, mh = x + 4, y + 4, w - 8, h - 8
    for poly in CONTINENTS:
        pts = [(mx + int(px / 330.0 * mw), my + int(py / 190.0 * mh))
               for (px, py) in poly]
        c.poly(pts, LAND)
    pins = [
        # (story, lon, lat, region, dx, dy)
        (1, 50.6, 26.2, REG_MIDEAST, -6, -6),
        (2, 27.0, 60.0, REG_EUROPE, 0, 0),
        (3, 30.7, 36.9, REG_GLOBAL, 0, 0),
        (4, 4.35, 50.85, REG_EUROPE, -12, -10),
        (5, -108.5, 25.6, REG_AMERICAS, 0, 0),
        (6, 6.14, 46.2, REG_GLOBAL, 8, -10),
        (7, -168.0, 70.0, REG_GLOBAL, 0, 0),
        (8, 6.3, 4.8, REG_AFRICA, 0, 0),
        (9, 127.0, -8.5, REG_SEASIA, 0, 0),
        (10, 94.0, 24.5, REG_SASIA, 0, 0),
        (11, -0.34, 51.45, REG_EUROPE, 12, 8),
        (12, 135.5, 34.7, REG_EASIA, 0, 0),
        (13, 2.35, 48.85, REG_EUROPE, -2, 12),
        (14, 35.2, 31.8, REG_MIDEAST, 0, -8),
        (15, 30.5, 50.45, REG_EUROPE, 0, 0),
        (16, 34.45, 31.5, REG_MIDEAST, 8, 8),
        (17, 46.7, 24.6, REG_MIDEAST, 10, 6),
        (18, 35.5, 33.9, REG_MIDEAST, -8, 2),
        (19, 4.35, 50.85, REG_EUROPE, 12, -10),
        (20, -47.9, -15.8, REG_AMERICAS, 0, 0),
        (21, -76.0, -10.9, REG_AMERICAS, 0, 0),
        (22, -77.0, 38.9, REG_AMERICAS, 0, 0),
        (23, 106.2, -6.1, REG_SEASIA, 0, 0),
        (24, 105.85, 21.0, REG_SEASIA, 0, 0),
        (25, 90.4, 23.8, REG_SASIA, 0, 0),
        (26, 66.8, 29.8, REG_SASIA, 0, 0),
        (27, 116.4, 39.9, REG_EASIA, 0, 0),
        (28, 96.0, 36.0, REG_EASIA, 0, 0),
        (29, 16.0, 45.8, REG_EUROPE, 0, 0),
        (30, -6.26, 53.35, REG_EUROPE, -12, 2),
        (31, 7.7, 45.07, REG_EUROPE, -8, -6),
        (32, 151.2, -33.9, REG_OCEANIA, 0, 0),
        (33, 174.8, -41.3, REG_OCEANIA, 0, 0),
        (34, 7.5, 9.06, REG_AFRICA, 0, 0),
        (35, 6.5, 10.0, REG_AFRICA, 7, 7),
        (36, -5.0, 50.2, REG_EUROPE, -14, 10),
        (37, 56.5, 26.6, REG_MIDEAST, 8, -8),
    ]
    for num, lon, lat, col, dx, dy in pins:
        px, py = lonlat_to_xy(lon, lat, mx, my, mw, mh)
        px += dx
        py += dy
        r = 7 if num >= 10 else 6
        c.disc(px, py, r, col)
        c.circle(px, py, r, WHITE, 1)
        c.text(px, py - 3, str(num), 1, WHITE, bold=True, align='center')


# ----------------------------------------------------------------- ticker
TICKER = [
    (14, 'Jerusalem: Eisenkot invites Likud to talks', 'AFP', REG_MIDEAST),
    (15, "Kyiv: Zelensky calls bridge strike 'fair'", 'BBC', REG_EUROPE),
    (16, 'Gaza City: strike on food vehicle kills 3', 'AP', REG_MIDEAST),
    (17, 'Riyadh: coalition downed 3 Houthi missiles', 'AJ', REG_MIDEAST),
    (18, 'Beirut: Aoun demands Israeli pull-out', 'AJ', REG_MIDEAST),
    (19, "Brussels: Costa's EU budget: EUR 204bn cut", 'DW', REG_EUROPE),
    (20, 'Brasilia: Bolsonaro moved to intensive care', 'AJ', REG_AMERICAS),
    (21, 'Junin, Peru: M6.7 quake, 00:09 UTC', 'USGS', REG_AMERICAS),
    (22, 'Washington: FBI probes crime database breach', 'BBC', REG_AMERICAS),
    (23, 'Serang, Java: factory fire, 3 dead, 36 lost', 'BBC', REG_SEASIA),
    (24, 'Hanoi: parliament speeds land seizures', 'REUTERS', REG_SEASIA),
    (25, 'Sevara: 80 garment factories shut in protest', 'TBS', REG_SASIA),
    (26, 'Mastung: forces kill 15 militants', 'DAWN', REG_SASIA),
    (27, "Beijing: Singapore's Wong meets Li Qiang", 'ST', REG_EASIA),
    (28, 'Qinghai: M5.9 quake in remote west China', 'USGS', REG_EASIA),
    (29, 'Zagreb: rally over psychiatric ward death', 'RTE', REG_EUROPE),
    (30, 'Dublin: Ireland beat South Africa 20-17', 'BBC', REG_EUROPE),
    (31, 'Turin: Alcaraz beats Shelton, faces Zverev', 'AFP', REG_EUROPE),
    (32, 'Australia: hosts beat England in first T20', 'AP', REG_OCEANIA),
    (33, 'Wellington: India 486-4, lead NZ by 118', 'AFP', REG_OCEANIA),
    (34, 'Abuja: CAF makes Kiswahili 5th language', 'CAF', REG_AFRICA),
    (35, 'Niger State: gunmen kill head in dawn raid', 'PT', REG_AFRICA),
    (36, 'Cornwall: Peter Fluck dies at 85', 'BBC', REG_EUROPE),
    (37, 'Hormuz: Pugh ends swim for whale sharks', 'AP', REG_MIDEAST),
]


def draw_ticker(c, x, y, w, h):
    c.text(x, y, 'ALSO ON SATURDAY 21 NOVEMBER 2026', 2, INK, bold=True)
    c.text(x + w, y, '24 MORE STORIES', 1, RED, bold=True, align='right')
    c.hline(x, y + 16, w, INK, 1)
    colw = (w - 10) // 2
    for i, (num, txt, src, col) in enumerate(TICKER):
        col_i, row = divmod(i, 12)
        ix = x + col_i * (colw + 10)
        iy = y + 22 + row * 16
        c.disc(ix + 6, iy + 3, 6, col)
        c.text(ix + 6, iy, str(num), 1, WHITE, bold=True, align='center')
        line = '%s (%s)' % (txt, src)
        c.text(ix + 15, iy, line, 1, INK)


def draw_bottom(c, y0):
    # world map (left) + ticker (right)
    c.rect(M, y0, 330, 14, BLACK)
    c.text(M + 8, y0 + 3, 'WHERE IT HAPPENED', 1, WHITE, bold=True)
    c.text(M + 322, y0 + 3, 'pins = story numbers', 1, WHITE, align='right')
    draw_worldmap(c, M, y0 + 14, 330, 186)
    c.text(M + 165, y0 + 204, 'Pin numbers match the stories; pin colour = region.',
           1, INK2, align='center')
    draw_ticker(c, M + 340, y0, 656, 216)


def draw_datecheck(c, y0):
    c.rect(M, y0, CW, 40, PAPER)
    c.rect(M, y0, CW, 40, RED, fill=False)
    c.text(M + 8, y0 + 4, 'DATE CHECK \u2014 ', 1, RED, bold=True)
    c.text(M + 8 + 78, y0 + 4,
           'Well-known stories left out: they belong to another day (UTC).',
           1, INK)
    lines = [
        'Fri 20 Nov: Russian missiles land in Poland \u2022 Denmark expels Russian attache \u2022 GTA VI sales record.',
        'Sun 22 Nov: Verstappen wins Las Vegas GP \u2022 new COP31 draft \u2022 India declare at 720-9.',
        'Not yet: COP31 approval session (Sun 06:00 GMT) \u2022 Las Vegas GP race (Sun 04:00 UTC).',
    ]
    c.text_block(M + 8, y0 + 13, lines, 1, INK, leading=9)


def draw_footer(c, y0):
    c.text(512, y0,
           'HOW SURE   \u2713 CONFIRMED  2+ major outlets    \u2022 OFFICIAL  on the record, agency or ministry    \u2022 REPORTED  one major outlet    \u2022 CLAIM  one side says',
           1, INK, align='center')
    c.text(512, y0 + 12,
           'Every story here happened or was first reported on Saturday 21 November 2026 (UTC), told as the named outlets reported it.',
           1, INK2, align='center')
    c.text(512, y0 + 21, 'All maps and drawings are original vector work.',
           1, INK2, align='center')


def build():
    c = Canvas(W, H, PAPER)
    draw_top(c)
    draw_timeline(c, 112)
    draw_numbers(c, 160)
    draw_regions(c, 210)
    xs = [M, M + 336, M + 672]
    leads = [
        (1, 'BAHRAIN / HORMUZ \u2022 CONFLICT', '\u2713 CONFIRMED',
         'Iran strikes Bahrain as tankers hit in Hormuz',
         'Iranian attack set a civil industrial site ablaze, no one hurt. UKMTO: two tankers attacked off Khasab.',
         'AL JAZEERA \u2022 REUTERS \u2022 AFP', draw_gulf_map, REG_MIDEAST),
        (2, 'GULF OF FINLAND \u2022 CONFLICT', '\u2713 CONFIRMED',
         'Drones set Russian cargo ship ablaze off Finland',
         'Sparta II, for Kaliningrad, hit about 06:50 UTC, drifted into Finnish waters. Crew of 16 evacuated.',
         'BBC \u2022 FRANCE 24 \u2022 MOSCOW TIMES', draw_sparta_map, REG_EUROPE),
        (3, 'COP31, ANTALYA \u2022 CLIMATE', '\u2713 CONFIRMED',
         'COP31 deadlocked over fossil fuels in overtime',
         'Past deadline, talks paused overnight. The EU rejects a draft that omits fossil fuels.',
         'BBC \u2022 AFP \u2022 FRANCE 24', draw_cop31_map, REG_GLOBAL),
    ]
    for (num, kicker, badge, head, body, src, fn, col), x in zip(leads, xs):
        draw_lead(c, x, 244, 326, num, kicker, badge, head, body, src, fn,
                  col)
    draw_grid(c, 490)
    draw_bottom(c, 724)
    draw_datecheck(c, 944)
    draw_footer(c, 988)
    return c


def main():
    outdir = os.environ.get('MAKEFUN_OUTPUT_DIR') or 'out'
    os.makedirs(outdir, exist_ok=True)
    data = png_bytes(build())
    path = os.path.join(outdir, 'entry.png')
    with open(path, 'wb') as f:
        f.write(data)
    print('wrote %s (%d bytes)' % (path, len(data)))


if __name__ == '__main__':
    main()
