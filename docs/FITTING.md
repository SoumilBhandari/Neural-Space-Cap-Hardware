# Fitting the cap to a head

Twenty minutes, once per subject. Two people: one measures, one records.

## The four landmarks

Find these by feel, not by eye. Marking them with a skin pencil first makes
every later step repeatable.

- **Nasion** — the dip at the top of the nose, between the eyebrows.
- **Inion** — the bump at the back of the skull, where it meets the neck. Run
  a thumb up the back of the neck until it stops.
- **Preauricular points** — the small notch directly in front of each ear
  canal. Ask the subject to open and close their jaw; the notch is the dent
  that stays still while the jaw moves.

Every measurement and every electrode position is defined from these four. If
they are found sloppily, nothing downstream is repeatable, and two sessions on
the same person will not be comparable.

## The three measurements

All in millimetres, tape snug but not tight, hair flattened under it.

1. **Circumference** — around the head through the nasion, both preauricular
   points, and the inion. This sits lower than a hat band, and will read a
   centimetre or two under a hat size. That is expected.
2. **Nasion to inion** — front to back, straight over the top of the head.
   Keep the tape on the midline; letting it drift to one side is the most
   common error.
3. **Ear to ear** — left preauricular point, over the vertex, to the right
   preauricular point.

Take each one twice. If the two readings differ by more than 5 mm, take it a
third time — a bad measurement here moves every electrode.

## Generating the template

```bash
make fit SUBJECT="subject A" CIRC=570 NI=370 PA=350
```

This writes into `build/`:

- `*_marking_template_p1.svg` — print at 100%, do not scale to fit
- `*_montage_map.svg` — the montage as a diagram, for the poster
- `*_positions.csv` — 3D coordinates for the CAD

The tool prints a **fit residual**. The 10-20 system fixes T7 twice over, by
two different arcs, and the residual is how far apart those two definitions
land on this particular head. Under 5 mm, use the template. Above it, the head
deviates enough from the model that the lateral sites should be marked with a
tape from the landmarks directly.

The tool also rejects measurements that are not head-shaped, which catches the
error that actually happens — entering centimetres, or a tape that slipped off
the vertex.

## Marking the head

1. Print page one. **Measure the 100 mm ruler on the printout before cutting.**
   If it is not 100 mm, the print scaled and every tick is wrong.
2. Cut out the three strips along the solid lines. Join the segments at the
   matching letters, overlapping to the dashed fold mark.
3. Midline strip: start at the nasion, run over the vertex, end at the inion.
   Mark through each tick.
4. Coronal strip: left preauricular point to right, over the vertex. The Cz
   tick must land on the Cz already marked from the midline strip. If it
   misses by more than about 5 mm, one of the two strips is off the midline —
   redo both rather than splitting the difference.
5. Lateral strip: start at the Fpz mark, wrap around the head at that level,
   and finish back at Fpz.

That Cz cross-check in step 4 is the one place the method catches its own
mistakes. Do not skip it.

## Which sites to fit

For this build, three: **O1, O2, Fp1**, plus a reference electrode on the
mastoid or an earlobe clip.

O1 and O2 are the ones that matter. Alpha lives at the back of the head, and
the eyes-closed / eyes-open validation test is what tells the team whether the
EEG is measuring a brain or measuring the building's wiring. Fp1 is easy to
place, sits on bare skin, and sees every blink — which makes it useful for
recognising and rejecting eye-movement artifacts in the other channels.

Add more sites only after those three record clean data.
