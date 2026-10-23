# m0116_usb
[![CC BY-NC-SA 4.0][cc-by-nc-sa-shield]][cc-by-nc-sa]<a href="https://ko-fi.com/kb_elmo"><img src="https://i.imgur.com/9T0bvqO.png" alt="kofibadge" align="right"/></a>

## This project is completed and will not get updated anymore.
We are complete beginners and want to build a pcb for some of our m0118s, eventually with support for ansi keymap, by using some aek keycaps. 
Any help or tips appreciated

## Wireless TrackPoint revision (branch `wireless-trackpoint`)

Work in progress: the original ATmega32A/V-USB controller is replaced by a
socketed **nice!nano v2** running **ZMK**, with a PS/2 TrackPoint and LiPo
battery. Board outline, switch positions, the 5x18 matrix and the mounting
holes stay unchanged. Design notes, pin assignment and open points:
[docs/wireless-trackpoint-design.md](docs/wireless-trackpoint-design.md).

- `m0116_usb.kicad_sch` - matrix (unchanged) plus two sub-sheets:
  - `controller.kicad_sch` - nice!nano, 3x 74HC595 column drivers, LiPo,
    always-on LDO, TrackPoint header
  - `usb_daughterboard.kicad_sch` - USB-C pass-through on the break-off tab
    in the rear ADB cut-out, for wired use and charging
- `m0116_wireless.kicad_sym` - project symbol library (nice!nano v2)
- `tools/` - helper scripts used by the Makefile

Requires KiCad 7 (`kicad-cli` and the `pcbnew` Python module of the system
Python). Run `git submodule update --init` once to fetch the footprint
libraries.

| Command | What it does |
|---|---|
| `make check` | Export the netlist and verify the intended connections |
| `make pcb-update` | Update the PCB from the schematic without the GUI (close Pcbnew first) |
| `make pcb-check` | List unrouted connections net by net |
| `make pdf` | Schematic as PDF in `build/` |
| `make gerbers` | Gerber and drill files, zipped in `build/` |
| `make clean` | Remove `build/` |

`make pcb-update` places new footprints according to `tools/placement.json`
only when they are first created, so manual placement in Pcbnew is kept.

Status: schematic done (ERC clean), footprints placed in the rear strip,
routing of the new controller connections still to do. The daughterboard
tab has to be resized once the rear ADB cut-out of the case is measured.

The rest of this README describes the original design.

### QMK compatible drop-in replacement PCB for the Apple M0116
The PCB is built entirely with THT parts to keep a somewhat "vintage" look to it and it uses the fullsize 40-pin DIP package ATmega32A.
The controller is placed in the exact same location as the one on the original PCB meaning that it can be accessed through the plate cutout under the spacebar.
(Note from the wireless revision: on this board the controller actually sits in the strip behind the number row; the spacebar remark was inherited from the M0110a project.)

<img src="https://files.elmo.space/kicad_images/m0116_usb-Front.png" alt="drawing" height="300"/>
<img src="https://files.elmo.space/kicad_images/m0116_usb-Back.png" alt="drawing" height="300"/>

### Partslist
 |Count|Part|
 |-|-|
 |1|ATmega32A 40 pin DIP (32L works too)|
 |1|40 pin DIP socket (optional but highly recommended)|
 |1|2x3 pin header 2.54mm (for ISP flashing)|
 |1|JST PH 2mm 4pin connector + cable|
 |1|mini usb port|
 |1|500 mA polyfuse|
 |2|6mm momentary push buttons|
 |1|16 MHz quarz crystal|
 |1|4.7 uF electrolytic capacitor|
 |2|100 nF ceramic disk capacitor|
 |2|22 pF ceramic disk capacitor|
 |1|10 kΩ resistor|
 |2|68 Ω resistor|
 |1|1.5 kΩ resistor|
 |2|3.6 V zener diode (DO-35 BZX55C3V6)|
 |81|universal switching diode (DO-35 1N4148)|
 

#### Some pictures of the first finished PCB
[![](https://i.imgur.com/0l0W3oYm.jpg)](https://i.imgur.com/0l0W3oY.jpg) [![](https://i.imgur.com/iAKeK4cm.jpg)](https://i.imgur.com/iAKeK4c.jpg)
[![](https://i.imgur.com/Zk1t3iOm.jpg)](https://i.imgur.com/Zk1t3iO.jpg) [![](https://i.imgur.com/qjwVC6qm.jpg)](https://i.imgur.com/qjwVC6q.jpg)
[![](https://i.imgur.com/mmxlIqLm.jpg)](https://i.imgur.com/mmxlIqL.jpg) [![](https://i.imgur.com/rhK3iEWm.jpg)](https://i.imgur.com/rhK3iEW.jpg)

This work is licensed under a
[Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License][cc-by-nc-sa].

[![CC BY-NC-SA 4.0][cc-by-nc-sa-image]][cc-by-nc-sa]

[cc-by-nc-sa]: http://creativecommons.org/licenses/by-nc-sa/4.0/
[cc-by-nc-sa-image]: https://licensebuttons.net/l/by-nc-sa/4.0/88x31.png
[cc-by-nc-sa-shield]: https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg
