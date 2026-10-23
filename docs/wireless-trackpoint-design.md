# Wireless TrackPoint revision

Status: architecture draft for the first prototype

## Fixed requirements

- Keep the complete Apple M0116 ANSI layout and original PCB outline.
- Keep the original Alps switch positions and Apple keycaps.
- Use a socketed nice!nano v2 and ZMK.
- Add a PS/2 TrackPoint and retain wired USB operation through the nice!nano.
- Reuse the existing 81-key, diode-protected `5 x 18` matrix.
- Preserve the original mounting holes and case interfaces.

## Matrix architecture

The original board uses a `COL2ROW` matrix:

- inputs: `row0` through `row4`
- outputs: `col1` through `col18`

The five row nets remain connected directly to nice!nano GPIOs so that a key
press can wake the controller. The 18 column nets are driven by three
daisy-chained 74HC595 shift registers:

| Function | Count | nice!nano GPIO usage |
|---|---:|---:|
| Matrix row inputs | 5 | 5 |
| 74HC595 SPI clock/data/latch | 3 | 3 |
| Total keyboard matrix | | **8** |

The 74HC595 devices run at 3.3 V. Each device gets a local 100 nF bypass
capacitor. `/SRCLR` is pulled high, `/OE` is held active, and unused outputs
remain unconnected. The exact column-to-output order may be chosen to minimize
routing and corrected in the ZMK devicetree configuration.

The shift registers must remain powered while the keyboard sleeps so that the
direct row inputs can wake the nice!nano.

## TrackPoint prototype interface

The photographed module has a ten-contact cable termination and a Synaptics
controller. The four metal areas labelled `F/T-1` through `F/T-3` and
`A-Check` appear to belong to the force-sensor/calibration assembly; they are
not assumed to be user mouse buttons. The exact part number and pinout are not
yet known. The first mainboard revision therefore provides a generic ten-pin
adapter header rather than assuming a pinout.

Provisional signals:

| Signal | Purpose |
|---|---|
| `TP_PWR` | switched TrackPoint supply |
| `GND` | ground |
| `TP_CLK` | PS/2 clock |
| `TP_DATA` | bidirectional PS/2 data |
| `TP_RESET` | optional module reset/power-on-reset |
| `TP_BTN_L` | optional left-button input |
| `TP_BTN_M` | optional middle-button input |
| `TP_BTN_R` | optional right-button input |
| `TP_AUX1` | reserved/detect signal |
| `TP_AUX2` | reserved/detect signal |

The connector pin order will only be assigned after continuity and voltage
measurements. Clock and data must not receive 5 V because the nRF52840 GPIOs
are not 5 V tolerant.

Revision A assumes a TrackPoint that operates from 3.3 V. A 5 V-only module
would require a boost supply and bidirectional open-drain level translation;
that should be tested on a breakout before adding it to the keyboard PCB.

## Power

- 3.7 V rechargeable LiPo connected according to the nice!nano v2
  documentation.
- Physical battery disconnect switch.
- 74HC595 chain powered continuously from regulated 3.3 V.
- TrackPoint powered through a controllable load switch.
- Battery connector polarity clearly marked on copper and silkscreen.
- Battery and TrackPoint test points.

The TrackPoint will probably dominate idle current. Firmware should switch it
off during deep sleep. In that state TrackPoint movement cannot wake the
keyboard, but a key press can.

## Mechanical and RF placement

- Keep the original board outline and all switch coordinates unchanged.
- Reuse the former ATmega/USB component area for the nice!nano and matrix
  electronics where possible.
- Place the nice!nano antenna close to a plastic case edge.
- No copper, traces, battery or ground plane underneath or immediately in
  front of the antenna.
- Check the metal plate position before finalizing the antenna location.
- Add a plate opening and a mechanical support for the TrackPoint between
  G/H/B.
- Verify that the TrackPoint cap clears the skirts of the original Apple
  keycaps throughout their travel.

## Inputs needed before schematic and placement freeze

1. TrackPoint PCB width, height and thickness.
2. Center-to-center distances of its mounting holes.
3. Pitch and numbering/orientation of the ten connector pads.
4. Origin laptop/keyboard or any label/FRU from the TrackPoint assembly.
5. Resistance/continuity measurements from connector pads to ground, supply
   decoupling and any known external mouse-button contacts.
6. Available internal height between main PCB, metal plate and bottom case.
7. Desired TrackPoint cap position and desired mouse-button arrangement.
8. Intended LiPo dimensions/capacity.

## Revision A schematic

Implemented in `controller.kicad_sch` (branch `wireless-trackpoint`).
The matrix on the root sheet is unchanged and connects through the global
labels `row0`-`row4` and `col1`-`col18`. The ATmega32A, V-USB circuit, crystal,
ISP header, mini-USB, polyfuse and boot button were removed.

### nice!nano v2 pin assignment

