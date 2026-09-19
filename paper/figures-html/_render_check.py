#!/usr/bin/env python3
"""_render_check.py — render an HTML figure with headless Chrome and verify the PNG.
Temporary work file for the round-19 figure rebuild (deleted afterwards).

Usage:
  python _render_check.py <name> <W> <H> [--out figures/<name>.png]

Checks:
  - PNG dimensions == (3W, 3H)  (device-scale-factor 3, window respected)
  - content bounding box (non-white) with tolerance, so nothing is cut at the edges
  - printed pt/css px at the LaTeX width (343.7pt textwidth; fig-specific include factor)
"""
import os
import subprocess
import sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
FIGS = os.path.abspath(os.path.join(HERE, "..", "figures"))
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PAD = 24  # same tolerance as trim_white.py

INCLUDE = {  # fraction of \textwidth used by the LaTeX include
    "fig_trace": 0.94,
    "fig_tep_perfault": 0.88,
}
TEXTPW = 343.7  # measured in main.pdf (343.7pt placed width)


def main():
    name, w, h = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    out = os.path.join(FIGS, name + ".png")
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    url = "file:///" + os.path.join(HERE, name + ".html").replace("\\", "/")
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           f"--force-device-scale-factor=3", f"--window-size={w},{h}",
           f"--screenshot={out}", url]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if not os.path.exists(out):
        print("RENDER FAILED", r.stderr[-2000:])
        sys.exit(1)
    im = Image.open(out).convert("RGB")
    ok = True
    if im.size != (3 * w, 3 * h):
        print(f"SIZE MISMATCH: got {im.size}, want {(3*w, 3*h)}")
        ok = False
    gray = im.convert("L")
    bbox = gray.point(lambda x: 0 if x > 248 else 255).getbbox()
    if bbox is None:
        print("BLANK IMAGE")
        sys.exit(1)
    l, t, rr, b = bbox
    margins = dict(left=l, top=t, right=im.size[0] - rr, bottom=im.size[1] - b)
    # content must not touch the window edges (would indicate clipping)
    for side, m in margins.items():
        if m < 2:
            print(f"CONTENT TOUCHES {side} EDGE (margin {m}px) — possible clip")
            ok = False
    inc = INCLUDE.get(name, 1.0)
    ppt = TEXTPW * inc / (im.size[0] / 3.0)
    print(f"{name}: png {im.size[0]}x{im.size[1]} css {im.size[0]/3:.0f}x{im.size[1]/3:.0f} "
          f"content bbox margins {margins} | scale {ppt:.4f} pt/css-px "
          f"(include {inc:.2f})")
    print("OK" if ok else "CHECK FAILED")
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
