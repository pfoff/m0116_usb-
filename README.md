# m0116_usb
[![CC BY-NC-SA 4.0][cc-by-nc-sa-shield]][cc-by-nc-sa]<a href="https://ko-fi.com/kb_elmo"><img src="https://i.imgur.com/9T0bvqO.png" alt="kofibadge" align="right"/></a>

**[Deutsch](#deutsch) | [English](#english)**

## Deutsch

### Dieses Projekt ist abgeschlossen und wird nicht mehr aktualisiert.
Wir sind absolute Anfänger und wollen eine Platine für einige unserer M0118
bauen, irgendwann mit Unterstützung für ANSI-Belegung mit AEK-Tastenkappen.
Hilfe und Tipps sind willkommen.

### Wireless-TrackPoint-Revision (Branch `wireless-trackpoint`)

In Arbeit: Der ursprüngliche ATmega32A/V-USB-Controller wird durch einen
gesockelten **nice!nano v2** mit **ZMK** ersetzt, dazu ein PS/2-TrackPoint
und ein LiPo-Akku. Platinenkontur, Schalterpositionen, die 5×18-Matrix und
die Befestigungslöcher bleiben unverändert. Designnotizen, Pinbelegung und
offene Punkte: [docs/wireless-trackpoint-design.md](docs/wireless-trackpoint-design.md)
(englisch).

- `m0116_usb.kicad_sch` – Matrix (unverändert) plus zwei Unterblätter:
  - `controller.kicad_sch` – nice!nano, 3× 74HC595 als Spaltentreiber, LiPo,
    dauerhaft aktiver LDO, TrackPoint-Stecker
  - `usb_daughterboard.kicad_sch` – USB-C-Durchführung auf dem abbrechbaren
    Tab in der hinteren ADB-Aussparung, für Kabelbetrieb und Laden
- `m0116_wireless.kicad_sym` – Projekt-Symbolbibliothek (nice!nano v2)
- `tools/` – Hilfsskripte für das Makefile

Benötigt KiCad 7 (`kicad-cli` und das `pcbnew`-Python-Modul des
System-Pythons). Einmal `git submodule update --init` ausführen, um die
Footprint-Bibliotheken zu holen.

| Befehl | Was er macht |
|---|---|
| `make check` | Netzliste exportieren und die vorgesehenen Verbindungen prüfen |
| `make pcb-update` | Platine ohne GUI aus dem Schaltplan aktualisieren (Pcbnew vorher schließen) |
| `make pcb-check` | Ungeroutete Verbindungen Netz für Netz auflisten |
| `make pdf` | Schaltplan als PDF in `build/` |
| `make gerbers` | Gerber- und Bohrdateien, gezippt in `build/` |
| `make dsn` | Specctra-DSN der Tastenmatrix für Freerouting, in `build/` |
| `make dsn-continue` | DSN mit den vorhandenen Leiterbahnen, Freerouting ergänzt nur die offenen Verbindungen |
| `make clean` | `build/` löschen |

Die Schalter-Footprints sind MX/Alps-Hybride (`MX_Alps_Hybrid:MX-1U-NoLED`);
MX82 ist ein optionaler mittiger MX-Leertastenschalter parallel zum
außermittigen Alps-Leertastenschalter MX73 (nur einen der beiden bestücken).
Die Matrix wird mit Freerouting geroutet: `make dsn`, die DSN routen, dann
ersetzt `/usr/bin/python3 tools/import_ses.py <board> <datei.ses>` die
Leiterbahnen aller Netze aus der Session. Bei einem Teilergebnis
`make dsn-continue` ausführen (GND wird dort als Leiterbahn geroutet, damit
Inseln der Massefläche keine offenen Pads verstecken), routen und erneut
importieren; `/usr/bin/python3 tools/stitch_gnd.py <board>` setzt Vias von
GND-Inseln zur Hauptfläche, wo sich beide Lagen überlappen. Die exportierte
Kontur wird um 0,35 mm verkleinert und die Bohrungen vergrößert, weil
Freerouting nur 0,2 mm Abstand zur Kante hält und KiCad 0,5 mm prüft. Die
Netze der USB-Tochterplatine fehlen in der DSN (enge USB-C-Pads) und werden
von Hand geroutet. Die Frage von Freerouting, eine `.rules`-Datei zu
importieren, mit „Nein“ beantworten: Sie überschreibt die Regeln der neuen
DSN.

#### TKL-Variante (ohne Ziffernblock)

`m0116_tkl.*` wird per Skript aus der großen Platine erzeugt, Änderungen
lassen sich also übertragen: `make tkl-sch` erzeugt die Schaltpläne neu,
`make tkl-pcb` baut die Platine neu (überschreibt `m0116_tkl.kicad_pcb`).
Die anderen Targets nehmen `PROJECT=m0116_tkl`. Die Platine endet nach
Backspace/Return/Pfeiltasten mit der originalen rechten Kontur, um 94,43 mm
nach links verschoben; U4/C5 entfallen (14 Spalten), die rechte
Plattenschraube wandert mit der Kontur und muss in die gekürzte Platte
gebohrt werden.

`make pcb-update` platziert neue Footprints nur beim ersten Anlegen nach
`tools/placement.json`, manuelle Platzierung in Pcbnew bleibt also erhalten.

Stand: Schaltplan fertig (ERC sauber). Die TKL-Platine ist bis auf zwei
Verbindungen autogeroutet; die große Platine muss noch neu geroutet werden.
Der Tab der Tochterplatine muss angepasst werden, sobald die hintere
ADB-Aussparung des Gehäuses ausgemessen ist. Offene Schritte, für
KiCad-Einsteiger beschrieben: [TODO.md](TODO.md) (englisch).

### Originaldesign

Die folgenden Abschnitte beschreiben das ursprüngliche Design.

QMK-kompatible Drop-in-Ersatzplatine für den Apple M0116. Die Platine ist
komplett mit THT-Bauteilen aufgebaut, um einen etwas „vintage“ Look zu
behalten, und verwendet den ATmega32A im 40-poligen DIP-Gehäuse. (Hinweis
der Wireless-Revision: Der Controller sitzt in der Leiste hinter der
Zahlenreihe; die Bemerkung zur Leertaste in der englischen Fassung stammt
aus dem M0110a-Projekt.)

Stückliste (Partslist) und Bilder: siehe unten im englischen Teil, die
Tabelle ist sprachunabhängig.

## English
### This project is completed and will not get updated anymore.
We are complete beginners and want to build a pcb for some of our m0118s, eventually with support for ansi keymap, by using some aek keycaps. 
Any help or tips appreciated

### Wireless TrackPoint revision (branch `wireless-trackpoint`)

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
| `make dsn` | Specctra DSN of the key matrix for Freerouting, in `build/` |
| `make dsn-continue` | DSN that keeps the existing tracks, so Freerouting only completes open connections |
| `make clean` | Remove `build/` |

Switch footprints are MX/Alps hybrids (`MX_Alps_Hybrid:MX-1U-NoLED`); MX82 is
an optional centred MX spacebar switch in parallel with the off-centre Alps
spacebar switch MX73. The matrix is routed with Freerouting: `make dsn`, route
the DSN, then `/usr/bin/python3 tools/import_ses.py <board> <file.ses>`
replaces the tracks of every net in the session. For a partial result run
`make dsn-continue` (GND is routed as tracks there, so pour islands cannot
hide open pads), route that and import again;
`/usr/bin/python3 tools/stitch_gnd.py <board>` adds vias from GND pour islands
to the main pour where both layers overlap. The exported outline is
shrunk and the holes enlarged by 0.35 mm, because Freerouting keeps only
0.2 mm to the edge and KiCad checks 0.5 mm. The USB daughterboard nets are
left out of the DSN (tight USB-C pads), route them by hand. When Freerouting
asks whether to import a `.rules` file, answer "No": it would override the
rules of the new DSN.

#### TKL variant (no keypad)

`m0116_tkl.*` is derived from the full board by scripts, so changes to the
full board can be carried over: `make tkl-sch` regenerates the schematics,
`make tkl-pcb` rebuilds the PCB (overwrites `m0116_tkl.kicad_pcb`). Other
targets take `PROJECT=m0116_tkl`. The board ends after Backspace/Return/arrows
with the original right-hand contour moved 94.43 mm left; U4/C5 are dropped
(14 columns), the right plate screw moves with the contour and has to be
drilled into the cut-down plate.

`make pcb-update` places new footprints according to `tools/placement.json`
only when they are first created, so manual placement in Pcbnew is kept.

Status: schematic done (ERC clean). The TKL board is autorouted except for
two connections; the full board still has to be rerouted. The daughterboard
tab has to be resized once the rear ADB cut-out of the case is measured.
Open steps, written for KiCad beginners: [TODO.md](TODO.md).

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


## Lizenz / License

Dieses Werk ist lizenziert unter einer / This work is licensed under a
[Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License][cc-by-nc-sa].

[![CC BY-NC-SA 4.0][cc-by-nc-sa-image]][cc-by-nc-sa]

[cc-by-nc-sa]: http://creativecommons.org/licenses/by-nc-sa/4.0/
[cc-by-nc-sa-image]: https://licensebuttons.net/l/by-nc-sa/4.0/88x31.png
[cc-by-nc-sa-shield]: https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg

