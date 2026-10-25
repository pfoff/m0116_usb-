#!/usr/bin/python3
"""Connect GND pour islands to the main GND pour with vias.

Freerouting treats a plane as one conductor, so after autorouting the GND
pour can be cut into islands that only KiCad notices. For every island on
one layer this looks for a spot that lies inside the island and inside the
main pour of the other layer (both shrunk by the via radius, so the via only
touches GND copper) and puts a via there. Repeats until nothing changes.

Usage: /usr/bin/python3 tools/stitch_gnd.py board.kicad_pcb
"""
import sys

import pcbnew

VIA_SIZE, VIA_DRILL = 0.8, 0.4
GRID = 0.25     # mm, search raster
HOLE_GAP = 0.5  # mm, via drill to other drills


def mm(v):
    return pcbnew.FromMM(v)


def fill_pieces(board):
    """All filled GND pieces as (layer, SHAPE_POLY_SET with one outline)."""
    pieces = []
    for z in board.Zones():
        if z.GetNetname() != "GND":
            continue
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            if not z.IsOnLayer(layer):
                continue
            polys = z.GetFilledPolysList(layer)
            for i in range(polys.OutlineCount()):
                s = pcbnew.SHAPE_POLY_SET()
                s.AddOutline(polys.Outline(i))
                for h in range(polys.HoleCount(i)):
                    s.AddHole(polys.Hole(i, h))
                pieces.append((layer, s))
    return pieces


def touches(piece, pos, radius):
    """Piece reaches the ring around a pad/via (fill keeps a thermal gap)."""
    import math
    r = radius + mm(0.7)
    return any(piece.Contains(pcbnew.VECTOR2I(int(pos.x + r * math.cos(a * math.pi / 8)),
                                               int(pos.y + r * math.sin(a * math.pi / 8))))
               for a in range(16))


def components(board, pieces):
    """Group pieces connected by through-hole GND pads/vias (union-find)."""
    parent = list(range(len(pieces)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    links = [(p.GetPosition(), max(p.GetSize().x, p.GetSize().y) // 2) for f in board.GetFootprints()
             for p in f.Pads() if p.GetNetname() == "GND"]
    links += [(t.GetPosition(), t.GetWidth() // 2) for t in board.GetTracks()
              if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND"]
    has_pad = [False] * len(pieces)
    for pos, r in links:
        hit = [i for i, (_, s) in enumerate(pieces) if s.BBox(r + mm(1)).Contains(pos) and touches(s, pos, r)]
        for i in hit:
            has_pad[i] = True
        for i in hit[1:]:
            parent[root(i)] = root(hit[0])
    return [root(i) for i in range(len(pieces))], has_pad


def drills(board):
    pts = [(p.GetPosition(), max(p.GetDrillSize().x, p.GetDrillSize().y) / 2)
           for f in board.GetFootprints() for p in f.Pads() if p.GetDrillSize().x > 0]
    pts += [(t.GetPosition(), t.GetDrillValue() / 2) for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    return pts


def free_of_drills(pos, dr):
    for p, r in dr:
        if (p - pos).EuclideanNorm() < r + mm(VIA_DRILL / 2 + HOLE_GAP):
            return False
    return True


def find_spot(a, b, dr):
    """A point inside both shrunk pieces, away from other drills."""
    a = pcbnew.SHAPE_POLY_SET(a)
    b = pcbnew.SHAPE_POLY_SET(b)
    a.Deflate(mm(VIA_SIZE / 2), 16)
    b.Deflate(mm(VIA_SIZE / 2), 16)
    both = pcbnew.SHAPE_POLY_SET(a)
    both.BooleanIntersection(b, pcbnew.SHAPE_POLY_SET.PM_FAST)
    if not both.OutlineCount():
        return None
    box = both.BBox()
    y = box.GetTop()
    while y <= box.GetBottom():
        x = box.GetLeft()
        while x <= box.GetRight():
            p = pcbnew.VECTOR2I(int(x), int(y))
            if both.Contains(p) and free_of_drills(p, dr):
                return p
            x += mm(GRID)
        y += mm(GRID)
    return None


def stitch_once(board):
    pieces = fill_pieces(board)
    comp, has_pad = components(board, pieces)
    main = comp[max(range(len(pieces)), key=lambda i: pieces[i][1].Area())]
    # components that carry a pad but are not the main one
    lonely = sorted({comp[i] for i in range(len(pieces)) if has_pad[i] and comp[i] != main})
    dr = drills(board)
    gnd = board.FindNet("GND")
    added = 0
    for c in lonely:
        spot = None
        for i in (i for i in range(len(pieces)) if comp[i] == c):
            for j in (j for j in range(len(pieces)) if comp[j] == main and pieces[j][0] != pieces[i][0]):
                if pieces[i][1].BBox().Intersects(pieces[j][1].BBox()):
                    spot = find_spot(pieces[i][1], pieces[j][1], dr)
                    if spot:
                        break
            if spot:
                break
        if spot is None:
            print("no spot for an island near (%.1f, %.1f)" % tuple(pcbnew.ToMM(v) for v in
                  (pieces[comp.index(c)][1].BBox().Centre().x, pieces[comp.index(c)][1].BBox().Centre().y)))
            continue
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(spot)
        v.SetWidth(mm(VIA_SIZE))
        v.SetDrill(mm(VIA_DRILL))
        v.SetNet(gnd)
        board.Add(v)
        dr.append((spot, mm(VIA_DRILL / 2)))
        print("via at (%.2f, %.2f)" % (pcbnew.ToMM(spot.x), pcbnew.ToMM(spot.y)))
        added += 1
    return added


def main():
    board = pcbnew.LoadBoard(sys.argv[1])
    filler = pcbnew.ZONE_FILLER(board)
    total = 0
    for _ in range(5):
        filler.Fill(board.Zones())
        n = stitch_once(board)
        total += n
        if not n:
            break
    filler.Fill(board.Zones())
    board.Save(sys.argv[1])
    print("%d GND vias added, saved %s" % (total, sys.argv[1]))


if __name__ == "__main__":
    main()
