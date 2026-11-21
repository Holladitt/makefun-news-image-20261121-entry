#!/usr/bin/env python3
"""Build-time font atlas generator (NOT run at grade time).

Renders DejaVu glyphs with PIL into fonts.bin, a tiny FNT1 container:
  magic "FNT1", u16 n_fonts
  per font: u8 name_len, name, u16 n_chars
  per char: u32 codepoint, u16 advance, u16 w, u16 h, i16 ox, i16 oy,
            then w*h coverage bytes (0..255)

Glyphs are drawn with anchor "la" (left, ascender top) at a fixed
origin, so ox/oy are offsets from the shared ascender top of the line.
"""
import struct
from PIL import Image, ImageDraw, ImageFont

MASTER = 80
FONTS = {
    "serif": ("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 0.0),
    "serif_bold": ("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 0.0),
    # No serif italic file is installed: shear the upright serif instead.
    "serif_italic": ("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 0.2),
    "sans": ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 0.0),
    "sans_bold": ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0.0),
}
CHARS = sorted(set(
    list(range(32, 127))
    + list(range(0xA0, 0x100))
    + [0x2022, 0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D]
))

ORIGIN = 70
CANVAS = 220


def build_font(path, shear=0.0):
    font = ImageFont.truetype(path, MASTER)
    glyphs = []
    for cp in CHARS:
        ch = chr(cp)
        adv = int(round(font.getlength(ch)))
        img = Image.new("L", (CANVAS, CANVAS), 0)
        d = ImageDraw.Draw(img)
        d.text((ORIGIN, ORIGIN), ch, font=font, fill=255, anchor="la")
        if shear:
            y_base = ORIGIN + 60
            img = img.transform((CANVAS, CANVAS), Image.AFFINE,
                                (1, shear, -shear * y_base, 0, 1, 0))
        bbox = img.getbbox()
        if bbox is None:
            glyphs.append((cp, adv, 0, 0, 0, 0, b""))
            continue
        x0, y0, x1, y1 = bbox
        w, h = x1 - x0, y1 - y0
        crop = img.crop(bbox)
        glyphs.append((cp, adv, w, h, x0 - ORIGIN, y0 - ORIGIN, crop.tobytes()))
    return glyphs


def main():
    out = bytearray(b"FNT1")
    out += struct.pack("<H", len(FONTS))
    for name, (path, shear) in FONTS.items():
        glyphs = build_font(path, shear)
        nb = name.encode()
        out += struct.pack("<B", len(nb)) + nb
        out += struct.pack("<H", len(glyphs))
        for cp, adv, w, h, ox, oy, bmp in glyphs:
            out += struct.pack("<IHHHhh", cp, adv, w, h, ox, oy)
            out += bmp
        print(f"{name}: {len(glyphs)} glyphs")
    with open("fonts.bin", "wb") as f:
        f.write(bytes(out))
    print(f"fonts.bin: {len(out)} bytes")


if __name__ == "__main__":
    main()
