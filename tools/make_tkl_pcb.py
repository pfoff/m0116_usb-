#!/usr/bin/python3
"""Turn m0116_tkl.kicad_pcb (after "make pcb-update PROJECT=m0116_tkl") into the TKL board.

- right board edge: the original right-hand contour (main body corner radii,
  step of the rear strip) is copied and moved left by SHIFT so the board ends
  with the same margin next to Backspace/Return/arrows as the original has
  next to the keypad
- holes: everything left of the cut stays at its original position (the
  original plate is cut down, so its features stay where they were); the
  right-hand plate screw moves with the contour (drill it into the plate),
  the right big clearance hole and the right Ø3.8 hole are dropped
- the controller parts that sat in the cut-off part of the rear strip are
  placed again (positions below, centre of the pads in board mm)
- all matrix tracks are removed (they cross the MX centre holes of the
  hybrid footprints and are rerouted), so are tracks outside the new outline
- silkscreen items outside the new outline are removed, copper pour outlines
  are cut back to the new edge

Run once on a freshly updated board; running it twice shifts nothing twice
because the contour is rebuilt from the original right-hand side only when it
is still present.

Usage: /usr/bin/python3 tools/make_tkl_pcb.py m0116_tkl.kicad_pcb
"""
import sys

import pcbnew

SHIFT = 94.43          # mm: 396.748 (old edge) - 302.318 (Backspace edge + original 0.633 margin)
OLD_RIGHT_MIN_X = 331.9  # original right-hand contour starts here (top edge ends at 331.978)
NEW_EDGE_X = 396.748 - SHIFT

# pad-centre positions (x, y, rotation) for parts in the shortened rear strip
PLACE = {
    "U3":  (248.7, 83.1, 90),   # low strip right of the step, socket 238.2-259.2
    "J2":  (246.45, 90.9, 90),  # TrackPoint header below U3
    "U2":  (224.9, 83.4, 0),    # upright between the middle clearance hole and the new screw
    "C3":  (232.5, 84.5, 90),
    "C4":  (235.8, 84.5, 90),
    "R1":  (150.5, 82.6, 90),   # between the power key and the nice!nano
    "R2":  (154.0, 82.6, 90),
    "R3":  (157.5, 82.6, 90),
    "C6":  (160.8, 81.5, 90),
    "C7":  (163.9, 81.5, 90),
    "TP4": (204.5, 75.3, 0),    # row above the middle clearance hole
    "TP5": (208.5, 75.3, 0),
    "TP6": (212.5, 75.3, 0),
    "TP7": (216.5, 75.3, 0),
    # matrix diodes that sat in the gap to the keypad, now at the board edge
    "D34": (300.0, 124.71, -90),  # Return: between switch body and edge
    "D80": (299.0, 163.31, -90),  # arrow up: moved up next to right Shift
}
REMOVE_FOOTPRINTS = ("custom_parts:m0116_qr",)   # sat in the keypad gap, no room left

_GRAVEYARD = []   # KiCad 7 SWIG: keep removed items alive (see update_pcb.py)


def mm(v):
    return pcbnew.FromMM(v)


def tomm(v):
    return pcbnew.ToMM(v)


def discard(board, item):
    board.Remove(item)
    _GRAVEYARD.append(item)


