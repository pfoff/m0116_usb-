#!/usr/bin/python3
"""Export a Specctra DSN for autorouting the key matrix.

On an in-memory copy of the board: all tracks on matrix nets (switch and
diode pads, including their run to the controller) are removed, all other
tracks are locked (exported as protected wires), and the silkscreen-only
logo footprints (G***) are dropped because they make KiCad 7's exporter fail.
Freerouting keeps only its normal clearance (0.2 mm) to the board edge and
to holes, KiCad wants min_copper_edge_clearance (0.5 mm), so the exported
outline is shrunk and the holes are enlarged by EDGE_MARGIN.

Nets of the USB daughterboard (SKIP_NET_PREFIX) are left out: its pads stay
as obstacles without a net and its tracks are dropped from the copy, so
Freerouting does not spend its time on the tight USB-C pads (route those by
hand; import_ses.py leaves nets that are not in the session alone).

With --continue nothing is removed or locked, so Freerouting only completes
the connections that are still open (after importing a partial result).
The GND pours are also dropped from that copy, so GND is routed as tracks:
Freerouting sees a plane as one conductor and does not notice when tracks
cut it into islands, KiCad does.

Route the DSN in Freerouting, export the .ses and bring it back with
tools/import_ses.py.

Usage: /usr/bin/python3 tools/export_matrix_dsn.py [--continue] board.kicad_pcb out.dsn
"""
import sys

import pcbnew

_GRAVEYARD = []
SKIP_NET_PREFIX = "/USB daughterboard/"
EDGE_MARGIN = 0.35   # mm, + Freerouting's 0.2 mm clearance > 0.5 mm edge clearance


def matrix_fp(fp):
    r = fp.GetReference()
    return r.startswith("MX") or (r.startswith("D") and fp.GetValue() == "D_Small")


def shrink_outline(b):
    outline = pcbnew.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(outline)
    outer = pcbnew.SHAPE_POLY_SET(outline.Outline(0))
    outer.Deflate(pcbnew.FromMM(EDGE_MARGIN), 32)
    for d in list(b.GetDrawings()):
        if d.GetLayer() != pcbnew.Edge_Cuts:
            continue
        if d.GetShape() == pcbnew.SHAPE_T_CIRCLE:
            if d.GetRadius() < pcbnew.FromMM(1):   # mouse bites: would merge, no copper there anyway
                continue
            c = d.GetCenter()
            d.SetEnd(pcbnew.VECTOR2I(c.x + d.GetRadius() + pcbnew.FromMM(EDGE_MARGIN), c.y))
        else:
            b.Remove(d)
            _GRAVEYARD.append(d)
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_POLY)
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetPolyShape(outer)
    b.Add(s)


def main():
    args = sys.argv[1:]
    cont = "--continue" in args
    src, dsn = [a for a in args if a != "--continue"]
    b = pcbnew.LoadBoard(src)
    nets = {p.GetNetname() for f in b.GetFootprints() if matrix_fp(f) for p in f.Pads() if p.GetNetname()}
    for t in list(b.GetTracks()):
        if t.GetNetname().startswith(SKIP_NET_PREFIX):
            b.Remove(t)
            _GRAVEYARD.append(t)
        elif cont:
            continue
        elif t.GetNetname() in nets:
            b.Remove(t)
            _GRAVEYARD.append(t)
        else:
            t.SetLocked(True)
    for f in list(b.GetFootprints()):
        if f.GetReference().startswith("G"):
            b.Remove(f)
            _GRAVEYARD.append(f)
    if cont:
        for z in list(b.Zones()):
            if z.GetNetname() == "GND":
                b.Remove(z)
                _GRAVEYARD.append(z)
    none = b.FindNet("")
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetname().startswith(SKIP_NET_PREFIX):
                p.SetNet(none)
    shrink_outline(b)
    if not pcbnew.ExportSpecctraDSN(b, dsn):
        raise SystemExit("DSN export failed")
    print("wrote", dsn)


if __name__ == "__main__":
    main()
