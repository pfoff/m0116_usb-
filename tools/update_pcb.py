#!/usr/bin/python3
"""Headless "Update PCB from Schematic" for KiCad 7.

Reads a KiCad s-expression netlist (kicad-cli sch export netlist) and brings
the board in line with it, the way Pcbnew's F8 dialog does with
"Delete footprints with no symbols" and "Replace footprints" enabled:

- footprints are matched to symbols by sheet path + symbol UUID
- footprints whose symbol no longer exists are removed (unlinked footprints
  such as logos are kept)
- new footprints are loaded from the libraries, linked to their symbol and
  placed according to the placement file (only when first created, so manual
  placement is never overwritten)
- pad nets are reassigned; tracks, vias and zones follow their pads to the
  new net names, tracks of vanished nets and dangling track stubs are removed
- optional copper keepouts are created relative to a footprint
- zones are refilled

Usage:
    /usr/bin/python3 tools/update_pcb.py --netlist build/m0116_usb.net \
        --pcb m0116_usb.kicad_pcb [--placement tools/placement.json] [--dry-run]

Close the board in Pcbnew before running this, otherwise saving there will
overwrite the result. The script refuses to run while Pcbnew's lock file exists.
"""
import argparse
import json
import math
import os
import re
import sys
import time

import pcbnew

_T0 = time.time()


# KiCad 7's SWIG bindings lose the FOOTPRINT type (later loads return a bare
# SwigPyObject) once the Python wrapper of a removed item is garbage
# collected. Keep every removed item referenced until the script exits.
_GRAVEYARD = []


def discard(board, item):
    board.Remove(item)
    _GRAVEYARD.append(item)


def log(msg):
    print("[%5.1fs] %s" % (time.time() - _T0, msg), file=sys.stderr, flush=True)

SYSTEM_FP_DIR = os.environ.get("KICAD7_FOOTPRINT_DIR", "/usr/share/kicad/footprints")
KEEPOUT_NAME_PREFIX = "update_pcb:"


# ---------------------------------------------------------------- netlist

def parse_sexpr(text):
    stack = [[]]
    pos, n = 0, len(text)
    while pos < n:
        c = text[pos]
        if c in " \t\r\n":
            pos += 1
        elif c == "(":
            stack.append([])
            pos += 1
        elif c == ")":
            done = stack.pop()
            stack[-1].append(done)
            pos += 1
        elif c == '"':
            end = pos + 1
            buf = []
            while text[end] != '"':
                if text[end] == "\\":
                    buf.append(text[end + 1])
                    end += 2
                else:
                    buf.append(text[end])
                    end += 1
            stack[-1].append("".join(buf))
            pos = end + 1
        else:
            end = pos
            while end < n and text[end] not in ' \t\r\n()"':
                end += 1
            stack[-1].append(text[pos:end])
            pos = end
    return stack[0][0]


def child(node, key):
    for c in node:
        if isinstance(c, list) and c and c[0] == key:
            return c
    return None


