#!/usr/bin/env python3
"""Render the 20 November 2026 world-news poster.

Supersamples at 3x (3072x3072) and downsamples with LANCZOS to a
1024x1024 PNG at art/entry.png. Takes no network or clock input.
"""

import os

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- palette ---
PAPER = (244, 239, 230)   # #F4EFE6
INK = (18, 16, 14)        # #12100E
RED = (200, 16, 46)       # #C8102E
GREY = (110, 106, 99)     # #6E6A63

BOLD_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REG_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

S = 3                     # supersample factor
SIZE = 1024               # final size
CANVAS = SIZE * S

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "art")
OUT_PATH = os.path.join(OUT_DIR, "entry.png")

DATE_TEXT = "20 NOVEMBER 2026"

# ------------------------------------------------------------------ fonts ---
_font_cache = {}
_measure_cache = {}


def font(bold, size):
    key = (bold, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(
            BOLD_PATH if bold else REG_PATH, size * S)
    return _font_cache[key]


def mfont(bold, size):
    key = ("m", bold, size)
    if key not in _measure_cache:
        _measure_cache[key] = ImageFont.truetype(
            BOLD_PATH if bold else REG_PATH, size)
    return _measure_cache[key]


_measurer = ImageDraw.Draw(Image.new("RGB", (8, 8)))


def tw(text, bold, size):
    """Advance width of a string in 1024-space units."""
    return _measurer.textlength(text, font=mfont(bold, size))


def tw_tracked(text, bold, size, tracking):
    return sum(tw(ch, bold, size) for ch in text) + tracking * max(0, len(text) - 1)


def ink_extent(text, bold, size):
    """(left, top, right, bottom) of actual glyph ink relative to the pen."""
    return mfont(bold, size).getbbox(text, anchor="la")


# ------------------------------------------------------------ text layout ---
def _wrap_dp(words, bold, size, avail, max_lines):
    """Split words into <= max_lines lines minimising the widest line."""
    n = len(words)
    if n == 0:
        return None
    widths = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i, n):
            widths[i][j] = tw(" ".join(words[i:j + 1]), bold, size)

    INF = float("inf")
    best = [[INF] * (n + 1) for _ in range(max_lines + 1)]
    prev = [[-1] * (n + 1) for _ in range(max_lines + 1)]
    best[0][0] = 0.0
    for k in range(1, max_lines + 1):
        for j in range(1, n + 1):
            for i in range(j):
                if best[k - 1][i] < INF:
                    val = max(best[k - 1][i], widths[i][j - 1])
                    if val < best[k][j]:
                        best[k][j] = val
                        prev[k][j] = i

    for k in range(1, max_lines + 1):
        if best[k][n] <= avail:
            lines, j, kk = [], n, k
            while kk > 0:
                i = prev[kk][j]
                lines.append(" ".join(words[i:j]))
                j, kk = i, kk - 1
            return lines[::-1]
    return None


def fit(text, bold, max_size, min_size, avail, max_lines):
    """Largest size (<= max_size) whose best wrap fits avail in max_lines."""
    for size in range(max_size, min_size - 1, -1):
        lines = _wrap_dp(text.split(), bold, size, avail, max_lines)
        if lines is not None:
            return size, lines
    size = min_size
    return size, _wrap_dp(text.split(), bold, size, avail, max_lines) or [text]


# ------------------------------------------------------------- draw shim ---
class Canvas:
    """Draw wrapper taking 1024-space coordinates and scaling them by S."""

    def __init__(self, draw):
        self.d = draw

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width=1):
        self.d.rectangle([x0 * S, y0 * S, x1 * S, y1 * S], fill=fill,
                         outline=outline, width=max(1, int(round(width * S))))

    def poly(self, pts, fill=None, outline=None, width=1):
        self.d.polygon([(x * S, y * S) for x, y in pts], fill=fill,
                       outline=outline, width=max(1, int(round(width * S))))

    def line(self, pts, fill, width=1):
        self.d.line([(x * S, y * S) for x, y in pts], fill=fill,
                    width=max(1, int(round(width * S))), joint="curve")

    def ell(self, x0, y0, x1, y1, fill=None, outline=None, width=1):
        self.d.ellipse([x0 * S, y0 * S, x1 * S, y1 * S], fill=fill,
                       outline=outline, width=max(1, int(round(width * S))))

    def arc(self, x0, y0, x1, y1, start, end, fill, width=1):
        self.d.arc([x0 * S, y0 * S, x1 * S, y1 * S], start, end, fill=fill,
                   width=max(1, int(round(width * S))))

    def text(self, x, y, s, bold, size, fill, anchor="la"):
        self.d.text((x * S, y * S), s, font=font(bold, size), fill=fill,
                    anchor=anchor)

    def text_ink_top(self, x, ink_top, s, bold, size, fill):
        """Draw with the top of the glyph ink exactly at ink_top."""
        _, top, _, _ = ink_extent(s, bold, size)
        self.text(x, ink_top - top, s, bold, size, fill)

    def text_tracked(self, x, ink_top, s, bold, size, fill, tracking):
        _, top, _, _ = ink_extent(s, bold, size)
        pen, y = x, ink_top - top
        for ch in s:
            self.d.text((pen * S, y * S), ch, font=font(bold, size), fill=fill,
                        anchor="la")
            pen += tw(ch, bold, size) + tracking
        return pen - tracking


