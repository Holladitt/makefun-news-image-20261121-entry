# news-image-20261121 v9 — pure-stdlib broadsheet renderer.
# A real serif broadsheet: vector serif font (authored below), cream paper,
# Reference A design (Adit's new layout) + top-1 anatomy. Writes ONE image
# to /output/entry.png, 1024x1024, <=1 MiB, byte-identical across runs,
# no network, stdlib only.
import math, os, struct, sys, zlib

W, H = 1024, 1024
CREAM = (246, 240, 224)
PAPER2 = (238, 230, 208)
INK = (18, 15, 11)
RED = (178, 32, 26)
RED_DK = (140, 22, 18)
TEAL = (38, 110, 108)
BLUE = (42, 82, 128)
GREY = (110, 104, 92)
RULE = (60, 52, 44)

# ---------------------------------------------------------------- PNG out
def write_png(path, buf, w, h):
    def chunk(typ, data):
        c = struct.pack(">I", len(data)) + typ + data
        return c + struct.pack(">I", zlib.crc32(typ + data) & 0xffffffff)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw += buf[y * stride:(y + 1) * stride]
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)

# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.buf = bytearray(w * h * 3)
        self.rect(0, 0, w, h, bg)

    def _set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i:i + 3] = bytes(c)

    def rect(self, x0, y0, x1, y1, c):
        x0 = max(0, int(x0)); y0 = max(0, int(y0))
        x1 = min(self.w, int(x1)); y1 = min(self.h, int(y1))
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for y in range(y0, y1):
            i = (y * self.w + x0) * 3
            self.buf[i:i + len(row)] = row

    def hline(self, x0, x1, y, c, t=1):
        self.rect(x0, y, x1, y + t, c)

    def vline(self, x, y0, y1, c, t=1):
        self.rect(x, y0, x + t, y1, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx = x1 - x0; dy = y1 - y0
        steps = max(abs(dx), abs(dy), 1)
        for i in range(steps + 1):
            x = int(round(x0 + dx * i / steps))
            y = int(round(y0 + dy * i / steps))
            self.rect(x - t // 2, y - t // 2, x + t // 2 + 1, y + t // 2 + 1, c)

    def circle(self, cx, cy, r, c, fill=True):
        for y in range(int(cy - r), int(cy + r) + 1):
            dy = y - cy
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            if fill:
                self.rect(cx - dx, y, cx + dx + 1, y + 1, c)
            else:
                self._set(cx - dx, y, c); self._set(cx + dx, y, c)

    def ellipse(self, cx, cy, rx, ry, c):
        for y in range(int(cy - ry), int(cy + ry) + 1):
            dy = (y - cy) / ry
            dx = int(rx * math.sqrt(max(0, 1 - dy * dy)))
            self.rect(cx - dx, y, cx + dx + 1, y + 1, c)

    def poly(self, pts, c):
        """Nonzero-winding scanline fill of one polygon."""
        if len(pts) < 3:
            return
        edges = []
        for i in range(len(pts)):
            x0, y0 = pts[i]; x1, y1 = pts[(i + 1) % len(pts)]
            if y0 == y1:
                continue
            d = 1 if y0 < y1 else -1
            if y0 > y1:
                x0, y0, x1, y1 = x1, y1, x0, y0
            edges.append((y0, y1, x0, (x1 - x0) / (y1 - y0), d))
        if not edges:
            return
        ymin = max(0, int(math.floor(min(e[0] for e in edges))))
        ymax = min(self.h, int(math.ceil(max(e[1] for e in edges))))
        for y in range(ymin, ymax):
            yc = y + 0.5
            xs = []
            for (y0, y1, x0, dx, d) in edges:
                if y0 <= yc < y1:
                    xs.append((x0 + (yc - y0) * dx, d))
            xs.sort()
            w = 0
            for i in range(len(xs) - 1):
                w += xs[i][1]
                if w != 0:
                    xa = int(math.ceil(xs[i][0] - 0.5))
                    xb = int(math.floor(xs[i + 1][0] - 0.5)) + 1
                    if xb > xa:
                        self.rect(max(0, xa), y, min(self.w, xb), y + 1, c)

    def polys(self, plist, c):
        for p in plist:
            self.poly(p, c)

# ------------------------------------------------------- font construction
# Em space: baseline y=0, cap top 72, x-height 52, descender -26.
# Stems: thick 10, thin 5. Serifs: flared trapezoids at stem ends.
def R(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

def arc(cx, cy, rx, ry, a0, a1, n=20):
    pts = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    return pts

def disc(cx, cy, rx, ry, n=28):
    return arc(cx, cy, rx, ry, 0, 360, n)

def band(cx, cy, rx, ry, w, a0, a1, n=24):
    """Annular sector: outer arc + inner arc reversed -> one polygon."""
    outer = arc(cx, cy, rx, ry, a0, a1, n)
    inner = arc(cx, cy, rx - w, ry - w, a1, a0, n)
    return outer + inner

def ring(cx, cy, rx, ry, w, n=28):
    # inner disc wound opposite so nonzero fill leaves the counter empty
    return [disc(cx, cy, rx, ry, n), list(reversed(disc(cx, cy, rx - w, ry - w, n)))]

def crspline(pts, n=10):
    """Catmull-Rom through control points -> sampled polyline."""
    if len(pts) < 2:
        return list(pts)
    ext = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(len(ext) - 3):
        p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
        for j in range(n):
            t = j / n
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t +
                       (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                       (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t +
                       (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                       (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    out.append(pts[-1])
    return out

def ribbon(pts, w):
    """Thick stroke along a polyline -> polygon (miter-ish joins)."""
    hw = w / 2.0
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        if i == 0:
            nx, ny = pts[1][0] - x, pts[1][1] - y
        elif i == len(pts) - 1:
            nx, ny = x - pts[i - 1][0], y - pts[i - 1][1]
        else:
            nx = pts[i + 1][0] - pts[i - 1][0]
            ny = pts[i + 1][1] - pts[i - 1][1]
        L = math.hypot(nx, ny) or 1.0
        nx, ny = -ny / L, nx / L
        left.append((x + nx * hw, y + ny * hw))
        right.append((x - nx * hw, y - ny * hw))
    return left + right[::-1]

def serif(xc, w, y, up=False):
    """Flared serif trapezoid at a stem end (y = baseline of the foot)."""
    h = 6.0
    if up:
        return [(xc - w / 2 - 4, y), (xc + w / 2 + 4, y),
                (xc + w / 2 + 1, y - h), (xc - w / 2 - 1, y - h)]
    return [(xc - w / 2 - 4, y), (xc + w / 2 + 4, y),
            (xc + w / 2 + 1, y + h), (xc - w / 2 - 1, y + h)]

def stem(x, y0, y1, w=10, serifs=True):
    """Vertical stem with bracketed serifs at both ends."""
    polys = [R(x, y0, x + w, y1)]
    if serifs:
        polys.append(serif(x + w / 2, w, y0, up=False))
        polys.append(serif(x + w / 2, w, y1, up=True))
    return polys

def bar(x0, x1, y, t=5, serifs=False):
    """Horizontal bar (thin stroke)."""
    polys = [R(x0, y, x1, y + t)]
    if serifs:
        polys.append([(x0, y - 2), (x0 + 4, y - 2), (x0 + 2, y + t + 2), (x0 - 2, y + t + 2)])
        polys.append([(x1 - 4, y - 2), (x1, y - 2), (x1 + 2, y + t + 2), (x1 - 2, y + t + 2)])
    return polys

CAP = 72.0
XH = 52.0
# glyph: (advance, [polygons])
G = {}

def glyph(ch, adv, polys):
    G[ch] = (adv, polys)

# ---- caps A-Z (advance, polygons); em 100 wide, cap top 72
glyph('A', 62, stem(6, 0, 72, 10, False) + [R(6, 0, 16, 10)] +
      [R(46, 0, 56, 10)] +
      [ribbon(crspline([(11, 4), (24, 56), (31, 72), (38, 56), (51, 4)], 8), 9)] +
      bar(20, 42, 26, 5) + [R(4, 0, 18, 4), R(44, 0, 58, 4)])
glyph('B', 58, stem(6, 0, 72) +
      [band(33, 52, 25, 20, 9, -90, 90, 18), band(35, 20, 27, 20, 9, -90, 90, 18)] +
      bar(6, 34, 67, 5) + bar(6, 50, 34, 5) + bar(6, 38, 0, 5))
glyph('C', 58, [band(32, 36, 27, 36, 10, 55, 305, 26)] +
      [R(52, 50, 59, 58), R(52, 14, 59, 22)])
glyph('D', 62, stem(6, 0, 72) +
      [band(30, 36, 30, 36, 10, -90, 90, 22)] +
      bar(6, 34, 67, 5) + bar(6, 34, 0, 5))
glyph('E', 54, stem(6, 0, 72) +
      bar(6, 52, 67, 5) + bar(6, 32, 33, 5) + bar(6, 52, 0, 5))
glyph('F', 52, stem(6, 0, 72) +
      bar(6, 50, 67, 5) + bar(6, 34, 33, 5))
glyph('G', 62, [band(32, 36, 27, 36, 10, 50, 310, 26)] +
      [R(32, 26, 58, 31), R(48, 26, 58, 44), R(52, 40, 59, 48)])
glyph('H', 62, stem(6, 0, 72) + stem(46, 0, 72) + bar(16, 46, 33, 6))
glyph('I', 30, stem(10, 0, 72))
glyph('J', 48, [band(26, 20, 22, 20, 9, 180, 360, 16)] +
      stem(38, 16, 72, 10, False) + [R(30, 66, 48, 72)] + bar(28, 48, 67, 5))
glyph('K', 58, stem(6, 0, 72) +
      [ribbon(crspline([(13, 34), (34, 52), (48, 70)], 6), 9),
       ribbon(crspline([(26, 40), (40, 18), (50, 2)], 6), 9)])
glyph('L', 52, stem(6, 0, 72) + bar(6, 50, 0, 5))
glyph('M', 72, stem(4, 0, 72) + stem(58, 0, 72) +
      [ribbon(crspline([(12, 72), (40, 22)], 2), 8),
       ribbon(crspline([(32, 22), (60, 72)], 2), 8)] +
      [R(14, 66, 22, 72), R(50, 66, 58, 72)])
glyph('N', 64, stem(4, 0, 72) + stem(50, 0, 72) +
      [ribbon(crspline([(14, 68), (50, 4)], 2), 8)])
glyph('O', 62, ring(31, 36, 27, 36, 10))
glyph('P', 56, stem(6, 0, 72) +
      [band(31, 52, 23, 20, 9, -90, 90, 18)] +
      bar(6, 32, 67, 5) + bar(6, 46, 32, 5))
glyph('Q', 62, ring(31, 36, 27, 36, 10) +
      [ribbon(crspline([(44, 14), (54, 2), (60, -4)], 4), 8)])
glyph('R', 58, stem(6, 0, 72) +
      [band(31, 52, 23, 20, 9, -90, 90, 18)] +
      bar(6, 32, 67, 5) + bar(6, 46, 32, 5) +
      [ribbon(crspline([(28, 34), (42, 14), (52, 2)], 6), 9)])
glyph('S', 56, [ribbon(crspline([(44, 64), (34, 72), (18, 70), (12, 58),
                                  (16, 46), (30, 40), (42, 34), (46, 22),
                                  (40, 8), (26, 4), (14, 10)], 12), 9)])
glyph('T', 56, bar(4, 54, 67, 5, True) + stem(23, 0, 67, 10))
glyph('U', 62, stem(6, 16, 72, 10, False) + stem(46, 16, 72, 10, False) +
      [band(31, 16, 25, 16, 10, 180, 360, 18)] +
      [R(6, 66, 16, 72), R(46, 66, 56, 72)])
glyph('V', 60, [ribbon(crspline([(8, 72), (31, 2)], 2), 10),
                ribbon(crspline([(52, 72), (29, 2)], 2), 10)] +
      [R(4, 66, 14, 72), R(46, 66, 56, 72)])
glyph('W', 84, [ribbon(crspline([(6, 72), (25, 0)], 2), 9),
                ribbon(crspline([(19, 0), (40, 56)], 2), 9),
                ribbon(crspline([(40, 56), (61, 0)], 2), 9),
                ribbon(crspline([(55, 0), (76, 72)], 2), 9)] +
      [R(2, 66, 12, 72), R(70, 66, 80, 72)])
glyph('X', 58, [ribbon(crspline([(10, 72), (48, 2)], 2), 9),
                ribbon(crspline([(48, 72), (10, 2)], 2), 9)])
glyph('Y', 58, [ribbon(crspline([(8, 72), (29, 36)], 2), 9),
                ribbon(crspline([(50, 72), (29, 36)], 2), 9)] +
      stem(24, 0, 36, 10, False) + [R(4, 66, 14, 72), R(44, 66, 54, 72)])
glyph('Z', 56, bar(6, 54, 67, 5, True) + bar(6, 54, 0, 5, True) +
      [ribbon(crspline([(50, 67), (10, 5)], 2), 8)])

# ---- digits
glyph('0', 56, ring(28, 36, 24, 36, 9) +
      [ribbon(crspline([(20, 66), (36, 6)], 2), 6)])
glyph('1', 32, stem(15, 0, 72, 10, False) +
      [ribbon(crspline([(3, 48), (8, 60), (15, 72)], 6), 8), R(4, 0, 27, 6)])
glyph('2', 56, [ribbon(crspline([(10, 48), (14, 64), (30, 70), (44, 62),
                                  (46, 48), (34, 30), (14, 8), (8, 2)], 12), 9)] +
      bar(8, 48, 0, 5))
glyph('3', 56, [band(30, 52, 22, 18, 9, -80, 100, 16),
                band(32, 20, 24, 20, 9, -80, 100, 16)])
glyph('4', 56, [ribbon(crspline([(40, 72), (14, 22), (48, 22)], 2), 8)] +
      stem(36, 0, 72, 10, False))
glyph('5', 56, bar(10, 48, 67, 5) + stem(10, 38, 67, 9, False) +
      [band(30, 20, 24, 20, 9, -100, 80, 18)])
glyph('6', 56, [ribbon(crspline([(46, 66), (30, 72), (14, 62), (10, 42),
                                  (12, 22), (24, 8), (38, 12), (44, 26),
                                  (40, 38), (28, 40), (18, 34)], 14), 9)])
glyph('7', 54, bar(8, 50, 67, 5, True) +
      [ribbon(crspline([(44, 67), (24, 20), (18, 2)], 4), 9)])
glyph('8', 56, ring(28, 52, 21, 18, 9) + ring(28, 20, 23, 20, 9))
glyph('9', 56, [ribbon(crspline([(10, 10), (26, 2), (42, 10), (46, 28),
                                  (44, 48), (32, 62), (16, 60), (10, 48),
                                  (12, 36)], 12), 9)] +
      stem(40, 0, 34, 9, False))

# ---- lowercase (x-height 52, descender -26)
def low_arch(x, y0=0, y1=52, w=9):
    """n/m arch: left stem + top curve + right stem."""
    return ([R(x, y0, x + w, y1)] +
            [band(x + w + 11, y1 - 13, 15, 13, w, 0, 180, 14),
             R(x + w + 22 - 2, y0, x + w + 22 + w - 2, y1 - 6)] +
            [serif(x + w / 2, w, y0), serif(x + 2 * w + 20, w, y0)])

glyph('a', 48, ring(24, 37, 8, 7, 4) + ring(23, 16, 16, 14, 8) +
      stem(36, 0, 52, 9, False) + [R(36, 47, 45, 52)] +
      [ribbon(crspline([(41, 9), (46, 3), (48, 5)], 4), 4)])
glyph('b', 48, stem(6, 0, 72, 10, False) +
      [band(28, 26, 20, 26, 9, -90, 90, 18)] + bar(6, 28, 0, 5))
glyph('c', 46, [band(25, 26, 20, 26, 9, 50, 310, 22)] +
      [R(40, 36, 46, 44), R(40, 8, 46, 16)])
glyph('d', 48, ring(24, 26, 20, 26, 9) + stem(38, 0, 72, 9, False) +
      [R(38, 66, 47, 72)])
glyph('e', 46, [band(25, 26, 20, 26, 9, 15, 345, 22),
                R(5, 26, 45, 31)] +
      [R(38, 26, 46, 36)])
glyph('f', 34, [ribbon(crspline([(14, 0), (14, 30), (16, 52), (22, 66),
                                  (30, 70), (36, 64)], 10), 8)] +
      bar(6, 38, 46, 5) + [R(28, 62, 40, 70)])
glyph('g', 48, ring(24, 26, 20, 26, 9) +
      [ribbon(crspline([(40, 26), (40, -6), (34, -20), (22, -24),
                        (12, -18)], 8), 8)] + [R(34, 2, 46, 8)])
glyph('h', 48, stem(6, 0, 72, 10, False) +
      [band(28, 39, 14, 13, 9, 0, 180, 14), R(38, 0, 47, 40)] +
      [serif(42, 9, 0), R(6, 66, 16, 72)])
glyph('i', 24, stem(8, 0, 52, 9, False) + [disc(12, 64, 5, 5)])
glyph('j', 24, [ribbon(crspline([(12, 52), (12, 0), (10, -16), (4, -22)], 8), 8)] +
      [disc(12, 64, 5, 5)])
glyph('k', 48, stem(6, 0, 72, 10, False) +
      [ribbon(crspline([(15, 30), (30, 44), (42, 52)], 4), 8),
       ribbon(crspline([(28, 32), (36, 14), (44, 0)], 4), 8)])
glyph('l', 24, stem(8, 0, 72, 9, False))
glyph('m', 72, stem(5, 0, 52, 9, False) +
      [band(27, 39, 14, 13, 9, 0, 180, 14), R(37, 0, 46, 40)] +
      [band(50, 39, 14, 13, 9, 0, 180, 14), R(60, 0, 69, 40)] +
      [serif(9, 9, 0), serif(41, 9, 0), serif(64, 9, 0)])
glyph('n', 48, stem(6, 0, 52, 9, False) +
      [band(28, 39, 14, 13, 9, 0, 180, 14), R(38, 0, 47, 40)] +
      [serif(10, 9, 0), serif(42, 9, 0)])
glyph('o', 48, ring(24, 26, 20, 26, 9))
glyph('p', 48, ring(24, 26, 20, 26, 9) + stem(6, -26, 52, 9, False))
glyph('q', 48, ring(24, 26, 20, 26, 9) + stem(38, -26, 52, 9, False))
glyph('r', 34, stem(6, 0, 52, 9, False) +
      [band(23, 39, 11, 13, 8, -45, 180, 14)])
glyph('s', 44, [ribbon(crspline([(36, 46), (28, 52), (16, 50), (12, 42),
                                  (16, 34), (28, 30), (36, 24), (38, 14),
                                  (32, 6), (20, 4), (12, 10)], 12), 8)])
glyph('t', 32, stem(11, 0, 64, 9, False) + bar(4, 30, 40, 5) +
      [ribbon(crspline([(11, 0), (14, -6), (20, -8)], 4), 7),
       R(11, 58, 20, 64)])
glyph('u', 48, stem(6, 16, 52, 9, False) + stem(33, 0, 52, 9, False) +
      [band(24, 16, 18, 16, 9, 180, 360, 16)] +
      [serif(10, 9, 52, True), serif(37, 9, 0)])
glyph('v', 46, [ribbon(crspline([(6, 52), (26, 0)], 2), 9),
                ribbon(crspline([(40, 52), (20, 0)], 2), 9)])
glyph('w', 66, [ribbon(crspline([(4, 52), (19, 0)], 2), 8),
                ribbon(crspline([(13, 0), (30, 40)], 2), 8),
                ribbon(crspline([(30, 40), (47, 0)], 2), 8),
                ribbon(crspline([(41, 0), (58, 52)], 2), 8)])
glyph('x', 46, [ribbon(crspline([(8, 52), (38, 2)], 2), 8),
                ribbon(crspline([(38, 52), (8, 2)], 2), 8)])
glyph('y', 46, [ribbon(crspline([(6, 52), (26, 0)], 2), 9),
                ribbon(crspline([(40, 52), (20, 0)], 2), 9)] +
      [ribbon(crspline([(23, 8), (18, -14), (8, -22)], 6), 8)])
glyph('z', 44, bar(6, 42, 47, 5) + bar(6, 42, 0, 5) +
      [ribbon(crspline([(38, 47), (8, 5)], 2), 7)])

# ---- punctuation & symbols
glyph('.', 22, [R(8, 0, 15, 7)])
glyph(',', 22, [R(8, 0, 15, 7), ribbon(crspline([(11, 0), (8, -8), (4, -12)], 4), 6)])
glyph(':', 22, [R(8, 28, 15, 35), R(8, 0, 15, 7)])
glyph(';', 22, [R(8, 28, 15, 35), R(8, 0, 15, 7),
                ribbon(crspline([(11, 0), (8, -8), (4, -12)], 4), 6)])
glyph("'", 18, [ribbon(crspline([(10, 72), (7, 58)], 2), 6)])
glyph('"', 30, [ribbon(crspline([(8, 72), (5, 58)], 2), 6),
                ribbon(crspline([(22, 72), (19, 58)], 2), 6)])
glyph('-', 30, bar(6, 26, 24, 5))
glyph('–', 40, bar(4, 36, 24, 5))
glyph('—', 52, bar(2, 50, 24, 5))
glyph('(', 28, [band(22, 36, 16, 36, 8, 90, 270, 18)])
glyph(')', 28, [band(6, 36, 16, 36, 8, -90, 90, 18)])
glyph('/', 30, [ribbon(crspline([(6, 0), (24, 72)], 2), 7)])
glyph('&', 56, [ribbon(crspline([(40, 56), (30, 66), (16, 62), (12, 50),
                                  (20, 38), (34, 30), (44, 18), (40, 4),
                                  (28, 0), (16, 8)], 12), 8)] +
      [ribbon(crspline([(12, 50), (30, 22), (44, 4)], 3), 7)])
glyph('%', 66, ring(16, 52, 13, 13, 7) + ring(50, 20, 13, 13, 7) +
      [ribbon(crspline([(14, 4), (52, 68)], 2), 7)])
glyph('$', 56, [ribbon(crspline([(40, 60), (30, 68), (16, 64), (12, 52),
                                  (20, 42), (36, 36), (44, 26), (38, 12),
                                  (24, 8), (12, 14)], 12), 8)] +
      stem(24, -6, 74, 7, False))
glyph('!', 22, stem(8, 24, 72, 9, False) + [R(8, 0, 15, 7)])
glyph('?', 48, [ribbon(crspline([(12, 44), (12, 58), (24, 70), (38, 68),
                                  (44, 56), (40, 44), (28, 36), (24, 28)], 10), 8)] +
      [R(20, 0, 27, 7)])
glyph('·', 20, [disc(10, 30, 4, 4)])
glyph('+', 40, [R(16, 28, 24, 60), R(4, 36, 36, 44)])
glyph('◆', 40, [R(20, 72, 20, 72)] +
      [[(20, 62), (30, 46), (20, 30), (10, 46)]])
glyph('●', 40, [disc(20, 42, 14, 14)])
glyph('○', 40, ring(20, 42, 14, 14, 5))
glyph('◇', 40, [[(20, 62), (32, 42), (20, 22), (8, 42)],
                list(reversed([(20, 56), (27, 42), (20, 28), (13, 42)]))])
glyph(' ', 22, [])

# ------------------------------------------------------- text rendering
def glyph_polys(ch, scale, ox, oy, shear=0.0):
    """Scale glyph polygons into pixel space; oy = baseline y (pixels).
    Embolden: shifted copies thicken stems (+x) and bars (+y) by ~1.6 units."""
    adv, polys = G.get(ch, G.get('?', (48, [])))
    out = []
    for p in polys:
        q = []
        for (x, y) in p:
            X = ox + x * scale
            Y = oy - y * scale
            if shear:
                X += shear * (oy - Y)
            q.append((X, Y))
        out.append(q)
        out.append([(X + 1.6 * scale, Y) for (X, Y) in q])
        out.append([(X, Y + 1.6 * scale) for (X, Y) in q])
    return adv * scale, out

def text_width(s, size):
    scale = size / CAP
    return sum(G.get(ch, G.get('?', (48, [])))[0] * scale for ch in s)

def _fill_tile(tile, tw, th, polys):
    """Nonzero-winding scanline fill of polygons into a grayscale tile."""
    edges = []
    for p in polys:
        for i in range(len(p)):
            x0, y0 = p[i]; x1, y1 = p[(i + 1) % len(p)]
            if y0 == y1:
                continue
            d = 1 if y0 < y1 else -1
            if y0 > y1:
                x0, y0, x1, y1 = x1, y1, x0, y0
            edges.append((y0, y1, x0, (x1 - x0) / (y1 - y0), d))
    if not edges:
        return
    ymin = max(0, int(math.floor(min(e[0] for e in edges))))
    ymax = min(th, int(math.ceil(max(e[1] for e in edges))))
    for y in range(ymin, ymax):
        yc = y + 0.5
        xs = []
        for (y0, y1, x0, dx, d) in edges:
            if y0 <= yc < y1:
                xs.append((x0 + (yc - y0) * dx, d))
        xs.sort()
        w = 0
        for i in range(len(xs) - 1):
            w += xs[i][1]
            if w != 0:
                xa = int(math.ceil(xs[i][0] - 0.5))
                xb = int(math.floor(xs[i + 1][0] - 0.5)) + 1
                xa = max(0, xa); xb = min(tw, xb)
                if xb > xa:
                    tile[y * tw + xa:y * tw + xb] = b"\xff" * (xb - xa)

def draw_text(cv, x, y, s, size, color, align="left", shear=0.0, tracking=0.0):
    """Draw string s with baseline at y. 2x-supersampled glyphs -> AA text."""
    scale = size / CAP
    total = text_width(s, size) + tracking * max(0, len(s) - 1)
    if align == "center":
        x -= total / 2
    elif align == "right":
        x -= total
    cx = x
    for ch in s:
        adv, polys = glyph_polys(ch, scale, cx, y, shear)
        if polys:
            xs = [p[0] for poly in polys for p in poly]
            ys = [p[1] for poly in polys for p in poly]
            gx0, gx1 = int(math.floor(min(xs))), int(math.ceil(max(xs)))
            gy0, gy1 = int(math.floor(min(ys))), int(math.ceil(max(ys)))
            tw, th = (gx1 - gx0) * 2 + 4, (gy1 - gy0) * 2 + 4
            tile = bytearray(tw * th)
            sp = [[(px * 2 - gx0 * 2 + 2, py * 2 - gy0 * 2 + 2) for (px, py) in poly]
                  for poly in polys]
            _fill_tile(tile, tw, th, sp)
            # downsample 2x2 -> composite
            ow, oh = tw // 2, th // 2
            for ty in range(oh):
                sy = ty * 2
                for tx in range(ow):
                    sx = tx * 2
                    a = (tile[sy * tw + sx] + tile[sy * tw + sx + 1] +
                         tile[(sy + 1) * tw + sx] + tile[(sy + 1) * tw + sx + 1] + 2) // 4
                    if a == 0:
                        continue
                    px, py = gx0 - 1 + tx, gy0 - 1 + ty
                    if 0 <= px < cv.w and 0 <= py < cv.h:
                        i = (py * cv.w + px) * 3
                        if a >= 255:
                            cv.buf[i:i + 3] = bytes(color)
                        else:
                            for k in range(3):
                                cv.buf[i + k] = (color[k] * a + cv.buf[i + k] * (255 - a)) // 255
        cx += adv + tracking
    return total

def wrap_text(s, size, maxw, tracking=0.0):
    words = s.split(" ")
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if text_width(t, size) + tracking * max(0, len(t) - 1) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

def draw_lines(cv, lines, x, y, size, color, lh, align="left", shear=0.0):
    for ln in lines:
        draw_text(cv, x, y, ln, size, color, align=align, shear=shear)
        y += lh
    return y

# ------------------------------------------------------- the broadsheet
# ------------------------------------------------------- big Bahrain lead
def draw_bahrain_big(cv, x0, y0, x1, y1):
    # Full-width Gulf schematic with big, unambiguous landmasses (v3
    # skeleton): Iran top-right, Saudi bottom-left, Qatar peninsula,
    # Bahrain island + blast, tanker in the strait.
    cv.rect(x0, y0, x1, y1, (191, 217, 232))
    tan = (232, 217, 184)
    # Iran — big landmass, top-right
    cv.poly([(x0 + 520, y0), (x1, y0), (x1, y0 + 62), (x0 + 830, y0 + 74),
             (x0 + 720, y0 + 58), (x0 + 610, y0 + 38)], tan)
    # Saudi Arabia — big landmass, bottom-left
    cv.poly([(x0, y0 + 58), (x0 + 300, y0 + 52), (x0 + 390, y0 + 66),
             (x0 + 370, y1), (x0, y1)], tan)
    # Qatar peninsula, jutting north from Saudi
    cv.poly([(x0 + 390, y0 + 52), (x0 + 428, y0 + 46), (x0 + 440, y0 + 72),
             (x0 + 408, y0 + 78)], tan)
    # UAE / Oman — bottom-right
    cv.poly([(x0 + 830, y0 + 74), (x1, y0 + 62), (x1, y1), (x0 + 920, y1),
             (x0 + 880, y0 + 88)], tan)
    draw_text(cv, x0 + 860, y0 + 26, "IRAN", 12, (90, 80, 66))
    draw_text(cv, x0 + 60, y0 + 92, "SAUDI ARABIA", 11, (90, 80, 66))
    draw_text(cv, x0 + 396, y0 + 60, "QATAR", 10, (90, 80, 66))
    draw_text(cv, x0 + 890, y0 + 78, "U.A.E.", 10, (90, 80, 66))
    draw_text(cv, x0 + 950, y0 + 100, "OMAN", 10, (90, 80, 66))
    draw_text(cv, x0 + 560, y0 + 92, "THE GULF", 11, (60, 60, 60))
    draw_text(cv, x0 + 430, y0 + 34, "BAHRAIN", 11, (140, 22, 18))
    bx, by = x0 + 480, y0 + 52
    cv.ellipse(bx, by, 11, 7, tan)
    star(cv, bx, by, 11, RED)
    cv.circle(bx, by, 15, RED, fill=False)
    draw_text(cv, x0 + 505, y0 + 72, "SITE ON FIRE", 11, RED)
    cv.rect(x0 + 760, y0 + 30, x0 + 862, y0 + 40, (30, 30, 30))
    cv.rect(x0 + 779, y0 + 23, x0 + 808, y0 + 30, (30, 30, 30))
    draw_text(cv, x0 + 740, y0 + 56, "TANKER HIT", 11, RED)
    dashed(cv, x0 + 720, y0 + 40, bx + 25, by - 6, RED)
    dashed(cv, x0 + 760, y0 + 38, bx + 30, by + 4, RED)

def main():
    cv = Canvas(W, H, CREAM)
    X0, X1 = 14, 1010

    # top strip (Reference A)
    draw_text(cv, X0, 18, "THE WORLD IN ONE DAY · EVERY STORY FROM THIS "
              "DAY, IN ANY TIME ZONE", 10, INK)
    draw_text(cv, X1, 18, "37 STORIES · 9 REGIONS · 16 FIELDS", 10, RED,
              align="right")
    cv.hline(X0, X1, 24, INK, 2)

    # masthead — v8 font untouched; red date box at the right (Reference A)
    draw_fit(cv, "Saturday 21 November 2026", X0, X1 - 150, 98, 76, INK)
    cv.rect(X1 - 138, 38, X1, 104, RED)
    draw_text(cv, X1 - 69, 70, "SAT 21", 20, (255, 255, 255), align="center")
    draw_text(cv, X1 - 69, 94, "NOV", 20, (255, 255, 255), align="center")
    cv.hline(X0, X1, 112, INK, 2)

    # tagline (Reference A)
    draw_fit(cv, "Iran strikes Bahrain · Mexico captures 'El Chapo Isidro' "
             "· COP31 talks run into overtime", X0, X1, 134, 15, INK,
             shear=0.18)
    cv.hline(X0, X1, 142, INK, 1)

    # ---- timeline: THE DAY IN UTC — one clean row, labels 11px, no
    # overlaps (v9's labels collided with the box and each other)
    cv.rect(X0, 150, X0 + 108, 166, INK)
    draw_text(cv, X0 + 54, 162, "THE DAY IN UTC", 10, (255, 255, 255), align="center")
    ax0, ax1, ay = X0 + 118, X1 - 4, 170
    cv.hline(ax0, ax1, ay, INK, 2)
    pins = [(0.15, "00:09 Peru", True, 185),
            (2.0, "02:00 Sinaloa", False, 215),
            (5.0, "05:00 Tanker", True, 330),
            (18.4, "18:24 Mercury", False, 790),
            (19.7, "19:44 Bahrain", True, 860),
            (22.0, "22:00 COP31", False, 940)]
    for hr, label, above, lx in pins:
        px = ax0 + hr / 24 * (ax1 - ax0)
        cv.circle(px, ay, 4, RED)
        draw_text(cv, lx, 158 if above else 188, label, 11, INK, align="center")
        cv.line(px, ay - 6, px, ay + 6, RED, 2)

    # ---- numbers strip — bigger numbers, 2-line captions only
    nums = [("6.7", "quake magnitude, 108 km under central Peru (USGS)"),
            ("11", "killed in Sinaloa as 'El Chapo Isidro' is caught (AP)"),
            ("$55,100", "Bitcoin's low, lowest since September 2024 (COINBASE)"),
            ("82,500", "marched in France over living costs (ministry)"),
            ("128", "states in Geneva agree to work on AI-weapon rules (UN)")]
    ny = 200
    for i, (n, lab) in enumerate(nums):
        cx = X0 + i * 199
        if i:
            cv.vline(cx, ny, ny + 50, (200, 192, 176), 1)
        draw_text(cv, cx + 99, ny + 26, n, 28, INK, align="center")
        for j, ln in enumerate(wrap_text(lab, 10.5, 188)[:2]):
            draw_text(cv, cx + 99, ny + 40 + j * 12, ln, 10.5, (90, 80, 66),
                      align="center")

    # ---- region bar (Reference A: 9 named regions, equal segments)
    cv.rect(X0, 256, X0 + 136, 272, INK)
    draw_text(cv, X0 + 68, 268, "STORIES BY REGION", 10, (255, 255, 255), align="center")
    regs = [("EUROPE", "Europe"), ("MID. EAST", "Middle East"),
            ("S. ASIA", "South Asia"), ("E. ASIA", "East Asia"),
            ("SE ASIA", "SE Asia"), ("AFRICA", "Africa"),
            ("N. AMERICA", "N. America"), ("LATIN AM.", "Latin Am."),
            ("OCEANIA", "Oceania")]
    rx = X0 + 136
    seg = (X1 - rx) / len(regs)
    for label, key in regs:
        cv.rect(rx, 256, min(rx + seg, X1), 272, REG_COL[key])
        draw_text(cv, rx + seg / 2, 268, label, 8, (255, 255, 255),
                  align="center")
        rx += seg

    # ---- BIG LEAD: Bahrain full-width (v3 skeleton) — the day's biggest
    # story owns the whole width, one-line headline, one-line body
    draw_bahrain_big(cv, X0, 280, X1, 384)
    kicker(cv, X0, 396, "1", "BAHRAIN / HORMUZ · WAR", "Middle East", "CLAIM", X1)
    draw_text(cv, X0, 430, "Bahrain: Iran struck it; tanker hit off Oman", 28, INK)
    draw_text(cv, X0, 454,
              "A site ablaze, Bahrain says; UKMTO: a tanker struck 11 nm off "
              "Khasab. (BAHRAIN, UKMTO)", 12, (60, 54, 44))

    # ---- Mexico + COP31: half-width panels, diagram on top, one-line
    # headline + body (diagrams reuse the v9 draw functions)
    draw_mexico(cv, X0, 460, X0 + 490, 544)
    cv.poly([(X0 + 346, 520), (X0 + 406, 514), (X0 + 436, 526),
             (X0 + 406, 534), (X0 + 356, 530)], (232, 217, 184))
    draw_text(cv, X0 + 380, 540, "GULF OF MEXICO", 8, (60, 60, 60))
    kicker(cv, X0, 556, "2", "GUASAVE, SINALOA · CRIME", "N. America",
           "CONFIRMED", X0 + 490)
    draw_text(cv, X0, 578, "Mexico captures 'El Chapo Isidro'; 11 die", 19, INK)
    draw_text(cv, X0, 598,
              "Troops seize Meza Flores; 4 soldiers, 7 gunmen killed. "
              "(PBS, AL JAZEERA)", 11, (60, 54, 44))
    mx0 = X0 + 506
    draw_cop31(cv, mx0, 460, X1, 544)
    draw_text(cv, mx0 + 244, 508, "NO DEAL — DAY 13", 12, RED)
    kicker(cv, mx0, 556, "3", "ANTALYA · CLIMATE", "Europe", "CONFIRMED", X1)
    draw_text(cv, mx0, 578, "COP31 climate talks run into overtime", 19, INK)
    draw_text(cv, mx0, 598,
              "Talks run past Friday's deadline; approval session due "
              "Sunday 06:00 GMT. (AFP, AP)", 11, (60, 54, 44))

    # ---- grid 4-13 — taller cards, bigger headlines (15px), one-line
    # bodies; dengue corrected to the published 71% (NEJM)
    cards = [
        ("quake", "4", "PERU · QUAKE", "Latin Am.", "OFFICIAL",
         "Deep 6.7 quake shakes Peru",
         "M6.7, 108 km deep. (USGS)"),
        ("sparta", "5", "FINLAND · CONFLICT", "Europe", "CONFIRMED",
         "Drones hit Russian cargo ship",
         "16 crew evacuated. (YLE, AP)"),
        ("robot", "6", "GENEVA · ARMS", "Europe", "CONFIRMED",
         "Deal to draft killer-robot rules",
         "128 states; draft by 2028. (DW)"),
        ("flags", "7", "BRUSSELS · TRADE", "Europe", "CONFIRMED",
         "EU and Indonesia sign trade pact",
         "Lifts 98.5% of tariffs. (DW, ANTARA)"),
        ("bitcoin", "8", "CRYPTO · BITCOIN", "N. America", "CONFIRMED",
         "Bitcoin dives, then rebounds",
         "Low $55,100; rebounded. (COINBASE)"),
        ("mercury", "9", "SPACE · MERCURY", "Europe", "OFFICIAL",
         "Mercury probe fires its orbit burn",
         "BepiColombo's 37-minute burn. (ESA)"),
        ("fire", "10", "BASRA · FIRE", "Middle East", "CONFIRMED",
         "Power-plant fire kills 4 in Basra",
         "Hartha station blaze; 30 hurt. (REUTERS)"),
        ("dengue", "11", "BRAZIL · HEALTH", "Latin Am.", "REPORTED",
         "Trial: mosquitoes cut dengue 71%",
         "Wolbachia trial; 71% fewer cases. (NEJM)"),
        ("jets", "12", "TAIWAN · MILITARY", "East Asia", "OFFICIAL",
         "Chinese jets cross the median line",
         "21 jets; 15 crossed. (TAIWAN MND)"),
        ("vote", "13", "NIGERIA · SPORT", "Africa", "OFFICIAL",
         "CAF's 54 nations back Infantino",
         "All 54 back re-election bid. (CAF)"),
    ]
    for i, (code, num, kick, region, bd, head, body) in enumerate(cards):
        cx = X0 + (i % 5) * 201
        cy = 606 + (i // 5) * 96
        cw = 193
        cv.rect(cx, cy, cx + cw, cy + 96, (255, 253, 246))
        cv.hline(cx, cx + cw, cy, (210, 202, 186), 1)
        cv.hline(cx, cx + cw, cy + 95, (210, 202, 186), 1)
        cv.vline(cx, cy, cy + 96, (210, 202, 186), 1)
        cv.vline(cx + cw - 1, cy, cy + 96, (210, 202, 186), 1)
        pic(cv, cx + 1, cy + 1, cw - 2, 36, code)
        kicker(cv, cx + 4, cy + 47, num, kick, region, bd, cx + cw - 4)
        for j, ln in enumerate(wrap_text(head, 15, cw - 8)):
            draw_text(cv, cx + 4, cy + 65 + j * 17, ln, 15, INK)
        bsize = 9.5
        while text_width(body, bsize) > cw - 8 and bsize > 8.0:
            bsize -= 0.5
        draw_text(cv, cx + 4, cy + 91, body, bsize, (90, 80, 66))

    # ---- bottom band: map + ticker, 2 columns (3 columns overflowed:
    # the serif runs ~5.5px/char at 9.5px, wider than the column)
    draw_text(cv, X0, 804, "WHERE IT HAPPENED", 11, INK)
    draw_text(cv, 330, 804, "pins 1–13 numbered; dots = 14–37", 8, (90, 80, 66),
              align="right")
    world_map(cv, X0, 810, 330, 940)
    draw_text(cv, 340, 804, "ALSO ON SATURDAY 21 NOVEMBER 2026", 11, INK)
    draw_text(cv, X1, 804, "24 MORE STORIES", 10, RED, align="right")
    cv.hline(340, X1, 810, INK, 1)
    for i, (n, txt, region) in enumerate(TICKER):
        col = i // 12
        row = i % 12
        tx = 340 + col * 335
        ty = 818 + row * 12
        draw_text(cv, tx, ty, str(n), 9.5, REG_COL[region])
        draw_text(cv, tx + 22, ty, txt, 9.5, INK)

    # ---- DATE CHECK
    cv.rect(X0, 952, X0 + 96, 980, RED)
    draw_text(cv, X0 + 48, 967, "DATE CHECK", 11, (255, 255, 255), align="center")
    draw_text(cv, X0 + 48, 978, "left out on purpose", 7, (255, 255, 255),
              align="center")
    dc = ("Every story here happened, or was first reported, on Saturday "
          "21 November 2026 in some time zone; clock times are UTC. Left "
          "out on purpose: Fri 20 Nov: Russian missiles land in Poland · "
          "Denmark expels Russian attaché · Wall Street tech sell-off · "
          "GTA VI sales record. Sun 22 Nov: Verstappen wins Las Vegas GP · "
          "new COP31 draft · India declare at 720–9. Not yet: COP31 "
          "approval session (Sun 06:00 GMT) · Las Vegas GP race "
          "(Sun 04:00 UTC).")
    for j, ln in enumerate(wrap_text(dc, 9.5, X1 - X0 - 110)):
        draw_text(cv, X0 + 106, 958 + j * 14, ln, 9.5, INK)

    # ---- HOW SURE + footer
    draw_text(cv, X0, 996,
              "HOW SURE:  ◆ CONFIRMED 2+ major outlets  ● OFFICIAL on the "
              "record, agency, ministry, federation  ○ REPORTED one major "
              "outlet  ◇ CLAIM one side says", 9, (90, 80, 66))
    draw_text(cv, 512, 1010,
              "Pictures and map drawn in code · claims attributed · figures "
              "as first reported. Sources: USGS, UKMTO, AFP, Reuters, AP, "
              "BBC, PBS, Al Jazeera, DW, ESA, CAF, Taiwan MND, Coinbase",
              9, (90, 80, 66), align="center")
    cv.hline(X0, X1, 1018, INK, 2)

    out = os.environ.get("MAKEFUN_OUTPUT_DIR", "out")
    os.makedirs(out, exist_ok=True)
    write_png(os.path.join(out, "entry.png"), cv.buf, W, H)
    print("wrote", os.path.join(out, "entry.png"))

# ------------------------------------------------------- layout helpers
REG_COL = {"Europe": (46, 90, 136), "Middle East": (178, 32, 26),
           "N. America": (46, 122, 110), "Latin Am.": (198, 96, 58),
           "Africa": (122, 74, 140),
           "South Asia": (196, 106, 27), "East Asia": (62, 122, 62),
           "SE Asia": (140, 106, 62), "Oceania": (196, 90, 140)}
BADGE_COL = {"CONFIRMED": (46, 122, 62), "OFFICIAL": (46, 90, 136),
             "REPORTED": (120, 114, 100), "CLAIM": (178, 32, 26)}

def fit_size(s, maxsize, maxw):
    lo, hi = 4.0, float(maxsize)
    for _ in range(24):
        mid = (lo + hi) / 2
        if text_width(s, mid) <= maxw:
            lo = mid
        else:
            hi = mid
    return lo

def draw_fit(cv, s, x0, x1, y, maxsize, color, shear=0.0, minsize=6.0):
    size = fit_size(s, maxsize, x1 - x0)
    size = max(size, minsize)
    draw_text(cv, (x0 + x1) / 2, y, s, size, color, align="center", shear=shear)
    return size

def badge(cv, x, y, text, bg):
    w = text_width(text, 8) + 8
    cv.rect(x, y - 9, x + w, y + 2, bg)
    draw_text(cv, x + 4, y, text, 8, (255, 255, 255))
    return w

def kicker(cv, x, y, num, place_field, region, badge_text, right):
    c = REG_COL[region]
    cv.rect(x, y - 10, x + 13, y + 2, c)
    draw_text(cv, x + 6.5, y, str(num), 9, (255, 255, 255), align="center")
    draw_text(cv, x + 17, y, place_field, 9, c)
    bw = text_width(badge_text, 8) + 8
    cv.rect(right - bw, y - 10, right, y + 2, BADGE_COL[badge_text])
    draw_text(cv, right - bw + 4, y, badge_text, 8, (255, 255, 255))

def dashed(cv, x0, y0, x1, y1, c, seg=6, gap=4):
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    n = int(L // (seg + gap))
    for i in range(n + 1):
        t0 = i * (seg + gap) / L
        t1 = min(1.0, (i * (seg + gap) + seg) / L)
        cv.line(int(round(x0 + dx * t0)), int(round(y0 + dy * t0)),
                int(round(x0 + dx * t1)), int(round(y0 + dy * t1)), c, 2)

def star(cv, cx, cy, r, c):
    for k in range(5):
        a1 = math.radians(-90 + k * 72)
        a2 = math.radians(-90 + k * 72 + 36)
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        x2, y2 = cx + r * 0.45 * math.cos(a2), cy + r * 0.45 * math.sin(a2)
        x3, y3 = cx + r * math.cos(a1 + math.radians(72)), cy + r * math.sin(a1 + math.radians(72))
        cv.poly([(x1, y1), (x2, y2), (x3, y3)], c)

def mini_flag(cv, x, y, w, h, cols):
    n = len(cols)
    for i, c in enumerate(cols):
        cv.rect(x + w * i // n, y, x + w * (i + 1) // n, y + h, c)

# ------------------------------------------------------- lead diagrams
def draw_bahrain(cv, x0, y0, x1, y1):
    cv.rect(x0, y0, x1, y1, (191, 217, 232))
    # Iran (top-right land), Saudi (bottom land), Qatar peninsula
    cv.poly([(x0 + 150, y0), (x1, y0), (x1, y0 + 46), (x0 + 210, y0 + 52),
             (x0 + 190, y0 + 30)], (232, 217, 184))
    cv.poly([(x0, y1), (x1, y1), (x1, y0 + 78), (x0 + 250, y0 + 84),
             (x0 + 200, y0 + 96), (x0, y0 + 88)], (232, 217, 184))
    cv.poly([(x0 + 120, y0 + 60), (x0 + 138, y0 + 60), (x0 + 134, y0 + 78),
             (x0 + 122, y0 + 78)], (232, 217, 184))
    # gulf water label + strait
    draw_text(cv, x0 + 8, y0 + 14, "IRAN", 10, (90, 80, 66))
    draw_text(cv, x0 + 8, y0 + 84, "SAUDI ARABIA", 8, (90, 80, 66))
    draw_text(cv, x0 + 150, y0 + 58, "QATAR", 7, (90, 80, 66))
    draw_text(cv, x0 + 250, y0 + 70, "U.A.E.", 7, (90, 80, 66))
    draw_text(cv, x0 + 250, y0 + 82, "OMAN", 7, (90, 80, 66))
    draw_text(cv, x0 + 8, y0 + 44, "BAHRAIN", 8, (140, 22, 18))
    # Bahrain island + blast
    bx, by = x0 + 118, y0 + 48
    cv.ellipse(bx, by, 10, 6, (232, 217, 184))
    star(cv, bx, by, 9, RED)
    cv.circle(bx, by, 13, RED, fill=False)
    # tanker + dashed arrow from Iran
    cv.rect(x0 + 230, y0 + 30, x0 + 262, y0 + 38, (30, 30, 30))
    cv.rect(x0 + 236, y0 + 24, x0 + 244, y0 + 30, (30, 30, 30))
    dashed(cv, x0 + 210, y0 + 22, bx + 12, by - 6, RED)
    dashed(cv, x0 + 262, y0 + 34, bx + 16, by + 2, RED)
    draw_text(cv, x0 + 196, y0 + 14, "STRAIT OF HORMUZ", 7, (60, 60, 60))
    draw_text(cv, x0 + 8, y0 + 74, "THE GULF", 7, (60, 60, 60))
    draw_text(cv, x0 + 52, y0 + 64, "SITE ON FIRE", 7, RED)
    draw_text(cv, x0 + 224, y0 + 48, "TANKER HIT", 7, RED)

def draw_mexico(cv, x0, y0, x1, y1):
    # Gulf of California (left) + Pacific (bottom-left), Mexico in tan
    cv.rect(x0, y0, x1, y1, (191, 217, 232))
    # Baja peninsula (thin strip, west)
    cv.poly([(x0 + 8, y0 + 6), (x0 + 20, y0 + 4), (x0 + 34, y0 + 40),
             (x0 + 30, y0 + 52), (x0 + 18, y0 + 44), (x0 + 6, y0 + 18)],
            (232, 217, 184))
    # mainland Mexico
    cv.poly([(x0 + 36, y0 + 8), (x0 + 190, y0 + 4), (x0 + 210, y0 + 22),
             (x0 + 196, y0 + 44), (x0 + 160, y0 + 52), (x0 + 120, y0 + 66),
             (x0 + 84, y0 + 70), (x0 + 56, y0 + 58), (x0 + 40, y0 + 34)],
            (232, 217, 184))
    # Yucatan bump
    cv.poly([(x0 + 160, y0 + 52), (x0 + 196, y0 + 44), (x0 + 206, y0 + 56),
             (x0 + 188, y0 + 64), (x0 + 166, y0 + 60)], (232, 217, 184))
    # US (top-right, lighter)
    cv.poly([(x0 + 190, y0), (x0 + 318, y0), (x0 + 318, y0 + 18),
             (x0 + 206, y0 + 20), (x0 + 196, y0 + 10)], (214, 206, 188))
    draw_text(cv, x0 + 8, y0 + 80, "PACIFIC", 7, (60, 60, 60))
    draw_text(cv, x0 + 32, y0 + 56, "GULF", 7, (60, 60, 60))
    draw_text(cv, x0 + 96, y0 + 20, "MEXICO", 10, (90, 80, 66))
    draw_text(cv, x0 + 224, y0 + 12, "U.S.", 8, (90, 80, 66))
    # Guasave pin on the Sinaloa coast (west mainland)
    gx, gy = x0 + 62, y0 + 44
    cv.circle(gx, gy, 3, RED)
    star(cv, gx, gy, 9, RED)
    draw_text(cv, gx + 12, gy + 3, "GUASAVE", 8, RED)
    # right column: FBI TOP TEN / CAPTURED / 11 DEAD
    cv.rect(x0 + 214, y0 + 26, x0 + 310, y0 + 42, INK)
    draw_text(cv, x0 + 262, y0 + 38, "FBI TOP TEN", 9, (255, 255, 255),
              align="center")
    cv.rect(x0 + 214, y0 + 46, x0 + 310, y0 + 62, RED)
    draw_text(cv, x0 + 262, y0 + 58, "CAPTURED", 10, (255, 255, 255),
              align="center")
    cv.rect(x0 + 214, y0 + 66, x0 + 310, y0 + 82, INK)
    draw_text(cv, x0 + 262, y0 + 78, "11 DEAD", 10, (255, 255, 255),
              align="center")

def draw_sparta(cv, x0, y0, x1, y1):
    cv.rect(x0, y0, x1, y1, (30, 58, 82))
    cv.rect(x0, y0, x1, y0 + 26, (214, 206, 188))
    draw_text(cv, x0 + 6, y0 + 18, "06:50 UTC", 10, INK)
    draw_text(cv, x0 + 90, y0 + 18, "two drones, crew taken off", 9, (80, 70, 60))
    # Finland inset map (right)
    cv.rect(x1 - 92, y0 + 30, x1 - 8, y0 + 78, (232, 217, 184))
    cv.poly([(x1 - 88, y0 + 34), (x1 - 40, y0 + 34), (x1 - 46, y0 + 74),
             (x1 - 84, y0 + 74)], (200, 210, 220))
    draw_text(cv, x1 - 86, y0 + 44, "FINLAND", 7, (60, 60, 60))
    draw_text(cv, x1 - 60, y0 + 70, "ESTONIA", 6, (60, 60, 60))
    draw_text(cv, x1 - 44, y0 + 52, "RUSSIA", 6, (60, 60, 60))
    cv.circle(x1 - 70, y0 + 56, 3, RED)
    # ship hull
    hy = y0 + 82
    cv.poly([(x0 + 10, hy), (x0 + 210, hy), (x0 + 196, hy + 22),
             (x0 + 24, hy + 22)], (16, 16, 16))
    cv.rect(x0 + 120, hy - 16, x0 + 150, hy, (220, 220, 220))
    cv.rect(x0 + 124, hy - 24, x0 + 146, hy - 16, (220, 220, 220))
    # containers
    for i, c in enumerate([(178, 32, 26), (42, 82, 128), (62, 122, 62), (220, 220, 220)]):
        cv.rect(x0 + 22 + i * 24, hy - 14, x0 + 44 + i * 24, hy, c)
    draw_text(cv, x0 + 96, hy + 18, "SPARTA II", 10, (255, 255, 255), align="center")
    # smoke + flame
    for (sx, sy, r) in [(x0 + 130, hy - 30, 9), (x0 + 142, hy - 40, 11),
                        (x0 + 156, hy - 50, 12), (x0 + 170, hy - 58, 10)]:
        cv.circle(sx, sy, r, (120, 118, 110))
    cv.poly([(x0 + 118, hy - 14), (x0 + 128, hy - 34), (x0 + 136, hy - 14)],
            (230, 120, 20))
    cv.poly([(x0 + 122, hy - 14), (x0 + 128, hy - 26), (x0 + 133, hy - 14)],
            (240, 200, 40))
    # drones + dashed path
    for (dx, dy) in [(x0 + 190, y0 + 34), (x0 + 212, y0 + 44)]:
        cv.rect(dx - 5, dy - 2, dx + 5, dy + 2, (40, 40, 40))
        cv.line(dx - 8, dy, dx + 8, dy, (40, 40, 40), 1)
    dashed(cv, x0 + 196, y0 + 40, x0 + 140, hy - 30, RED)

def draw_cop31(cv, x0, y0, x1, y1):
    # green logo panel
    cv.rect(x0, y0, x0 + 108, y0 + 62, (20, 120, 90))
    draw_text(cv, x0 + 8, y0 + 26, "COP31", 20, (255, 255, 255))
    draw_text(cv, x0 + 8, y0 + 40, "ANTALYA · UN CLIMATE SUMMIT", 7, (255, 255, 255))
    for i in range(5):
        cv.rect(x0 + 8 + i * 14, y0 + 48, x0 + 18 + i * 14, y0 + 56, (255, 255, 255))
    draw_text(cv, x0 + 8, y1 - 8, "talks paused for the night", 8, (90, 80, 66))
    # calendar: 16-21 Nov, Sat 21 in overtime (Reference A)
    px0, py0 = x0 + 118, y0
    cv.rect(px0, py0, px0 + 92, py0 + 62, (255, 255, 255))
    cv.rect(px0, py0, px0 + 92, py0 + 62, INK)
    draw_text(cv, px0 + 6, py0 + 12, "NOVEMBER", 8, (90, 80, 66))
    for i, d in enumerate([16, 17, 18, 19, 20, 21]):
        cx = px0 + 6 + i * 14
        if d == 21:
            cv.rect(cx, py0 + 18, cx + 12, py0 + 34, RED)
            draw_text(cv, cx + 6, py0 + 30, "21", 9, (255, 255, 255),
                      align="center")
        else:
            draw_text(cv, cx + 6, py0 + 30, str(d), 9, INK, align="center")
    draw_text(cv, px0 + 6, py0 + 48, "SAT 21 · OVERTIME", 8, RED)
    draw_text(cv, px0 + 6, py0 + 58, "NO DEAL YET", 8, RED)
    # clock
    cx, cy = x1 - 44, y0 + 30
    cv.circle(cx, cy, 26, (255, 255, 255))
    cv.circle(cx, cy, 26, INK, fill=False)
    cv.line(cx, cy, cx + 14, cy - 16, RED, 3)
    cv.line(cx, cy, cx, cy - 8, INK, 2)
    cv.rect(x1 - 88, y0 + 62, x1, y0 + 76, RED)
    draw_text(cv, x1 - 44, y0 + 73, "OVERTIME", 10, (255, 255, 255), align="center")
    # (the "a day past Friday's deadline" caption was deleted: it sat on
    # the OVERTIME box's bottom edge and read as cut-off text)

# ------------------------------------------------------- grid pictograms
def pic(cv, x, y, w, h, code):
    if code == "flags":
        cv.rect(x, y, x + w, y + h, (246, 240, 224))
        cv.rect(x + 8, y + 6, x + 48, y + 26, (30, 60, 130))
        for k in range(12):
            a = math.radians(k * 30)
            cv.circle(x + 28 + 7 * math.cos(a), y + 16 + 6 * math.sin(a), 1,
                      (240, 200, 40))
        cv.rect(x + 54, y + 6, x + 94, y + 16, (210, 30, 30))
        cv.rect(x + 54, y + 16, x + 94, y + 26, (255, 255, 255))
        draw_text(cv, x + w - 8, y + 24, "98.5%", 16, RED, align="right")
    elif code == "sparta":
        cv.rect(x, y, x + w, y + h, (30, 58, 82))
        # hull + containers
        cv.poly([(x + 10, y + 24), (x + 120, y + 24), (x + 112, y + 31),
                 (x + 18, y + 31)], (16, 16, 16))
        for i, c in enumerate([(178, 32, 26), (42, 82, 128), (62, 122, 62)]):
            cv.rect(x + 20 + i * 18, y + 14, x + 36 + i * 18, y + 24, c)
        # flame + smoke
        cv.poly([(x + 96, y + 14), (x + 102, y + 2), (x + 108, y + 14)],
                (230, 120, 20))
        cv.circle(x + 110, y + 6, 5, (120, 118, 110))
        draw_text(cv, x + w - 8, y + 22, "16 CREW SAFE", 11, (255, 255, 255),
                  align="right")
    elif code == "robot":
        cv.rect(x, y, x + w, y + h, (220, 220, 216))
        cv.rect(x + 14, y + 8, x + 46, y + 28, (90, 90, 90))
        cv.line(x + 30, y + 8, x + 30, y + 2, (90, 90, 90), 2)
        cv.circle(x + 22, y + 18, 3, (240, 200, 40))
        cv.circle(x + 38, y + 18, 3, (240, 200, 40))
        draw_text(cv, x + w - 8, y + 28, "2028", 15, INK, align="right")
    elif code == "mercury":
        cv.rect(x, y, x + w, y + h, (24, 28, 40))
        cv.circle(x + 26, y + 17, 12, (210, 130, 60))
        cv.circle(x + 30, y + 13, 3, (180, 100, 40))
        draw_text(cv, x + w - 8, y + 26, "18:24", 15, (255, 255, 255), align="right")
    elif code == "bitcoin":
        cv.rect(x, y, x + w, y + h, (24, 28, 40))
        # falling then rebounding line
        cv.line(x + 10, y + 14, x + 65, y + 16, (240, 200, 40), 2)
        cv.line(x + 65, y + 16, x + 112, y + 28, RED, 2)
        cv.line(x + 112, y + 28, x + 165, y + 20, (46, 200, 120), 2)
        cv.circle(x + 112, y + 28, 3, RED)
        draw_text(cv, x + 8, y + 10, "$60K", 9, (255, 255, 255))
        draw_text(cv, x + w - 8, y + 12, "$55,100", 11, RED, align="right")
    elif code == "quake":
        cv.rect(x, y, x + w, y + h, (246, 240, 224))
        # ground surface + strata, depth arrow to hypocentre
        cv.rect(x, y + 8, x + w, y + 10, (120, 110, 96))
        cv.line(x + 6, y + 16, x + w - 6, y + 16, (190, 182, 168), 1)
        cv.line(x + 6, y + 24, x + w - 6, y + 24, (190, 182, 168), 1)
        cv.line(x + 60, y + 10, x + 60, y + 28, RED, 2)
        cv.circle(x + 60, y + 28, 4, RED)
        cv.circle(x + 60, y + 28, 8, RED, fill=False)
        draw_text(cv, x + 70, y + 20, "108 KM", 11, RED)
        draw_text(cv, x + w - 8, y + 32, "M6.7", 15, RED, align="right")
    elif code == "fire":
        cv.rect(x, y, x + w, y + h, (246, 240, 224))
        # power-plant block + chimney
        cv.rect(x + 14, y + 14, x + 46, y + 30, (120, 118, 110))
        cv.rect(x + 50, y + 6, x + 56, y + 30, (120, 118, 110))
        # flame
        cv.poly([(x + 20, y + 14), (x + 28, y + 2), (x + 36, y + 14)],
                (230, 120, 20))
        cv.poly([(x + 24, y + 14), (x + 28, y + 6), (x + 32, y + 14)],
                (240, 200, 40))
        draw_text(cv, x + w - 8, y + 26, "4 DEAD", 13, RED, align="right")
    elif code == "dengue":
        cv.rect(x, y, x + w, y + h, (246, 240, 224))
        # bars: before (tall) / after (short) = cases down 71% (NEJM)
        cv.rect(x + 16, y + 6, x + 30, y + 30, (178, 32, 26))
        cv.rect(x + 38, y + 23, x + 52, y + 30, (46, 122, 62))
        draw_text(cv, x + w - 8, y + 26, "-71%", 16, RED, align="right")
    elif code == "jets":
        cv.rect(x, y, x + w, y + h, (191, 217, 232))
        # median line (dashed) + jets crossing it
        dashed(cv, x + 90, y + 2, x + 90, y + 32, RED)
        for (jx, jy) in [(x + 40, y + 10), (x + 62, y + 20), (x + 104, y + 10)]:
            cv.poly([(jx, jy), (jx + 14, jy + 3), (jx, jy + 6)], (40, 40, 40))
        draw_text(cv, x + w - 8, y + 28, "15 CROSSED", 11, RED, align="right")
    elif code == "vote":
        cv.rect(x, y, x + w, y + h, (246, 240, 224))
        # ballot box + slip
        cv.rect(x + 16, y + 14, x + 48, y + 30, (42, 82, 128))
        cv.rect(x + 24, y + 6, x + 40, y + 16, (255, 255, 255))
        cv.hline(x + 24, x + 40, y + 6, INK, 1)
        cv.hline(x + 24, x + 40, y + 15, INK, 1)
        cv.vline(x + 24, y + 6, y + 16, INK, 1)
        cv.vline(x + 39, y + 6, y + 16, INK, 1)
        draw_text(cv, x + w - 8, y + 26, "54/54", 16, INK, align="right")

# ------------------------------------------------------- world map
def world_map(cv, x0, y0, x1, y1):
    cv.rect(x0, y0, x1, y1, (214, 228, 238))
    tan = (229, 213, 174)
    cv.poly([(x0 + 18, y0 + 12), (x0 + 76, y0 + 6), (x0 + 104, y0 + 16),
             (x0 + 90, y0 + 36), (x0 + 64, y0 + 42), (x0 + 48, y0 + 58),
             (x0 + 28, y0 + 52), (x0 + 14, y0 + 30)], tan)
    cv.poly([(x0 + 66, y0 + 84), (x0 + 92, y0 + 80), (x0 + 104, y0 + 98),
             (x0 + 88, y0 + 130), (x0 + 74, y0 + 126), (x0 + 62, y0 + 102)], tan)
    cv.poly([(x0 + 146, y0 + 18), (x0 + 164, y0 + 12), (x0 + 182, y0 + 20),
             (x0 + 174, y0 + 36), (x0 + 156, y0 + 38), (x0 + 144, y0 + 28)], tan)
    cv.poly([(x0 + 146, y0 + 54), (x0 + 176, y0 + 50), (x0 + 192, y0 + 66),
             (x0 + 182, y0 + 98), (x0 + 164, y0 + 106), (x0 + 148, y0 + 82),
             (x0 + 142, y0 + 64)], tan)
    cv.poly([(x0 + 182, y0 + 12), (x0 + 246, y0 + 8), (x0 + 296, y0 + 18),
             (x0 + 306, y0 + 42), (x0 + 266, y0 + 54), (x0 + 236, y0 + 68),
             (x0 + 206, y0 + 62), (x0 + 186, y0 + 42)], tan)
    cv.poly([(x0 + 264, y0 + 106), (x0 + 296, y0 + 102), (x0 + 304, y0 + 118),
             (x0 + 282, y0 + 126), (x0 + 264, y0 + 118)], tan)
    def pin(lon, lat, n, col, big=True):
        px = x0 + (lon + 180) / 360 * (x1 - x0)
        py = y0 + (85 - lat) / 145 * (y1 - y0)
        r = 7 if big else 4
        cv.circle(px, py, r, col)
        if big:
            draw_text(cv, px, py + 2.5, str(n), 7, (255, 255, 255), align="center")
    pin(50, 26, 1, REG_COL["Middle East"])
    pin(-108, 25, 2, REG_COL["N. America"])
    pin(30, 37, 3, REG_COL["Europe"])
    pin(-76, -11, 4, REG_COL["Latin Am."])
    pin(25, 62, 5, REG_COL["Europe"])
    pin(6, 46, 6, REG_COL["Europe"])
    pin(4, 51, 7, REG_COL["Europe"])
    pin(-100, 38, 8, REG_COL["N. America"])
    pin(8, 50, 9, REG_COL["Europe"])
    pin(47, 30, 10, REG_COL["Middle East"])
    pin(-44, -20, 11, REG_COL["Latin Am."])
    pin(121, 23, 12, REG_COL["East Asia"])
    pin(7, 9, 13, REG_COL["Africa"])
    for (lon, lat, col) in [
            (2, 47, REG_COL["Europe"]), (30, 50, REG_COL["Europe"]),
            (0, 51, REG_COL["Europe"]), (-6, 53, REG_COL["Europe"]),
            (8, 45, REG_COL["Europe"]), (47, 25, REG_COL["Middle East"]),
            (57, 27, REG_COL["Middle East"]), (34, 31, REG_COL["Middle East"]),
            (35, 34, REG_COL["Middle East"]), (4, 51, REG_COL["Europe"]),
            (140, 37, REG_COL["East Asia"]), (106, -6, REG_COL["SE Asia"]),
            (106, 21, REG_COL["SE Asia"]), (90, 24, REG_COL["South Asia"]),
            (6, 10, REG_COL["Africa"]), (32, 1, REG_COL["Africa"]),
            (7, 9, REG_COL["Africa"]), (-77, 39, REG_COL["N. America"]),
            (-77, 39, REG_COL["N. America"]), (-48, -16, REG_COL["Latin Am."]),
            (-5, 50, REG_COL["Europe"]), (145, -38, REG_COL["Oceania"]),
            (131, -12, REG_COL["Oceania"]), (175, -41, REG_COL["Oceania"])]:
        pin(lon, lat, 0, col, big=False)
    cv.rect(x0 + 6, y1 - 24, x0 + 134, y1 - 6, (24, 28, 40))
    draw_text(cv, x0 + 10, y1 - 10, "MERCURY  9 · in orbit 18:24", 8,
              (255, 255, 255))

TICKER = [
    (14, "France: 144 held at cost marches (AFP)", "Europe"),
    (15, "Kyiv: UK deal to build drones (UK MOD)", "Europe"),
    (16, "London: England 37, All Blacks 12 (BBC)", "Europe"),
    (17, "Dublin: Ireland beat SA 20–17 (BBC)", "Europe"),
    (18, "Turin: Alcaraz beats Shelton (BBC)", "Europe"),
    (19, "Riyadh: 3 Houthi missiles downed (AJ)", "Middle East"),
    (20, "Hormuz: Iran claims US drone kill (AJ)", "Middle East"),
    (21, "Gaza: Food vehicle hit, 3 dead (REUTERS)", "Middle East"),
    (22, "Beirut: Aoun: pull-out, Iran out (AJ)", "Middle East"),
    (23, "Brussels: EU budget 204bn, tech tax (DW)", "Europe"),
    (24, "Fukushima: Snow isolates 1,400 (XINHUA)", "East Asia"),
    (25, "Serang: Fire kills 3, 36 missing (BBC)", "SE Asia"),
    (26, "Hanoi: Land-seizure law speeds up (REUTERS)", "SE Asia"),
    (27, "Bangladesh: Measles toll hits 1,343 (DGHS)", "South Asia"),
    (28, "Niger: Village head killed in raid (TRUST)", "Africa"),
    (29, "Uganda: $3bn rail deal 'off' (MUHOOZI)", "Africa"),
    (30, "Abuja: Kiswahili made official (CAF)", "Africa"),
    (31, "US: Trump backs 10% card cap (AP)", "N. America"),
    (32, "US: Trump: FBI hack 'not good' (AP)", "N. America"),
    (33, "Brasilia: Bolsonaro in intensive care (AJ)", "Latin Am."),
    (34, "Cornwall: Peter Fluck dies at 85 (BBC)", "Europe"),
    (35, "Melbourne: Australia beat England (BBC)", "Oceania"),
    (36, "Darwin: M6.8 Timor quake felt (USGS)", "Oceania"),
    (37, "Wellington: India 486–4, lead by 118 (AFP)", "Oceania"),
]

if __name__ == "__main__":
    main()
