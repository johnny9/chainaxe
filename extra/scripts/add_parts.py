#!/usr/bin/env python3
"""Bring the board in line with the schematic's parts list.

Usage: add_parts.py <board> <netlist.xml> <footprint dir> <placements.json>
- removes footprints whose reference left the schematic
- adds footprints for new references at the given (x, y, rot)
- sets every pad's net from the netlist
- removes tracks/vias whose net no longer exists, and segments listed in
  placements.json "drop_segments" ([x1, y1, x2, y2, net])
"""
import json, re, sys, uuid, xml.etree.ElementTree as ET

board, netlist, fpdir, placements = sys.argv[1:5]
P = json.load(open(placements))
s = open(board).read()

comps, padnet, netnames = {}, {}, set()
for c in ET.parse(netlist).iter('comp'):
    comps[c.get('ref')] = dict(value=c.findtext('value'), footprint=c.findtext('footprint'),
                               ts=c.find('tstamps').text,
                               fields={f.get('name'): (f.text or '') for f in c.iter('field')})
for n in ET.parse(netlist).iter('net'):
    nm = n.get('name')
    if nm.startswith('unconnected-'):
        nm = nm.replace('/', '{slash}')
    netnames.add(nm)
    for node in n.iter('node'):
        padnet.setdefault(node.get('ref'), {})[node.get('pin')] = nm

FP = r'\n\t\(footprint (?:(?!\n\t\)).)*\n\t\)'
present = set(re.findall(r'\n\t\(footprint (?:(?!\n\t\)).)*?\(property "Reference" "([^"]*)"', s, re.S))

def fix_pads(fp, ref):
    nets = padnet.get(ref, {})
    def one(pm):
        body, num = pm.group(0), pm.group(1)
        new = nets.get(num)
        old = re.search(r'\(net "([^"]*)"\)', body)
        if new is None:
            return re.sub(r'\n\t\t\t\(net "[^"]*"\)', '', body)
        if old:
            return body.replace(old.group(0), f'(net "{new}")', 1)
        return re.sub(r'\n(\t\t\t)\(uuid', lambda u: f'\n{u.group(1)}(net "{new}")\n{u.group(1)}(uuid', body, count=1)
    return re.sub(r'\(pad "([^"]*)"(?:(?!\n\t\t\)).)*?\n\t\t\)', one, fp, flags=re.S)

def keep(m):
    fp = m.group(0)
    ref = re.search(r'\(property "Reference" "([^"]*)"', fp).group(1)
    if ref not in comps:
        return ''
    return fix_pads(fp, ref)
s = re.sub(FP, keep, s, flags=re.S)

drop = [tuple(x) for x in P.get('drop_segments', [])]
def tracks(m):
    it = m.group(0)
    nm = re.search(r'\(net "([^"]*)"\)', it)
    net = nm.group(1) if nm else ''
    if net and net not in netnames:
        return ''
    se = re.search(r'\(start ([\d.-]+) ([\d.-]+)\)\s*\(end ([\d.-]+) ([\d.-]+)\)', it)
    if se:
        a = tuple(round(float(v), 3) for v in se.groups())
        for d in drop:
            dd = tuple(round(float(v), 3) for v in d[:4])
            if d[4] == net and (a == dd or a == (dd[2], dd[3], dd[0], dd[1])):
                return ''
    return it
s = re.sub(r'\n\t\((?:segment|via|arc)\n(?:(?!\n\t\)).)*\n\t\)', tracks, s, flags=re.S)

def items(txt):
    out, depth, start, instr, esc = [], 0, None, False, False
    for i, ch in enumerate(txt):
        if instr:
            if esc: esc = False
            elif ch == '\\': esc = True
            elif ch == '"': instr = False
            continue
        if ch == '"': instr = True
        elif ch == '(':
            depth += 1
            if depth == 2: start = i
        elif ch == ')':
            if depth == 2: out.append((start, i + 1))
            depth -= 1
    return out

added = []
for ref, (x, y, rot) in P['place'].items():
    if ref in present:
        continue
    c = comps[ref]
    name = c['footprint'].split(':', 1)[1]
    txt = open(f'{fpdir}/{name}.kicad_mod').read()
    a, b = [(a, b) for a, b in items(txt) if txt[a:].startswith('(footprint')][0]
    fp = txt[a:b].replace(f'(footprint "{name}"', f'(footprint "{c["footprint"]}"', 1)
    fp = re.sub(r'(\(property "Reference" ")[^"]*"', lambda m: m.group(1) + ref + '"', fp, count=1)
    fp = re.sub(r'(\(property "Value" ")[^"]*"', lambda m: m.group(1) + c['value'] + '"', fp, count=1)
    for k in ('Datasheet', 'Description'):
        v = c['fields'].get(k, '').replace('"', "'")
        fp = re.sub(r'(\(property "%s" ")[^"]*"' % k, lambda m: m.group(1) + v + '"', fp, count=1)
    head = (f'\n\t\t(uuid "{uuid.uuid4()}")\n\t\t(transform\n\t\t\t(translate {x} {y})\n'
            f'\t\t\t(rotate {rot})\n\t\t\t(scale 1 1)\n\t\t)')
    fp = fp.replace('\n\t\t(layer "F.Cu")', '\n\t\t(layer "F.Cu")' + head, 1)
    extra = ''
    for k, v in c['fields'].items():
        if k in ('Footprint', 'Datasheet', 'Description', 'Reference', 'Value'):
            continue
        extra += (f'\n\t\t(property "{k}" "{v}"\n\t\t\t(at 0 0 0)\n\t\t\t(layer "F.Fab")\n\t\t\t(hide yes)\n'
                  f'\t\t\t(uuid "{uuid.uuid4()}")\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)')
    extra += f'\n\t\t(path "/{c["ts"]}")\n\t\t(sheetname "Root")\n\t\t(sheetfile "chainaxe.kicad_sch")'
    props = [m.end() for m in re.finditer(r'\n\t\t\(property (?:(?!\n\t\t\)).)*\n\t\t\)', fp, re.S)]
    fp = fp[:props[-1]] + extra + fp[props[-1]:]
    fp = fix_pads(fp, ref)
    fp = re.sub(r'\(uuid "[^"]*"\)', lambda m: f'(uuid "{uuid.uuid4()}")', fp)
    added.append(fp)

s = s.rstrip()
s = s[:-1].rstrip() + '\n' + '\n'.join(added) + '\n)\n'
open(board, 'w').write(s)
print('added', len(added), 'footprints; removed', sorted(present - set(comps)))
