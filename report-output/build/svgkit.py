"""Tiny SVG helper for the report diagrams. Original drawing code; renders to PNG through headless Chromium.
Canvas widths are kept near 820 px so that text stays legible when the figure is scaled to the 16 cm text width."""
import html, os, sys
from pathlib import Path

FONT = "Arial, Helvetica, sans-serif"
INK = "#111111"

PALETTE = {
    "white": ("#ffffff", "#222222"),
    "blue": ("#e3eefb", "#2a5d9f"),
    "green": ("#e2f3e4", "#2f7d3a"),
    "yellow": ("#fff4cf", "#a67c00"),
    "red": ("#fbe3e3", "#b3261e"),
    "grey": ("#eeeeee", "#555555"),
    "purple": ("#efe6f8", "#6a3d9a"),
    "orange": ("#fde8d3", "#c25e00"),
}


def esc(s):
    return html.escape(str(s), quote=False)


class Canvas:
    def __init__(self, w, h, title=""):
        self.w, self.h = w, h
        self.items = []
        self.defs = (
            '<defs>'
            '<marker id="ah" markerUnits="userSpaceOnUse" markerWidth="11" markerHeight="9" refX="10" refY="4.5" orient="auto"><path d="M0,0 L11,4.5 L0,9 z" fill="#222"/></marker>'
            '<marker id="ahr" markerUnits="userSpaceOnUse" markerWidth="11" markerHeight="9" refX="10" refY="4.5" orient="auto"><path d="M0,0 L11,4.5 L0,9 z" fill="#b3261e"/></marker>'
            '<marker id="ahg" markerUnits="userSpaceOnUse" markerWidth="11" markerHeight="9" refX="10" refY="4.5" orient="auto"><path d="M0,0 L11,4.5 L0,9 z" fill="#2f7d3a"/></marker>'
            '</defs>'
        )

    # ---- primitives -------------------------------------------------
    def text(self, x, y, s, size=16, anchor="middle", bold=False, color=INK, italic=False, lh=None, bg=False):
        lines = str(s).split("\n")
        if bg:
            tw = max(len(l) for l in lines) * size * 0.52 + 8
            th = len(lines) * size * 1.22 + 2
            bx = x - tw / 2 if anchor == "middle" else x - 4
            self.items.append(f'<rect x="{bx:.1f}" y="{y - th / 2:.1f}" width="{tw:.1f}" height="{th:.1f}" fill="#ffffff" fill-opacity="0.92"/>')
        lh = lh or size * 1.22
        y0 = y - (len(lines) - 1) * lh / 2
        tsp = "".join(
            f'<tspan x="{x}" y="{y0 + i * lh:.1f}">{esc(l)}</tspan>' for i, l in enumerate(lines)
        )
        self.items.append(
            f'<text font-family="{FONT}" font-size="{size}" text-anchor="{anchor}" dominant-baseline="central" '
            f'font-weight="{"700" if bold else "400"}" font-style="{"italic" if italic else "normal"}" fill="{color}">{tsp}</text>'
        )

    def box(self, x, y, w, h, label="", color="white", size=16, bold=False, rx=8, dashed=False, sub=None, lw=1.6):
        fill, stroke = PALETTE[color]
        dash = ' stroke-dasharray="7,5"' if dashed else ""
        self.items.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{lw}"{dash}/>'
        )
        if label:
            if sub:
                self.text(x + w / 2, y + h / 2 - size * 0.62, label, size, bold=True)
                self.text(x + w / 2, y + h / 2 + size * 0.78, sub, size - 3, color="#333333")
            else:
                self.text(x + w / 2, y + h / 2, label, size, bold=bold)

    def titled(self, x, y, w, h, title, body, color="white", size=15, bsize=14, lh=19):
        self.box(x, y, w, h, "", color)
        self.text(x + w / 2, y + 20, title, size, bold=True)
        self.text(x + w / 2, y + 22 + (h - 22) / 2 + 2, body, bsize, lh=lh)

    def zone(self, x, y, w, h, label, color="grey", size=15):
        fill, stroke = PALETTE[color]
        self.items.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" fill-opacity="0.45" stroke="{stroke}" '
            f'stroke-width="1.8" stroke-dasharray="9,6"/>'
        )
        self.text(x + 12, y + 16, label, size, anchor="start", bold=True, color=stroke)

    def line(self, pts, label=None, dashed=False, color="#222", arrow=True, lpos=0.5, loff=(0, -10), size=14, both=False, lbg=True, lw=1.8):
        d = "M" + " L".join(f"{x},{y}" for x, y in pts)
        mk = {"#222": "ah", "#b3261e": "ahr", "#2f7d3a": "ahg"}.get(color, "ah")
        dash = ' stroke-dasharray="7,5"' if dashed else ""
        ms = f' marker-end="url(#{mk})"' if arrow else ""
        mst = f' marker-start="url(#{mk})"' if both else ""
        self.items.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{lw}"{dash}{ms}{mst}/>')
        if label:
            # label sits on the longest segment
            segs = list(zip(pts[:-1], pts[1:]))
            a, b = max(segs, key=lambda s: abs(s[0][0] - s[1][0]) + abs(s[0][1] - s[1][1]))
            lx = a[0] + (b[0] - a[0]) * lpos + loff[0]
            ly = a[1] + (b[1] - a[1]) * lpos + loff[1]
            if lbg:
                tw = max(len(l) for l in label.split("\n")) * size * 0.54 + 8
                th = len(label.split("\n")) * size * 1.22 + 2
                self.items.append(f'<rect x="{lx - tw / 2:.1f}" y="{ly - th / 2:.1f}" width="{tw:.1f}" height="{th:.1f}" fill="#ffffff" fill-opacity="0.9"/>')
            self.text(lx, ly, label, size, color="#222")

    def circle(self, cx, cy, r, label="", color="white", size=14):
        fill, stroke = PALETTE[color]
        self.items.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="1.8"/>')
        if label:
            self.text(cx, cy, label, size, bold=True)

    def diamond(self, cx, cy, w, h, label="", color="yellow", size=14):
        fill, stroke = PALETTE[color]
        pts = f"{cx},{cy - h / 2} {cx + w / 2},{cy} {cx},{cy + h / 2} {cx - w / 2},{cy}"
        self.items.append(f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="1.6"/>')
        self.text(cx, cy, label, size)

    def cylinder(self, x, y, w, h, label, color="blue", size=16, sub=None):
        fill, stroke = PALETTE[color]
        e = 12
        self.items.append(
            f'<path d="M{x},{y + e} v{h - 2 * e} a{w / 2},{e} 0 0 0 {w},0 v{-(h - 2 * e)} a{w / 2},{e} 0 0 0 {-w},0 z" fill="{fill}" stroke="{stroke}" stroke-width="1.6"/>'
            f'<ellipse cx="{x + w / 2}" cy="{y + e}" rx="{w / 2}" ry="{e}" fill="{fill}" stroke="{stroke}" stroke-width="1.6"/>'
        )
        if sub:
            self.text(x + w / 2, y + h / 2 + 4, label, size, bold=True)
            self.text(x + w / 2, y + h / 2 + 4 + size * 1.2, sub, size - 3, color="#333")
        else:
            self.text(x + w / 2, y + h / 2 + 6, label, size, bold=True)

    def rect_raw(self, x, y, w, h, fill, stroke="none", opacity=1, rx=0, lw=1):
        self.items.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" fill-opacity="{opacity}" stroke="{stroke}" stroke-width="{lw}"/>')

    def svg(self):
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}">'
            f'<rect width="100%" height="100%" fill="#ffffff"/>{self.defs}{"".join(self.items)}</svg>'
        )


