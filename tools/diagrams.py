#!/usr/bin/env python3
"""Generate the rccar documentation diagrams as SVG, then rasterize to PNG.

Cyberpunk HUD style, vector-accurate labels. No third-party Python modules.
Run from the repo root:  python3 tools/diagrams.py (needs rsvg-convert).
"""

import html
import math
import os
import subprocess

BG = "#04060c"
PANEL = "#08111f"
CY = "#22e6ff"
MG = "#ff3ea5"
LM = "#9dff5a"
AM = "#ffb020"
RD = "#ff4d6d"
TX = "#d9f6ff"
MU = "#6c93ad"
GOLD = "#f6c76a"

DISPLAY = "Orbitron, Chakra Petch, sans-serif"
SANS = "Chakra Petch, Liberation Sans, sans-serif"
MONO = "JetBrainsMono Nerd Font, JetBrains Mono, Liberation Mono, monospace"

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "images")


def esc(s):
    return html.escape(str(s), quote=True)


class Svg:
    def __init__(self, w, h, sheet=None, rev="0.2"):
        self.w, self.h = w, h
        self.body = []
        self.defs = []
        self._grads = set()
        self._filters = set()
        self.sheet = sheet
        self.rev = rev

    # ---------- primitives ----------
    def add(self, s):
        self.body.append(s)

    def grad(self, name):
        if name in self._grads:
            return name
        self._grads.add(name)
        if name == "metal":
            self.defs.append(
                '<linearGradient id="metal" x1="0" y1="0" x2="1" y2="1">'
                '<stop offset="0" stop-color="#dfe8f3"/><stop offset="0.35" stop-color="#8b98a8"/>'
                '<stop offset="0.55" stop-color="#c9d4e2"/><stop offset="1" stop-color="#5d6a7a"/>'
                '</linearGradient>')
        elif name == "pcb":
            self.defs.append(
                '<linearGradient id="pcb" x1="0" y1="0" x2="0" y2="1">'
                '<stop offset="0" stop-color="#0e3346"/><stop offset="1" stop-color="#06141f"/>'
                '</linearGradient>')
        elif name == "pcbblue":
            self.defs.append(
                '<linearGradient id="pcbblue" x1="0" y1="0" x2="0" y2="1">'
                '<stop offset="0" stop-color="#123a5c"/><stop offset="1" stop-color="#071a2a"/>'
                '</linearGradient>')
        elif name == "gold":
            self.defs.append(
                '<linearGradient id="gold" x1="0" y1="0" x2="1" y2="0">'
                '<stop offset="0" stop-color="#ffe6a8"/><stop offset="0.5" stop-color="#e0a83c"/>'
                '<stop offset="1" stop-color="#8a5b12"/></linearGradient>')
        elif name == "cellred":
            self.defs.append(
                '<linearGradient id="cellred" x1="0" y1="0" x2="1" y2="0">'
                '<stop offset="0" stop-color="#fa5568"/><stop offset="0.5" stop-color="#c31f35"/>'
                '<stop offset="1" stop-color="#6e0c1a"/></linearGradient>')
        elif name == "bg":
            self.defs.append(
                '<radialGradient id="bg" cx="0.5" cy="0.42" r="0.75">'
                '<stop offset="0" stop-color="#0a1828"/><stop offset="0.6" stop-color="#060b14"/>'
                '<stop offset="1" stop-color="#03050a"/></radialGradient>')
        elif name == "carbon":
            self.defs.append(
                '<pattern id="carbon" width="8" height="8" patternUnits="userSpaceOnUse" '
                'patternTransform="rotate(45)">'
                '<rect width="8" height="8" fill="#0a0f16"/>'
                '<rect width="4" height="4" fill="#111923"/></pattern>')
        return name

    def f_glow(self, big=False):
        name = "glowBig" if big else "glow"
        if name in self._filters:
            return name
        self._filters.add(name)
        sd = 4.5 if big else 3.0
        self.defs.append(
            f'<filter id="{name}" x="-60%" y="-60%" width="220%" height="220%">'
            f'<feGaussianBlur stdDeviation="{sd}" result="b"/>'
            '<feMerge><feMergeNode in="b"/><feMergeNode in="b"/>'
            '<feMergeNode in="SourceGraphic"/></feMerge></filter>')
        return name

    def defs_block(self):
        # grid and vignette are per-sheet, not per-call
        grid = ('<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">'
                '<path d="M 40 0 L 0 0 0 40" fill="none" stroke="#22e6ff" '
                'stroke-opacity="0.055" stroke-width="1"/></pattern>')
        return "<defs>" + grid + "".join(self.defs) + "</defs>"

    def rect(self, x, y, w, h, fill="none", stroke=CY, rx=4, sw=1.2, opacity=1.0, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{sw}" opacity="{opacity}"{d}/>')

    def cut(self, x, y, w, h, cut=12, fill=PANEL, stroke=CY, sw=1.2, opacity=1.0):
        p = (f"M {x+cut},{y} L {x+w-cut},{y} L {x+w},{y+cut} "
             f"L {x+w},{y+h-cut} L {x+w-cut},{y+h} L {x+cut},{y+h} "
             f"L {x},{y+h-cut} L {x},{y+cut} Z")
        self.add(f'<path d="{p}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{opacity}"/>')

    def bracket(self, x, y, w, h, color=CY, size=16, sw=2):
        for (px, py, dx, dy) in [(x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)]:
            self.add(f'<path d="M {px + dx * size} {py} L {px} {py} L {px} {py + dy * size}" '
                     f'fill="none" stroke="{color}" stroke-width="{sw}"/>')

    def text(self, x, y, s, size=14, fill=TX, anchor="start", weight="400", family=SANS,
             spacing=None, opacity=1.0, glow=False):
        sp = f' letter-spacing="{spacing}"' if spacing else ""
        g = f' filter="url(#{self.f_glow()})"' if glow else ""
        self.add(f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" fill="{fill}" '
                 f'text-anchor="{anchor}" font-weight="{weight}" opacity="{opacity}"{sp}{g}>{esc(s)}</text>')

    def wire(self, pts, color=CY, sw=2.6, arrow=False, casing=False, glow=True, dash=None):
        d = "M " + " L ".join(f"{x} {y}" for x, y in pts)
        if casing:
            self.add(f'<path d="{d}" fill="none" stroke="{BG}" stroke-width="{sw + 6}" '
                     f'stroke-linejoin="round" stroke-linecap="round"/>')
        if dash:
            dd = f' stroke-dasharray="{dash}"'
        else:
            dd = ""
        fl = f' filter="url(#{self.f_glow()})"' if glow else ""
        self.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" '
                 f'stroke-linejoin="round" stroke-linecap="round"{dd}{fl}/>')
        if arrow:
            self.arrowhead(pts[-2], pts[-1], color, sw)

    def arrowhead(self, p0, p1, color, sw=2.6, size=9):
        x0, y0 = p0
        x1, y1 = p1
        ang = math.atan2(y1 - y0, x1 - x0)
        a = math.radians(26)
        x2 = x1 - size * math.cos(ang - a)
        y2 = y1 - size * math.sin(ang - a)
        x3 = x1 - size * math.cos(ang + a)
        y3 = y1 - size * math.sin(ang + a)
        self.add(f'<path d="M {x1} {y1} L {x2:.2f} {y2:.2f} L {x3:.3f} {y3:.2f} Z" '
                 f'fill="{color}" stroke="none"/>')

    def dot(self, x, y, color=CY, r=4):
        self.add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}" filter="url(#{self.f_glow()})"/>')

    def gnd(self, x, y, color=MU):
        self.add(f'<path d="M {x} {y} L {x} {y+8} M {x-14} {y+8} L {x+14} {y+8} '
                 f'M {x-9} {y+14} L {x+9} {y+14} M {x-4} {y+20} L {x+4} {y+20}" '
                 f'stroke="{color}" stroke-width="2" fill="none"/>')

    # ---------- sheet chrome ----------
    def frame(self):
        self.add(f'<rect width="100%" height="100%" fill="url(#{self.grad("bg")})"/>')
        self.add(f'<rect width="100%" height="100%" fill="url(#grid)"/>')
        self.rect(18, 18, self.w - 36, self.h - 36, stroke="#22e6ff", rx=2, sw=1, opacity=0.22)
        self.bracket(18, 18, self.w - 36, self.h - 36, CY, 22, 2)
        if self.sheet:
            self.text(self.w - 34, self.h - 30, f"{self.sheet}   REV {self.rev}", size=10,
                      fill=MU, anchor="end", family=MONO, spacing="1")
            self.text(34, self.h - 30, "RCCAR // HARDWARE", size=10, fill=MU, family=MONO,
                      spacing="1")

    def title(self, t, sub=None, accent=CY):
        self.text(52, 52, t, size=27, fill=accent, weight="800", family=DISPLAY,
                  spacing="2", glow=True)
        if sub:
            self.text(54, 76, sub, size=12.5, fill=MU, family=MONO, spacing="0.5")

    def panel(self, x, y, w, h, label, sub=None, color=CY):
        self.cut(x, y, w, h, 12, fill=PANEL, stroke=color, sw=1.1, opacity=0.92)
        self.bracket(x, y, w, h, color, 12, 1.6)
        self.text(x + 2, y - 9, label, size=9.5, fill=color, family=MONO, spacing="1.2")
        if sub:
            self.text(x + 16 + len(label) * 6.6, y - 9, sub, size=9, fill=MU,
                      family=MONO, spacing="0.4")

    def pad(self, x, y, side="left", color=GOLD, w=10, h=7):
        self.add(f'<rect x="{x - w}" y="{y - h/2}" width="{w}" height="{h}" rx="1.5" '
                 f'fill="url(#{self.grad("gold")})" stroke="#3a2a08" stroke-width="0.6"/>')

    # ---------- devices ----------
    def esp_board(self, x, y, w, h, pad_l, pad_r, big=False):
        """Top view of the ESP32-C3 SuperMini, pads at the given absolute y positions."""
        self.rect(x, y, w, h, fill=f"url(#{self.grad('pcb')})", stroke="#1d4b63", rx=6, sw=1.4)
        # antenna meander
        ax0, ax1 = x + w * 0.18, x + w * 0.82
        ay = y + h * 0.045
        seg = (ax1 - ax0) / 6
        pts = [(ax0, ay)]
        for i in range(6):
            pts.append((ax0 + seg * (i + 0.5), ay + (10 if i % 2 == 0 else 0)))
        pts.append((ax1, ay))
        d = "M " + " L ".join(f"{px:.1f} {py:.1f}" for px, py in pts)
        self.add(f'<path d="{d}" fill="none" stroke="{GOLD}" stroke-width="2.2" opacity="0.85"/>')
        self.text(x + w / 2, y + h * 0.045 + 26, "ANTENNA", size=7 if not big else 9,
                  fill=MU, anchor="middle", family=MONO, spacing="1")

        # shield can
        sx, sy = x + w * 0.1, y + h * 0.13
        sw_, sh = w * 0.8, h * 0.58
        self.add(f'<rect x="{sx}" y="{sy}" width="{sw_}" height="{sh}" rx="3" '
                 f'fill="url(#{self.grad("metal")})" stroke="#3c4756" stroke-width="1"/>')
        self.add(f'<rect x="{sx+6}" y="{sy+6}" width="{sw_-12}" height="{sh-12}" rx="2" '
                 f'fill="none" stroke="#4a5665" stroke-width="0.8" opacity="0.7"/>')
        self.text(x + w / 2, sy + sh / 2 - 2, "ESP32-C3", size=15 if big else 11,
                  fill="#20262e", anchor="middle", weight="700", family=DISPLAY, spacing="1")
        self.text(x + w / 2, sy + sh / 2 + 14, "SuperMini", size=9 if not big else 12,
                  fill="#3c4756", anchor="middle", family=MONO, spacing="1")
        # shield dimples
        for dx in (sx + 12, sx + sw_ - 12):
            for dy in (sy + 12, sy + sh - 12):
                self.add(f'<circle cx="{dx}" cy="{dy}" r="2.2" fill="#6b7684" opacity="0.8"/>')

        # buttons
        by = y + h * 0.755
        for bx in (x + w * 0.26, x + w * 0.62):
            self.add(f'<rect x="{bx}" y="{by}" width="{w*0.12}" height="{h*0.032}" rx="2" '
                     f'fill="url(#{self.grad("metal")})" stroke="#3c4756" stroke-width="0.8"/>')
        self.text(x + w * 0.32, by + h * 0.032 + 10, "BOOT", size=7 if not big else 9,
                  fill=MU, anchor="middle", family=MONO)
        self.text(x + w * 0.68, by + h * 0.032 + 10, "RST", size=7 if not big else 9,
                  fill=MU, anchor="middle", family=MONO)

        # status LED
        lx, ly = x + w * 0.84, y + h * 0.815
        self.add(f'<circle cx="{lx}" cy="{ly}" r="2.6" fill="{CY}" filter="url(#{self.f_glow()})"/>')

        # USB-C
        uw = w * 0.3
        ux = x + (w - uw) / 2
        uy = y + h - 14
        self.add(f'<rect x="{ux}" y="{uy}" width="{uw}" height="18" rx="3" '
                 f'fill="url(#{self.grad("metal")})" stroke="#3c4756" stroke-width="1"/>')
        self.add(f'<rect x="{ux+5}" y="{uy+5}" width="{uw-10}" height="6" rx="2" '
                 f'fill="#1a2029"/>')

        # pads
        for py in pad_l:
            self.pad(x, py, "left")
        for py in pad_r:
            self.pad(x + w, py, "right")

    def battery_pack(self, x, y, w, h, pin_ys=None):
        plus_y, minus_y = pin_ys or (y + h * 0.42, y + h * 0.64)
        bw = w * 0.58
        bx, by, bh = x + 14, y + 26, h * 0.72
        self.add(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="10" '
                 f'fill="url(#{self.grad("cellred")})" stroke="#3d0a12" stroke-width="1.2"/>')
        self.add(f'<rect x="{bx+10}" y="{by+10}" width="{bw-20}" height="{bh-20}" rx="7" '
                 f'fill="none" stroke="#ff8a96" stroke-width="0.8" opacity="0.45"/>')
        self.text(bx + bw / 2, by + bh * 0.34, "2S 18650", size=10, fill="#ffe3e7",
                  anchor="middle", family=MONO, spacing="1.2")
        self.text(bx + bw / 2, by + bh * 0.5, "7.4 V", size=10, fill="#ffe3e7",
                  anchor="middle", family=MONO, spacing="1.2")
        cx0 = x + w - 34
        self.add(f'<rect x="{cx0}" y="{plus_y-14}" width="34" height="{minus_y-plus_y+28}" rx="4" '
                 f'fill="#e8edf2" stroke="#9aa7b6" stroke-width="1"/>')
        for ty in (plus_y, minus_y):
            self.add(f'<rect x="{cx0+6}" y="{ty-6}" width="14" height="12" rx="2" fill="#1a2029"/>')
            self.add(f'<rect x="{x+w-8}" y="{ty-4}" width="8" height="8" '
                     f'fill="url(#{self.grad("gold")})" stroke="#3a2a08" stroke-width="0.5"/>')
        self.wire([(bx + bw, plus_y), (cx0, plus_y)], RD, 2.2, glow=False)
        self.wire([(bx + bw, minus_y), (cx0, minus_y)], MU, 2.2, glow=False)

    def hbridge_module(self, x, y, w, h, pads):
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" '
                 f'fill="url(#{self.grad("pcbblue")})" stroke="#1d4b63" stroke-width="1.3"/>')
        # mounting holes
        for dx, dy in ((x + 12, y + 12), (x + w - 12, y + 12), (x + 12, y + h - 12), (x + w - 12, y + h - 12)):
            self.add(f'<circle cx="{dx}" cy="{dy}" r="3" fill="#04060c" stroke="{GOLD}" stroke-width="1"/>')
        # chip
        cw, ch = w * 0.34, h * 0.2
        cx, cy = x + w * 0.33, y + h * 0.36
        self.add(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" rx="2" fill="#0a0d12" '
                 f'stroke="#2c3746" stroke-width="1"/>')
        for i in range(5):
            self.add(f'<rect x="{cx+6+i*(cw-12)/4}" y="{cy-3}" width="3" height="3" fill="#9aa7b6"/>')
            self.add(f'<rect x="{cx+6+i*(cw-12)/4}" y="{cy+ch}" width="3" height="3" fill="#9aa7b6"/>')
        self.text(cx + cw / 2, cy + ch / 2 + 3, "H-BRIDGE", size=6.5, fill="#8fa3b5",
                  anchor="middle", family=MONO, spacing="0.8")
        # heatsink
        hx, hy = x + w * 0.68, y + h * 0.28
        self.add(f'<rect x="{hx}" y="{hy}" width="{w*0.2}" height="{h*0.34}" rx="2" '
                 f'fill="url(#{self.grad("metal")})" stroke="#3c4756" stroke-width="1"/>')
        for i in range(4):
            self.add(f'<rect x="{hx+4}" y="{hy+5+i*(h*0.34-10)/3.5}" width="{w*0.2-8}" height="3" '
                     f'fill="#6b7684" opacity="0.75"/>')
        # silk
        self.text(x + w * 0.06, y + h * 0.86, "TB6612FNG", size=8.5, fill="#9ecbe0",
                  family=MONO, spacing="0.8")
        self.text(x + w * 0.06, y + h * 0.92, "VM 2.7-13.5V", size=7, fill=MU, family=MONO)
        # pads
        for (px, py, side) in pads:
            self.pad(px, py, side, GOLD, 11, 8)

    def buck_module(self, x, y, w, h, pads):
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" '
                 f'fill="url(#{self.grad("pcbblue")})" stroke="#1d4b63" stroke-width="1.3"/>')
        for dx, dy in ((x + 12, y + 12), (x + w - 12, y + 12), (x + 12, y + h - 12), (x + w - 12, y + h - 12)):
            self.add(f'<circle cx="{dx}" cy="{dy}" r="3" fill="#04060c" stroke="{GOLD}" stroke-width="1"/>')
        # toroid inductor
        ix, iy, ir = x + w * 0.3, y + h * 0.45, min(w, h) * 0.2
        self.add(f'<circle cx="{ix}" cy="{iy}" r="{ir}" fill="#3a2a18" stroke="#8a6a3a" stroke-width="3"/>')
        self.add(f'<circle cx="{ix}" cy="{iy}" r="{ir*0.45}" fill="#0a0d12" stroke="#8a6a3a" stroke-width="1"/>')
        for k in range(8):
            a0 = k * math.pi / 4
            self.add(f'<path d="M {ix + ir*math.cos(a0):.1f} {iy + ir*math.sin(a0):.1f} '
                     f'L {ix + ir*1.25*math.cos(a0):.1f} {iy + ir*1.25*math.sin(a0):.1f}" '
                     f'stroke="#c99a4d" stroke-width="1.4"/>')
        # pot
        self.add(f'<rect x="{x+w*0.62}" y="{y+h*0.3}" width="{w*0.14}" height="{h*0.16}" rx="2" '
                 f'fill="#1c4b6b" stroke="#3f7f9f" stroke-width="1"/>')
        self.add(f'<circle cx="{x+w*0.69}" cy="{y+h*0.38}" r="{w*0.025}" fill="#c9d4e2" opacity="0.8"/>')
        self.text(x + w * 0.06, y + h * 0.9, "MP1584  5 V", size=8.5, fill="#9ecbe0",
                  family=MONO, spacing="0.6")
        for (px, py, side) in pads:
            self.pad(px, py, side, GOLD, 10, 8)

    def servo(self, x, y, w, h):
        body_w, body_h = w * 0.52, h * 0.6
        bx, by = x + w * 0.28, y + h * 0.22
        # cable
        self.wire([(x + 2, y + h * 0.57), (bx, y + h * 0.57)], "#7a4a2a", 2.4, glow=False)
        # tabs
        self.add(f'<rect x="{bx-10}" y="{by}" width="{body_w+20}" height="8" rx="2" fill="#1c3346" '
                 f'stroke="#2e5670" stroke-width="1"/>')
        self.add(f'<rect x="{bx-10}" y="{by+body_h-8}" width="{body_w+20}" height="8" rx="2" fill="#1c3346" '
                 f'stroke="#2e5670" stroke-width="1"/>')
        # body
        self.add(f'<rect x="{bx}" y="{by}" width="{body_w}" height="{body_h}" rx="5" '
                 f'fill="#152c3d" stroke="{MG}" stroke-width="1.2"/>')
        self.add(f'<rect x="{bx+6}" y="{by+6}" width="{body_w-12}" height="{body_h-12}" rx="3" '
                 f'fill="none" stroke="#2e5670" stroke-width="1"/>')
        self.text(bx + body_w / 2, by + body_h * 0.52, "SERVO", size=9, fill=TX,
                  anchor="middle", family=MONO, spacing="1.2")
        # horn
        hx, hy = bx + body_w * 0.5, by + body_h * 0.18
        self.add(f'<circle cx="{hx}" cy="{hy}" r="{w*0.06}" fill="url(#{self.grad("metal")})" '
                 f'stroke="#3c4756" stroke-width="1"/>')
        self.add(f'<rect x="{hx-3}" y="{hy-w*0.16}" width="6" height="{w*0.16}" rx="2" fill="#dfe8f3"/>')
        self.add(f'<rect x="{hx-3}" y="{hy}" width="{w*0.14}" height="6" rx="2" fill="#dfe8f3"/>')

    def motor(self, x, y, w, h, terms=None):
        if terms:
            t0, t1 = min(terms), max(terms)
            top, bot = t0 - 26, t1 + 26
            cy = (top + bot) / 2
            r = (bot - top) / 2
            body_x = x + 26
        else:
            cy = y + h * 0.5
            r = h * 0.34
            top, bot = cy - r, cy + r
            body_x = x + w * 0.08
        body_w = w * 0.6
        self.add(f'<rect x="{body_x}" y="{top}" width="{body_w}" height="{bot-top}" rx="{r}" '
                 f'fill="url(#{self.grad("metal")})" stroke="#3c4756" stroke-width="1.2"/>')
        for i in range(6):
            self.add(f'<line x1="{body_x+10+i*(body_w-20)/6}" y1="{top+6}" '
                     f'x2="{body_x+10+i*(body_w-20)/6}" y2="{bot-6}" stroke="#6b7684" '
                     f'stroke-width="0.8" opacity="0.45"/>')
        # shaft
        self.add(f'<rect x="{body_x+body_w-6}" y="{cy-r*0.18}" width="{w*0.2}" height="{r*0.36}" '
                 f'rx="3" fill="url(#{self.grad("metal")})" stroke="#3c4756" stroke-width="0.8"/>')
        # terminals at the requested y
        if terms:
            for ty in terms:
                self.add(f'<rect x="{x}" y="{ty-5}" width="{body_x-x}" height="10" rx="2" '
                         f'fill="{GOLD}" stroke="#3a2a08" stroke-width="0.6"/>')
        else:
            for ty in (cy - r * 0.5, cy + r * 0.5):
                self.add(f'<rect x="{x+w*0.1}" y="{ty-4}" width="10" height="8" rx="1.5" fill="{GOLD}"/>')
        self.text(body_x + body_w / 2, bot + 16, "BRUSHED DC", size=8, fill=MU,
                  anchor="middle", family=MONO, spacing="1")

    def rocker(self, x, y, w, h):
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="#0d1728" '
                 f'stroke="{MU}" stroke-width="1.2"/>')
        self.add(f'<rect x="{x+w*0.18}" y="{y+h*0.2}" width="{w*0.64}" height="{h*0.6}" rx="3" '
                 f'fill="url(#{self.grad("metal")})" stroke="#3c4756" stroke-width="1"/>')
        self.add(f'<rect x="{x+w*0.34}" y="{y+h*0.34}" width="{w*0.32}" height="{h*0.32}" rx="2" '
                 f'fill="#ffcf5a"/>')

    def divider(self, x, y, w, h):
        """100k from IN to node, 47k node to GND, node to OUT (ADC tap)."""
        ytop = y + 38
        node = x + 150
        pin_x = x + w  # 380
        # 100k zigzag from the IN pin to the node
        self.zigzag(pin_x, ytop, node + 8 - pin_x, 7)
        self.wire([(node, ytop), (node + 8, ytop)], TX, 2, glow=False)
        self.dot(node, ytop, TX, 3)
        for i in range(4):
            yy = ytop + 12 + i * 9
            self.add(f'<path d="M {node-7} {yy} L {node+7} {yy+4.5} L {node-7} {yy+9}" '
                     f'fill="none" stroke="{TX}" stroke-width="1.6"/>')
        self.wire([(node, ytop), (node, ytop + 12)], TX, 2, glow=False)
        self.wire([(node, ytop + 48), (node, ytop + 56)], TX, 2, glow=False)
        self.gnd(node, ytop + 56, MU)
        self.text((pin_x + node) / 2, ytop - 12, "100k", size=9.5, fill=TX, anchor="middle",
                  family=MONO, spacing="0.5")
        self.text(node + 12, ytop + 30, "47k", size=9.5, fill=TX, family=MONO)
        self.wire([(node, ytop), (node + 40, ytop), (node + 40, ytop + 40),
                   (pin_x, ytop + 40)], LM, 2, glow=False)
        self.text(x + 8, y + h - 6, "3.13:1  ->  GPIO0", size=8.5, fill=LM,
                  family=MONO, spacing="0.4")

    def zigzag(self, x, y, length, amp=8):
        n = 6
        step = length / n
        pts = [(x, y)]
        for i in range(n):
            pts.append((x + step * (i + 0.5), y + (amp if i % 2 == 0 else -amp)))
        pts.append((x + length, y))
        d = "M " + " L ".join(f"{px:.1f} {py:.1f}" for px, py in pts)
        self.add(f'<path d="{d}" fill="none" stroke="{TX}" stroke-width="2"/>')

    def pout(self, x, y, label, color, side):
        self.add(f'<circle cx="{x}" cy="{y}" r="4" fill="{color}" filter="url(#{self.f_glow()})"/>')
        if side == "left":
            self.text(x - 11, y - 7, label, size=9.5, fill=color, anchor="end", family=MONO)
        elif side == "right":
            self.text(x + 11, y - 7, label, size=9.5, fill=color, anchor="start", family=MONO)
        elif side == "top":
            self.text(x + 8, y - 9, label, size=9.5, fill=color, anchor="start", family=MONO)
        else:
            self.text(x + 8, y + 20, label, size=9.5, fill=color, anchor="start", family=MONO)

    def pin_in(self, x, y, label, color):
        """Pin dot with its label inside the panel, right-aligned."""
        self.add(f'<circle cx="{x}" cy="{y}" r="4" fill="{color}" filter="url(#{self.f_glow()})"/>')
        self.text(x - 12, y + 4, label, size=9.5, fill=color, anchor="end", family=MONO)

    def pin_inside(self, x, y, label, color, side="left"):
        self.add(f'<circle cx="{x}" cy="{y}" r="4" fill="{color}" filter="url(#{self.f_glow()})"/>')
        if side == "bottom":
            self.text(x + 8, y - 8, label, size=9.5, fill=color, anchor="start", family=MONO)
        else:
            self.text(x + 12, y + 4, label, size=9.5, fill=color, anchor="start", family=MONO)

    def legend(self, x, y):
        items = [(RD, "PACK POWER"), (AM, "5 V RAIL"), (CY, "LOGIC / PWM"), (MU, "GROUND")]
        for i, (c, label) in enumerate(items):
            cx = x + i * 150
            self.wire([(cx, y), (cx + 24, y)], c, 2.4, glow=True)
            self.text(cx + 32, y + 4, label, size=9, fill=MU, family=MONO, spacing="0.8")

    def render(self):
        bg = f'<rect width="100%" height="100%" fill="#04060c"/>'
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}">' + self.defs_block() + bg +
                "".join(self.body) + "</svg>")

    def save(self, name):
        os.makedirs(OUT, exist_ok=True)
        svg_path = os.path.join(OUT, name + ".svg")
        png_path = os.path.join(OUT, name + ".png")
        with open(svg_path, "w", encoding="utf-8") as fh:
            fh.write(self.render())
        subprocess.run(["rsvg-convert", "-z", "2", "-o", png_path, svg_path], check=True)
        print(f"{svg_path}  {png_path}")


