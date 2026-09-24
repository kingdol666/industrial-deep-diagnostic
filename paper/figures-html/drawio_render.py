#!/usr/bin/env python3
"""drawio_render.py — render the paper's own .drawio subset to SVG.

The two flowchart figures (fig_architecture, fig_pipeline) are authored as
.drawio files (editable in draw.io desktop). This script renders exactly the
mxGraph subset those files use, so the paper's PNG is a faithful export of the
.drawio source — no manual duplication of geometry.

Supported subset (everything the paper's diagrams use):
  vertices : rect/rounded rect, fillColor, strokeColor, strokeWidth, dashed,
             arcSize (rounded corner radius), opacity, text-only cells
             (style contains "text;"), label align / verticalAlign / fontSize /
             fontColor / fontStyle(1=bold) / spacing / spacingTop, whiteSpace=wrap,
             label value with \n line breaks.
  edges    : source/target vertex ids, exitX/exitY/entryX/entryY anchors,
             explicit waypoints (Array as="points"), strokeColor, strokeWidth,
             dashed, endArrow=none|classic, opacity. Orthogonal polylines only
             (the renderer draws source -> waypoints -> target as given).

Usage:  python drawio_render.py <file.drawio> <out.svg> [scale]
        python drawio_render.py --all           # render every .drawio here
Wrapper HTML for screenshotting is written next to the SVG as <name>_svg.html.
"""
import html
import re
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

INK = "#1a1a1a"

def parse_style(s):
    out = {}
    if not s:
        return out
    for part in s.split(";"):
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
            out[k] = v
        else:
            out[part] = True
    return out

def esc(t):
    return html.escape(t, quote=True)

