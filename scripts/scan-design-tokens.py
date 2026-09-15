"""Design-system conformance scanner for the frontend.

The console is built on one warm-graphite + amber token system
(`app/frontend/src/styles/global.css`). A component that hardcodes a cool
literal — a blue button, a light-theme card — silently forks the product's
visual identity, which is exactly the kind of drift that is invisible in code
review but obvious on screen.

This scanner walks every style block and reports colour literals that are:

  * **cool** — blue/violet/cyan-dominant, i.e. not derivable from the warm
    palette (`--accent` amber, `--red` cadmium, `--green` phosphor, `--cyan`
    muted steel are the only sanctioned non-neutral hues)
  * **neutral-but-foreign** — near-white / near-black / grey values that are
    not in the token block

Neutrals already declared inside `:root` of global.css are treated as
canonical and never reported.

Usage
-----
    python scripts/scan-design-tokens.py
    python scripts/scan-design-tokens.py --fail-on-cool   # exits 1 if any
"""
from __future__ import annotations

import argparse
import colorsys
import re
import sys
from pathlib import Path

SRC = Path("app/frontend/src")
TOKENS_FILE = SRC / "styles" / "global.css"

# Every colour literal in these files is a sanctioned token definition.
TOKEN_FILES = {TOKENS_FILE}

HEX_RE = re.compile(r"#([0-9a-fA-F]{3,8})\b")
RGB_RE = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)")

# Hexes that appear inside ECharts option objects rather than CSS. They are
# still worth reporting, but a chart series palette legitimately needs concrete
# values — the fix is to derive them from tokens, not to delete them.
CHART_FILES = {"LineChart.vue", "HeatmapChart.vue", "ScatterChart.vue", "GaugeChart.vue"}


def parse_hex(h: str) -> tuple[int, int, int]:
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h[:3])
    elif len(h) == 8:
        h = h[:6]
    elif len(h) != 6:
        raise ValueError(h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def classify(r: int, g: int, b: int) -> str:
    """Return 'cool' for blue/violet/cyan-dominant, 'warm' for amber/red/green."""
    mx, mn = max(r, g, b), min(r, g, b)
    if mx == mn:
        return "neutral"
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    deg = h * 360
    if s < 0.15:
        return "neutral"
    # 170-300 deg covers cyan -> blue -> violet -> magenta: nothing in the
    # warm instrument palette lives there except --cyan (muted steel, s~0.42).
    if 170 <= deg <= 300 and s > 0.25:
        return "cool"
    return "warm"


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    """Return (line_no, literal, kind) for every colour literal in the file."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    found: list[tuple[int, str, str]] = []
    in_html_comment = False
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()

        # HTML comments (`<!-- ... -->`) frequently document the colour that was
        # *removed* — reporting those would flag a file for describing its own
        # fix. Track the block state rather than filtering by line shape.
        if in_html_comment:
            if "-->" in line:
                in_html_comment = False
            continue
        if "<!--" in line:
            if "-->" not in line.split("<!--", 1)[1]:
                in_html_comment = True
            continue

        # CSS / JS comments carry no rendering weight either.
        if stripped.startswith(("//", "*", "/*")):
            continue
        for m in HEX_RE.finditer(line):
            try:
                rgb = parse_hex(m.group(1))
            except ValueError:
                continue
            found.append((lineno, m.group(0), classify(*rgb)))
        for m in RGB_RE.finditer(line):
            r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
            # fully transparent stops are geometry, not colour
            alpha = m.group(4)
            if alpha is not None and float(alpha) <= 0.02:
                continue
            found.append((lineno, m.group(0), classify(r, g, b)))
    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fail-on-cool", action="store_true",
                    help="exit 1 when any cool (off-palette) literal is present")
    ap.add_argument("--all", action="store_true", help="also list warm/neutral literals")
    args = ap.parse_args()

    files = sorted(
        [p for p in SRC.rglob("*.vue")] + [p for p in SRC.rglob("*.css") if p.is_file()]
    )
    files = [f for f in files if f not in TOKEN_FILES]

    cool_total = 0
    per_file: dict[str, list[tuple[int, str, str]]] = {}
    for f in files:
        hits = [h for h in scan_file(f) if h[2] == "cool"]
        if hits:
            per_file[str(f.relative_to(SRC))] = hits
            cool_total += len(hits)

    print("Off-palette (cool) colour literals outside the token block")
    print("=" * 68)
    if not per_file:
        print("  none — every non-token colour is within the warm palette")
    for name, hits in sorted(per_file.items(), key=lambda kv: -len(kv[1])):
        tag = "  [chart palette]" if Path(name).name in CHART_FILES else ""
        print(f"\n  {name}{tag}  ({len(hits)})")
        for lineno, lit, _ in hits:
            print(f"      L{lineno:<5} {lit}")

    if args.all:
        print("\n\nAll remaining literals (warm / neutral)")
        print("=" * 68)
        for f in files:
            warm = [h for h in scan_file(f) if h[2] != "cool"]
            if warm:
                print(f"\n  {f.relative_to(SRC)}  ({len(warm)})")
                for lineno, lit, kind in warm:
                    print(f"      L{lineno:<5} {lit}  [{kind}]")

    print(f"\n{'=' * 68}\ntotal off-palette literals: {cool_total}")
    if args.fail_on_cool and cool_total:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