def wiring():
    s = Svg(1600, 1020, "SHEET 01 // WIRING")
    s.frame()
    s.title("RCCAR // WIRING", "ESP32-C3 SUPERMINI   ·   2S LI-ION   ·   BRUSHED MOTOR + SERVO   ·   V0")
    s.legend(1020, 70)

    # ---------- battery ----------
    s.panel(70, 104, 260, 176, "PACK // 2S", "7.4 V nominal, 8.4 V full")
    s.battery_pack(80, 118, 240, 150, (205, 250))
    s.add(f'<circle cx="320" cy="205" r="4" fill="{RD}" filter="url(#{s.f_glow()})"/>')
    s.add(f'<circle cx="320" cy="250" r="4" fill="{MU}" filter="url(#{s.f_glow()})"/>')
    s.text(338, 198, "BAT +", size=9.5, fill=RD, family=MONO, spacing="0.8")
    s.text(338, 243, "BAT -", size=9.5, fill=MU, family=MONO, spacing="0.8")

    # switch
    s.panel(340, 110, 90, 80, "SW", None, AM)
    s.rocker(352, 138, 62, 44)

    # ---------- H-bridge ----------
    s.panel(748, 100, 352, 300, "H-BRIDGE", "TB6612FNG  /  DRV8251A")
    s.hbridge_module(760, 104, 330, 288, [
        (760, 150, "left"), (760, 210, "left"), (760, 270, "left"), (760, 330, "left"),
        (1090, 180, "right"), (1090, 250, "right"),
    ])
    s.pout(760, 150, "VM", RD, "left")
    s.pout(760, 210, "VCC", AM, "left")
    s.pout(760, 270, "STBY", AM, "left")
    s.pout(760, 330, "GND", MU, "left")
    s.pout(880, 400, "AIN1", CY, "bottom")
    s.pout(950, 400, "AIN2", CY, "bottom")
    s.pout(1090, 180, "AO1", RD, "right")
    s.pout(1090, 250, "AO2", RD, "right")

    # ---------- motor ----------
    s.panel(1170, 112, 320, 168, "MOTOR", "brushed DC, gearbox side")
    s.motor(1185, 150, 290, 100, terms=[180, 250])
    s.pout(1180, 180, "M+", RD, "left")
    s.pout(1180, 250, "M-", RD, "left")

    # ---------- buck ----------
    s.panel(508, 552, 300, 180, "5 V BUCK", "2-3 A, MP1584 class")
    s.buck_module(520, 580, 280, 140, [(520, 600, "left"), (520, 660, "left"),
                                       (800, 600, "right"), (800, 660, "right")])
    s.pout(520, 600, "IN+", RD, "left")
    s.pout(520, 660, "IN-", MU, "left")
    s.pout(800, 600, "5V", AM, "right")
    s.pout(800, 660, "GND", MU, "right")

    # ---------- ESP board ----------
    s.esp_board(900, 560, 180, 320,
                pad_l=[600, 636, 672, 708, 744, 780, 816, 852],
                pad_r=[600, 636, 672, 708, 744, 780, 816, 852])
    s.text(900, 546, "ESP32-C3 // SUPERMINI", size=10.5, fill=CY, family=MONO, spacing="1.2")
    s.pout(900, 600, "5V", AM, "left")
    s.pout(900, 636, "GND", MU, "left")
    s.pout(900, 852, "GPIO0", LM, "left")
    s.pout(1080, 600, "GPIO5", CY, "right")

    # ---------- servo ----------
    s.panel(1320, 612, 250, 178, "SERVO", "steering, 50 Hz")
    s.servo(1330, 640, 230, 140)
    s.pin_inside(1330, 720, "SIG", CY)
    s.pin_inside(1330, 760, "GND", MU)
    s.pin_inside(1370, 780, "V+", AM, "bottom")

    # ---------- divider ----------
    s.panel(70, 298, 320, 124, "SENSE DIVIDER", "pack voltage -> ADC")
    s.divider(80, 300, 300, 112)
    s.pout(380, 340, "IN", RD, "right")
    s.pout(380, 380, "OUT", LM, "right")

    # ---------- power wiring ----------
    s.wire([(320, 205), (335, 205), (335, 160), (350, 160)], RD)
    s.wire([(410, 160), (450, 160)], RD)
    s.wire([(450, 150), (450, 600), (520, 600)], RD, arrow=False)
    s.wire([(450, 150), (760, 150)], RD, arrow=True)
    s.dot(450, 160, RD, 3.5)
    s.dot(450, 340, RD, 3.5)
    s.dot(450, 600, RD, 3.5)
    s.text(470, 140, "8.4 V MAX", size=8.5, fill=MU, family=MONO, spacing="1")

    s.wire([(450, 340), (380, 340)], RD, arrow=True)

    # divider out -> GPIO0
    s.wire([(380, 380), (430, 380), (430, 852), (900, 852)], LM, arrow=True, casing=True)
    s.text(470, 844, "VBAT / 3.13 -> GPIO0", size=9, fill=LM, family=MONO, spacing="0.6")

    s.wire([(520, 660), (500, 660), (500, 700)], MU, arrow=False)
    s.gnd(500, 700, MU)
    s.wire([(320, 250), (360, 250)], MU, arrow=False)
    s.gnd(360, 250, MU)

    # 5 V rails
    s.wire([(800, 600), (900, 600)], AM, arrow=True)
    s.dot(810, 600, AM, 3.5)
    s.wire([(810, 600), (810, 450), (700, 450), (700, 210), (760, 210)], AM, arrow=False)
    s.wire([(700, 270), (760, 270)], AM, arrow=True)
    s.dot(700, 270, AM, 3.5)
    s.wire([(810, 600), (810, 940), (1370, 940), (1370, 780)], AM, arrow=True)

    s.wire([(800, 660), (812, 660), (812, 700)], MU, arrow=False)
    s.gnd(812, 700, MU)
    s.wire([(900, 636), (885, 636), (885, 680)], MU, arrow=False)
    s.gnd(885, 680, MU)
    s.wire([(760, 330), (740, 330), (740, 380)], MU, arrow=False)
    s.gnd(740, 380, MU)
    s.wire([(1330, 760), (1315, 760), (1315, 820)], MU, arrow=False)
    s.gnd(1315, 820, MU)

    # ---------- signals ----------
    s.wire([(900, 744), (860, 744), (860, 430), (880, 430), (880, 400)], CY, arrow=True)
    s.wire([(900, 708), (840, 708), (840, 455), (950, 455), (950, 400)], CY, arrow=True,
           casing=True)
    s.wire([(1080, 600), (1100, 600), (1100, 720), (1330, 720)], CY, arrow=True)

    s.wire([(1090, 180), (1180, 180)], RD, arrow=True)
    s.wire([(1090, 250), (1180, 250)], RD, arrow=True)

    s.text(52, 930, "ALL GROUNDS COMMON  ·  WIRE CROSSING WITHOUT A DOT IS NOT A CONNECTION",
           size=9, fill=MU, family=MONO, spacing="0.8")
    s.text(52, 950, "V0 VALUES: CONFIRM MOTOR STALL CURRENT, SERVO VOLTAGE AND CONNECTOR PINOUT",
           size=9, fill=MU, family=MONO, spacing="0.8")
    s.save("wiring")


