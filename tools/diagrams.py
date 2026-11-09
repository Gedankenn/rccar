#!/usr/bin/env python3
"""Generate the rccar documentation diagrams as SVG, then rasterize to PNG.

No third-party Python modules: plain SVG strings plus rsvg-convert.
Run from the repo root:  python3 tools/diagrams.py
"""

import html
import os
import subprocess

BG = "#fbfcfd"
INK = "#16181d"
MUT = "#57606a"
LINE = "#c9d1d9"
RED = "#cf222e"
ORG = "#bc4c00"
BLU = "#0969da"
GRN = "#1a7f37"
PUR = "#8250df"
TEAL = "#0d7a6f"
BLK = "#24292f"

SANS = "DejaVu Sans, Liberation Sans, sans-serif"
MONO = "DejaVu Sans Mono, monospace"

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "images")


def esc(s):
    return html.escape(str(s), quote=True)


class Svg:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.body = []
        self.markers = {}

    def add(self, s):
        self.body.append(s)

    def rect(self, x, y, w, h, fill="#ffffff", stroke=INK, rx=8, sw=2, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, stroke=INK, sw=2, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
                 f'stroke-width="{sw}" stroke-linecap="round"{d}/>')

    def text(self, x, y, s, size=15, fill=INK, anchor="start", weight="400",
             family=SANS, spacing=None, opacity=None):
        sp = f' letter-spacing="{spacing}"' if spacing else ""
        o = f' opacity="{opacity}"' if opacity else ""
        self.add(f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
                 f'fill="{fill}" text-anchor="{anchor}" font-weight="{weight}"{sp}{o}>{esc(s)}</text>')

    def marker(self, color):
        mid = "arr-" + color.replace("#", "")
        if mid not in self.markers:
            self.markers[mid] = (
                f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" '
                f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{color}"/></marker>')
        return mid

    def wire(self, pts, color=INK, sw=3, arrow=True, dash=None, casing=False):
        d = "M " + " L ".join(f"{x} {y}" for x, y in pts)
        if casing:
            self.add(f'<path d="{d}" fill="none" stroke="{BG}" stroke-width="{sw + 5}" '
                     f'stroke-linejoin="round" stroke-linecap="round"/>')
        dash_s = f' stroke-dasharray="{dash}"' if dash else ""
        mark = f' marker-end="url(#{self.marker(color)})"' if arrow else ""
        self.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" '
                 f'stroke-linejoin="round" stroke-linecap="round"{dash_s}{mark}/>')

    def dot(self, x, y, color=INK, r=4.5):
        self.add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>')

    def gnd(self, x, y, color=BLK):
        self.line(x, y, x, y + 8, color, 2.5)
        self.line(x - 15, y + 8, x + 15, y + 8, color, 2.5)
        self.line(x - 9, y + 14, x + 9, y + 14, color, 2.5)
        self.line(x - 3, y + 20, x + 3, y + 20, color, 2.5)

    def board(self, x, y, w, h, title, subs=None, accent=INK):
        self.rect(x, y, w, h, fill="#ffffff", stroke=accent, sw=2, rx=10)
        self.text(x + 18, y + 30, title, size=17, weight="700", fill=INK)
        for i, line in enumerate(subs or []):
            self.text(x + 18, y + 50 + i * 19, line, size=12.5, fill=MUT)

    def pin_out(self, x, y, label, color, side):
        """Pin dot on a box edge; label outside and clear of the wire."""
        self.add(f'<circle cx="{x}" cy="{y}" r="5" fill="{color}" stroke="#ffffff" stroke-width="1.5"/>')
        if side == "left":
            self.text(x - 12, y - 8, label, size=12.5, fill=color, anchor="end", family=MONO)
        elif side == "right":
            self.text(x + 12, y - 8, label, size=12.5, fill=color, anchor="start", family=MONO)
        elif side == "top":
            self.text(x + 9, y - 10, label, size=12.5, fill=color, anchor="start", family=MONO)
        else:  # bottom
            self.text(x + 9, y + 21, label, size=12.5, fill=color, anchor="start", family=MONO)

    def pin_in(self, x, y, label, color):
        """Pin dot with its label inside the box, right-aligned."""
        self.add(f'<circle cx="{x}" cy="{y}" r="5" fill="{color}" stroke="#ffffff" stroke-width="1.5"/>')
        self.text(x - 14, y + 5, label, size=12.5, fill=color, anchor="end", family=MONO)

    def pin_inside(self, x, y, label, color, side="left"):
        """Pin dot with its label inside the box."""
        self.add(f'<circle cx="{x}" cy="{y}" r="5" fill="{color}" stroke="#ffffff" stroke-width="1.5"/>')
        if side == "bottom":
            self.text(x + 9, y - 9, label, size=12.5, fill=color, anchor="start", family=MONO)
        else:
            self.text(x + 14, y + 5, label, size=12.5, fill=color, anchor="start", family=MONO)

    def render(self):
        defs = "<defs>" + "".join(self.markers.values()) + "</defs>" if self.markers else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}">{defs}'
                f'<rect width="100%" height="100%" fill="{BG}"/>' + "".join(self.body) + "</svg>")

    def save(self, name):
        os.makedirs(OUT, exist_ok=True)
        svg_path = os.path.join(OUT, name + ".svg")
        png_path = os.path.join(OUT, name + ".png")
        with open(svg_path, "w", encoding="utf-8") as fh:
            fh.write(self.render())
        subprocess.run(["rsvg-convert", "-z", "2", "-o", png_path, svg_path], check=True)
        print(f"{svg_path}  {png_path}")


