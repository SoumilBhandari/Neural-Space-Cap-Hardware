# Regenerate every printable and printed part. Outputs land in build/, which is
# git-ignored: the sources are the truth, not the exports.

SUBJECT ?= reference
CIRC    ?= 575
NI      ?= 350
PA      ?= 340

SCAD    = openscad
BLENDER = /Applications/Blender.app/Contents/MacOS/Blender
BUILD   = build

.PHONY: all fit parts headform preview renders animation sizes scan scan-sizes coupon test clean

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

## Fit the frame to a LiDAR scan instead of to an ellipsoid.
##
## Her contour comes from the scan; SCAN_CIRC sets only how much hair the
## frame expects to flatten. A scan measures hair uncompressed — this one
## reads about 800 mm around the ring against 575 mm of tape on her scalp —
## so building to the raw figure gives a frame nobody can print.
##
## None of the usable sizes fit a 220 mm bed. 250 mm or larger, or tie the
## hair back and rescan. See docs/DESIGN_NOTES.md.
SCAN      ?= scan/10_9_2026.obj
SCAN_GAP  ?= 4
SCAN_CIRC ?= 640

scan:
	cd fit && python3 -m nsc_fit.build_scan --scan ../$(SCAN) \
		--circumference $(SCAN_CIRC) --gap $(SCAN_GAP) \
		--tape $(CIRC) $(NI) $(PA) --out ../$(BUILD)/cap_frame.stl

## A size run on hair allowance — the one quantity nothing can predict.
## Spread chosen by how far hair might compress, not by bed size — the H2D
## takes any of these with room to spare. Her scan carries 36 mm of loft, so
## this run spans flattening it by about 80% down to about 27%.
SCAN_SIZES ?= 620 660 700 740

scan-sizes:
## Written to its own directory: build/sizes/ also holds the older
## ellipsoid-scaled run, and mixing the two means a render or a print queue
## silently picks up both.
	@mkdir -p $(BUILD)/scan_sizes
	@for c in $(SCAN_SIZES); do \
	  (cd fit && python3 -m nsc_fit.build_scan --scan ../$(SCAN) --circumference $$c \
	      --gap $(SCAN_GAP) --tape $(CIRC) $(NI) $(PA) \
	      --out ../$(BUILD)/scan_sizes/frame_$$c.stl) || exit 1; \
	done
	@echo "size run in $(BUILD)/scan_sizes/"

## Thumb-sized test piece: one electrode socket, one insert boss, cut with the
## same numbers as the frame. Print it before committing hours to a frame.
coupon:
	$(SCAD) -D 'part="coupon"' -o $(BUILD)/fit_coupon.stl cad/cap_frame.scad
	@echo "print $(BUILD)/fit_coupon.stl first — five minutes, saves a frame"