def pinout():
    s = Svg(1150, 1250, "SHEET 02 // PINOUT")
    s.frame()
    s.title("SUPERMINI // PIN MAP", "EVERY PIN THIS FIRMWARE TOUCHES  ·  VERIFY SILKSCREEN, CLONES DIFFER")

    bx, by, bw, bh = 410, 140, 330, 780
    pad_l = [230 + i * 82 for i in range(8)]
    pad_r = pad_l
    s.esp_board(bx, by, bw, bh, pad_l, pad_r, big=True)

    left = [
        ("5V", AM, "from the 5 V buck"),
        ("GND", MU, "common ground"),
        ("3V3", MG, "not used"),
        ("GPIO4", CY, "H-bridge IN2"),
        ("GPIO3", CY, "H-bridge IN1"),
        ("GPIO2", RD, "strapping · leave alone"),
        ("GPIO1", MU, "free"),
        ("GPIO0", LM, "battery sense · ADC1 ch0"),
    ]
    right = [
        ("GPIO5", CY, "servo PWM · 50 Hz"),
        ("GPIO6", MU, "I2C SDA (future)"),
        ("GPIO7", MU, "I2C SCL (future)"),
        ("GPIO8", AM, "onboard LED · active low"),
        ("GPIO9", RD, "BOOT + strapping"),
        ("GPIO10", MU, "free"),
        ("GPIO20", MU, "UART0 RX"),
        ("GPIO21", MU, "UART0 TX"),
    ]

    for i, (name, color, use) in enumerate(left):
        y = pad_l[i]
        s.wire([(bx - 34, y), (bx, y)], color, 2, glow=True)
        s.text(bx - 124, y + 4, use, size=11.5, fill=MU, anchor="end", family=SANS)
        s.text(bx - 44, y + 4, name, size=12.5, fill=TX, anchor="end", family=MONO, weight="700")
    for i, (name, color, use) in enumerate(right):
        y = pad_r[i]
        s.wire([(bx + bw, y), (bx + bw + 34, y)], color, 2, glow=True)
        s.text(bx + bw + 44, y + 4, name, size=12.5, fill=TX, family=MONO, weight="700")
        s.text(bx + bw + 118, y + 4, use, size=11.5, fill=MU, family=SANS)

    s.text(52, 1080, "GPIO11-17: INTERNAL FLASH, NEVER USE   ·   GPIO18/19: USB D-/D+   ·   GPIO2/8/9: STRAPPING",
           size=10, fill=MU, family=MONO, spacing="0.6")
    s.text(52, 1102, "GPIO4-7 DOUBLE AS JTAG; USING THEM COSTS HARDWARE DEBUGGING, NOT FUNCTIONALITY",
           size=10, fill=MU, family=MONO, spacing="0.6")
    s.text(52, 1124, "NO MCPWM ON THIS CHIP: THE 6 LEDC CHANNELS DO MOTOR AND SERVO PWM",
           size=10, fill=MG, family=MONO, spacing="0.6")
    s.save("pinout")


