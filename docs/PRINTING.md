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

## Why the frame has feet

The frame is a swept tube following a curved path, so no surface on it is
flat. Laid ring-down it meets the plate at a single tangent point with
**0.0 mm² of first-layer area**, which no brim can save because there is
nothing for a brim to hold on to. That is the usual reason a generated model
simply refuses to print.

It now carries eight sacrificial feet: 18 mm pads cut flat against the same
plane that trims the frame, tapering to a 3.5 mm neck. That gives
**2032 mm² of first layer** across eight well-spread pads, and the part's
centre of mass sits inside them, so it cannot rock or tip.

Snip the necks with flush cutters after printing and sand the eight stubs.
They are on the underside of the ring where nothing touches the head.

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

**Tree supports, build-plate-only.** 16% of the surface overhangs past 45
degrees: the undersides of both arches and the socket bosses. Organic
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
| foot pad | 0.60 mm = 3 layers | no partial top layer |
| foot neck | 2.52 mm = 6 lines | flush cutters go through in one squeeze; 3.5 mm took real force and risked marking the band |

If you change nozzle or layer height, change `nozzle_d`, `line_w` and
`layer_h` at the top of `cad/params.scad` and those features follow.

## Orientation

Print it exactly as exported — ring down, feet on the plate. The feet are cut
flat in that orientation and in no other. If the slicer auto-orients it, undo
that.

## What to expect

| size | hair allowance | footprint | solid volume |
|------|----------------|-----------|--------------|
| 620 mm | 7.2 mm | 215 x 223 mm | 191 cm³ |
| 660 mm | 13.5 mm | 225 x 236 mm | 203 cm³ |
| 700 mm | 19.9 mm | 237 x 248 mm | 216 cm³ |
| 740 mm | 26.3 mm | 247 x 261 mm | 228 cm³ |

Those are solid volumes. With 4 walls and 15% infill the part itself comes to
roughly 120 cm³, about 150 g, and tree supports add a good fraction again on
top. **Budget 6 to 9 hours each at 0.4 mm and 0.2 mm layers** — let the
slicer give you the real figure before you commit.

All four is most of a spool and the better part of two days. Print **660 and
700 first**: they bracket the likeliest fit, and if one of them sits right
the other two never need printing.

## Known mesh state

OpenSCAD's export is watertight and single-shell, which is what a slicer
needs, but its interior is untidy: a quarter of the triangles are exact
duplicates and a third of edges are shared by four or more faces. This is
harmless, and attempts to clean it up made it worse by tearing holes — see
docs/DESIGN_NOTES.md. If Bambu Studio offers to repair the model, let it.
