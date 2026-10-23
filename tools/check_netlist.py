#!/usr/bin/python3
"""Check the schematic netlist against the intended Revision A connections.

Verifies every controller-side pin assignment, that each row/column net
bridges the matrix and the controller, and that no net has a single pin
(except pins explicitly marked no-connect).

Usage: python3 tools/check_netlist.py build/m0116_usb.net
"""
import re
import sys

text = open(sys.argv[1]).read()
comps = dict(re.findall(r'\(comp \(ref "([^"]+)"\)\s*\(value "([^"]*)"\)', text))
nets = {}
for chunk in text.split('(net (code ')[1:]:
    name = re.match(r'"\d+"\) \(name "([^"]*)"\)', chunk).group(1)
    nets[name] = sorted(re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', chunk))


def net_of(ref, pin):
    for name, nodes in nets.items():
        if (ref, pin) in nodes:
            return name
    return None


def short(n):
    return n.rsplit("/", 1)[-1]


errors = []
print("components:", len(comps), " nets:", len(nets))
mx = [r for r in comps if r.startswith("MX")]
dio = [r for r in comps if re.fullmatch(r"D\d+", r)]
print("matrix switches:", len(mx), " diodes:", len(dio))

expect = {
    ("U1", "1"): "TP_CLK", ("U1", "2"): "TP_DATA", ("U1", "3"): "GND", ("U1", "4"): "GND",
    ("U1", "5"): "SR_DATA", ("U1", "6"): "SR_CLK", ("U1", "7"): "SR_LATCH", ("U1", "8"): "TP_RESET",
    ("U1", "9"): "TP_BTN_L", ("U1", "10"): "TP_BTN_M", ("U1", "11"): "TP_BTN_R", ("U1", "12"): "TP_AUX1",
    ("U1", "14"): "TP_AUX2", ("U1", "16"): "row4", ("U1", "17"): "row3", ("U1", "18"): "row2",
    ("U1", "19"): "row1", ("U1", "20"): "row0", ("U1", "21"): "TP_PWR", ("U1", "22"): "NRST",
    ("U1", "23"): "GND", ("U1", "24"): "VBAT",
    ("U2", "14"): "SR_DATA", ("U3", "14"): "SR_CHAIN1", ("U4", "14"): "SR_CHAIN2",
    ("U2", "9"): "SR_CHAIN1", ("U3", "9"): "SR_CHAIN2",
    ("U5", "2"): "VBAT", ("U5", "3"): "3V3_AON", ("U5", "1"): "GND",
    ("SW2", "2"): "BAT_IN", ("SW2", "1"): "VBAT", ("J1", "1"): "BAT_IN", ("J1", "2"): "GND",
    ("JP1", "1"): "3V3_AON", ("JP1", "2"): "3V3_SR", ("JP1", "3"): "TP_PWR",
    ("SW1", "1"): "NRST", ("SW1", "2"): "GND",
    ("R1", "1"): "TP_PWR", ("R1", "2"): "TP_CLK", ("R2", "1"): "TP_PWR", ("R2", "2"): "TP_DATA",
    ("R3", "1"): "TP_RESET", ("R3", "2"): "GND",
}
for i, n in enumerate(["TP_PWR", "GND", "TP_CLK", "TP_DATA", "TP_RESET", "TP_BTN_L", "TP_BTN_M",
                       "TP_BTN_R", "TP_AUX1", "TP_AUX2"]):
    expect[("J2", str(i + 1))] = n
qs = ["15", "1", "2", "3", "4", "5", "6", "7"]
for u, base in (("U2", 1), ("U3", 9), ("U4", 17)):
    for pin in ("11",):
        expect[(u, pin)] = "SR_CLK"
    expect[(u, "12")] = "SR_LATCH"
    expect[(u, "10")] = "3V3_SR"
    expect[(u, "16")] = "3V3_SR"
    expect[(u, "13")] = "GND"
    expect[(u, "8")] = "GND"
    for j, q in enumerate(qs):
        if base + j <= 18:
            expect[(u, q)] = "col%d" % (base + j)
for ref in ("J3", "J4"):
    for pin, want in (("A4", "DB_VBUS"), ("B9", "DB_VBUS"), ("A6", "DB_DP"), ("B6", "DB_DP"),
                      ("A7", "DB_DN"), ("B7", "DB_DN"), ("A1", "DB_GND"), ("S1", "DB_GND")):
        expect[(ref, pin)] = want
expect.update({("J3", "A5"): "DB_CC1", ("J3", "B5"): "DB_CC2", ("R4", "1"): "DB_CC1", ("R5", "1"): "DB_CC2",
               ("R4", "2"): "DB_GND", ("R5", "2"): "DB_GND"})
for (ref, pin), want in expect.items():
    got = net_of(ref, pin)
    if got is None or short(got) != want:
        errors.append("%s.%s: expected %s, got %s" % (ref, pin, want, got))

# every row/col net must reach the matrix AND the controller side
for name, nodes in nets.items():
    s = short(name)
    if re.fullmatch(r"row\d|col\d+", s):
        refs = {r for r, _ in nodes}
        side_matrix = any(r.startswith(("MX", "D")) for r in refs)
        side_ctrl = any(r in ("U1", "U2", "U3", "U4") for r in refs)
        if not (side_matrix and side_ctrl):
            errors.append("net %s not bridging matrix<->controller: %s" % (name, sorted(refs)))
rowcol = sorted(short(n) for n in nets if re.fullmatch(r"row\d|col\d+", short(n)))
print("row/col nets:", len(rowcol))

# single-node nets (excluding intentional NC pins and unconnected-* nets)
for name, nodes in nets.items():
    if len(nodes) == 1 and not name.startswith("unconnected"):
        errors.append("single-node net %s: %s" % (name, nodes))
unconnected = sorted(n for n in nets if n.startswith("unconnected"))
print("unconnected (NC) pins:", len(unconnected))
for n in unconnected:
    print("   ", n)

print("ERRORS:" if errors else "OK: all expected connections present")
for e in errors:
    print("  ", e)
sys.exit(1 if errors else 0)
