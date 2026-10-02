# Design notes

Why the parts are shaped the way they are, and what is still unverified.

## The head model is an ellipsoid, and says so

Three tape measurements solve for three semi-axes, so the model reproduces the
arcs it was fitted from exactly. It has no brow, no occipital bump, and perfect
left-right symmetry, none of which a real head has.

That is a defensible approximation for placing holders on a fabric cap, which
has a few millimetres of give anyway. What makes it honest rather than sloppy
is that the tool reports its own error: the 10-20 standard fixes T7 twice over,
by two different arcs, and how far apart those land is a direct measure of how
ellipsoid-like this particular head is. Across the range of heads tested it
comes out at 1-2 mm. Above 5 mm the tool tells the operator to stop trusting it
and mark by tape.

## Why a spider spring and not a foam pad

The obvious way to hold an electrode against a scalp is a foam pad and a tight
cap. It does not work well: cap tension varies with how the cap is put on, it
is different at every site, and it drops as the fabric relaxes over a session.
The failure is silent — the recording just gets noisier.

The spider spring decouples contact pressure from cap tension. The rim is sewn
to the fabric, the hub floats on three spiral arms, and the arms set the load.
Every site gets the same pressure, and it stays the same for as long as the
subject wears it.

It also prints flat with no supports and no overhangs, which matters when the
team will print a dozen of them and iterate on the spring rate.

## The frame is generated, and that is the point

Nothing about the frame is drawn by hand. Three tape measurements produce an
ellipsoid, the ellipsoid produces the 10-20 arcs, and the arcs produce the band
paths that the frame sweeps along. A different head gives a different frame
from the same source file.

That is worth the extra machinery for one reason: a frame drawn once to fit one
person's head is a frame that fits one person. The team has six members and
will want to record more than one of them.

The mount rotations come out of the same model. The outward normal of an
ellipsoid at a point is just the gradient, and `nsc_fit` converts it into the
two rotations that stand an OpenSCAD cylinder up along it, so every electrode
socket points straight out of the skull rather than being eyeballed.

## The montage is the team's, not the textbook's

The frame carries the eight sites the team specified: Fpz, F3, F4, C3, Cz, C4,
P3 and P4. Three of those — F4, Cz and P3 — are wired first while the circuit
is a single channel, and their sockets stand 2.5 mm proud of the others so they
can be found by hand without a drawing.

Carrying them needed two more arches. F3, F4, P3 and P4 sit on neither the ring
nor either original arch, so the frame gained the standard frontal
(F7-F3-Fz-F4-F8) and parietal (P7-P3-Pz-P4-P8) chains. Both land on the ring at
their ends, so they brace it rather than hanging off it.

Those two chains are not planar ellipses — F3 and P3 are defined as lying
between two other sites, so the curve through them has no closed form.
Interpolating in a plane and projecting afterwards would sag the path inside
the skull between control points, so the path is interpolated on a unit sphere,
where the shortest route between two points is a great-circle arc with an exact
formula, and mapped back onto the ellipsoid afterwards.

## The phase-one marker moved twice

First attempt: a sphere on the side of the socket boss, at boss_d/2 - 1.5.
That is inside the boss radius, so it rendered, existed in the mesh, and was
completely invisible and unfeelable.

Second attempt: the same sphere at boss_d/2 + 0.5, standing proud. That works
at some sockets and not others, because the nub points along whatever direction
the socket's local frame happens to face, and at Fpz and Cz that is straight
into a band.

What is there now: a collar extending along the socket axis, away from the
skull, where no band ever reaches. `tests/test_frame_geometry.py` measures
axial reach to confirm it, because a radial measurement cannot tell a collar
from the band the socket is sitting on.

## Splitting the frame is not solved

The frame is 172 x 202 x 128 mm, which fits a 220 mm bed but not every printer,
and it needs supports under both arches.

The obvious fix — cut it in half — does not work. The sagittal arch lies
exactly in the x = 0 plane and the coronal arch lies exactly in y = 0, so a cut
on either plane runs down an arch lengthwise and produces two half-pipes rather
than two halves of a frame. The first version of this part did exactly that.

Splitting it properly means cutting transversely at the four band junctions and
designing real joints there. Until that exists, print it whole.

## What the pod is not

It is a prototype enclosure, not a flight part. It is not sealed, not
shielded, and not rated for anything. It exists so the electronics stop being a
breadboard hanging off the back of someone's head, and so the demo looks like a
device rather than a science-fair project.

If shielding turns out to be needed — Dr. Porterfield suggested better
front-end filtering as the alternative to the team's foil Faraday cage — a
conductive coating on the inside of the shell, tied to the analog ground, is
the cheapest thing to try next.

## Open questions

- **Print tolerances are unverified.** Everything in `params.scad` came from
  datasheets and typical values, not from the team's printer. Print a coupon.
- **Spring rate is a guess.** `spring_t = 0.8` at 0.2 mm layers should give a
  comfortable press, but nobody has measured the force. Print three at 0.6,
  0.8 and 1.0 and pick by feel against a scalp.
- **Cable routing is not designed.** The pod has a gland and the holders have
  slots, but the path between them across the cap is not planned. Every wire
  that failed last semester failed where it left a connector unsupported.
- **Frame stiffness is untested.** An 11 mm swept band in PETG should be stiff
  enough for a ring braced by two arches, but nobody has worn one. If it flexes,
  the cheap fix is a wider band before a thicker one.
- **The frame and the sprung holder mount differently.** The holder has a sewn
  rim for a fabric cap; the frame has a press-fit socket. Both cannot be the
  answer, and which one wins should be decided after the first fit test.
- **The cap itself is not in this repository.** The fabric pattern, the sewing,
  and the head measurements from Spring are Jia's CAD work. This repository
  covers where things go on the cap and what holds them.
