"""Render the project's .slide files to PNG for visual QA.

`slidep screenshot` is broken in this environment (it resolves its renderer from
a POSIX /workspace path), so this script does the visual check instead: it
translates the restricted SlideDSL subset used by this deck (Slide / Box / Text /
Image with an inline style object) into plain HTML and screenshots it at the
real canvas size.

It is a *preview* only. The authoritative renderer is `slidep upsert-dsl`.
"""
from __future__ import annotations

import glob
import json
import os
import re

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
SLIDES = os.path.join(HERE, "slides")
OUT = os.path.join(HERE, "_preview")
from pathlib import Path as _P
_BASE = _P(HERE).resolve()
def safe_path(x):
    p = _P(x).resolve(); p.relative_to(_BASE); return p
def safe_open(x, mode="r", **kw):
    return open(safe_path(x), mode, **kw)
W, H = 1280, 720

UNITLESS = {"lineHeight", "fontWeight", "opacity", "flex", "flexGrow", "flexShrink",
            "zIndex", "order", "fontStyle"}


def kebab(name: str) -> str:
    return re.sub(r"[A-Z]", lambda m: "-" + m.group(0).lower(), name)


def style_to_css(raw: str) -> str:
    """`{ a: 1, b: 'x' }` (JS object literal) -> `a:1px;b:x`."""
    out = []
    # split on commas that are not inside quotes
    depth, buf, parts = 0, "", []
    in_s = None
    for ch in raw:
        if in_s:
            buf += ch
            if ch == in_s:
                in_s = None
            continue
        if ch in "\"'":
            in_s = ch
            buf += ch
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(buf)
            buf = ""
        else:
            buf += ch
    parts.append(buf)

    for p in parts:
        if ":" not in p:
            continue
        k, v = p.split(":", 1)
        k, v = k.strip(), v.strip()
        if not k:
            continue
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        elif re.fullmatch(r"-?\d+(\.\d+)?", v) and k not in UNITLESS:
            v = v + "px"
        out.append(f"{kebab(k)}:{v}")
    return ";".join(out)


TAG_RE = re.compile(r"<(/?)([A-Za-z]+)((?:\s+[^>]*?)?)(/?)>", re.S)
# style bodies are parked between two sentinels so their inner quotes can never
# terminate an attribute value
OPEN, CLOSE = "\x01", "\x02"
ATTR_RE = re.compile(r"(\w+)=(?:\x01(.*?)\x02|\"(?:[^\"]*)\"|'(?:[^']*)')", re.S)

VOID = {"Image", "FAIcon", "br"}


def convert(src: str) -> str:
    """Translate the deck's DSL subset into HTML."""
    # park every style body between sentinels so quotes inside it stay inert
    src = re.sub(r"style=\{\{(.*?)\}\}",
                 lambda m: "style=" + OPEN + m.group(1) + CLOSE, src, flags=re.S)

    out = []
    pos = 0
    for m in TAG_RE.finditer(src):
        out.append(src[pos:m.start()])
        pos = m.end()
        closing, tag, attrs, selfclose = m.group(1), m.group(2), m.group(3), m.group(4)
        if tag == "br":
            out.append("<br/>")
            continue

        style = ""
        for am in ATTR_RE.finditer(attrs or ""):
            if am.group(1) == "style" and am.group(2) is not None:
                style = style_to_css(am.group(2).strip().strip("{}"))
        # every Box/Slide defaults to display:flex + column (SlideDSL semantics);
        # an explicit flexDirection in the style overrides the column above
        if tag in ("Box", "Slide"):
            style = "display:flex;flex-direction:column" + (";" + style if style else "")
        css = f' style="{style}"' if style else ""

        if tag == "Image":
            srcm = re.search(r"src=(?:\x01(.*?)\x02|\"([^\"]+)\")", attrs or "")
            if srcm and srcm.group(2) is not None:
                srcm = None
            srcm = re.search(r"src=\"([^\"]+)\"", attrs or "")
            s = srcm.group(1) if srcm else ""
            out.append(f'<img src="{s}"{css}/>')
        elif closing:
            out.append(f"</div>")
        elif tag == "Text":
            out.append(f"<div class=\"tx\"{css}>")
        elif selfclose:
            out.append(f"<div{css}></div>")
        else:
            out.append(f"<div{css}>")
    out.append(src[pos:])

    body = "".join(out)
    # the DSL is JSX: strip `{/* ... */}` comments and lone `{}` expressions
    body = re.sub(r"\{/\*.*?\*/\}", "", body, flags=re.S)
    # `src` in the DSL is relative to the project root, so the preview must be too
    base = "file:///" + HERE.replace(os.sep, "/") + "/"
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"/>
<base href="{base}"/><style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:{W}px;height:{H}px;overflow:hidden;background:#fff;
  font-family:'Microsoft YaHei','Source Han Sans SC',sans-serif}}
body > div{{width:{W}px;height:{H}px;display:flex;flex-direction:column}}
.tx{{white-space:pre-wrap}}
img{{display:block}}
</style></head><body>{body}</body></html>"""


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    html_dir = os.path.join(HERE, "_preview-html")
    os.makedirs(html_dir, exist_ok=True)
    files = sorted(glob.glob(os.path.join(SLIDES, "*.slide")))
    if not files:
        print("no slides found")
        return 1

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": W, "height": H}, device_scale_factor=2)
        for f in files:
            name = os.path.splitext(os.path.basename(f))[0]
            html = convert(open(f, encoding="utf-8").read())
            hp = os.path.join(html_dir, name + ".html")
            with safe_open(hp, "w", encoding="utf-8") as fh:
                fh.write(html)
            pg = ctx.new_page()
            pg.goto("file:///" + hp.replace(os.sep, "/"), wait_until="load")
            pg.wait_for_timeout(450)
            # report any content that spills past the canvas
            spill = pg.evaluate(
                """() => {
                     // absolute decorations are allowed to bleed; only layout
                     // children must stay inside the canvas
                     const root = document.body.firstElementChild;
                     let right = 0, bottom = 0;
                     root.querySelectorAll('*').forEach(el => {
                       const cs = getComputedStyle(el);
                       if (cs.position === 'absolute') return;
                       const r = el.getBoundingClientRect();
                       right = Math.max(right, r.right);
                       bottom = Math.max(bottom, r.bottom);
                     });
                     // fixed-height boxes whose content no longer fits
                     const ov = [];
                     root.querySelectorAll('div').forEach(el => {
                       const cs = getComputedStyle(el);
                       if (cs.position === 'absolute') return;
                       const h = parseFloat(cs.height);
                       if (!h || cs.height === 'auto') return;
                       if (el.scrollHeight > el.clientHeight + 1) {
                         ov.push((el.textContent||'').slice(0,26).replace(/\s+/g,' ')
                                 + ' |' + el.clientHeight + '<' + el.scrollHeight);
                       }
                     });
                     return { h: Math.ceil(bottom), w: Math.ceil(right), ov };
                   }"""
            )
            bad = []
            if spill["h"] > H or spill["w"] > W:
                bad.append(f"CANVAS {spill['h']}x{spill['w']}")
            bad += spill.get("ov", [])
            flag = ("  <-- " + " ;; ".join(bad)) if bad else ""
            pg.screenshot(path=os.path.join(OUT, name + ".png"))
            print(f"  + {name}.png{flag}", flush=True)
            pg.close()
        b.close()
    print(f"\n{len(files)} previews -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
