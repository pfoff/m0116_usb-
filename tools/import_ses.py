"""Replace the tracks of a board with the wires/vias of a Freerouting .ses file.

Every net in the session replaces the board's tracks on that net (Freerouting
writes the complete wiring of each net, protected wires included).
"""
import pcbnew, re, sys
G = []  # keep removed items alive (KiCad 7 SWIG quirk, see tools/update_pcb.py)

def parse(text):
    tokens = re.findall(r'"[^"]*"|\(|\)|[^\s()"]+', text)
    stack = [[]]
    for t in tokens:
        if t == "(": stack.append([])
        elif t == ")": d = stack.pop(); stack[-1].append(d)
        else: stack[-1].append(t.strip('"'))
    return stack[0][0]

def find(node, key):
    if isinstance(node, list):
        if node and node[0] == key: yield node
        for c in node: yield from find(c, key)

pcb, ses = sys.argv[1:3]   # usage: /usr/bin/python3 tools/import_ses.py board.kicad_pcb routed.ses
b = pcbnew.LoadBoard(pcb)
tree = parse(open(ses).read())
routes = next(find(tree, "routes"))
nets = {n[1] for n in find(routes, "net") if any(isinstance(c, list) and c[0] in ("wire", "via") for c in n)}
res = next(find(routes, "resolution"))
scale = {"um": 1000, "mm": 1000000, "mil": 25400}[res[1]] / float(res[2])  # session units -> nm
def pt(x, y): return pcbnew.VECTOR2I(int(round(float(x) * scale)), int(round(-float(y) * scale)))
layers = {b.GetLayerName(l): l for l in (pcbnew.F_Cu, pcbnew.B_Cu)}

removed = 0
for t in list(b.GetTracks()):
    if t.GetNetname() in nets:
        b.Remove(t); G.append(t); removed += 1

added_t = added_v = 0
for net in find(routes, "net"):
    name = net[1]
    ni = b.FindNet(name)
    for w in (c for c in net if isinstance(c, list) and c[0] == "wire"):
        path = next(c for c in w if isinstance(c, list) and c[0] == "path")
        layer, width, coords = layers[path[1]], int(round(float(path[2]) * scale)), path[3:]
        for i in range(0, len(coords) - 2, 2):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pt(coords[i], coords[i + 1])); t.SetEnd(pt(coords[i + 2], coords[i + 3]))
            t.SetWidth(width); t.SetLayer(layer); t.SetNet(ni)
            b.Add(t); added_t += 1
    for v in (c for c in net if isinstance(c, list) and c[0] == "via"):
        size, drill = map(int, re.search(r"_(\d+):(\d+)_um", v[1]).groups())
        via = pcbnew.PCB_VIA(b)
        via.SetPosition(pt(v[2], v[3])); via.SetWidth(size * 1000); via.SetDrill(drill * 1000)
        via.SetNet(ni)
        b.Add(via); added_v += 1

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(pcb)
print("removed %d tracks, added %d segments and %d vias on %d nets" % (removed, added_t, added_v, len(nets)))
