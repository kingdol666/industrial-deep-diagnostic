"""Render the deck's structural figures.

Figures are authored at the CSS size they will occupy on the slide, so a font
size written here is the font size the reader actually sees — no downscaling.
(An earlier version drew the roadmap at 1660px and scaled it to 1014px on the
slide, which made the command text unreadable.)

Output: ../assets/<name>.png  (DPR 2 for crispness)
"""
from __future__ import annotations

import os

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "assets"))
from pathlib import Path as _P
_BASE = _P(HERE).resolve().parent
def safe_path(x):
    p = _P(x).resolve(); p.relative_to(_BASE); return p
def safe_open(x, mode="r", **kw):
    return open(safe_path(x), mode, **kw)
DPR = 2

BG = "#F7F4EC"
INK = "#1D1B16"
MUT = "#6B655A"
AMBER = "#B8730F"
FONT = "'Microsoft YaHei','Source Han Sans SC',system-ui,sans-serif"
MONO = "'Cascadia Mono','Consolas','Courier New',monospace"


def roadmap(w=1152, h=534):
    """Five onboarding steps as readable rows."""
    steps = [
        ("1", "查依赖", "确认四个依赖都达标",
         ["node --version", "npm --version", "python --version", "uv --version"],
         "四条全绿即可继续"),
        ("2", "装项目", "克隆仓库、装依赖、注册命令",
         ["git clone …", "cd industrial-deep-diagnostic", "npm install", "npm link"],
         "多出全局命令 ind-diag"),
        ("3", "起服务", "一条命令拉起三个服务",
         ["ind-diag start --all --detach"],
         "三服务后台常驻并立刻返回"),
        ("4", "验状态", "确认三个服务真的活着",
         ["ind-diag status", "curl :3210/api/health"],
         "三行都是 running / healthy"),
        ("5", "开浏览器", "注册账号，开始第一次诊断",
         ["http://localhost:5180"],
         "上传数据 → 点开始诊断"),
    ]
    rows = []
    for n, title, sub, cmds, expect in steps:
        chips = "".join(f'<span class="ch">{c}</span>' for c in cmds)
        rows.append(f"""<div class="row">
          <div class="n">{n}</div>
          <div class="tt"><div class="t">{title}</div><div class="s">{sub}</div></div>
          <div class="cmds">{chips}</div>
          <div class="ex">{expect}</div>
        </div>""")
    inner = f"""
<div class="hd"><span class="k">QUICK START</span>
  <span class="sub">五步上手 · 全程命令行 · 首次启动会自动装依赖，多花 1–3 分钟</span></div>
<div class="list">{''.join(rows)}</div>"""
    css = f"""
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:{BG};font-family:{FONT};color:{INK};-webkit-font-smoothing:antialiased}}
.wrap{{width:{w}px;height:{h}px;display:flex;flex-direction:column}}
.hd{{height:44px;display:flex;align-items:baseline;gap:14px}}
.k{{font:700 12.5px {FONT};letter-spacing:.22em;color:{AMBER}}}
.sub{{font:400 14.5px {FONT};color:{MUT}}}
.list{{flex:1;display:flex;flex-direction:column;gap:11px}}
.row{{height:91px;background:#fff;border:1px solid #E3DCCB;border-left:5px solid {AMBER};
  border-radius:11px;padding:0 18px;display:flex;align-items:center;
  box-shadow:0 2px 8px rgba(0,0,0,.045)}}
.n{{width:40px;height:40px;border-radius:10px;background:{INK};color:{AMBER};
  font:800 19px/40px {FONT};text-align:center;flex:0 0 40px}}
.tt{{width:182px;margin-left:14px;flex:0 0 182px}}
.t{{font:700 19px {FONT}}}
.s{{font:400 13.5px {FONT};color:{MUT};margin-top:2px}}
.cmds{{flex:1;display:flex;flex-wrap:wrap;gap:7px;align-items:center}}
.ch{{background:#14130F;color:#D9E8A8;font:400 14px {MONO};
  padding:5px 10px;border-radius:6px;white-space:nowrap}}
.ex{{width:236px;flex:0 0 236px;font:600 15px {FONT};color:#8A5608;text-align:right}}
"""
    return (f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{css}</style>'
            f'</head><body><div class="wrap">{inner}</div></body></html>')


JOBS = [("d_roadmap", roadmap(), 1152, 534)]


def main() -> int:
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        for name, html, w, h in JOBS:
            path = os.path.join(HERE, name + ".html")
            with safe_open(path, "w", encoding="utf-8") as f:
                f.write(html)
            pg = b.new_context(viewport={"width": w, "height": h},
                               device_scale_factor=DPR).new_page()
            pg.goto("file:///" + path.replace(os.sep, "/"), wait_until="load")
            pg.wait_for_timeout(500)
            pg.screenshot(path=os.path.join(OUT, name + ".png"))
            print(f"  + {name}.png  {w}x{h}", flush=True)
            pg.close()
        b.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
