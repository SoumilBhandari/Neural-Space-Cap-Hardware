# Printing the cap frame on a Bambu Lab H2D

The H2D takes 325 x 320 x 325 mm on a single nozzle, up to a 350 C hotend,
120 C bed and 65 C chamber. Every size in the run fits with at least 64 mm to
spare, so nothing here is constrained by the machine — which means the
settings can be chosen for part quality rather than to squeeze it on.

## Print the coupon first

```bash
make coupon
```

`build/fit_coupon.stl` is thumb-sized and takes a few minutes. It carries one
electrode socket bore and one heat-set insert boss, cut with exactly the
numbers the frame uses, and the bore diameter is printed on its face.

Press a cup electrode into the socket and sink an M2 insert into the boss. If
the electrode will not go, or goes in loose, change `clearance` and
`tight_fit` in `cad/params.scad` and print another coupon. Each round costs
five minutes. Finding the same problem on a finished frame costs the frame.

This is not optional politeness — the socket and the holder hub were
previously the *same* nominal diameter, which is not a press fit but a jam,
and nothing short of trial fitting would have caught it.

## Why the ring is flat

The frame is a swept tube following a curved path, so nothing on it started
out flat. Laid ring-down it met the plate at a single tangent point with
**0.0 mm² of first-layer area**, which no brim can save because there is
nothing for a brim to hold on to. That is the usual reason a generated model
simply refuses to print.

The first fix was eight sacrificial feet. They worked on paper and added
their own problems: thin necks, pads sharing faces with the band, and a ring
that still hung in the air between them.

The ring is now a planar loop at one height, and the bottom 3.8 mm of it is
cut off flat. That flat is the first layer: **about 3160 mm²** on the 660 mm
frame, one continuous track all the way round the head, 4 to 8 mm wide. Nothing to
snip, nothing to sand, and the tube wall leaves the bed at 45 degrees so the
ring itself needs no support.

## Why it slices clean now

The earlier STLs made slicers report non-manifold edges. Three causes, all
fixed and all tested:

- **The scan head was exported inside out.** Its signed volume was negative,
  so subtracting it from the bands left 45,689 of the frame's 89,764 vertices
  doubled up on top of another one. A slicer welds vertices by position, and
  after welding those became edges shared by four triangles. The exporter now
  flips the winding whenever the volume comes out negative.
- **Surfaces touching exactly.** Bands of the same diameter crossing, a boss
  ending on the same plane as its collar, a badge starting on the pad face.
  Each band is now one closed tube mesh with its own radius, and every
  feature either overlaps its neighbour properly or stays clear of it.
- **ASCII STL.** Six significant digits is enough to pull welded vertices
  apart. Everything is written as binary STL.

`make scan` now refuses to finish unless the result is one watertight shell
after position welding, which is how a slicer sees it. See
`fit/nsc_fit/meshcheck.py`.

## Settings

0.4 mm nozzle, PETG.

| | |
|---|---|
| Layer height | 0.2 mm |
| Nozzle temp | 240 °C (range 230-250) |
| Bed | 70-80 °C |
| Chamber | **off** |
| Walls | 4 (1.68 mm) |
| Top/bottom | 4 layers |
| Infill | 15% gyroid |
| Supports | tree / organic, **build plate only** |
| Brim | 5 mm |
| Seam | scarf joint on |

**Chamber off.** The H2D heats to 65 °C and PETG does not want it — a warm
chamber makes PETG string and raises the odds of heat creep in the hotend.
Chamber heating is for ABS, ASA and PC.

**Tree supports, build-plate-only.** About 10% of the surface overhangs past
45 degrees, down from 16%: the undersides of the arches near the crown and
the socket bosses. A dome printed ring-down cannot avoid that, so the slicer
will warn about overhangs until supports are switched on. Organic
supports touch far less of a curved tube and peel off it much more cleanly.
Build-plate-only stops them growing inside the dome, where you cannot reach
to remove them.

If you have the AMS, Bambu's Support for PLA/PETG as the interface layer is
worth it on this part — the supports come away by hand instead of being
picked out of the inside of a dome.

**Scarf seam.** Every band is a curved tube, so a conventional Z seam leaves
a visible scar straight down it and a line of weakness along the direction
the frame is actually loaded.

## Thin features are sized in printer units, not round numbers

A slicer cannot lay down a fraction of a line, so anything near the nozzle
size is dimensioned as a whole multiple of extrusion width or layer height:

| feature | value | why |
|---------|-------|-----|
| holder flexure | 0.84 mm = 2 lines | asking for 0.80 gets 0.84 anyway, and stiffness goes as thickness cubed — the spring would have come out 16% firmer than calculated |
| ring flat | 3.8 mm = 19 layers | cut on a layer boundary so the first layer is a full-width track |
| coupon engraving | 0.6 mm = 3 layers | no partial layer at the bottom of the text |

If you change nozzle or layer height, change `nozzle_d`, `line_w` and
`layer_h` at the top of `cad/params.scad` and those features follow.

## Orientation

Print everything exactly as exported. The frame goes ring down on its flat.
The sensor puck is exported ears-down, skin side up, so its sew ears sit on
the bed. If the slicer auto-orients a part, undo that.

## What to expect

| size | hair allowance | footprint | solid volume | sliced, with supports |
|------|----------------|-----------|--------------|-----------------------|
| 620 mm | 7.2 mm | 207 x 217 mm | 91 cm³ | 128 g |
| 660 mm | 13.5 mm | 219 x 229 mm | 97 cm³ | 137 g |
| 700 mm | 19.9 mm | 231 x 242 mm | 102 cm³ | 145 g |
| 740 mm | 26.3 mm | 243 x 254 mm | 108 cm³ | 154 g |

The last column is a real slice of each file: PrusaSlicer, 0.2 mm layers,
4 walls, 15% gyroid, organic supports from the build plate, 5 mm brim, PETG.
Every one came back `manifold = yes`, one part. PrusaSlicer's generic speeds
put each at 15 to 18 hours, which is far slower than an H2D actually runs, so
take the time from Bambu Studio and the grams from here.

The small parts slice with no supports and no warnings: electrode holder
3 g, sensor puck 2 g, pod base 15 g, pod lid 9 g, fit coupon 5 g.

All four is a bit over half a spool. Print **660 and
700 first**: they bracket the likeliest fit, and if one of them sits right
the other two never need printing.

## Known mesh state

OpenSCAD's export is watertight and single-shell, which is what a slicer
needs, but its interior is untidy: a quarter of the triangles are exact
duplicates and a third of edges are shared by four or more faces. This is
harmless, and attempts to clean it up made it worse by tearing holes — see
docs/DESIGN_NOTES.md. If Bambu Studio offers to repair the model, let it.
