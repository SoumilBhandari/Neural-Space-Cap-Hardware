# Regenerate every printable and printed part. Outputs land in build/, which is
# git-ignored: the sources are the truth, not the exports.

SUBJECT ?= reference
CIRC    ?= 570
NI      ?= 370
PA      ?= 350

SCAD    = openscad
BUILD   = build

.PHONY: all fit parts headform preview test clean

all: fit parts

## Marking template, montage map and 3D positions for one head.
fit:
	cd fit && python3 -m nsc_fit \
		--circumference $(CIRC) --nasion-inion $(NI) --ear-to-ear $(PA) \
		--subject "$(SUBJECT)" --out ../$(BUILD)

## STLs for the printed parts.
parts: $(BUILD)/cap_frame.stl $(BUILD)/electrode_holder.stl $(BUILD)/sensor_puck.stl \
       $(BUILD)/pod_base.stl $(BUILD)/pod_lid.stl

## The frame is generated from the fitted head, so it depends on the fit.
$(BUILD)/cap_frame.stl: cad/cap_frame.scad cad/head_params.scad cad/params.scad
	$(SCAD) -D 'part="frame"' -o $@ $<

## A hollow form of the same head, for dry-fitting without booking a person.
headform: cad/head_params.scad
	$(SCAD) -D 'part="headform"' -o $(BUILD)/head_form.stl cad/cap_frame.scad

cad/head_params.scad:
	$(MAKE) fit

$(BUILD)/electrode_holder.stl: cad/electrode_holder.scad cad/params.scad
	$(SCAD) -o $@ $<

$(BUILD)/sensor_puck.stl: cad/sensor_puck.scad cad/params.scad
	$(SCAD) -o $@ $<

$(BUILD)/pod_base.stl: cad/electronics_pod.scad cad/params.scad
	$(SCAD) -D 'part="base"' -o $@ $<

$(BUILD)/pod_lid.stl: cad/electronics_pod.scad cad/params.scad
	$(SCAD) -D 'part="lid"' -o $@ $<

## Preview renders for the poster and for checking a part before slicing.
preview:
	$(SCAD) --imgsize=900,700 --colorscheme=Tomorrow -o $(BUILD)/electrode_holder.png cad/electrode_holder.scad
	$(SCAD) --imgsize=900,700 --colorscheme=Tomorrow -o $(BUILD)/sensor_puck.png cad/sensor_puck.scad
	$(SCAD) -D 'part="base"' --imgsize=900,700 --colorscheme=Tomorrow -o $(BUILD)/electronics_pod.png cad/electronics_pod.scad
	$(SCAD) -D 'part="preview"' --imgsize=1000,760 --camera=0,0,70,68,0,35,520 --colorscheme=Tomorrow -o $(BUILD)/cap_frame_preview.png cad/cap_frame.scad
	$(SCAD) -D 'part="frame"' --imgsize=1000,760 --camera=0,0,75,64,0,205,500 --colorscheme=Tomorrow -o $(BUILD)/cap_frame.png cad/cap_frame.scad

test:
	python3 -m pytest -q

clean:
	rm -rf $(BUILD)/*.stl $(BUILD)/*.svg $(BUILD)/*.png $(BUILD)/*.csv