| Pin | GPIO | Net | Pin | GPIO | Net |
|---:|---|---|---:|---|---|
| 1 | P0.06 | `TP_CLK` | 24 | B+ | `VBAT` |
| 2 | P0.08 | `TP_DATA` | 23 | GND | `GND` |
| 3 | GND | `GND` | 22 | RST | `NRST` (reset button) |
| 4 | GND | `GND` | 21 | VCC (switched, P0.13) | `TP_PWR` |
| 5 | P0.17 | `SR_DATA` (SPI MOSI) | 20 | P0.31 | `row0` |
| 6 | P0.20 | `SR_CLK` (SPI SCK) | 19 | P0.29 | `row1` |
| 7 | P0.22 | `SR_LATCH` (SPI CS) | 18 | P0.02 | `row2` |
| 8 | P0.24 | `TP_RESET` | 17 | P1.15 | `row3` |
| 9 | P1.00 | `TP_BTN_L` | 16 | P1.13 | `row4` |
| 10 | P0.11 | `TP_BTN_M` | 15 | P1.11 | spare |
| 11 | P1.04 | `TP_BTN_R` | 14 | P0.10 (NFC) | `TP_AUX2` |
| 12 | P1.06 | `TP_AUX1` | 13 | P0.09 (NFC) | spare |

`TP_AUX2` on P0.10 requires `CONFIG_NFCT_PINS_AS_GPIOS=y`.

### Design decisions

- **Always-on rail for the shift registers.** ZMK switches the nice!nano VCC
  pin (P0.13, ext-power) off in deep sleep, which would leave the columns
  undriven and break key-press wake-up. A dedicated MCP1700-3302E/TO LDO
  (Iq ~1.6 uA) from `VBAT` supplies the 74HC595 chain (`3V3_SR`). Solder
  jumper JP1 selects LDO (1-2, default) or nice!nano VCC (2-3).
- **TrackPoint load switch** = nice!nano switched VCC (`TP_PWR`). It turns off
  automatically in deep sleep and can be toggled with ZMK `&ext_power`.
- **PS/2:** 4.7 k pull-ups on CLK/DATA to `TP_PWR` only, so a powered-down
  module is never back-fed. `TP_RESET` has a 100 k pull-down.
- **TrackPoint header J2** (1x10, 2.54 mm): 1 `TP_PWR`, 2 `GND`, 3 `TP_CLK`,
  4 `TP_DATA`, 5 `TP_RESET`, 6-8 `TP_BTN_L/M/R`, 9-10 `TP_AUX1/2`. This order
  is project-defined; an adapter maps it to the module once measured.
- **Battery:** JST PH 2-pin (J1, pin 1 = +) -> slide switch SW2 -> B+.
- **Parts stay THT** to match the original board: DIP sockets, TO-92 LDO,
  ceramic disc capacitors, axial resistors, THT test pads TP1-TP8.

The nice!nano v2 pinout was checked against the official pinout diagram:
pin 24 (top right, next to USB) is BATTERY+, followed by GND, RESET and the
switched 3.3 V pin. The extra B+/B- pads beside the USB port and the bottom
pads P1.01/P1.02/P1.07 are not used.

### USB-C daughterboard

The original electronics sit in the strip behind the number row, not under
the spacebar (the upstream README text was inherited from the M0110a
project). The original design already used a break-off daughterboard with
the USB jack, glued into the rear ADB cut-out of the case.

Revision A keeps that concept (`usb_daughterboard.kicad_sch`):

- J3: THT USB-C receptacle (GCT USB4085) facing outward through the case,
  5.1 k Rd on CC1/CC2 (R4/R5) so any USB-C host or charger supplies VBUS.
- J4: second USB4085 facing inward. A short off-the-shelf USB 2.0 C-to-C
  cable (10-15 cm, angled plugs preferred) connects it to the nice!nano.
  The nice!nano has its own Rd, so J4 CC1/CC2 stay open.
- Nets `DB_*` exist only on the tab; the cable is the only electrical link,
  so breaking the tab off leaves no unrouted connections.
- On the main board the nice!nano lies lengthwise in the rear strip with its
  USB port facing the daughterboard and the antenna end pointing away, clear
  of the metal plate.

The existing tab is only about 12 x 16 mm (x 48.6-60.9, y 72.4-88.4 in the
PCB). Two USB4085 receptacles (each about 9 x 7.4 mm) plus R4/R5 will not
fit comfortably; the tab outline has to grow or the receptacles have to be
arranged on opposite edges.

### Open points

1. Measure the rear ADB cut-out of the case (width, height, wall thickness)
   and the free space behind it, to size the daughterboard tab.
2. Confirm in ZMK that the kscan matrix drives all 74HC595 outputs active
   before entering deep sleep (required for row-based wake-up).
3. The PCB has not been updated from the new schematic yet.

## KiCad workflow

The source PCB is in KiCad 5 format and the schematic is a legacy `.sch`.
KiCad 7.0.11 can open both and save them in current formats. Do the first
format conversion as an isolated commit before changing the circuit, so the
mechanical conversion diff remains separate from the wireless redesign.

KiCad 7 is sufficient for Revision A. A later KiCad version is optional, but
all contributors should use the same major version once the project has been
migrated.