class Renderer:
    def __init__(self):
        self.vertices = {}   # id -> dict(x,y,w,h,style,value,parent)
        self.edges = []
        self.z_order = []    # (kind, id) in document order

    def load(self, path):
        tree = ET.parse(path)
        root = tree.getroot()
        model = root.find(".//mxGraphModel")
        for cell in model.find("root"):
            cid = cell.get("id")
            if cid in ("0", "1"):
                continue
            style = parse_style(cell.get("style", ""))
            if cell.get("vertex") == "1":
                geo = cell.find("mxGeometry")
                self.vertices[cid] = {
                    "x": float(geo.get("x", 0)), "y": float(geo.get("y", 0)),
                    "w": float(geo.get("width", 10)), "h": float(geo.get("height", 10)),
                    "style": style, "value": cell.get("value") or "",
                }
                self.z_order.append(("v", cid))
            elif cell.get("edge") == "1":
                geo = cell.find("mxGeometry")
                pts = []
                if geo is not None:
                    arr = geo.find('Array[@as="points"]')
                    if arr is not None:
                        pts = [(float(p.get("x")), float(p.get("y"))) for p in arr.findall("mxPoint")]
                self.edges.append({
                    "src": cell.get("source"), "tgt": cell.get("target"),
                    "style": style, "value": cell.get("value") or "", "points": pts,
                })
                self.z_order.append(("e", len(self.edges) - 1))
        pw = model.get("pageWidth")
        ph = model.get("pageHeight")
        return (float(pw), float(ph)) if pw and ph else self._auto_bounds()

    def _auto_bounds(self):
        x2 = max((v["x"] + v["w"]) for v in self.vertices.values()) if self.vertices else 800
        y2 = max((v["y"] + v["h"]) for v in self.vertices.values()) if self.vertices else 600
        return (x2 + 20, y2 + 20)

    # ---------- geometry helpers ----------
    def anchor(self, vid, fx, fy):
        v = self.vertices[vid]
        return (v["x"] + v["w"] * fx, v["y"] + v["h"] * fy)

    def edge_points(self, e):
        sx, sy = self.anchor(e["src"], float(e["style"].get("exitX", 0.5)),
                             float(e["style"].get("exitY", 0.5)))
        tx, ty = self.anchor(e["tgt"], float(e["style"].get("entryX", 0.5)),
                             float(e["style"].get("entryY", 0.5)))
        pts = [(sx, sy)] + list(e["points"]) + [(tx, ty)]
        # drop consecutive duplicates
        out = [pts[0]]
        for p in pts[1:]:
            if abs(p[0] - out[-1][0]) > 0.4 or abs(p[1] - out[-1][1]) > 0.4:
                out.append(p)
        return out

    # ---------- svg ----------
    def render(self, w, h):
        shapes, texts = [], []
        for kind, ref in self.z_order:
            if kind == "v":
                self.render_vertex(self.vertices[ref], shapes, texts)
            else:
                self.render_edge(self.edges[ref], shapes, texts)
        return ("\n".join([
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:g}" height="{h:g}" '
            f'viewBox="0 0 {w:g} {h:g}">',
            '<rect width="100%" height="100%" fill="#ffffff"/>',
        ]) + "\n" + "\n".join(shapes) + "\n" + "\n".join(texts) + "\n</svg>")

    def render_vertex(self, v, shapes, texts):
        st = v["style"]
        x, y, w, h = v["x"], v["y"], v["w"], v["h"]
        if "text" not in st:
            fill = st.get("fillColor", "none")
            fill = f'fill="{fill}"' if fill != "none" else 'fill="none"'
            stroke = st.get("strokeColor", "#000000")
            sw = float(st.get("strokeWidth", 1))
            dash = ' stroke-dasharray="7 4"' if st.get("dashed") == "1" else ""
            op = f' opacity="{st.get("opacity", 1)}"' if "opacity" in st else ""
            if st.get("rounded") == "1":
                r = float(st.get("arcSize", 8))
                if r <= 1:  # drawio arcSize is % of min(w,h) when <=1
                    r = r * min(w, h)
                r = min(r, min(w, h) / 2)
                shapes.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{r:g}" ry="{r:g}" {fill} stroke="{stroke}" stroke-width="{sw:g}"{dash}{op}/>')
            else:
                shapes.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" {fill} stroke="{stroke}" stroke-width="{sw:g}"{dash}{op}/>')
        if v["value"]:
            self.render_label(v, texts)

    # approximate Arial advance widths (em fractions) for wrap decisions
    _CW = {" ": 0.28, ".": 0.28, ",": 0.28, ":": 0.28, ";": 0.28, "'": 0.19, "l": 0.22,
           "i": 0.22, "j": 0.22, "t": 0.28, "f": 0.28, "r": 0.33, "-": 0.33, "·": 0.30,
           "(": 0.33, ")": 0.33, "/": 0.28, "|": 0.20, "!": 0.28, "I": 0.28, "1": 0.556}
    _CW_DEFAULT = 0.56

    @classmethod
    def text_width(cls, s, fs):
        w = 0.0
        for c in s:
            if c in cls._CW:
                w += cls._CW[c]
            elif c.isupper():
                w += 0.67
            elif c.isdigit():
                w += 0.556
            elif c == "_":
                w += 0.50
            else:
                w += cls._CW_DEFAULT
        return w * fs

    def wrap_line(self, line, maxw, fs):
        if self.text_width(line, fs) <= maxw:
            return [line]
        words = line.split(" ")
        out, cur = [], ""
        for w_ in words:
            trial = (cur + " " + w_) if cur else w_
            if self.text_width(trial, fs) <= maxw or not cur:
                cur = trial
            else:
                out.append(cur)
                cur = w_
        if cur:
            out.append(cur)
        return out

    def render_label(self, v, texts):
        st = v["style"]
        x, y, w, h = v["x"], v["y"], v["w"], v["h"]
        fs = float(st.get("fontSize", 12))
        color = st.get("fontColor", INK)
        bold = ' font-weight="700"' if st.get("fontStyle") == "1" else ""
        align = st.get("align", "center")
        valign = st.get("verticalAlign", "middle")
        anchor = {"left": "start", "center": "middle", "right": "end"}[align]
        pad = 4 + float(st.get("spacingLeft", 0))
        pad_r = 6
        tx = {"left": x + pad, "center": x + w / 2, "right": x + w - pad_r}[align]
        maxw = w - pad - pad_r
        spacing_top = float(st.get("spacingTop", 0))
        lines = []
        for raw in v["value"].replace("<br>", "\n").split("\n"):
            lines.extend(self.wrap_line(raw, maxw, fs))
        n = len(lines)
        lh = fs * 1.28
        total = n * lh
        if valign == "top":
            ty = y + spacing_top + lh * 0.82
        elif valign == "bottom":
            ty = y + h - spacing_top - (n - 1) * lh - fs * 0.28
        else:
            ty = y + h / 2 - total / 2 + lh * 0.82
        for i, ln in enumerate(lines):
            if ln == "":
                continue
            texts.append(f'<text x="{tx:g}" y="{ty + i * lh:g}" font-family="Arial, Helvetica, sans-serif" '
                         f'font-size="{fs:g}" fill="{color}"{bold} text-anchor="{anchor}">{esc(ln)}</text>')

    def render_edge(self, e, shapes, texts):
        st = e["style"]
        pts = self.edge_points(e)
        color = st.get("strokeColor", "#2b2b2b")
        sw = float(st.get("strokeWidth", 1.5))
        dash = ' stroke-dasharray="8 5"' if st.get("dashed") == "1" else ""
        op = f' opacity="{st.get("opacity", 1)}"' if "opacity" in st else ""
        pl = " ".join(f"{p[0]:g},{p[1]:g}" for p in pts)
        shapes.append(f'<polyline points="{pl}" fill="none" stroke="{color}" stroke-width="{sw:g}"{dash}{op}/>')
        if st.get("endArrow", "classic") != "none":
            (x1, y1), (x2, y2) = pts[-2], pts[-1]
            shapes.append(self._arrow(x1, y1, x2, y2, color, 9 + sw * 1.2))
        if e["value"]:
            mid = pts[len(pts) // 2]
            fs = float(st.get("fontSize", 12))
            texts.append(f'<text x="{mid[0]:g}" y="{mid[1] - 6:g}" font-family="Arial, Helvetica, sans-serif" '
                         f'font-size="{fs:g}" fill="{st.get("fontColor", INK)}" text-anchor="middle">{esc(e["value"])}</text>')

    def _arrow(self, x1, y1, x2, y2, color, size):
        import math
        ang = math.atan2(y2 - y1, x2 - x1)
        ax = x2 - (size * 0.92) * math.cos(ang)
        ay = y2 - (size * 0.92) * math.sin(ang)
        # pull line end back to arrow base
        left = (ax + size * 0.42 * math.cos(ang + math.pi / 2),
                ay + size * 0.42 * math.sin(ang + math.pi / 2))
        right = (ax + size * 0.42 * math.cos(ang - math.pi / 2),
                 ay + size * 0.42 * math.sin(ang - math.pi / 2))
        tip = (x2, y2)
        return (f'<polygon points="{tip[0]:g},{tip[1]:g} {left[0]:.1f},{left[1]:.1f} '
                f'{right[0]:.1f},{right[1]:.1f}" fill="{color}"/>')

def render_file(path, out_svg=None, out_html=None):
    path = Path(path)
    r = Renderer()
    w, h = r.load(path)
    svg = r.render(w, h)
    out_svg = Path(out_svg) if out_svg else path.with_suffix(".svg")
    out_svg.write_text(svg, encoding="utf-8")
    out_html = Path(out_html) if out_html else path.with_name(path.stem + "_svg.html")
    out_html.write_text(
        '<!DOCTYPE html><html><head><meta charset="utf-8"><style>'
        "body{margin:0;padding:0;background:#fff;}"
        f"body{{width:{w:g}px;height:{h:g}px;}}</style></head><body>"
        + svg + "</body></html>", encoding="utf-8")
    print(f"rendered {path.name} -> {out_svg.name} ({w:g}x{h:g})")
    return w, h

if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] != "--all":
        render_file(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        here = Path(__file__).parent
        for f in sorted(here.glob("*.drawio")):
            render_file(f)