def legend(s, x, y):
    items = [(RED, "battery power"), (ORG, "5 V rail"), (BLU, "logic / PWM"), (BLK, "ground")]
    for i, (c, label) in enumerate(items):
        cx = x + i * 155
        s.line(cx, y, cx + 26, y, c, 4)
        s.text(cx + 34, y + 5, label, size=13, fill=MUT)


def wiring():
    s = Svg(1600, 1020)
    s.text(40, 54, "rccar wiring", size=30, weight="700")
    s.text(40, 82, "ESP32-C3 SuperMini · 2S Li-ion · brushed motor + hobby servo · v0",
           size=15, fill=MUT)
    legend(s, 1035, 60)

    s.board(80, 90, 240, 160, "BATTERY", ["2S Li-ion 7.4 V", "BMS + balance charger"], RED)
    s.rect(350, 138, 60, 44, fill="#fff", stroke=BLK)
    s.text(380, 165, "SW", size=15, anchor="middle", weight="700")

    s.board(760, 90, 330, 310, "H-BRIDGE", ["TB6612FNG / DRV8251A", "VM = pack, VCC = 5 V"], INK)
    s.board(1180, 120, 300, 150, "MOTOR", ["brushed DC"], INK)
    s.board(520, 560, 280, 160, "5 V BUCK", ["2-3 A · MP1584 class"], ORG)
    s.board(900, 560, 340, 320, "ESP32-C3", ["SuperMini · 4 MB flash"], INK)
    s.board(1330, 620, 240, 160, "SERVO", ["existing steering servo"], GRN)
    s.board(80, 300, 300, 110, "BATTERY DIVIDER", ["100k top / 47k bottom", "3.13:1 → GPIO0"], TEAL)

    # pins
    s.pin_in(320, 200, "BAT +", RED)
    s.pin_in(320, 240, "BAT -", BLK)

    s.pin_out(760, 150, "VM", RED, "left")
    s.pin_out(760, 210, "VCC", ORG, "left")
    s.pin_out(760, 270, "STBY", ORG, "left")
    s.pin_out(760, 330, "GND", BLK, "left")
    s.pin_out(880, 400, "AIN1", BLU, "bottom")
    s.pin_out(950, 400, "AIN2", BLU, "bottom")
    s.pin_out(1090, 180, "AO1", RED, "right")
    s.pin_out(1090, 250, "AO2", RED, "right")

    s.pin_out(1180, 180, "M+", RED, "left")
    s.pin_out(1180, 250, "M-", RED, "left")

    s.pin_out(520, 600, "IN+", RED, "left")
    s.pin_out(520, 660, "IN-", BLK, "left")
    s.pin_out(800, 600, "5V", ORG, "right")
    s.pin_out(800, 660, "GND", BLK, "right")

    s.pin_out(900, 600, "5V", ORG, "left")
    s.pin_out(900, 660, "GND", BLK, "left")
    s.pin_out(900, 760, "GPIO0", TEAL, "left")
    s.pin_out(940, 560, "GPIO3", BLU, "top")
    s.pin_out(1000, 560, "GPIO4", BLU, "top")
    s.pin_out(1240, 720, "GPIO5", GRN, "right")

    s.pin_inside(1330, 720, "SIG", GRN)
    s.pin_inside(1330, 760, "GND", BLK)
    s.pin_inside(1370, 780, "V+", ORG, "bottom")

    s.pin_out(380, 340, "IN", RED, "right")
    s.pin_out(380, 380, "OUT", TEAL, "right")

    # power
    s.wire([(320, 200), (338, 200), (338, 160), (350, 160)], RED)
    s.wire([(410, 160), (450, 160)], RED)
    s.wire([(450, 150), (450, 600), (520, 600)], RED, arrow=False)
    s.wire([(450, 150), (760, 150)], RED)
    s.dot(450, 160, RED)
    s.dot(450, 340, RED)
    s.dot(450, 600, RED)
    s.text(470, 142, "8.4 V max", size=12, fill=MUT)
    s.wire([(450, 340), (380, 340)], RED)

    s.wire([(380, 380), (430, 380), (430, 760), (900, 760)], TEAL, casing=True)
    s.text(470, 752, "VBAT / 3.13 → GPIO0", size=12.5, fill=TEAL)

    s.wire([(520, 660), (500, 660), (500, 700)], BLK, arrow=False)
    s.gnd(500, 700)
    s.wire([(320, 240), (360, 240), (360, 270)], BLK, arrow=False)
    s.gnd(360, 270)

    s.wire([(800, 600), (900, 600)], ORG)
    s.wire([(800, 660), (812, 660), (812, 700)], BLK, arrow=False)
    s.gnd(812, 700)

    s.wire([(850, 600), (850, 450), (700, 450), (700, 210), (760, 210)], ORG, arrow=False)
    s.wire([(700, 270), (760, 270)], ORG)
    s.dot(850, 600, ORG)
    s.dot(700, 270, ORG)
    s.wire([(850, 600), (850, 940), (1370, 940), (1370, 780)], ORG)

    s.wire([(900, 660), (885, 660), (885, 700)], BLK, arrow=False)
    s.gnd(885, 700)
    s.wire([(760, 330), (740, 330), (740, 380)], BLK, arrow=False)
    s.gnd(740, 380)
    s.wire([(1330, 760), (1315, 760), (1315, 820)], BLK, arrow=False)
    s.gnd(1315, 820)

    # signals
    s.wire([(940, 560), (940, 520), (880, 520), (880, 400)], BLU)
    s.wire([(1000, 560), (1000, 500), (950, 500), (950, 400)], BLU)
    s.wire([(1240, 720), (1330, 720)], GRN)

    # motor
    s.wire([(1090, 180), (1180, 180)], RED)
    s.wire([(1090, 250), (1180, 250)], RED)

    s.text(40, 950, "All grounds common. A wire crossing without a dot is not a connection.",
           size=13, fill=MUT)
    s.text(40, 974, "v0 values: confirm motor stall current, servo voltage and connector pinout before soldering.",
           size=13, fill=MUT)
    s.save("wiring")