# ---------------------------------------------------------- illustrations ---
def art_facade(c, ox, oy):
    """1. Shattered building facade with an incoming missile streak."""
    def P(pts):
        return [(ox + x, oy + y) for x, y in pts]

    c.rect(ox + 28, oy + 26, ox + 124, oy + 138, fill=PAPER, outline=INK, width=5)
    c.rect(ox + 20, oy + 16, ox + 132, oy + 28, fill=INK)
    for wx in (40, 70, 100):
        for wy in (40, 74, 108):
            c.rect(ox + wx, oy + wy, ox + wx + 16, oy + wy + 16, fill=INK)
    # red impact wedge missing from the top-left corner
    c.poly(P([(28, 26), (58, 26), (28, 56)]), RED)
    # red fracture lines
    c.line(P([(112, 26), (96, 58), (108, 78), (92, 108), (100, 138)]), RED, 6)
    c.line(P([(58, 26), (66, 50), (52, 68), (62, 86)]), RED, 5)
    c.line(P([(124, 96), (108, 104), (116, 122)]), RED, 4)
    # missile streak entering top-left
    c.line(P([(0, 0), (36, 22)]), RED, 7)
    c.poly(P([(46, 28), (34, 20), (40, 34)]), RED)


def art_scales(c, ox, oy):
    """2. Scales of justice: post, beam, two red pans, plinth."""
    def P(pts):
        return [(ox + x, oy + y) for x, y in pts]

    c.rect(ox + 46, oy + 128, ox + 104, oy + 142, fill=INK)
    c.rect(ox + 70, oy + 48, ox + 80, oy + 130, fill=INK)
    c.poly(P([(75, 22), (63, 46), (87, 46)]), INK)
    c.rect(ox + 22, oy + 42, ox + 128, oy + 50, fill=INK)
    for cx, pan in ((24, 8), (126, 106)):
        c.line(P([(cx, 50), (pan + 4, 78)]), INK, 3)
        c.line(P([(cx, 50), (pan + 36, 78)]), INK, 3)
        c.arc(ox + pan, oy + 74, ox + pan + 40, oy + 102, 0, 180, RED, 7)
        c.line(P([(pan, 78), (pan + 40, 78)]), RED, 5)


def art_market(c, ox, oy):
    """3. Thick red arrow rising over ascending ink candlesticks."""
    def P(pts):
        return [(ox + x, oy + y) for x, y in pts]

    for x, top in ((12, 118), (38, 108), (64, 98), (90, 88)):
        c.line(P([(x + 7, top - 12), (x + 7, 140)]), INK, 3)
        c.rect(ox + x, oy + top, ox + x + 15, oy + 134, fill=INK)
    c.line(P([(6, 112), (126, 44)]), RED, 12)
    c.poly(P([(140, 28), (104, 40), (126, 62)]), RED)
    # ink slide at the right
    c.line(P([(110, 80), (130, 124)]), INK, 5)
    c.poly(P([(134, 136), (122, 122), (138, 118)]), INK)


def art_yemen(c, ox, oy):
    """4. Skyline behind a barbed-wire fence, red smoke plume."""
    def P(pts):
        return [(ox + x, oy + y) for x, y in pts]

    # red smoke plume, clear of the skyline
    c.poly(P([(54, 62), (42, 52), (54, 42), (46, 30), (60, 18), (74, 30),
              (66, 42), (76, 52), (62, 62)]), RED)
    # broken skyline: separated blocks with varied heights
    for x0, y0, x1 in ((6, 78, 32), (38, 66, 62), (68, 84, 92),
                       (98, 62, 118), (124, 74, 144)):
        c.rect(ox + x0, oy + y0, ox + x1, oy + 106, fill=INK)
    # cream ground band carries the black barbed wire
    c.rect(ox, oy + 108, ox + 150, oy + 150, fill=PAPER)
    for px in (12, 46, 80, 114, 140):
        c.rect(ox + px - 3, oy + 106, ox + px + 3, oy + 144, fill=INK)
    for base in (118, 134):
        pts, x, up = [(8, base + 1)], 8, True
        while x <= 142:
            pts.append((x, base - (8 if up else -2)))
            x += 9
            up = not up
        c.line(P(pts), INK, 3)
        for x in (8, 44, 80, 116, 142):
            c.line(P([(x - 6, base), (x + 6, base)]), INK, 3)


