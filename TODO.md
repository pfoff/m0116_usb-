# TODO – TKL board (`m0116_tkl`)

State on 2026-10-26: the TKL board is autorouted except for **2 connections**
on the main board. The USB daughterboard is not routed yet because its tab
outline does not exist yet (see step 4). Everything else in the DRC report is
known and acceptable (see "Expected DRC messages" at the end).

This file is written for KiCad beginners. All coordinates are in mm and match
the X/Y read-out in the bottom status bar of the KiCad PCB editor.

---

## 0. KiCad basics you need

Open the project: start KiCad 7, *File → Open Project* →
`m0116_tkl.kicad_pro`, then double-click `m0116_tkl.kicad_pcb` (the
**PCB Editor**).

| Action | How |
|---|---|
| Zoom | mouse wheel (zooms to the cursor) |
| Pan | hold the middle mouse button, or scroll bars |
| Zoom to whole board | `Home` |
| Find a part (e.g. `U2`) | `Ctrl+F`, type the reference, *Find* |
| Show the cursor position | bottom status bar, `X` / `Y` |
| Active copper layer | `PgUp` = **F.Cu** (front, red), `PgDn` = **B.Cu** (back, blue) |
| Route a track | press `X`, click on a pad, move, click to set corners, **double-click** on the target pad to finish |
| Change layer while routing (sets a via) | press `V` while the track is attached to the mouse |
| Cancel the current action | `Esc` |
| Delete a track segment | click it, `Delete` (`Ctrl+Z` undoes) |
| Highlight a net | click a pad, press `` ` `` (backtick); press again to clear |
| Refill copper zones | `B` |
| Save | `Ctrl+S` |

**Ratsnest:** thin straight lines between pads are connections that are
still missing. A finished connection has no ratsnest line any more.

**Rules while routing:** KiCad's interactive router does not let you place a
track that violates clearance, so if the track "refuses" to go somewhere,
there is not enough room there – try the other layer (`V`) or a different
path. Use the default track width (0.25 mm); it is preset.

> Close the PCB editor before running any `make` target or script from
> `tools/` – they write the same file.

---

## 1. GND to J2 pin 2

- **Where:** J2 is the 10-pin TrackPoint header in the rear strip, pin 2 at
  **(237.6 / 90.9)**. A GND track on F.Cu ends at **(236.7 / 84.0)**, about
  7 mm above it (between C4 and J2).
- **What:** connect pin 2 of J2 to that GND track (or to any other GND
  copper close by – C3/C4 pin 2 are GND too).
- **How:**
  1. `Ctrl+F` → `J2`, zoom in. You should see a ratsnest line from pin 2.
  2. Press `X`, click on pin 2 of J2, follow the ratsnest line, double-click
     on the GND track end (or a GND pad) to finish.
  3. If F.Cu is blocked, press `V` once to drop a via and continue on B.Cu.

## 2. col2 to U2 pin 1

- **Where:** U2 is the 74HC595 shift register (16-pin DIP socket), pin 1 at
  **(221.1 / 74.5)** – top left pin, next to the top board edge.
- **What:** the column net `col2` reaches all its switches, but the link to
  U2 pin 1 is missing. Freerouting could not find room there in four runs.
- **How:**
  1. `Ctrl+F` → `U2`. Click pin 1 and press `` ` `` to highlight `col2`: all
     col2 copper lights up, and the ratsnest line shows the shortest gap.
  2. Route from pin 1 to the nearest highlighted col2 track or via. The area
     left of U2 and towards the top edge is crowded; going down one layer
     with `V` and coming back is fine.
  3. Keep 0.5 mm away from the board edge (the DRC checks this).

## 3. Check

1. Press `B` (refill zones).
2. *Inspect → Design Rules Checker → Run DRC*.
3. Tab **Unconnected Items**: apart from `/USB daughterboard/DB_*` nothing
   should be left.
4. Tab **Violations**: compare with "Expected DRC messages" below; anything
   new (especially `clearance` or `copper_edge_clearance` near your new
   tracks) means a track is too close – delete it and route it again.
5. `Ctrl+S`, close the PCB editor.

## 4. USB daughterboard (do **not** route yet)

J4, R4 and R5 currently lie **outside** the board outline (above y 72.4).
The break-off tab is only about 12 × 16 mm and too small for two USB-C
receptacles (see `docs/wireless-trackpoint-design.md`, "USB-C daughterboard").

1. Measure the rear ADB cut-out of the case: width, height, wall thickness,
   and the free space behind it.
2. With these numbers the tab outline gets redrawn and J3/J4/R4/R5 placed
   (Claude can do this from the measurements).
3. Only then route the `DB_*` nets – they are short:
   - J3 and J4 each: connect the A/B pin pairs of the same signal
     (A6↔B6 D+, A7↔B7 D−, A4/A9/B4/B9 VBUS, A1/A12/B1/B12 and the shield
     pins S1 GND)
   - D+, D−, VBUS, GND from J3 to J4
   - R4 pin 1 to J3 A5 (CC1), R5 pin 1 to J3 B5 (CC2), R4/R5 pin 2 to GND
   The USB4085 pins are tight: route between the two pin rows on one layer
   and the other connections on the other layer.

## 5. Before ordering

- [ ] Steps 1–4 done, DRC without unconnected items
- [ ] Check the plate: U1 (nice!nano, x 165–197) and U2/R1–R3/C6/C7 sit under
      **solid** plate (the only plate window is at about x 229.6–307.6).
      Measure the gap between plate and PCB, or enlarge the window.
- [ ] Right plate screw at (234.37 / 76.58): drill this hole into the
      cut-down plate.
- [ ] `make gerbers PROJECT=m0116_tkl` → `build/m0116_tkl-gerbers.zip`
- [ ] ZMK firmware for 14 columns (U4 is not fitted on the TKL board)

## Later: full board (`m0116_usb`)

The old matrix tracks still cross the MX centre holes of the hybrid
footprints. Reroute it the same way: `make dsn`, Freerouting, import with
`tools/import_ses.py`, then `make dsn-continue` for the rest.

---

## Expected DRC messages (acceptable)

| Type | Count | Why |
|---|---|---|
| `hole_near_hole` | 64 | built into the MX/Alps hybrid footprint (overlapping drills), one per switch |
| `clearance` | 28 | inside the USB4085 footprints J3/J4 (pin pitch of the part) |
| `lib_footprint_issues` | ~93 | footprints differ from the library copy / library not found; no effect on copper |
| `silk_*` | ~18 | silkscreen overlaps, cosmetic |
| `courtyards_overlap` | 1 | J1 / SW2, pre-existing |
| `starved_thermal` | 2 | GND pads of U3 / C3 have fewer thermal spokes; still connected |
