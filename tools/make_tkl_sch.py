#!/usr/bin/python3
"""Derive the schematic of the TKL variant (no numeric keypad) from the full board.

Writes m0116_tkl.kicad_sch, controller_tkl.kicad_sch and
usb_daughterboard_tkl.kicad_sch next to the originals:

- root sheet: matrix columns col15-col18 (the keypad) are dropped, row wires
  are trimmed back to the last remaining diode, sub-sheets point to the
  *_tkl files
- controller: the third 74HC595 (U4) and its bypass capacitor C5 are removed,
  U3 outputs QG/QH (col15/col16) and QH' become no-connects
- symbol UUIDs are kept, so footprints on the PCB stay linked

Usage: python3 tools/make_tkl_sch.py   (run from the project directory)
"""
import re
import uuid

SRC, DST = "m0116_usb", "m0116_tkl"
CUT_X = 220.0          # root sheet: everything right of this belongs to col15-col18


def blocks(text):
    """(start, end) offsets of every depth-1 child of the top-level expression."""
    depth, out, start, instr, i = 0, [], None, False, 0
    while i < len(text):
        c = text[i]
        if instr:
            if c == "\\":
                i += 1
            elif c == '"':
                instr = False
        elif c == '"':
            instr = True
        elif c == "(":
            depth += 1
            if depth == 2:
                start = i
        elif c == ")":
            if depth == 2:
                out.append((start, i + 1))
            depth -= 1
        i += 1
    return out


def coords(block):
    return [(float(a), float(b)) for a, b in re.findall(r"\((?:at|xy) (-?[\d.]+) (-?[\d.]+)", block)]


def kind(block):
    return re.match(r"\((\w+)", block).group(1)


def rebuild(text, keep):
    """keep(block) -> None to drop, or the (possibly edited) block text."""
    parts, last = [], 0
    for s, e in blocks(text):
        new = keep(text[s:e])
        if new is None:
            # also swallow the indentation and newline in front of the block
            pre = text[last:s]
            parts.append(pre[: len(pre.rstrip(" ")) - (1 if pre.rstrip(" ").endswith("\n") else 0)])
        else:
            parts.append(text[last:s] + new)
        last = e
    parts.append(text[last:])
    return "".join(parts)


def rename_project(text):
    return text.replace('(project "%s"' % SRC, '(project "%s"' % DST)


def no_connect(x, y):
    return '(no_connect (at %s %s) (uuid %s))' % (x, y, uuid.uuid4())


# ---------------------------------------------------------------- root sheet

def root():
    text = open(SRC + ".kicad_sch", encoding="utf-8").read()
    # row-line connection points (diode cathodes) that survive, per y
    keep_x = {}
    for s, e in blocks(text):
        b = text[s:e]
        if kind(b) == "symbol" and 'lib_id "Device:D_Small"' in b:
            x, y = coords(b)[0]
            if x < CUT_X:
                keep_x.setdefault(round(y + 2.54, 2), []).append(x)

    def keep(b):
        k, c = kind(b), coords(b)
        if k in ("symbol", "junction", "no_connect", "global_label", "label", "wire") and c:
            if k == "wire":
                (x1, y1), (x2, y2) = c[:2]
                if min(x1, x2) >= CUT_X:
                    return None
                if max(x1, x2) > CUT_X and y1 == y2:
                    end = max(x for x in keep_x.get(round(y1, 2), [min(x1, x2)]) if x < CUT_X)
                    if end <= min(x1, x2):
                        return None
                    old = "(xy %s %s)" % (fmt(max(x1, x2)), fmt(y1))
                    assert old in b, (old, b)
                    return b.replace(old, "(xy %s %s)" % (fmt(end), fmt(y1)))
                return b
            if c[0][0] >= CUT_X:
                return None
        if k == "sheet":
            b = b.replace('"controller.kicad_sch"', '"controller_tkl.kicad_sch"')
            b = b.replace('"usb_daughterboard.kicad_sch"', '"usb_daughterboard_tkl.kicad_sch"')
        return b

    text = rename_project(rebuild(text, keep))
    open(DST + ".kicad_sch", "w", encoding="utf-8").write(text)


def fmt(v):
    return ("%.4f" % v).rstrip("0").rstrip(".")


# ---------------------------------------------------------------- controller

def controller():
    text = open("controller.kicad_sch", encoding="utf-8").read()
    drop_refs = {"U4", "C5"}
    # U4/C5 area (labels, wires, power symbols and no-connects that only serve them)
    u4_area = (185.0, 250.0, 150.0, 200.0)
    # U3 outputs that lose their column, and its now unused cascade output
    to_nc = {(213.36, 124.46), (213.36, 127.0), (213.36, 132.08)}
    nc_added = []

    def inside(x, y, box):
        return box[0] <= x <= box[1] and box[2] <= y <= box[3]

    def keep(b):
        k, c = kind(b), coords(b)
        ref = re.search(r'"Reference" "([^"]+)"', b)
        if k == "symbol" and ref and ref.group(1) in drop_refs:
            return None
        if c and k in ("wire", "label", "global_label", "no_connect", "junction") and all(inside(x, y, u4_area) for x, y in c):
            return None
        if k == "symbol" and ref and ref.group(1).startswith("#PWR") and inside(*c[0], u4_area):
            return None
        if k == "wire" and any(p in to_nc for p in c[:2]):
            for p in c[:2]:
                if p in to_nc:
                    nc_added.append(p)
            return None
        if k in ("label", "global_label") and c and (round(c[0][0] - 2.54, 2), c[0][1]) in to_nc:
            return None
        return b

    text = rebuild(text, keep)
    assert sorted(nc_added) == sorted(to_nc), nc_added
    ncs = "".join("  %s\n\n" % no_connect(fmt(x), fmt(y)) for x, y in sorted(to_nc))
    marker = "  (sheet_instances" if "  (sheet_instances" in text else None
    idx = text.rfind("\n)")
    text = text[:idx + 1] + ncs + text[idx + 1:] if marker is None else text.replace(marker, ncs + marker)
    open("controller_tkl.kicad_sch", "w", encoding="utf-8").write(rename_project(text))


def daughterboard():
    text = open("usb_daughterboard.kicad_sch", encoding="utf-8").read()
    open("usb_daughterboard_tkl.kicad_sch", "w", encoding="utf-8").write(rename_project(text))


if __name__ == "__main__":
    root()
    controller()
    daughterboard()
    print("wrote %s.kicad_sch, controller_tkl.kicad_sch, usb_daughterboard_tkl.kicad_sch" % DST)