def art_migration(c, ox, oy):
    """5. Boat on red wave bands, two figures, an empty seat, oars."""
    def P(pts):
        return [(ox + x, oy + y) for x, y in pts]

    def waves(y0, h):
        pts, x = [(0, y0 + h)], 0
        while x <= 150:
            pts.append((x, y0 + (0 if (x // 15) % 2 == 0 else 7)))
            x += 15
        pts += [(150, y0 + h), (0, y0 + h)]
        c.poly(P(pts), RED)

    # riders first, then the hull in front of them
    for sx in (44, 78):
        c.ell(ox + sx + 2, oy + 50, ox + sx + 16, oy + 64, fill=INK)
        c.line(P([(sx + 9, 62), (sx + 9, 92)]), INK, 7)
    c.rect(ox + 34, oy + 86, ox + 50, oy + 92, fill=INK)   # empty seat
    c.rect(ox + 68, oy + 86, ox + 84, oy + 92, fill=INK)   # empty seat
    c.line(P([(96, 60), (120, 84)]), INK, 5)               # raised oar
    c.poly(P([(24, 90), (128, 90), (114, 120), (36, 120)]), INK)
    c.rect(ox + 24, oy + 86, ox + 128, oy + 92, fill=INK)
    c.poly(P([(40, 120), (112, 120), (98, 134), (54, 134)]), INK)
    waves(128, 12)
    waves(142, 8)


def art_japan(c, ox, oy):
    """6. Red price tag with a black yen mark, ascending ink bars behind."""
    def P(pts):
        return [(ox + x, oy + y) for x, y in pts]

    for x, top in ((4, 108), (24, 92), (44, 74)):
        c.rect(ox + x, oy + top, ox + x + 14, oy + 146, fill=INK)
    # tag hangs from the bars, pointing left
    c.poly(P([(66, 48), (112, 48), (144, 76), (112, 104), (66, 104)]), RED)
    c.ell(ox + 70, oy + 68, ox + 81, oy + 79, fill=PAPER)
    # yen mark drawn as strokes
    c.line(P([(97, 58), (108, 72)]), INK, 4)
    c.line(P([(119, 58), (108, 72)]), INK, 4)
    c.line(P([(108, 71), (108, 95)]), INK, 4)
    c.line(P([(98, 76), (118, 76)]), INK, 3)
    c.line(P([(98, 84), (118, 84)]), INK, 3)


ART = [art_facade, art_scales, art_market, art_yemen, art_migration, art_japan]

# ------------------------------------------------------------------ stories ---
STORIES = [
    ("EUROPE \u00b7 UKRAINE", "EMBASSIES BOMBED IN KYIV",
     "Russian strikes damage the Austrian and Dutch missions; the Netherlands "
     "summons Russia's ambassador."),
    ("ASIA \u00b7 MYANMAR", "MYANMAR GUILTY OF GENOCIDE",
     "The ICJ holds Myanmar responsible for the Rohingya genocide; the EU, "
     "T\u00fcrkiye and Switzerland press it to comply."),
    ("AMERICAS \u00b7 MARKETS", "ANTHROPIC UP 17% ON DEBUT",
     "Shares close near $97 after an $83 IPO, briefly valuing it at $2 "
     "trillion; the S&P 500 falls a fifth straight day."),
    ("MIDDLE EAST \u00b7 YEMEN", "SIEGE TIGHTENS ON TAIZ",
     "Civilians trapped by the Houthi encirclement describe daily shelling and "
     "dwindling food."),
    ("AFRICA \u00b7 MIGRATION", "MIGRANT BOAT CAPSIZES",
     "Four bodies are recovered off Senegal's coast as arrivals to the Canary "
     "Islands surge."),
    ("ASIA-PACIFIC \u00b7 JAPAN", "JAPAN INFLATION ACCELERATES",
     "Core inflation picks up in October, firming expectations of a rate rise."),
]

FOOTER_PARTS = ["ALSO: Trump defers Iran strike call",
                "900,000 AI chips cleared for China",
                "Haiti raid kills 34"]

# ------------------------------------------------------------------ layout ---
MARGIN = 32
PANEL_W = 467
PANEL_H = 236
GUTTER_X = 26
COL_X = (MARGIN, MARGIN + PANEL_W + GUTTER_X)
ROW_Y = (192, 448, 704)

TEXT_X = 170
TEXT_W = PANEL_W - TEXT_X - 8
ILLUS = 150
ILLUS_X = 10
ILLUS_Y = (PANEL_H - ILLUS) // 2

TAG_SIZE = 22
HEAD_MAX = 46
DET_MAX = 23
HEAD_LINES = 3
DET_LINES = 4


def shared_sizes():
    """One headline size and one detail size that work for all six panels."""
    head = HEAD_MAX
    while head > 12 and not all(
            _wrap_dp(h.split(), True, head, TEXT_W, HEAD_LINES) is not None
            for _, h, _ in STORIES):
        head -= 1
    det = DET_MAX
    while det > 8 and not all(
            _wrap_dp(d.split(), False, det, TEXT_W, DET_LINES) is not None
            for _, _, d in STORIES):
        det -= 1
    return head, det


def draw_masthead(c):
    c.rect(0, 0, SIZE, 168, fill=PAPER)
    c.text_tracked(MARGIN, 30, "WORLD NEWS \u00b7 ONE DAY", True, 22, RED, 3.0)

    avail = SIZE - 2 * 12
    size, tracking = 104, 0.0
    for cand in range(104, 60, -1):
        nat = tw_tracked(DATE_TEXT, True, cand, 0.0)
        tr = (avail - nat) / (len(DATE_TEXT) - 1)
        # never squeeze the tracking tighter than 6% of the type size
        if tr >= -0.055 * cand:
            size, tracking = cand, tr
            break
    width = tw_tracked(DATE_TEXT, True, size, tracking)
    _, dtop, _, dbot = ink_extent(DATE_TEXT, True, size)
    ink_h = dbot - dtop
    ink_top = 56 + int((88 - ink_h) / 2)          # centre ink between label and rule
    c.text_tracked((SIZE - width) / 2.0, ink_top, DATE_TEXT, True, size, INK,
                   tracking)

    c.rect(MARGIN, 148, SIZE - MARGIN, 151, fill=RED)
    c.rect(0, 162, SIZE, 168, fill=INK)


def draw_panel(c, x, y, story, art, head, det, hlines, dlines):
    c.rect(x, y, x + PANEL_W, y + PANEL_H, fill=PAPER, outline=INK, width=4)
    art(c, x + ILLUS_X, y + ILLUS_Y)

    tag = story[0]
    hlead = int(round(head * 1.10))
    dlead = int(round(det * 1.42))
    block_h = tag_h = TAG_SIZE + 9
    block_h += 7 + len(hlines) * hlead
    block_h += 9 + (len(dlines) - 1) * dlead + det

    _, top, _, bot = ink_extent(tag, True, TAG_SIZE)
    ty = y + (PANEL_H - block_h) // 2
    c.text_ink_top(x + TEXT_X, ty, tag, True, TAG_SIZE, RED)
    ty += tag_h + 7

    for line in hlines:
        c.text_ink_top(x + TEXT_X, ty, line, True, head, INK)
        ty += hlead
    ty += 9 - (hlead - head)
    for line in dlines:
        c.text_ink_top(x + TEXT_X, ty, line, False, det, GREY)
        ty += dlead


def draw_body(c):
    used = []
    for i, story in enumerate(STORIES):
        hs, hlines = fit(story[1], True, HEAD_MAX, 26, TEXT_W, HEAD_LINES)
        ds, dlines = fit(story[2], False, DET_MAX, 15, TEXT_W, DET_LINES)
        used.append((hs, ds))
        draw_panel(c, COL_X[i % 2], ROW_Y[i // 2], story, ART[i],
                   hs, ds, hlines, dlines)
    return used


def draw_footer(c):
    c.rect(0, 962, SIZE, SIZE, fill=INK)
    avail = SIZE - 2 * 24
    sep = "  \u00b7  "
    size = 21
    for cand in range(21, 8, -1):
        w = (sum(tw(p, True, cand) for p in FOOTER_PARTS)
             + 2 * tw(sep, True, cand))
        if w <= avail:
            size = cand
            break
    sep_w = tw(sep, True, size)
    total = sum(tw(p, True, size) for p in FOOTER_PARTS) + 2 * sep_w
    pen = (SIZE - total) / 2.0
    for i, part in enumerate(FOOTER_PARTS):
        c.text_ink_top(pen, 982, part, True, size, PAPER)
        pen += tw(part, True, size)
        if i < len(FOOTER_PARTS) - 1:
            c.text_ink_top(pen, 982, sep, True, size, RED)
            pen += sep_w
    return size


def main():
    img = Image.new("RGB", (CANVAS, CANVAS), PAPER)
    c = Canvas(ImageDraw.Draw(img))
    draw_masthead(c)
    used = draw_body(c)
    fsize = draw_footer(c)
    out = img.resize((SIZE, SIZE), Image.LANCZOS)
    os.makedirs(OUT_DIR, exist_ok=True)
    out.save(OUT_PATH, format="PNG", optimize=True)
    print("wrote %s %dx%d heads=%s footer=%d"
          % (OUT_PATH, out.size[0], out.size[1],
             ",".join(str(h) for h, _ in used), fsize))


if __name__ == "__main__":
    main()