def children(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def load_netlist(path):
    tree = parse_sexpr(open(path, encoding="utf-8").read())
    comps = {}
    for comp in children(child(tree, "components"), "comp"):
        ref = child(comp, "ref")[1]
        fp = child(comp, "footprint")
        sheet = child(child(comp, "sheetpath"), "tstamps")[1]
        props = {child(p, "name")[1]: child(p, "value")[1] for p in children(comp, "property")}
        comps[ref] = {
            "ref": ref,
            "value": child(comp, "value")[1],
            "footprint": fp[1] if fp else "",
            "path": sheet + child(comp, "tstamps")[1],
            "sheetname": props.get("Sheetname", ""),
            "sheetfile": props.get("Sheetfile", ""),
        }
    nets = {}
    for net in children(child(tree, "nets"), "net"):
        name = child(net, "name")[1]
        nets[name] = [(child(nd, "ref")[1], child(nd, "pin")[1]) for nd in children(net, "node")]
    return comps, nets


# ---------------------------------------------------------------- libraries

def footprint_libs(project_dir):
    libs = {}
    table = os.path.join(project_dir, "fp-lib-table")
    if os.path.exists(table):
        for nick, uri in re.findall(r'\(lib \(name "?([^")]+)"?\)\(type "?[^")]+"?\)\(uri "?([^")]+)"?\)',
                                    open(table).read()):
            libs[nick] = uri.replace("${KIPRJMOD}", project_dir)
    return libs


_PLUGIN = pcbnew.PCB_PLUGIN()  # .pretty loader; pcbnew.FootprintLoad() is unreliable in KiCad 7 Python


def load_footprint(fpid, project_libs):
    nick, name = fpid.split(":", 1)
    path = project_libs.get(nick, os.path.join(SYSTEM_FP_DIR, nick + ".pretty"))
    fp = _PLUGIN.FootprintLoad(path, name) if os.path.isdir(path) else None
    if not isinstance(fp, pcbnew.FOOTPRINT):
        raise SystemExit("footprint %s not found in %s" % (fpid, path))
    fp.SetFPID(pcbnew.LIB_ID(nick, name))
    return fp


# ---------------------------------------------------------------- geometry helpers

def mm(v):
    return pcbnew.FromMM(v)


def place(fp, spec):
    """Place a new footprint; with "center", (x, y) is the centre of its pads."""
    if spec.get("side", "F") == "B":
        fp.Flip(fp.GetPosition(), False)
    fp.SetOrientationDegrees(spec.get("rot", 0))
    fp.SetPosition(pcbnew.VECTOR2I(mm(spec["x"]), mm(spec["y"])))
    if spec.get("center", True):
        box = pcbnew.BOX2I()
        for pad in fp.Pads():
            box.Merge(pad.GetBoundingBox())
        c = box.GetCenter()
        fp.Move(pcbnew.VECTOR2I(mm(spec["x"]) - c.x, mm(spec["y"]) - c.y))


def add_keepout(board, fp, spec):
    """Rule area (no tracks, vias or pour) given in footprint-local mm coordinates."""
    name = KEEPOUT_NAME_PREFIX + spec["name"]
    for z in list(board.Zones()):
        if z.GetIsRuleArea() and z.GetZoneName() == name:
            discard(board, z)
    x1, y1, x2, y2 = spec["rect"]
    zone = pcbnew.ZONE(board)
    zone.SetIsRuleArea(True)
    zone.SetDoNotAllowTracks(True)
    zone.SetDoNotAllowVias(True)
    zone.SetDoNotAllowCopperPour(True)
    zone.SetDoNotAllowPads(False)
    zone.SetDoNotAllowFootprints(False)
    zone.SetZoneName(name)
    layers = pcbnew.LSET()
    layers.AddLayer(pcbnew.F_Cu)
    layers.AddLayer(pcbnew.B_Cu)
    zone.SetLayerSet(layers)
    outline = zone.Outline()
    outline.NewOutline()
    # positive orientation is counter-clockwise on screen (y axis points down)
    a = math.radians(fp.GetOrientationDegrees())
    ca, sa = math.cos(a), math.sin(a)
    for lx, ly in ((x1, y1), (x2, y1), (x2, y2), (x1, y2)):
        dx, dy = lx * ca + ly * sa, -lx * sa + ly * ca
        outline.Append(fp.GetPosition().x + mm(dx), fp.GetPosition().y + mm(dy))
    board.Add(zone)


def remove_dangling_tracks(board):
    """Iteratively delete track segments with an end that touches nothing."""
    # SWIG hands out a new wrapper per call, so identity is compared by UUID
    def boxed(items):
        out = {}
        for it in items:
            bb = it.GetBoundingBox()
            out.setdefault(it.GetNetCode(), []).append(
                (it, it.m_Uuid.AsString(), bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()))
        return out

    def touches(candidates, end, layer, skip=None):
        for it, uid, x1, y1, x2, y2 in candidates:
            if uid == skip or not (x1 <= end.x <= x2 and y1 <= end.y <= y2):
                continue
            if it.IsOnLayer(layer) and it.HitTest(end):
                return True
        return False

    removed = 0
    while True:
        tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
        others = boxed([t for t in board.GetTracks()] + [p for fp in board.GetFootprints() for p in fp.Pads()])
        dead = []
        for t in tracks:
            cands = others.get(t.GetNetCode(), [])
            for end in (t.GetStart(), t.GetEnd()):
                if not touches(cands, end, t.GetLayer(), skip=t.m_Uuid.AsString()):
                    dead.append(t)
                    break
        if not dead:
            return removed
        for t in dead:
            discard(board, t)
        removed += len(dead)
        log("  removed %d dangling segments" % len(dead))


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--netlist", required=True)
    ap.add_argument("--pcb", required=True)
    ap.add_argument("--placement")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="run even if Pcbnew has the board open")
    args = ap.parse_args()

    lock = os.path.join(os.path.dirname(os.path.abspath(args.pcb)), "~%s.lck" % os.path.basename(args.pcb))
    if os.path.exists(lock) and not args.force and not args.dry_run:
        raise SystemExit("%s is open in Pcbnew (%s exists). Close it first, or pass --force." % (args.pcb, lock))

    project_dir = os.path.dirname(os.path.abspath(args.pcb))
    comps, nets = load_netlist(args.netlist)
    placement = json.load(open(args.placement)) if args.placement else {}
    parts = placement.get("parts", {})
    park = placement.get("park", {"x": 30, "y": 50, "step": 15})
    project_libs = footprint_libs(project_dir)

    log("loading board")
    board = pcbnew.LoadBoard(args.pcb)
    by_path = {fp.GetPath().AsString(): fp for fp in board.GetFootprints() if fp.GetPath().AsString()}
    wanted = {c["path"]: c for c in comps.values() if c["footprint"]}

    # old net of every pad of footprints that survive, for moving tracks along
    old_pad_net = {}
    for path, fp in by_path.items():
        if path in wanted:
            for pad in fp.Pads():
                old_pad_net[(path, pad.GetNumber(), pad.GetPosition().x, pad.GetPosition().y)] = pad.GetNetname()

    log("syncing footprints")
    # 1. remove footprints whose symbol is gone
    removed = sorted(fp.GetReference() for path, fp in by_path.items() if path not in wanted)
    for path, fp in list(by_path.items()):
        if path not in wanted:
            discard(board, fp)
            del by_path[path]

    # 2. update / replace / add footprints
    added, replaced, renamed = [], [], []
    parked = 0
    for path, comp in sorted(wanted.items(), key=lambda kv: kv[1]["ref"]):
        fp = by_path.get(path)
        if fp is not None and str(fp.GetFPID().GetUniStringLibId()) != comp["footprint"]:
            new = load_footprint(comp["footprint"], project_libs)
            new.SetPosition(fp.GetPosition())
            if fp.IsFlipped():
                new.Flip(new.GetPosition(), False)
            new.SetOrientation(fp.GetOrientation())
            discard(board, fp)
            fp = new
            board.Add(fp)
            replaced.append(comp["ref"])
        elif fp is None:
            fp = load_footprint(comp["footprint"], project_libs)
            spec = parts.get(comp["ref"])
            if spec is None:
                spec = {"x": park["x"] + parked * park["step"], "y": park["y"], "rot": 0}
                parked += 1
            board.Add(fp)
            place(fp, spec)
            added.append(comp["ref"] + ("" if comp["ref"] in parts else " (parked)"))
        if fp.GetReference() != comp["ref"] and comp["ref"] not in {a.split()[0] for a in added}:
            renamed.append("%s -> %s" % (fp.GetReference(), comp["ref"]))
        fp.SetReference(comp["ref"])
        fp.SetValue(comp["value"])
        fp.SetPath(pcbnew.KIID_PATH(path))
        fp.SetProperty("Sheetname", comp["sheetname"])
        fp.SetProperty("Sheetfile", comp["sheetfile"])
        by_path[path] = fp

    log("assigning nets")
    # 3. nets
    netinfo = {}
    for name in nets:
        ni = board.FindNet(name)
        if ni is None:
            ni = pcbnew.NETINFO_ITEM(board, name)
            board.Add(ni)
        netinfo[name] = ni
    pad_net = {(ref, pin): name for name, nodes in nets.items() for ref, pin in nodes}
    ref_to_path = {c["ref"]: c["path"] for c in comps.values()}
    remap = {}
    for ref, comp in comps.items():
        fp = by_path.get(comp["path"])
        if fp is None:
            continue
        for pad in fp.Pads():
            name = pad_net.get((ref, pad.GetNumber()))
            old = old_pad_net.get((comp["path"], pad.GetNumber(), pad.GetPosition().x, pad.GetPosition().y))
            if old and name:
                remap.setdefault(old, set()).add(name)
            pad.SetNet(netinfo[name] if name else board.FindNet(""))
    del ref_to_path

    log("remapping tracks")
    # 4. tracks, vias and zones follow their pads
    moved, dropped, ambiguous = 0, 0, []
    for item in list(board.GetTracks()) + list(board.Zones()):
        if isinstance(item, pcbnew.ZONE) and item.GetIsRuleArea():
            continue
        old = item.GetNetname()
        if not old or old in netinfo and old in remap.get(old, {old}):
            continue
        targets = remap.get(old, set())
        if len(targets) == 1:
            item.SetNet(netinfo[next(iter(targets))])
            moved += 1
        elif not targets and old not in netinfo:
            if isinstance(item, pcbnew.ZONE):
                ambiguous.append("zone on vanished net %s" % old)
            else:
                discard(board, item)
                dropped += 1
        elif len(targets) > 1:
            ambiguous.append("%s -> %s" % (old, sorted(targets)))
    log("removing dangling tracks")
    dangling = remove_dangling_tracks(board)

    # drop nets nothing uses any more
    used = {p.GetNetname() for fp in board.GetFootprints() for p in fp.Pads()}
    used |= {t.GetNetname() for t in board.GetTracks()} | {z.GetNetname() for z in board.Zones()}
    stale = [n for n in list(board.GetNetsByName().keys()) if str(n) and str(n) not in used]
    for name in stale:
        discard(board, board.FindNet(str(name)))

    # 5. keepouts relative to footprints
    keepouts = []
    for spec in placement.get("keepouts", []):
        fp = next((f for f in board.GetFootprints() if f.GetReference() == spec["ref"]), None)
        if fp is not None:
            add_keepout(board, fp, spec)
            keepouts.append(spec["name"])

    log("refilling zones")
    # 6. refill zones
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    log("done")

    print("removed footprints (%d): %s" % (len(removed), ", ".join(removed) or "-"))
    print("added footprints   (%d): %s" % (len(added), ", ".join(added) or "-"))
    print("replaced footprints: %s" % (", ".join(replaced) or "-"))
    print("renamed references : %s" % (", ".join(renamed) or "-"))
    print("tracks/zones moved to renamed nets: %d" % moved)
    print("tracks/vias of vanished nets removed: %d" % dropped)
    print("dangling track segments removed: %d" % dangling)
    print("stale nets removed: %d" % len(stale))
    print("keepouts: %s" % (", ".join(keepouts) or "-"))
    for a in ambiguous:
        print("WARNING: not remapped:", a)

    if args.dry_run:
        print("dry run: board not saved")
    else:
        board.Save(args.pcb)
        print("saved", args.pcb)
    return 1 if ambiguous else 0


if __name__ == "__main__":
    sys.exit(main())
