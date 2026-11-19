#!/usr/bin/env python3
"""Rebuild chainaxe signal routing on the Bitcrane's own trace geometry.

The ESP32-S3 sits where the FTDI was (centre bottom, antenna to the bottom edge).
Bitcrane's hashboard traces (B.Cu, 45 deg diagonals into the centre) and its I2C,
fan-alert and PSU-enable traces are restored from the original board and extended
straight onto the module pins.

Usage: rebuild_routes.py <board> <original bitcrane board, upgraded> <netlist.xml>
Edits <board> in place.
"""
import re, sys, uuid, xml.etree.ElementTree as ET

board, orig, netlist = sys.argv[1:4]
s = open(board).read()
o = open(orig).read()

# ---------------------------------------------------------------- pad nets
padnet = {}
for n in ET.parse(netlist).iter('net'):
    nm = n.get('name')
    if nm.startswith('unconnected-'):
        nm = nm.replace('/', '{slash}')
    for node in n.iter('node'):
        padnet.setdefault(node.get('ref'), {})[node.get('pin')] = nm

def fix_fp(m):
    fp = m.group(0)
    ref = re.search(r'\(property "Reference" "([^"]*)"', fp).group(1)
    if ref not in padnet:
        return ''  # part no longer in the schematic
    nets = padnet[ref]
    def fix_pad(pm):
        body, num = pm.group(0), pm.group(1)
        new = nets.get(num)
        old = re.search(r'\(net "([^"]*)"\)', body)
        if new is None or (old and old.group(1) == new):
            return body
        if old:
            return body.replace(old.group(0), f'(net "{new}")', 1)
        return re.sub(r'\n(\t\t\t)\(uuid', lambda u: f'\n{u.group(1)}(net "{new}")\n{u.group(1)}(uuid', body, count=1)
    return re.sub(r'\(pad "([^"]*)"(?:(?!\n\t\t\)).)*?\n\t\t\)', fix_pad, fp, flags=re.S)

s = re.sub(r'\n\t\(footprint (?:(?!\n\t\)).)*\n\t\)', fix_fp, s, flags=re.S)

# ---------------------------------------------------------------- rip up
HB = [f'/{k}{i}' for i in range(3) for k in ('TXD', 'RXD', 'RST', 'PLUG')]
RIP = set(HB + ['/SDA', '/SCL', '/FAN_ALERT', '/PSU_EN', '/USB_DP', '/USB_DN', '/CC1', '/CC2',
                'VBUS', '/EN', '/IO0', '/3V3_EN', '/VIN_3V3'])

def rip(m):
    it = m.group(0)
    nm = re.search(r'\(net "([^"]*)"\)', it)
    net = nm.group(1) if nm else ''
    if net in RIP:
        return ''
    if net == '/3V3':  # stubs left behind by the moved I2C pull-ups
        pts = [tuple(map(float, p)) for p in re.findall(r'\((?:start|end|at) ([\d.-]+) ([\d.-]+)', it)]
        if any(98 <= x <= 102.5 and 53 <= y <= 56 for x, y in pts):
            return ''
    return it

s = re.sub(r'\n\t\((?:segment|via|arc)\n(?:(?!\n\t\)).)*\n\t\)', rip, s, flags=re.S)

# ---------------------------------------------------------------- original geometry
oseg = re.findall(r'\(segment\s*\(start ([\d.]+) ([\d.]+)\)\s*\(end ([\d.]+) ([\d.]+)\)\s*\(width ([\d.]+)\)\s*'
                  r'\(layer "([^"]+)"\)\s*\(net "([^"]+)"\)', o)
ovia = re.findall(r'\(via\s*\(at ([\d.]+) ([\d.]+)\)(?:(?!\n\t\)).)*?\(net "([^"]+)"\)', o, re.S)

new = []
def seg(a, b, layer, net, w=0.25):
    new.append(f'\t(segment\n\t\t(start {a[0]} {a[1]})\n\t\t(end {b[0]} {b[1]})\n\t\t(width {w})\n'
               f'\t\t(layer "{layer}")\n\t\t(net "{net}")\n\t\t(uuid "{uuid.uuid4()}")\n\t)')
def via(p, net, size=0.8, drill=0.4):
    new.append(f'\t(via\n\t\t(at {p[0]} {p[1]})\n\t\t(size {size})\n\t\t(drill {drill})\n'
               f'\t\t(layers "F.Cu" "B.Cu")\n\t\t(net "{net}")\n\t\t(uuid "{uuid.uuid4()}")\n\t)')
def path(pts, layer, net):
    for a, b in zip(pts, pts[1:]):
        seg(a, b, layer, net)
def keep_orig(net, pred):
    for x1, y1, x2, y2, w, layer, n in oseg:
        if n == net and pred(float(x1), float(y1), float(x2), float(y2), layer):
            seg((x1, y1), (x2, y2), layer, net, w)

PIN_Y, VIA_Y = 109.0, 106.9           # module top-row pads, via row just outside its courtyard
def top_x(pin):                        # ESP32 at (116, 118.5) rot 180: top-row pad x
    return round(121.715 - (pin - 16) * 1.27, 3)

