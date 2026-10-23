#!/usr/bin/python3
"""Report routing completeness of a board, net by net.

Pads are grouped into islands that are connected through tracks, vias and
filled zones (same net, touching geometry). A net with more than one island
still has unrouted connections. Useful after update_pcb.py to confirm that
the existing matrix routing is intact and only new connections are open.

Usage: /usr/bin/python3 tools/check_pcb.py m0116_usb.kicad_pcb [--all]
"""
import collections
import sys

import pcbnew


class DSU:
    def __init__(self):
        self.parent = {}

    def find(self, a):
        self.parent.setdefault(a, a)
        while self.parent[a] != a:
            self.parent[a] = self.parent[self.parent[a]]
            a = self.parent[a]
        return a

    def union(self, a, b):
        self.parent[self.find(a)] = self.find(b)


def islands(board):
    """Return {net name: [sorted pad labels per island]}."""
    items = collections.defaultdict(list)  # net -> [(key, item, label)]
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() > 0:
                label = "%s.%s" % (fp.GetReference(), pad.GetNumber())
                items[pad.GetNetname()].append((pad.m_Uuid.AsString(), pad, label))
    for t in board.GetTracks():
        if t.GetNetCode() > 0:
            items[t.GetNetname()].append((t.m_Uuid.AsString(), t, None))

    zones = collections.defaultdict(list)
    for z in board.Zones():
        if not z.GetIsRuleArea() and z.GetNetCode() > 0:
            zones[z.GetNetname()].append(z)

    result = {}
    for net, members in items.items():
        dsu = DSU()
        for key, _, _ in members:
            dsu.find(key)
        tracks = [(k, it) for k, it, lbl in members if lbl is None]
        pads = [(k, it) for k, it, lbl in members if lbl is not None]
        for key, t in tracks:
            for p in (t.GetStart(), t.GetEnd()):
                for k2, other in tracks + pads:
                    if k2 != key and _shares_layer(t, other) and other.HitTest(p):
                        dsu.union(key, k2)
        for key, pad in pads:  # track passing through a pad centre
            for k2, t in tracks:
                if _shares_layer(pad, t) and t.HitTest(pad.GetPosition()):
                    dsu.union(key, k2)
        for z in zones.get(net, []):
            zkey = "zone:" + z.m_Uuid.AsString()
            for key, it, label in members:
                # pads join through thermal spokes, so test against the pad outline
                bb = it.GetBoundingBox()
                reach = max(bb.GetWidth(), bb.GetHeight()) // 2 if label else 0
                for layer in z.GetLayerSet().Seq():
                    if it.IsOnLayer(layer) and z.GetFilledPolysList(layer).Collide(it.GetPosition(), reach):
                        dsu.union(key, zkey)
                        break
        groups = collections.defaultdict(list)
        for key, it, label in members:
            if label:
                groups[dsu.find(key)].append(label)
        result[net] = sorted(sorted(g) for g in groups.values())
    return result


def _shares_layer(a, b):
    return any(b.IsOnLayer(layer) for layer in a.GetLayerSet().Seq())


def main():
    board = pcbnew.LoadBoard(sys.argv[1])
    show_all = "--all" in sys.argv
    res = islands(board)
    open_nets = {n: g for n, g in res.items() if len(g) > 1}
    print("nets with pads: %d, fully routed: %d, with unrouted connections: %d"
          % (len(res), len(res) - len(open_nets), len(open_nets)))
    for net in sorted(open_nets if not show_all else res):
        groups = res[net]
        print("  %-28s %s" % (net, " | ".join(", ".join(g) for g in groups)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