def pinout():
    s = Svg(1100, 1230)
    s.text(40, 54, "ESP32-C3 SuperMini pin map", size=30, weight="700")
    s.text(40, 82, "as used by this firmware · verify the silkscreen: clones differ", size=15, fill=MUT)

    s.rect(400, 130, 340, 860, fill="#ffffff", stroke=INK, sw=2.5, rx=26)
    s.text(570, 170, "ESP32-C3", size=25, weight="700", anchor="middle")
    s.text(570, 196, "SuperMini", size=17, fill=MUT, anchor="middle")
    s.rect(450, 240, 240, 34, fill="#eef1f4", stroke=LINE, rx=6)
    s.text(570, 262, "antenna end", size=12, fill=MUT, anchor="middle")

    s.rect(510, 990, 120, 40, fill="#eef1f4", stroke=LINE, rx=4)
    s.text(570, 1016, "USB-C", size=13, fill=MUT, anchor="middle", family=MONO)

    left = [
        ("5V", ORG, "from the 5 V buck"),
        ("GND", BLK, "common ground"),
        ("3V3", PUR, "not used"),
        ("GPIO4", BLU, "H-bridge IN2"),
        ("GPIO3", BLU, "H-bridge IN1"),
        ("GPIO2", RED, "strapping · leave alone"),
        ("GPIO1", MUT, "free"),
        ("GPIO0", TEAL, "battery sense · ADC1 ch0"),
    ]
    right = [
        ("GPIO5", GRN, "servo PWM · 50 Hz"),
        ("GPIO6", MUT, "I2C SDA (future)"),
        ("GPIO7", MUT, "I2C SCL (future)"),
        ("GPIO8", ORG, "onboard LED · active low"),
        ("GPIO9", RED, "BOOT + strapping"),
        ("GPIO10", MUT, "free"),
        ("GPIO20", MUT, "UART0 RX"),
        ("GPIO21", MUT, "UART0 TX"),
    ]
    y0, step = 330, 78
    for i, (name, color, use) in enumerate(left):
        y = y0 + i * step
        s.line(370, y, 400, y, color, 3)
        s.add(f'<circle cx="400" cy="{y}" r="6" fill="{color}" stroke="#fff" stroke-width="1.5"/>')
        s.text(420, y + 5, name, size=15, fill=INK, family=MONO, weight="700")
        s.text(352, y + 5, use, size=13, fill=MUT, anchor="end")
    for i, (name, color, use) in enumerate(right):
        y = y0 + i * step
        s.line(740, y, 770, y, color, 3)
        s.add(f'<circle cx="740" cy="{y}" r="6" fill="{color}" stroke="#fff" stroke-width="1.5"/>')
        s.text(720, y + 5, name, size=15, fill=INK, anchor="end", family=MONO, weight="700")
        s.text(808, y + 5, use, size=13, fill=MUT)

    s.text(40, 1090, "GPIO11-17: internal flash, never use.  GPIO18/19: USB D-/D+.  GPIO2/8/9: strapping.",
           size=14, fill=MUT)
    s.text(40, 1118, "GPIO4-7 double as JTAG; using them costs hardware debugging, not functionality.",
           size=14, fill=MUT)
    s.text(40, 1146, "No MCPWM on this chip: the 6 LEDC channels do motor and servo PWM.",
           size=14, fill=MUT)
    s.save("pinout")