def pt(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def edge(board, shape, *pts):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(shape)
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(mm(0.15))
    if shape == pcbnew.SHAPE_T_ARC:
        s.SetArcGeometry(pt(*pts[0]), pt(*pts[1]), pt(*pts[2]))
    elif shape == pcbnew.SHAPE_T_CIRCLE:
        s.SetCenter(pt(*pts[0]))
        s.SetEnd(pt(pts[0][0] + pts[1], pts[0][1]))
    else:
        s.SetStart(pt(*pts[0]))
        s.SetEnd(pt(*pts[1]))
    board.Add(s)


def xs(d):
    if d.GetShape() == pcbnew.SHAPE_T_CIRCLE:
        return [tomm(d.GetCenter().x)]
    return [tomm(d.GetStart().x), tomm(d.GetEnd().x)]


def rebuild_outline(board):
    edges = [d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
    right = [d for d in edges if d.GetShape() != pcbnew.SHAPE_T_CIRCLE and min(xs(d)) >= OLD_RIGHT_MIN_X - 0.01]
    if not right:
        print("outline already rebuilt, skipping")
        return
    # bottom edge is slightly slanted in the original: keep its line, shorten it
    bottom = next(d for d in edges if d.GetShape() == pcbnew.SHAPE_T_SEGMENT
                  and abs(tomm(d.GetStart().y) - tomm(d.GetEnd().y)) < 1 and tomm(d.GetStart().y) > 180)
    (bx1, by1), (bx2, by2) = [(tomm(p.x), tomm(p.y)) for p in (bottom.GetStart(), bottom.GetEnd())]
    if bx1 < bx2:
        bx1, by1, bx2, by2 = bx2, by2, bx1, by1
    new_bx = bx1 - SHIFT
    dy = (by2 - by1) * (bx1 - new_bx) / (bx1 - bx2)          # y drift along the slanted line
    top = next(d for d in edges if d.GetShape() == pcbnew.SHAPE_T_SEGMENT
               and tomm(d.GetStart().y) < 72.5 and tomm(d.GetEnd().y) < 72.5 and max(xs(d)) > OLD_RIGHT_MIN_X - 0.01)

    def moved(p, extra_dy=0.0):
        return (tomm(p.x) - SHIFT, tomm(p.y) + extra_dy)

    for d in right:
        s, e = d.GetStart(), d.GetEnd()
        bottom_corner = max(tomm(s.y), tomm(e.y)) > 180
        if d.GetShape() == pcbnew.SHAPE_T_ARC:
            ddy = dy if bottom_corner else 0.0
            edge(board, pcbnew.SHAPE_T_ARC, moved(s, ddy), moved(d.GetArcMid(), ddy), moved(e, ddy))
        else:
            a, b = moved(s), moved(e)
            if abs(a[0] - b[0]) < 1e-6 and max(a[1], b[1]) > 180:    # right-hand vertical edge
                if a[1] > b[1]:
                    a = (a[0], a[1] + dy)
                else:
                    b = (b[0], b[1] + dy)
            edge(board, pcbnew.SHAPE_T_SEGMENT, a, b)
        discard(board, d)
    # shorten top and bottom edges to the moved contour
    t1, t2 = sorted([(tomm(p.x), tomm(p.y)) for p in (top.GetStart(), top.GetEnd())])
    edge(board, pcbnew.SHAPE_T_SEGMENT, t1, (t2[0] - SHIFT, t2[1]))
    discard(board, top)
    edge(board, pcbnew.SHAPE_T_SEGMENT, (new_bx, by1 + dy), (bx2, by2))
    discard(board, bottom)

    # holes
    for d in [d for d in edges if d.GetShape() == pcbnew.SHAPE_T_CIRCLE]:
        x, y, r = tomm(d.GetCenter().x), tomm(d.GetCenter().y), tomm(d.GetRadius())
        if x > NEW_EDGE_X - 1 or (x > 300 and r > 5):
            if abs(r - 1.524) < 0.01:     # plate screw: moves with the contour
                edge(board, pcbnew.SHAPE_T_CIRCLE, (x - SHIFT, y), r)
            discard(board, d)


def place_parts(board):
    for ref, (x, y, rot) in PLACE.items():
        fp = board.FindFootprintByReference(ref)
        if fp is None:
            raise SystemExit("footprint %s not on the board" % ref)
        fp.SetOrientationDegrees(rot)
        box = pcbnew.BOX2I()
        for pad in fp.Pads():
            box.Merge(pad.GetBoundingBox())
        c = box.GetCenter()
        fp.Move(pcbnew.VECTOR2I(mm(x) - c.x, mm(y) - c.y))


def cleanup(board):
    matrix = {p.GetNetname() for fp in board.GetFootprints()
              if fp.GetReference().startswith("MX") or (fp.GetReference().startswith("D") and fp.GetValue() == "D_Small")
              for p in fp.Pads() if p.GetNetname()}
    outline = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(outline)
    removed = 0
    for t in list(board.GetTracks()):
        ends = [t.GetPosition()] if t.GetClass() == "PCB_VIA" else [t.GetStart(), t.GetEnd()]
        if (t.GetNetname() in matrix or t.GetNetname().startswith("unconnected-")
                or not all(outline.Contains(e) for e in ends)):
            discard(board, t)
            removed += 1
    # copper pours: KiCad clips the fill at the edge, but Freerouting shows the raw outline
    for z in board.Zones():
        if z.GetIsRuleArea():
            continue
        outline = z.Outline()
        for i in range(outline.TotalVertices()):
            v = outline.CVertex(i)
            if tomm(v.x) > NEW_EDGE_X:
                outline.SetVertex(i, pcbnew.VECTOR2I(mm(NEW_EDGE_X), v.y))
    for fp in list(board.GetFootprints()):
        if fp.GetFPIDAsString() in REMOVE_FOOTPRINTS:
            discard(board, fp)
    for d in list(board.GetDrawings()):
        if d.GetLayer() != pcbnew.Edge_Cuts and tomm(d.GetBoundingBox().GetLeft()) > NEW_EDGE_X:
            discard(board, d)
    return removed


def main():
    board = pcbnew.LoadBoard(sys.argv[1])
    rebuild_outline(board)
    place_parts(board)
    removed = cleanup(board)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(sys.argv[1])
    print("new right edge x=%.3f, %d tracks removed, saved %s" % (NEW_EDGE_X, removed, sys.argv[1]))


if __name__ == "__main__":
    main()