# hashboard 0/1: Bitcrane escapes (y < 64) + its diagonal, turned straight down onto the pin
HB01 = {  # net: (diagonal start, module pin)
    '/TXD0': ((78.054416, 45.68), 25), '/RXD0': ((78.230812, 45.22), 24),
    '/PLUG0': ((78.417208, 44.77), 23), '/RST0': ((78.523604, 44.24), 22),
    '/RST1': ((90.505, 55.585), 21), '/RXD1': ((90.955, 55.398604), 20),
    '/TXD1': ((91.51, 55.21), 19), '/PLUG1': ((97.51, 60.573604), 18),
}
for net, (st, pin) in HB01.items():
    keep_orig(net, lambda x1, y1, x2, y2, l: max(y1, y2) < 64 and l == 'B.Cu')
    x = top_x(pin)
    c = st[1] - st[0]
    turn = (x, round(x + c, 6))
    path([st, turn, (x, VIA_Y)], 'B.Cu', net)
    via((x, VIA_Y), net)
    seg((x, VIA_Y), (x, PIN_Y), 'F.Cu', net)

# hashboard 2: Bitcrane escapes + diagonals, nested verticals onto the left-column pins
LEFT_X, LVIA_X = 107.25, 105.6
def left_y(pin):                       # left column (pins 27..40) pad y
    return round(110.25 + (pin - 27) * 1.27, 3)
HB2 = {
    '/PLUG2': ([(76.08, 57.01), (75.883198, 57.206802), (75.883198, 69.646802), (94.526396, 88.29)], 104.5, 31),
    '/TXD2': ([(70.08, 57.01), (70.08, 64.48), (94.66, 89.06)], 103.5, 32),
    '/RXD2': ([(70.08, 55.01), (69.105, 55.985), (69.105, 64.141396), (94.473604, 89.51)], 102.5, 33),
    '/RST2': ([(66.08, 57.01), (66.08, 61.79), (94.25, 89.96)], 101.5, 34),
}
for net, (pts, vx, pin) in HB2.items():
    y = left_y(pin)
    path(pts + [(vx, pts[-1][1]), (vx, y), (LVIA_X, y)], 'B.Cu', net)
    via((LVIA_X, y), net)
    seg((LVIA_X, y), (LEFT_X, y), 'F.Cu', net)

# I2C: everything Bitcrane had, minus its stubs into the FTDI, plus drops onto pins 17/15
FTDI = lambda x1, y1, x2, y2, l: (119 < min(x1, x2) and max(x1, x2) < 123.3 and 99 < min(y1, y2) and max(y1, y2) < 103)
keep_orig('/SDA', lambda *a: not FTDI(*a) and not (a[0] == 123.217653 and a[2] == 145.982347))
keep_orig('/SCL', lambda *a: not FTDI(*a) and not (a[2] == 146.168743 and a[0] == 122.222653))
for x, y, n in ovia:
    if (n, x, y) in (('/SDA', '109.68', '67.28'), ('/SCL', '111.285304', '67.889999'), ('/SCL', '160.935', '87.15')):
        via((x, y), n)
sda_x, scl_x = top_x(17), top_x(15)
path([(145.982347, 102.317653), (sda_x, 102.317653), (sda_x, VIA_Y)], 'B.Cu', '/SDA')
via((sda_x, VIA_Y), '/SDA'); seg((sda_x, VIA_Y), (sda_x, PIN_Y), 'F.Cu', '/SDA')
path([(146.168743, 102.767653), (scl_x, 102.767653), (scl_x, VIA_Y)], 'B.Cu', '/SCL')
via((scl_x, VIA_Y), '/SCL'); seg((scl_x, VIA_Y), (scl_x, PIN_Y), 'F.Cu', '/SCL')

# fan alert: Bitcrane's run from the EMC2305 past R19, then down beside the module to pin 12
keep_orig('/FAN_ALERT', lambda x1, y1, x2, y2, l: l == 'F.Cu' and min(x1, x2) > 126)
path([(127.1755, 92.40986), (126.5, 93.08536), (126.5, 107.2)], 'F.Cu', '/FAN_ALERT')
via((126.5, 107.2), '/FAN_ALERT'); seg((126.5, 107.2), (126.5, 112.79), 'B.Cu', '/FAN_ALERT')
via((126.5, 112.79), '/FAN_ALERT'); seg((126.5, 112.79), (124.75, 112.79), 'F.Cu', '/FAN_ALERT')

# PSU enable: Bitcrane's diagonal from the PSU header, then down to pin 11
path([(158.21, 80.245), (157.635, 80.245), (139.755, 98.125), (127.8, 98.125), (127.8, 107.2)], 'F.Cu', '/PSU_EN')
via((127.8, 107.2), '/PSU_EN'); seg((127.8, 107.2), (127.8, 114.3), 'B.Cu', '/PSU_EN')
via((127.8, 114.3), '/PSU_EN')
path([(127.8, 114.3), (127.56, 114.06), (124.75, 114.06)], 'F.Cu', '/PSU_EN')

s = s.rstrip()
assert s.endswith(')')
s = s[:-1].rstrip() + '\n' + '\n'.join(new) + '\n)\n'
open(board, 'w').write(s)
print('added', len(new), 'items')