def layout():
    s = Svg(1400, 980)
    s.text(40, 54, "Chassis layout (top view)", size=30, weight="700")
    s.text(40, 82, "approximate placement · not to scale · rear at left", size=15, fill=MUT)

    for x, y in [(70, 240), (70, 630), (1150, 240), (1150, 630)]:
        s.rect(x, y, 170, 130, fill="#e6e9ec", stroke="#8c959f", rx=24)
        s.text(x + 85, y + 74, "wheel", size=13, fill=MUT, anchor="middle")

    s.text(150, 220, "REAR", size=13, fill=MUT, spacing="2")
    s.text(1235, 220, "FRONT", size=13, fill=MUT, spacing="2")

    s.rect(200, 250, 960, 490, fill="#f3f5f7", stroke="#8c959f", sw=2, rx=46)

    s.rect(230, 380, 190, 250, fill="#e6e9ec", stroke=INK, rx=10)
    s.text(325, 420, "motor +", size=15, anchor="middle", weight="700")
    s.text(325, 440, "gearbox", size=15, anchor="middle", weight="700")
    s.text(325, 470, "brushed", size=12, fill=MUT, anchor="middle")
    s.line(210, 385, 130, 320, MUT, 2)
    s.line(210, 625, 130, 690, MUT, 2)

    s.rect(1000, 560, 130, 150, fill="#e8f5ec", stroke=GRN, rx=10)
    s.text(1065, 595, "servo", size=15, anchor="middle", weight="700", fill=GRN)
    s.text(1065, 618, "50 Hz", size=12, fill=GRN, anchor="middle")
    s.line(1130, 590, 1180, 330, GRN, 2, dash="5 4")
    s.line(1130, 680, 1180, 690, GRN, 2, dash="5 4")

    s.rect(480, 480, 300, 190, fill="#fdeeee", stroke=RED, rx=12)
    s.text(630, 522, "2S Li-ion", size=18, anchor="middle", weight="700", fill=RED)
    s.text(630, 548, "7.4 V · BMS", size=13, anchor="middle", fill=MUT)
    s.text(630, 615, "centered, low", size=12, anchor="middle", fill=MUT)

    s.rect(650, 300, 180, 110, fill="#eef4fd", stroke=BLU, rx=10)
    s.text(740, 330, "ESP32-C3", size=15, anchor="middle", weight="700", fill=BLU)
    s.text(740, 350, "SuperMini", size=12, anchor="middle", fill=MUT)

    s.rect(480, 300, 130, 90, fill="#fff4e8", stroke=ORG, rx=10)
    s.text(545, 330, "5 V buck", size=14, anchor="middle", weight="700", fill=ORG)
    s.text(545, 352, "2-3 A", size=12, anchor="middle", fill=MUT)

    s.rect(880, 300, 150, 110, fill="#eef4fd", stroke=BLU, rx=10)
    s.text(955, 334, "H-bridge", size=14, anchor="middle", weight="700", fill=BLU)
    s.text(955, 356, "TB6612", size=12, anchor="middle", fill=MUT)
    s.text(955, 376, "or DRV8251", size=11, anchor="middle", fill=MUT)

    s.rect(790, 710, 120, 50, fill="#fff", stroke=BLK, rx=8)
    s.text(850, 741, "SW", size=15, anchor="middle", weight="700")

    # 5 V bus feeds both boards
    s.wire([(545, 300), (545, 285), (955, 285), (955, 300)], ORG, arrow=False)
    s.dot(740, 285, ORG)
    s.wire([(740, 285), (740, 300)], ORG, arrow=False)
    s.text(600, 276, "5 V", size=11, fill=ORG)

    # pack power
    s.wire([(560, 480), (560, 390)], RED, arrow=False)
    s.wire([(650, 670), (650, 725), (790, 725)], RED, arrow=False)
    s.text(660, 716, "battery +", size=11, fill=RED)
    s.wire([(910, 725), (950, 725), (950, 410)], RED, arrow=False)

    # signals
    s.wire([(830, 380), (880, 380)], BLU, arrow=False)
    s.text(834, 371, "AIN1/2", size=10, fill=BLU)
    s.wire([(830, 400), (845, 400), (845, 455), (1065, 455), (1065, 560)],
           GRN, arrow=False, casing=True)
    s.text(1072, 500, "PWM", size=11, fill=GRN)

    s.text(40, 820, "Battery centered and low. H-bridge next to the motor, servo leads short.",
           size=14, fill=MUT)
    s.text(40, 846, "One ground point at the battery negative; star everything from there.",
           size=14, fill=MUT)
    s.text(40, 872, "Keep the antenna end of the SuperMini away from motor and battery leads.",
           size=14, fill=MUT)
    s.save("layout")


if __name__ == "__main__":
    wiring()
    pinout()
    layout()
