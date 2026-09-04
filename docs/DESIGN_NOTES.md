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
