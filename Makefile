# M0116 wireless TrackPoint - KiCad 7 helper targets
#
#   make check        export the netlist and verify the intended connections
#   make pcb-update   bring the PCB in line with the schematic (headless F8)
#   make pcb-check    report unrouted connections net by net
#   make pdf          schematic PDF
#   make gerbers      Gerber + drill files, zipped for the fab
#   make clean        remove build/
#
# Close the board in Pcbnew before "make pcb-update".

SHELL       := /bin/bash
.SHELLFLAGS := -o pipefail -c

PROJECT   := m0116_usb
SCH       := $(PROJECT).kicad_sch
PCB       := $(PROJECT).kicad_pcb
SCH_FILES := $(wildcard *.kicad_sch)
BUILD     := build

KICAD_CLI ?= kicad-cli
# KiCad's pcbnew Python module is only available to the system interpreter
PYTHON    ?= /usr/bin/python3 -I

NETLIST   := $(BUILD)/$(PROJECT).net
GERBER_DIR := $(BUILD)/gerbers
LAYERS    := F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts

# KiCad 7 warnings that are noise for these targets
FILTER    := grep -v -e 'memory leak' -e 'Legacy zone fill' -e 'best-effort basis' || true

.PHONY: all check netlist pcb-update pcb-check pdf gerbers clean

all: check

$(BUILD):
	mkdir -p $@

netlist: $(NETLIST)

$(NETLIST): $(SCH_FILES) | $(BUILD)
	$(KICAD_CLI) sch export netlist --format kicadsexpr -o $@ $(SCH)

check: $(NETLIST)
	$(PYTHON) tools/check_netlist.py $(NETLIST)

pcb-update: $(NETLIST)
	$(PYTHON) tools/update_pcb.py --netlist $(NETLIST) --pcb $(PCB) \
		--placement tools/placement.json 2>&1 | $(FILTER)

pcb-check:
	$(PYTHON) tools/check_pcb.py $(PCB) 2>&1 | $(FILTER)

pdf: $(BUILD)/$(PROJECT)-schematic.pdf

$(BUILD)/$(PROJECT)-schematic.pdf: $(SCH_FILES) | $(BUILD)
	$(KICAD_CLI) sch export pdf -o $@ $(SCH)

gerbers: $(BUILD)/$(PROJECT)-gerbers.zip

$(BUILD)/$(PROJECT)-gerbers.zip: $(PCB) | $(BUILD)
	rm -rf $(GERBER_DIR) && mkdir -p $(GERBER_DIR)
	$(KICAD_CLI) pcb export gerbers --layers $(LAYERS) --subtract-soldermask \
		-o $(GERBER_DIR)/ $(PCB)
	$(KICAD_CLI) pcb export drill --excellon-separate-th --generate-map --map-format gerberx2 \
		-o $(GERBER_DIR)/ $(PCB)
	rm -f $@ && cd $(GERBER_DIR) && zip -q ../$(notdir $@) *

clean:
	rm -rf $(BUILD)
