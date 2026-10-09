# Regenerate every printable and printed part. Outputs land in build/, which is
# git-ignored: the sources are the truth, not the exports.

SUBJECT ?= reference
CIRC    ?= 575
NI      ?= 350
PA      ?= 340

SCAD    = openscad
BLENDER = /Applications/Blender.app/Contents/MacOS/Blender
BUILD   = build

.PHONY: all fit parts headform preview renders animation sizes test clean

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
	rm -rf $(BUILD)/*.stl $(BUILD)/*.svg $(BUILD)/*.png $(BUILD)/*.csv $(BUILD)/renders

## Studio renders for the poster, the report and the deck. OpenSCAD's own
## previews are for checking geometry while working; these are for showing
## people. Needs Blender:  brew install --cask blender
##
##   make renders                      four stills
##   make animation                    turntable + fit clips
##   make renders SAMPLES=256          final quality
##   make renders THEME=light          light background instead of dark
SAMPLES      ?= 96
ANIM_SAMPLES ?= 48
FRAMES       ?= 96
THEME        ?= dark

RENDER = $(BLENDER) --background --python render/blender_render.py --

renders: parts headform
	$(RENDER) --mode stills --samples $(SAMPLES) --theme $(THEME)
	@echo "stills in $(BUILD)/renders/"

## One animation per Blender process: two FFmpeg outputs from a single session
## leaves the second file an empty container.
animation: parts headform
	$(RENDER) --mode turntable --anim-samples $(ANIM_SAMPLES) --frames $(FRAMES) --theme $(THEME)
	$(RENDER) --mode fit --anim-samples $(ANIM_SAMPLES) --theme $(THEME)
	@echo "animations in $(BUILD)/renders/"

## A size run: four frames a fixed percentage apart, printed together.
##
## Scan-derived sizing is not trustworthy here. A tape on the scalp reads
## 575 mm; a convex hull round the LiDAR scan at ring height reads about
## 790 mm, and the difference is hair. How far hair compresses under a cap is
## the number that decides fit, and nothing in the scan predicts it. So print
## the run and keep whichever sits right.
##
## Base measurements are the chat's tape numbers with the two arcs swapped —
## see docs/DESIGN_NOTES.md, the scan confirmed they were recorded backwards.
BASE_CIRC ?= 575
BASE_NI   ?= 350
BASE_PA   ?= 340
SIZE_PCT  ?= 4 12 20 28

sizes: headform
	@mkdir -p $(BUILD)/sizes
	@for pct in $(SIZE_PCT); do \
	  circ=$$(echo "$(BASE_CIRC) * (100 + $$pct) / 100" | bc); \
	  ni=$$(echo "$(BASE_NI) * (100 + $$pct) / 100" | bc); \
	  pa=$$(echo "$(BASE_PA) * (100 + $$pct) / 100" | bc); \
	  echo "size +$$pct%  ->  circumference $$circ mm"; \
	  (cd fit && python3 -m nsc_fit --circumference $$circ --nasion-inion $$ni \
	      --ear-to-ear $$pa --subject "size-$$circ" --out ../$(BUILD)/sizes) >/dev/null \
	      || { echo "fit failed for $$circ mm"; exit 1; }; \
	  $(SCAD) -D 'part="frame"' -D "size_label=\"$$circ\"" \
	      -o $(BUILD)/sizes/frame_$$circ.stl cad/cap_frame.scad 2>/dev/null; \
	done
	@echo "size run in $(BUILD)/sizes/"
