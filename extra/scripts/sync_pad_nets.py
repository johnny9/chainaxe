#!/usr/bin/env python3
"""Set every footprint pad's net on a board from a KiCad XML netlist; drop tracks/vias
of nets whose pads changed (they are re-routed afterwards).

Usage: sync_pad_nets.py <board> <netlist.xml>   (edits the board in place)
"""
import re, sys, xml.etree.ElementTree as ET

board, netlist = sys.argv[1:3]
padnet = {}
for n in ET.parse(netlist).iter('net'):
    nm = n.get('name')
    if nm.startswith('unconnected-'):
        nm = nm.replace('/', '{slash}')
    for node in n.iter('node'):
        padnet.setdefault(node.get('ref'), {})[node.get('pin')] = nm

s = open(board).read()
changed = set()

def fix_fp(m):
    fp = m.group(0)
    ref = re.search(r'\(property "Reference" "([^"]*)"', fp).group(1)
    nets = padnet.get(ref)
    if nets is None:
        return fp
    def fix_pad(pm):
        body, num = pm.group(0), pm.group(1)
        new = nets.get(num)
        old = re.search(r'\(net "([^"]*)"\)', body)
        if new is None or (old and old.group(1) == new):
            return body
        if old:
            changed.add(old.group(1))
        changed.add(new)
        if old:
            return body.replace(old.group(0), f'(net "{new}")', 1)
        return re.sub(r'\n(\t\t\t)\(uuid', lambda u: f'\n{u.group(1)}(net "{new}")\n{u.group(1)}(uuid', body, count=1)
    return re.sub(r'\(pad "([^"]*)"(?:(?!\n\t\t\)).)*?\n\t\t\)', fix_pad, fp, flags=re.S)

s = re.sub(r'\n\t\(footprint (?:(?!\n\t\)).)*\n\t\)', fix_fp, s, flags=re.S)
changed = {c for c in changed if not c.startswith('unconnected-')}
dropped = 0
def drop(m):
    global dropped
    nm = re.search(r'\(net "([^"]*)"\)', m.group(0))
    if nm and nm.group(1) in changed:
        dropped += 1
        return ''
    return m.group(0)
s = re.sub(r'\n\t\((?:segment|via|arc)\n(?:(?!\n\t\)).)*\n\t\)', drop, s, flags=re.S)
open(board, 'w').write(s)
print('nets changed:', sorted(changed), 'tracks/vias dropped:', dropped)