# ---- sequence diagram helper -----------------------------------------------
def sequence(c, parts, msgs, top=20, head_h=46, step=44, x0=60, x1=None, size=14):
    """parts: list of (name, color). msgs: list of (from_idx, to_idx, text, kind) kind in {'', 'dash', 'self', 'note', 'bad'}."""
    x1 = x1 or c.w - 60
    n = len(parts)
    xs = [x0 + (x1 - x0) * i / (n - 1) for i in range(n)] if n > 1 else [c.w / 2]
    bw = min(150, (x1 - x0) / max(n - 1, 1) - 14)
    bottom = top + head_h + step * (len(msgs) + 1)
    for (name, color), x in zip(parts, xs):
        c.box(x - bw / 2, top, bw, head_h, name, color, size=size, bold=True)
        c.items.append(f'<line x1="{x}" y1="{top + head_h}" x2="{x}" y2="{bottom}" stroke="#777" stroke-width="1.3" stroke-dasharray="5,5"/>')
    y = top + head_h + step * 0.8
    for a, b, t, kind in msgs:
        if kind == "note":
            xa = xs[a]
            wd = max(len(l) for l in t.split("\n")) * size * 0.55 + 20
            ht = len(t.split("\n")) * size * 1.25 + 12
            c.box(xa - wd / 2, y - ht / 2, wd, ht, t, "yellow", size=size - 1, rx=4, lw=1.2)
            y += step * max(1, ht / step) * 0.95
            continue
        col = "#b3261e" if kind == "bad" else "#222"
        if kind == "self":
            xa = xs[a]
            c.line([(xa, y - 8), (xa + 46, y - 8), (xa + 46, y + 10), (xa, y + 10)], None, color=col)
            c.text(xa + 54, y, t, size - 1, anchor="start", bg=True)
        else:
            c.line([(xs[a], y), (xs[b], y)], None, dashed=(kind == "dash"), color=col)
            mid = (xs[a] + xs[b]) / 2
            c.text(mid, y - 13, t, size - 1, color=col, bg=True)
        y += step
    return bottom


# ---- rendering ----------------------------------------------------------------
def render_all(jobs, outdir):
    """jobs: list of (name, Canvas). Writes name.svg and name.png (2x) into outdir."""
    from playwright.sync_api import sync_playwright

    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, cv in jobs:
            svg = cv.svg()
            (outdir / f"{name}.svg").write_text(svg)
            ctx = b.new_context(viewport={"width": cv.w, "height": cv.h}, device_scale_factor=2.4)
            pg = ctx.new_page()
            pg.set_content(f'<html><body style="margin:0;background:#fff">{svg}</body></html>')
            pg.screenshot(path=str(outdir / f"{name}.png"), clip={"x": 0, "y": 0, "width": cv.w, "height": cv.h})
            ctx.close()
        b.close()