def layout():
    s = Svg(1400, 980, "SHEET 03 // LAYOUT")
    s.frame()
    s.title("CHASSIS // LAYOUT", "TOP VIEW  ·  APPROXIMATE PLACEMENT  ·  NOT TO SCALE  ·  REAR AT LEFT")

    # wheels
    for x, y in [(60, 235), (60, 625), (1150, 235), (1150, 625)]:
        s.add(f'<rect x="{x}" y="{y}" width="180" height="140" rx="26" fill="#0a0f16" '
              f'stroke="#2b3a4a" stroke-width="2"/>')
        for i in range(6):
            s.add(f'<rect x="{x+14}" y="{y+18+i*18}" width="152" height="8" rx="3" fill="#141c26"/>')
        s.text(x + 90, y + 78, "WHEEL", size=9, fill=MU, anchor="middle", family=MONO, spacing="1.2")

    s.text(120, 218, "REAR", size=11, fill=MG, spacing="3", family=MONO, glow=True)
    s.text(1210, 218, "FRONT", size=11, fill=MG, spacing="3", family=MONO, glow=True)

    # tub
    s.add('<rect x="200" y="250" width="960" height="490" rx="46" fill="url(#carbon)" '
          'stroke="#22e6ff" stroke-opacity="0.35" stroke-width="1.6"/>')

    # motor + gearbox
    s.panel(225, 372, 200, 266, "GEARBOX", "brushed motor")
    s.motor(240, 400, 170, 90)
    s.add(f'<rect x="255" y="500" width="140" height="110" rx="8" fill="#101a26" stroke="{MU}" stroke-width="1.2"/>')
    s.text(325, 560, "GEAR", size=9, fill=MU, anchor="middle", family=MONO, spacing="1.5")
    s.wire([(230, 400), (115, 300)], MU, 2, glow=False)
    s.wire([(230, 620), (115, 700)], MU, 2, glow=False)

    # servo + linkage
    s.panel(1000, 552, 148, 176, "SERVO", None, MG)
    s.servo(1005, 580, 138, 120)
    s.wire([(1080, 606), (1190, 340)], MG, 2, dash="6 4", glow=True)
    s.wire([(1080, 690), (1190, 700)], MG, 2, dash="6 4", glow=True)

    # battery
    s.panel(470, 462, 320, 220, "PACK // 2S", "centered, low")
    s.battery_pack(485, 496, 290, 150)

    # ESP + buck + HB
    s.esp_board(672, 292, 94, 168, pad_l=[], pad_r=[])
    s.text(672, 284, "ESP32-C3", size=9.5, fill=CY, family=MONO, spacing="1")

    s.panel(478, 292, 148, 110, "5V BUCK", None, AM)
    s.buck_module(486, 306, 132, 86, [])

    s.panel(872, 292, 168, 128, "H-BRIDGE", "TB6612")
    s.hbridge_module(880, 306, 152, 106, [])

    # switch
    s.panel(780, 700, 140, 88, "SW", None, AM)
    s.rocker(798, 724, 104, 44)

    # 5 V bus: buck output, across the top, down into the ESP and H-bridge
    s.wire([(626, 345), (640, 345), (640, 256), (1032, 256), (1032, 292)], AM, arrow=False, glow=True)
    s.dot(758, 256, AM, 3)
    s.wire([(758, 256), (758, 292)], AM, arrow=False)
    s.text(660, 248, "5 V BUS", size=8.5, fill=AM, family=MONO, spacing="1")

    # pack power
    s.wire([(560, 462), (560, 378)], RD, arrow=False, glow=True)
    s.wire([(775, 559), (820, 559), (820, 724)], RD, arrow=False, glow=True)
    s.text(826, 626, "PACK +", size=8, fill=RD, family=MONO, spacing="1")
    s.wire([(902, 744), (950, 744), (950, 420)], RD, arrow=False, glow=True)

    # signals
    s.wire([(766, 380), (872, 380)], CY, arrow=True, glow=True)
    s.wire([(766, 400), (800, 400), (800, 456), (1060, 456), (1060, 552)], CY, arrow=True,
           casing=True, glow=True)
    s.text(1068, 500, "PWM", size=8.5, fill=CY, family=MONO, spacing="1")

    s.text(52, 830, "PACK CENTERED AND LOW  ·  H-BRIDGE NEXT TO THE MOTOR  ·  SERVO LEADS SHORT",
           size=10, fill=MU, family=MONO, spacing="0.7")
    s.text(52, 852, "ONE GROUND POINT AT THE PACK NEGATIVE, STAR EVERYTHING FROM THERE",
           size=10, fill=MU, family=MONO, spacing="0.7")
    s.text(52, 874, "KEEP THE ANTENNA END AWAY FROM MOTOR AND PACK LEADS",
           size=10, fill=MU, family=MONO, spacing="0.7")
    s.save("layout")


if __name__ == "__main__":
    wiring()
    pinout()
    layout()
