# M0116 wireless TrackPoint - KiCad 7 helper targets
#
#   make check        export the netlist and verify the intended connections
#   make pcb-update   bring the PCB in line with the schematic (headless F8)
#   make pcb-check    report unrouted connections net by net
#   make pdf          schematic PDF
#   make gerbers      Gerber + drill files, zipped for the fab
#   make dsn          Specctra DSN of the key matrix for Freerouting (import: tools/import_ses.py)
#   make dsn-continue DSN that keeps the existing tracks, Freerouting only completes what is open
#   make clean        remove build/
#
# TKL variant (no keypad):
#   make tkl-sch      derive the m0116_tkl schematics from the full board
#   make tkl-pcb      rebuild m0116_tkl.kicad_pcb from m0116_usb.kicad_pcb (overwrites it!)
#   then any target with PROJECT=m0116_tkl, e.g. make check PROJECT=m0116_tkl
#
# Close the board in Pcbnew before "make pcb-update".

SHELL       := /bin/bash
.SHELLFLAGS := -o pipefail -c

PROJECT   ?= m0116_usb
SCH       := $(PROJECT).kicad_sch
PCB       := $(PROJECT).kicad_pcb
SCH_FILES := $(wildcard *.kicad_sch)
BUILD     := build

KICAD_CLI ?= kicad-cli
# KiCad's pcbnew Python module is only available to the system interpreter
PYTHON    ?= /usr/bin/python3 -I

NETLIST   := $(BUILD)/$(PROJECT).net
COLS      := $(if $(filter m0116_tkl,$(PROJECT)),14,18)
PLACEMENT := $(if $(filter m0116_tkl,$(PROJECT)),tools/placement_tkl.json,tools/placement.json)
GERBER_DIR := $(BUILD)/gerbers
LAYERS    := F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts

# KiCad 7 warnings that are noise for these targets
FILTER    := grep -v -e 'memory leak' -e 'Legacy zone fill' -e 'best-effort basis' || true

.PHONY: all check netlist pcb-update pcb-check pdf gerbers clean tkl-sch tkl-pcb dsn dsn-continue

all: check

$(BUILD):
	mkdir -p $@

netlist: $(NETLIST)

$(NETLIST): $(SCH_FILES) | $(BUILD)
	$(KICAD_CLI) sch export netlist --format kicadsexpr -o $@ $(SCH)

check: $(NETLIST)
	$(PYTHON) tools/check_netlist.py $(NETLIST) $(COLS)

pcb-update: $(NETLIST)
	$(PYTHON) tools/update_pcb.py --netlist $(NETLIST) --pcb $(PCB) \
		--placement $(PLACEMENT) 2>&1 | $(FILTER)

pcb-check:
	$(PYTHON) tools/check_pcb.py $(PCB) 2>&1 | $(FILTER)

pdf: $(BUILD)/$(PROJECT)-schematic.pdf

$(BUILD)/$(PROJECT)-schematic.pdf: $(SCH_FILES) | $(BUILD)
	$(KICAD_CLI) sch export pdf -o $@ $(SCH)

dsn: | $(BUILD)
	$(PYTHON) tools/export_matrix_dsn.py $(PCB) $(BUILD)/$(PROJECT)-matrix.dsn 2>&1 | $(FILTER)

dsn-continue: | $(BUILD)
	$(PYTHON) tools/export_matrix_dsn.py --continue $(PCB) $(BUILD)/$(PROJECT)-continue.dsn 2>&1 | $(FILTER)

gerbers: $(BUILD)/$(PROJECT)-gerbers.zip

$(BUILD)/$(PROJECT)-gerbers.zip: $(PCB) | $(BUILD)
	rm -rf $(GERBER_DIR) && mkdir -p $(GERBER_DIR)
	$(KICAD_CLI) pcb export gerbers --layers $(LAYERS) --subtract-soldermask \
		-o $(GERBER_DIR)/ $(PCB)
	$(KICAD_CLI) pcb export drill --excellon-separate-th --generate-map --map-format gerberx2 \
		-o $(GERBER_DIR)/ $(PCB)
	rm -f $@ && cd $(GERBER_DIR) && zip -q ../$(notdir $@) *

tkl-sch:
	$(PYTHON) tools/make_tkl_sch.py

tkl-pcb: tkl-sch
	cp m0116_usb.kicad_pcb m0116_tkl.kicad_pcb
	$(MAKE) pcb-update PROJECT=m0116_tkl
	$(PYTHON) tools/make_tkl_pcb.py m0116_tkl.kicad_pcb 2>&1 | $(FILTER)

clean:
	rm -rf $(BUILD)
