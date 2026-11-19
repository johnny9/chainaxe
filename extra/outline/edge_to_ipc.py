import sys, os, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dxfload import load
d = load(sys.argv[1])
OX, OY = 58.26, 134.245            # DXF (0,0) -> KiCad (OX, OY), y flipped
nm = lambda v: int(round(v*1e6))
P = lambda x, y: {"x_nm": nm(OX+x), "y_nm": nm(OY-y)}
attrs = {"stroke":{"width":{"value_nm":50000},"style":"SLS_DEFAULT"},"fill":{"fill_type":"GFT_UNFILLED"}}
T = "type.googleapis.com/kiapi.board.types.BoardGraphicShape"
items = []
for x0,y0,x1,y1,_ in d['lines']:
    items.append({"@type":T,"layer":"BL_Edge_Cuts","shape":{"attributes":attrs,"segment":{"start":P(x0,y0),"end":P(x1,y1)}}})
for cx,cy,r,a0,a1 in d['arcs']:
    if a1 < a0: a1 += 360
    pt = lambda a: P(cx+r*math.cos(math.radians(a)), cy+r*math.sin(math.radians(a)))
    items.append({"@type":T,"layer":"BL_Edge_Cuts","shape":{"attributes":attrs,"arc":{"start":pt(a0),"mid":pt((a0+a1)/2),"end":pt(a1)}}})
# the 3.5 mm hole (the 3.0 mm ones are the mounting-hole footprints)
for cx,cy,r in d['circles']:
    if r > 1.6:
        items.append({"@type":T,"layer":"BL_Edge_Cuts","shape":{"attributes":attrs,"circle":{"center":P(cx,cy),"radius_point":P(cx+r,cy)}}})
print(json.dumps({"header":{"document":{"type":"DOCTYPE_PCB","board_filename":"chainaxe.kicad_pcb"}},"items":items},separators=(',',':')))
