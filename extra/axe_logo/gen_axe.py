#!/usr/bin/env python3
"""Chainaxe silkscreen logo traced from a reference photo (pixel coords, y down).
Usage: gen_axe.py [mm_per_px] [cx_mm] [cy_mm]  -> preview png + board_items.json (IPC CreateItems)"""
import math, sys, os, json
S = float(sys.argv[1]) if len(sys.argv) > 1 else 0.055
BX = float(sys.argv[2]) if len(sys.argv) > 2 else 115.0
BY = float(sys.argv[3]) if len(sys.argv) > 3 else 83.0
HERE = os.path.dirname(os.path.abspath(__file__))
polys = []

# head slab with C cut-out (open toward the haft)
polys.append([(68,330),(158,236),(232,215),(244,172),(292,168),(360,232),(352,275),(418,300),(422,332),
              (392,342),(352,312),(318,312),(290,336),(283,352),(298,392),(335,420),(380,432),(445,488),
              (452,502),(360,522),(128,352),(88,346)])
# top spike
polys.append([(325,122),(351,120),(300,170)])
# chain teeth along lower-left edge
p0, p1 = (128,352), (358,520)
L = math.dist(p0, p1); d = ((p1[0]-p0[0])/L, (p1[1]-p0[1])/L); n = (-d[1], d[0])
if n[0] > 0: n = (-n[0], -n[1])
n = (-abs(n[0]), abs(n[1]))
N = 8; pitch = L/(N)
for i in range(N):
    c = (i+0.5)*pitch
    b0 = (p0[0]+d[0]*(c-11), p0[1]+d[1]*(c-11)); b1 = (p0[0]+d[0]*(c+11), p0[1]+d[1]*(c+11))
    tip = (p0[0]+d[0]*(c+24)+n[0]*38, p0[1]+d[1]*(c+24)+n[1]*38)
    polys.append([b0, tip, b1])
# coiled haft
h0, h1 = (440,382), (672,630)
HL = math.dist(h0, h1); hd = ((h1[0]-h0[0])/HL, (h1[1]-h0[1])/HL); hn = (-hd[1], hd[0])
def quad(a, l0, l1, w):
    P = lambda l, s: (h0[0]+hd[0]*l+hn[0]*s, h0[1]+hd[1]*l+hn[1]*s)
    return [P(l0,-w), P(l1,-w), P(l1,w), P(l0,w)]
polys.append(quad(0, -52, -20, 15))          # neck from block
polys.append(quad(0, -14, 8, 28))            # collar
k = 0; l = 14
while l + 15 < HL - 6:
    polys.append(quad(0, l, l+15, 19)); l += 21
polys.append(quad(0, HL-4, HL+22, 27))      # end cap

xs = [p[0] for q in polys for p in q]; ys = [p[1] for q in polys for p in q]
cx, cy = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2
T = lambda p: ((p[0]-cx)*S+BX, (p[1]-cy)*S+BY)
print("size mm: %.1f x %.1f, %d polys" % ((max(xs)-min(xs))*S, (max(ys)-min(ys))*S, len(polys)))

from PIL import Image, ImageDraw
im = Image.new("RGB", (800, 800), (20,70,40)); d_ = ImageDraw.Draw(im)
for q in polys: d_.polygon(q, fill=(240,240,235))
im.save(os.path.join(HERE, "chainaxe_logo_preview.png"))

items = [{"@type":"type.googleapis.com/kiapi.board.types.BoardGraphicShape","layer":"BL_F_SilkS",
  "shape":{"attributes":{"stroke":{"width":{"value_nm":0}},"fill":{"fill_type":"GFT_FILLED"}},
  "polygon":{"polygons":[{"outline":{"closed":True,"nodes":[{"point":{"x_nm":round(T(p)[0]*100)*10000,"y_nm":round(T(p)[1]*100)*10000}} for p in q]}}]}}} for q in polys]
json.dump({"header":{"document":{"type":"DOCTYPE_PCB","board_filename":"chainaxe.kicad_pcb"}},"items":items},
          open(os.path.join(HERE,"board_items.json"),"w"), separators=(",",":"))
