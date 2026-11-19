#!/usr/bin/env python3
"""One-off transfer of the chainaxe schematic onto the Bitcrane-derived board.

Usage: sch_to_pcb.py <upgraded board in> <netlist.xml> <footprint dir> <board out>

- removes footprints whose reference is gone from the schematic or that are
  (re)added below, plus the Bitcrane logo
- reassigns every kept pad to its net from the new netlist
- removes tracks/vias of nets that touched removed parts (GND and the 3V3
  plane net only inside the old FTDI area), renames the rest to new net names
- adds the new footprints (unrotated) at rough positions, nets on every pad
"""
import re, sys, uuid, xml.etree.ElementTree as ET

board_in, netlist, fpdir, board_out = sys.argv[1:5]

def items(s, depth_want=1):
    """Top-level child items of the root s-expression: list of (start, end)."""
    out = []; depth = 0; start = None; instr = False; esc = False
    for i, ch in enumerate(s):
        if instr:
            if esc: esc = False
            elif ch == '\\': esc = True
            elif ch == '"': instr = False
            continue
        if ch == '"': instr = True
        elif ch == '(':
            depth += 1
            if depth == depth_want + 1: start = i
        elif ch == ')':
            if depth == depth_want + 1: out.append((start, i + 1))
            depth -= 1
    return out

s = open(board_in).read()

# ---- new netlist
t = ET.parse(netlist)
comps = {}
for c in t.iter('comp'):
    ref = c.get('ref')
    fields = {f.get('name'): (f.text or '') for f in c.iter('field')}
    tst = c.find('tstamps')
    comps[ref] = dict(value=c.findtext('value'), footprint=c.findtext('footprint'),
                      ts=(tst.text if tst is not None else c.findtext('tstamp')), fields=fields)
padnet = {}
for n in t.iter('net'):
    for node in n.iter('node'):
        nm = n.get('name')
        if nm.startswith('unconnected-'):
            nm = nm.replace('/', '{slash}')
        padnet.setdefault(node.get('ref'), {})[node.get('pin')] = nm

NEW = ['U1', 'U2', 'C1', 'C2', 'C6', 'C7', 'C9', 'C10', 'C11', 'R4', 'R5', 'R6', 'R7', 'R8',
       'J11', 'D2', 'D3', 'SW1', 'SW2', 'J8', 'J12']
POS = {  # rough first placement, refined with kicad_edit afterwards
    'U1': (142, 116), 'C9': (128, 106), 'C10': (128, 109), 'R8': (126, 113), 'C11': (126, 116),
    'SW1': (92, 127), 'SW2': (126, 127), 'J12': (100, 117), 'J11': (111.09, 129.41),
    'R4': (103.57, 128.73), 'R5': (118.36, 128.75), 'J8': (84, 105),
    'U2': (150, 94), 'D2': (150, 87), 'D3': (138, 99), 'C1': (156, 91), 'C2': (156, 94),
    'R6': (145, 91), 'R7': (145, 94), 'C6': (150, 99), 'C7': (154, 99),
}

its = items(s)
keep = []
removed_nets = set()
rename = {}  # old net -> set(new nets)
region = (88, 78, 137, 135)  # old FTDI / USB area

def inreg(x, y):
    return region[0] <= x <= region[2] and region[1] <= y <= region[3]

out_parts = []
for a, b in its:
    it = s[a:b]
    if it.startswith('(footprint'):
        ref = re.search(r'\(property "Reference" "([^"]*)"', it).group(1)
        pads = [(None, n) for n in re.findall(r'\(net "([^"]*)"\)', it)]
        if ref not in comps or ref in NEW or 'logo' in it[:80]:
            for p, n in pads: removed_nets.add(n)
            continue
        # reassign pad nets
        def fix(m):
            body = m.group(0)
            pnum = m.group(1)
            new = padnet.get(ref, {}).get(pnum)
            oldm = re.search(r'\(net "([^"]*)"\)', body)
            if oldm and new: rename.setdefault(oldm.group(1), set()).add(new)
            if new is None:
                return re.sub(r'\n\t\t\t\(net "[^"]*"\)', '', body)
            if oldm:
                return body.replace(oldm.group(0), f'(net "{new}")')
            return body.replace('\n\t\t\t(pintype', f'\n\t\t\t(net "{new}")\n\t\t\t(pintype', 1)
        it = re.sub(r'\(pad "([^"]*)"(?:(?!\n\t\t\)).)*?\n\t\t\)', fix, it, flags=re.S)
        it = it.replace('(sheetfile "bitcrane.kicad_sch")', '(sheetfile "chainaxe.kicad_sch")')
        out_parts.append((a, b, it))
    else:
        out_parts.append((a, b, it))

def newname(old):
    r = rename.get(old)
    if r and len(r) == 1: return next(iter(r))
    return None

