#!/usr/bin/env python3
"""Put Reference/Value fields of displaced footprints back at their library offsets.

Usage: reset_ref_text.py <board> <footprint dir> [<other board for defaults> ...]
A field counts as displaced when its offset from the footprint is over 6 mm.
Defaults come from the footprint dir (by footprint name), else from the same
footprint name on another board.
"""
import re, sys, glob, os

board, fpdir, *others = sys.argv[1:]
defaults = {}
def grab(txt, name):
    d = {}
    for k in ('Reference', 'Value'):
        m = re.search(r'\(property "%s" "[^"]*"\s*\(at ([\d.-]+) ([\d.-]+)(?: ([\d.-]+))?\)' % k, txt)
        if m:
            d[k] = (float(m.group(1)), float(m.group(2)))
    if len(d) == 2:
        defaults.setdefault(name, d)
for f in glob.glob(os.path.join(fpdir, '*.kicad_mod')):
    grab(open(f).read(), os.path.basename(f)[:-10])
for ob in others:
    t = open(ob).read()
    for m in re.finditer(r'\n\t\(footprint "(?:[^":]*:)?([^"]+)"(?:(?!\n\t\)).)*\n\t\)', t, re.S):
        fp = m.group(0)
        if re.search(r'\(rotate 0\)', fp):
            grab(fp, m.group(1))

s = open(board).read()
fixed = []
def fix(m):
    fp = m.group(0)
    name = m.group(1)
    ref = re.search(r'\(property "Reference" "([^"]*)"', fp).group(1)
    rot = float(re.search(r'\(rotate ([\d.-]+)\)', fp).group(1))
    d = defaults.get(name, {'Reference': (0.0, -2.0), 'Value': (0.0, 2.0)})
    def one(pm):
        k, x, y = pm.group(1), float(pm.group(2)), float(pm.group(3))
        if (x * x + y * y) ** 0.5 <= 6:
            return pm.group(0)
        dx, dy = d[k]
        fixed.append(ref)
        return f'(property "{k}"{pm.group(4)}(at {dx} {dy} {rot % 360:g})'
    return re.sub(r'\(property "(Reference|Value)"( "[^"]*"\s*)\(at ([\d.-]+) ([\d.-]+)(?: [\d.-]+)?\)',
                  lambda pm: one(type('M', (), {'group': lambda self, i: [pm.group(0), pm.group(1), pm.group(3), pm.group(4), pm.group(2)][i]})()),
                  fp)

s = re.sub(r'\n\t\(footprint "(?:[^":]*:)?([^"]+)"(?:(?!\n\t\)).)*\n\t\)', fix, s, flags=re.S)
open(board, 'w').write(s)
print('reset', sorted(set(fixed)))
