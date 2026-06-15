"""Render assets/lethe-demo.gif from the demo's real output — no ttyd/VHS needed.

    python assets/make_gif.py

Captures the colored output of `lethe.examples.mcp_demo`, then draws it as a
dark-terminal animated GIF (line-by-line reveal) with Pillow. Self-contained and
reproducible on Windows, unlike VHS (which needs ttyd).
"""
from __future__ import annotations

import io
import os
import re
import contextlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "lethe-demo.gif"

# --- capture the demo's colored output --------------------------------------
import sys  # noqa: E402
sys.path.insert(0, str(ROOT))
os.environ["LETHE_DEMO_FAST"] = "1"
from lethe.examples import mcp_demo  # noqa: E402

mcp_demo._COLOR = True  # force ANSI even though we're not a tty
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    mcp_demo.main()
TEXT = buf.getvalue().replace("\r\n", "\n").rstrip("\n")
LINES = TEXT.split("\n")

# --- ANSI -> colored segments -----------------------------------------------
TOK = re.compile(r"\x1b\[([0-9;]*)m")
BG = (30, 30, 46)
PALETTE = {
    "default": (208, 208, 214),
    "white": (245, 245, 245),
    "dim": (120, 122, 138),
    "red": (255, 107, 107),
    "green": (90, 247, 142),
    "yellow": (243, 249, 157),
    "cyan": (97, 199, 255),
}
CODE = {31: "red", 32: "green", 33: "yellow", 36: "cyan"}


def parse(line: str):
    segs, pos, color, bold = [], 0, "default", False
    for m in TOK.finditer(line):
        if m.start() > pos:
            segs.append((line[pos:m.start()], color, bold))
        for c in (int(x) for x in m.group(1).split(";") if x != ""):
            if c == 0:
                color, bold = "default", False
            elif c == 1:
                bold = True
            elif c == 2:
                color = "dim"
            elif c in CODE:
                color = CODE[c]
        pos = m.end()
    if pos < len(line):
        segs.append((line[pos:], color, bold))
    return segs


def color_of(name: str, bold: bool):
    if name == "default" and bold:
        return PALETTE["white"]
    return PALETTE[name]


# --- layout ------------------------------------------------------------------
SIZE = 22
PAD = 26
reg = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", SIZE)
bold = ImageFont.truetype(r"C:\Windows\Fonts\consolab.ttf", SIZE)
CW = reg.getlength("M")
LH = int(SIZE * 1.42)

plain = [TOK.sub("", ln) for ln in LINES]
max_chars = max(len(p) for p in plain)
W = int(CW * max_chars) + PAD * 2
H = LH * len(LINES) + PAD * 2


def render(upto: int) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    for row in range(upto):
        x, y = PAD, PAD + row * LH
        for txt, cname, b in parse(LINES[row]):
            d.text((x, y), txt, font=(bold if b else reg), fill=color_of(cname, b))
            x += CW * len(txt)
    return img


frames = [render(i) for i in range(1, len(LINES) + 1)]
master = frames[-1].quantize(colors=64, method=Image.MEDIANCUT)
frames_p = [f.quantize(palette=master, dither=Image.NONE) for f in frames]
durations = [110] * (len(frames_p) - 1) + [4000]

OUT.parent.mkdir(exist_ok=True)
frames_p[0].save(OUT, save_all=True, append_images=frames_p[1:],
                 duration=durations, loop=0, optimize=True, disposal=2)
print(f"wrote {OUT}  ({OUT.stat().st_size // 1024} KB, {len(frames_p)} frames, {W}x{H})")