kept = []
stats = dict(track_del=0, track_ren=0)
for a, b, it in out_parts:
    if it.startswith(('(segment', '(via', '(arc')):
        nm = re.search(r'\(net "([^"]*)"\)', it)
        net = nm.group(1) if nm else ''
        pts = [tuple(map(float, p)) for p in re.findall(r'\((?:start|end|at|mid) ([\d.-]+) ([\d.-]+)', it)]
        if net in ('GND', 'VCCIO'):
            if any(inreg(*p) for p in pts):
                stats['track_del'] += 1; continue
        elif net in removed_nets or newname(net) is None:
            stats['track_del'] += 1; continue
        nn = newname(net)
        if nn and nn != net:
            it = it.replace(nm.group(0), f'(net "{nn}")'); stats['track_ren'] += 1
        kept.append(it)
    elif it.startswith('(zone'):
        nm = re.search(r'\(net "([^"]*)"\)', it)
        if nm and nm.group(1):
            nn = newname(nm.group(1)) or nm.group(1)
            it = it.replace(nm.group(0), f'(net "{nn}")')
        # drop stale fill; kicad_edit refills on save
        parts = []; pos = 0
        for fa, fb in [(fa, fb) for fa, fb in items(it, 1) if it[fa:].startswith('(filled_polygon')]:
            parts.append(it[pos:fa].rstrip(' \t')); pos = fb
        parts.append(it[pos:])
        it = ''.join(parts)
        kept.append(it)
    else:
        kept.append(it)

# ---- new footprints
def load_fp(libid):
    name = libid.split(':', 1)[1]
    txt = open(f'{fpdir}/{name}.kicad_mod').read()
    a, b = [(a, b) for a, b in items(txt) if txt[a:].startswith('(footprint')][0]
    return txt[a:b]

def indent(txt):
    return '\n'.join(('\t' + ln[1:] if ln.startswith('\t') else ln) for ln in txt.split('\n'))

added = []
for ref in NEW:
    c = comps[ref]
    fp = load_fp(c['footprint'])
    name = c['footprint'].split(':', 1)[1]
    fp = fp.replace(f'(footprint "{name}"', f'(footprint "{c["footprint"]}"', 1)
    fp = re.sub(r'(\(property "Reference" ")[^"]*"', lambda m: m.group(1) + ref + '"', fp, count=1)
    fp = re.sub(r'(\(property "Value" ")[^"]*"', lambda m: m.group(1) + c['value'] + '"', fp, count=1)
    fp = re.sub(r'\n\t\t\(uuid "[^"]*"\)', '', fp, 1) if fp.find('(uuid') < fp.find('(property') else fp
    x, y = POS[ref]
    head = (f'\n\t\t(uuid "{uuid.uuid4()}")\n\t\t(transform\n\t\t\t(translate {x} {y})\n'
            f'\t\t\t(rotate 0)\n\t\t\t(scale 1 1)\n\t\t)')
    fp = fp.replace('\n\t\t(layer "F.Cu")', '\n\t\t(layer "F.Cu")' + head, 1)
    for k in ('Datasheet', 'Description'):
        v = c['fields'].get(k, '').replace('"', "'")
        fp = re.sub(r'(\(property "%s" ")[^"]*"' % k, lambda m: m.group(1) + v + '"', fp, count=1)
    extra = ''
    for k in [k for k in c['fields'] if k not in ('Footprint', 'Datasheet', 'Description', 'Reference', 'Value')]:
        if c['fields'].get(k):
            extra += (f'\n\t\t(property "{k}" "{c["fields"][k]}"\n\t\t\t(at 0 0 0)\n\t\t\t(layer "F.Fab")\n'
                      f'\t\t\t(hide yes)\n\t\t\t(uuid "{uuid.uuid4()}")\n\t\t\t(effects\n\t\t\t\t(font\n'
                      f'\t\t\t\t\t(size 1 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)')
    extra += (f'\n\t\t(path "/{c["ts"]}")\n\t\t(sheetname "Root")\n\t\t(sheetfile "chainaxe.kicad_sch")')
    # insert after the last top-level property of the footprint
    props = [m.end() for m in re.finditer(r'\n\t\t\(property (?:(?!\n\t\t\)).)*\n\t\t\)', fp, re.S)]
    fp = fp[:props[-1]] + extra + fp[props[-1]:]
    nets = padnet.get(ref, {})
    def addnet(m):
        body = m.group(0); p = m.group(1)
        if p in nets:
            body = re.sub(r'\n(\t\t\t)\(uuid', lambda mm: f'\n{mm.group(1)}(net "{nets[p]}")\n{mm.group(1)}(uuid', body, count=1)
        return body
    fp = re.sub(r'\(pad "([^"]*)"(?:(?!\n\t\t\)).)*?\n\t\t\)', addnet, fp, flags=re.S)
    fp = re.sub(r'\(uuid "[^"]*"\)', lambda m: f'(uuid "{uuid.uuid4()}")', fp)
    added.append(fp)

# reassemble: header up to first item, kept items, new footprints, closing paren
first = its[0][0]
body = s[:first] + '\n\t'.join(kept) + '\n\t' + '\n\t'.join(added) + '\n)\n'
open(board_out, 'w').write(body)
print('removed nets', len(removed_nets), stats, 'ambiguous renames',
      {k: v for k, v in rename.items() if len(v) > 1})
print('renames', {k: next(iter(v)) for k, v in rename.items() if len(v) == 1 and next(iter(v)) != k})
