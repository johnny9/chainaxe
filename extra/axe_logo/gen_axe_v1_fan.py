#!/usr/bin/env python3
"""Warhammer-style chainaxe side profile -> KiCad silkscreen footprint + PNG preview.
Usage: gen_axe.py [scale]   (scale 0.6)"""
import math, sys, os, uuid
S = float(sys.argv[1]) if len(sys.argv) > 1 else 0.6
HERE = os.path.dirname(os.path.abspath(__file__))
polys = []                       # each: list of (x,y), mm, y down, unscaled

def rect(x0, y0, x1, y1): polys.append([(x0,y0),(x1,y0),(x1,y1),(x0,y1)])

# --- haft: wrapped grip + plain shaft
x = 0.0
while x < 21:
    rect(x, -1.2, x+2.0, 1.2); x += 2.5
rect(21.5, -1.0, 27, 1.0)
# pommel: diamond spike
polys.append([(-0.5,-2.4),(-4,-3.2),(-8,0),(-4,3.2),(-0.5,2.4)])
polys.append([(-8.6,0),(-11.5,-0.5),(-11.5,0.5)])
# guard collar
rect(18.9, -3.4, 20.5, 3.4)

# --- engine housing: solid block + vent bars
polys.append([(26,-3.5),(27.5,-5),(30,-5),(30,5),(27.5,5),(26,3.5)])
for i in range(3):
    x0 = 30.5 + i*1.5
    rect(x0, -4.6, x0+1.0, 4.6)
# rear pick
polys.append([(26.5,5.6),(32,5.6),(18,16),(21.5,8.5)])

# --- crescent blade: D-shaped body + chain-tooth edge
xc, R = 33.0, 20.0
A0, A1 = -72.0, 38.0
def pt(r, a): return (xc + r*math.cos(math.radians(a)), r*math.sin(math.radians(a)))
def sector(r0, r1, a0, a1, n=None):
    n = n or max(2, int(abs(a1-a0)/3))
    out  = [pt(r1, a0+(a1-a0)*i/n) for i in range(n+1)]
    back = [pt(r0, a1-(a1-a0)*i/n) for i in range(n+1)]
    return out + back
GAP = 0.4
cuts = [-48, -24, 0, 20]
edges = [A0] + cuts + [A1]
for i in range(len(edges)-1):
    a0 = edges[i] + (0 if i == 0 else GAP/2/ 9*180/math.pi*0.5)
    a1 = edges[i+1] - (0 if i == len(edges)-2 else GAP/2/ 9*180/math.pi*0.5)
    polys.append(sector(8.0, 16.4, a0, a1))
polys.append([(33,-4),(40,-4),(40,4),(33,4)])       # neck into blade
# teeth
pitch, half = 5.6, 2.0
n = int((A1-A0) // pitch)
a_start = (A0+A1)/2-(n-1)/2*pitch
for i in range(n):
    a = a_start + i*pitch
    tilt = 1.2 if i % 2 == 0 else -1.2
    polys.append([pt(17.0, a-half), pt(R, a+tilt-0.9), pt(R, a+tilt+0.9), pt(17.0, a+half)])

ROT = math.radians(-32)
polys = [[(x*math.cos(ROT)-y*math.sin(ROT), x*math.sin(ROT)+y*math.cos(ROT)) for x,y in q] for q in polys]
# --- bounds / centre
xs = [p[0] for q in polys for p in q]; ys = [p[1] for q in polys for p in q]
cx, cy = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2
W, H = (max(xs)-min(xs))*S, (max(ys)-min(ys))*S
def T(p): return ((p[0]-cx)*S, (p[1]-cy)*S)

# --- footprint
name = "Silk_ChainAxe"
L = [f'(footprint "{name}" (version 20241229) (generator "chainaxe_silk") (generator_version "1.0")',
     '  (layer "F.Cu")',
     '  (descr "Warhammer-style chainaxe side profile, silkscreen logo")',
     '  (tags "logo silkscreen chainaxe warhammer")',
     '  (attr board_only exclude_from_pos_files exclude_from_bom)',
     f'  (property "Reference" "G***" (at 0 {-H/2-1.5:.2f}) (layer "F.SilkS") (hide yes) (effects (font (size 1 1) (thickness 0.15))))',
     f'  (property "Value" "{name}" (at 0 {H/2+1.5:.2f}) (layer "F.Fab") (hide yes) (effects (font (size 1 1) (thickness 0.15))))']
for q in polys:
    pts = " ".join("(xy %.3f %.3f)" % T(p) for p in q)
    L.append(f'  (fp_poly (pts {pts}) (stroke (width 0) (type solid)) (fill yes) (layer "F.SilkS") (uuid "{uuid.uuid4()}"))')
L.append(')')
out = os.path.join(HERE, "..", "..", "boards", "chainaxe", "chainaxe.pretty", name + ".kicad_mod")
open(out, "w").write("\n".join(L) + "\n")
print(f"footprint {W:.1f} x {H:.1f} mm -> {os.path.normpath(out)}")

# --- preview
from PIL import Image, ImageDraw
px = 24
im = Image.new("RGB", (int(W*px)+40, int(H*px)+40), (20, 70, 40))
d = ImageDraw.Draw(im)
for q in polys:
    d.polygon([((T(p)[0]+W/2)*px+20, (T(p)[1]+H/2)*px+20) for p in q], fill=(240, 240, 235))
im.save(os.path.join(HERE, "chainaxe_logo_preview.png"))

# --- board-ready JSON (native F.SilkS polygons) for the IPC, centred at BOARD_AT
import json
BX, BY = (float(sys.argv[2]), float(sys.argv[3])) if len(sys.argv) > 3 else (88.0, 85.0)
items = []
for q in polys:
    nodes = [{"point": {"x_nm": int(round((T(p)[0]+BX)*1e6)), "y_nm": int(round((T(p)[1]+BY)*1e6))}} for p in q]
    items.append({"@type": "type.googleapis.com/kiapi.board.types.BoardGraphicShape",
                  "layer": "BL_F_SilkS",
                  "shape": {"attributes": {"stroke": {"width": {"value_nm": 0}}, "fill": {"fill_type": "GFT_FILLED"}},
                            "polygon": {"polygons": [{"outline": {"closed": True, "nodes": nodes}}]}}})
json.dump({"header": {"document": {"type": "DOCTYPE_PCB", "board_filename": "chainaxe.kicad_pcb"}}, "items": items},
          open(os.path.join(HERE, "board_items.json"), "w"), separators=(",", ":"))
