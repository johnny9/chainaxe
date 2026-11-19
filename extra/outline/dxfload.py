import math
def load(f):
    L=[l.rstrip('\n') for l in open(f,errors='replace')]
    pairs=[(int(L[i]),L[i+1].strip()) for i in range(0,len(L)-1,2)]
    ents=[];cur=None;sec=None
    for c,v in pairs:
        if c==0 and v=='SECTION': sec=None
        if c==2 and sec is None: sec=v
        if sec in('ENTITIES','BLOCKS'):
            if c==0: cur={'t':v,'d':{}}; ents.append(cur)
            elif cur is not None: cur['d'].setdefault(c,[]).append(v)
    g=lambda e,c: float(e['d'][c][0]) if c in e['d'] else 0.0
    out={'lines':[],'circles':[],'arcs':[],'text':[]}
    for e in ents:
        if e['t']=='LINE': out['lines'].append((g(e,10),g(e,20),g(e,11),g(e,21),e['d'].get(8,[''])[0]))
        elif e['t']=='CIRCLE': out['circles'].append((g(e,10),g(e,20),g(e,40)))
        elif e['t']=='ARC': out['arcs'].append((g(e,10),g(e,20),g(e,40),g(e,50),g(e,51)))
        elif e['t']=='MTEXT': out['text'].append(e['d'])
    return out
