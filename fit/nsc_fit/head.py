"""A head model built from three tape-measure numbers.

The head is modelled as the upper half of an ellipsoid, centred on the plane
that contains the nasion, the inion, and both preauricular points:

    x  left-right, +x toward the right ear
    y  front-back, +y toward the nose
    z  up, +z toward the vertex

Three semi-axes (a, b, c) are solved so the model's own arc lengths match the
three measurements taken on the actual head. That is what makes positions
computed on the model land on the right places on the person.

An ellipsoid is not a head. It has no brow, no occipital bump, and perfect
left-right symmetry. For placing electrode holders on a fabric cap, where a
few millimetres of give exists anyway, it is close enough — and it is honest
about what it is, which a hand-drawn template is not.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares
from scipy.special import ellipe

# Resolution of the arc-length tables. 4000 steps over a half-ellipse puts the
# interpolation error far below the millimetre that matters here.
_ARC_STEPS = 4000


@dataclass(frozen=True)
class Measurements:
    """The three numbers to take with a tape measure, in millimetres.

    circumference_mm
        Around the head through the nasion, both preauricular points, and the
        inion. Deliberately the same four landmarks as the other two
        measurements, so whoever holds the tape only has to find them once.
        Note this sits lower than a hat-band measurement and will read a
        centimetre or two smaller than a hat size.
    nasion_inion_mm
        From the nasion (the dip between the eyes) back over the vertex to the
        inion (the bump at the base of the skull).
    preauricular_mm
        From the notch just in front of the left ear, over the vertex, to the
        same notch in front of the right ear.

    See docs/FITTING.md for how to take each one.
    """

    circumference_mm: float
    nasion_inion_mm: float
    preauricular_mm: float

    def __post_init__(self) -> None:
        # Plausible ranges for a human head, in millimetres. These are wide
        # enough to cover any team member and narrow enough to catch the
        # mistake that actually happens: typing 57 for 570, or handing the
        # tool inches. A bad measurement caught here costs a re-measure; one
        # caught later costs a printed template and a cut cap.
        for name, value, lo, hi in (
            ("circumference_mm", self.circumference_mm, 400.0, 700.0),
            ("nasion_inion_mm", self.nasion_inion_mm, 250.0, 500.0),
            ("preauricular_mm", self.preauricular_mm, 250.0, 500.0),
        ):
            if not lo <= value <= hi:
                raise ValueError(
                    f"{name} = {value} is outside the plausible range {lo:.0f}-{hi:.0f} mm. "
                    "Measurements are in millimetres — check for a units mix-up."
                )

        # Each over-the-vertex arc should be roughly 55-75% of the
        # circumference. Outside that, one of the three was taken along the
        # wrong path — usually the tape slipping off the vertex.
        for name, arc in (
            ("nasion_inion_mm", self.nasion_inion_mm),
            ("preauricular_mm", self.preauricular_mm),
        ):
            ratio = arc / self.circumference_mm
            if not 0.50 <= ratio <= 0.80:
                raise ValueError(
                    f"{name} is {ratio:.0%} of the circumference, which is not a head shape. "
                    "Re-take all three measurements over the vertex."
                )


@dataclass(frozen=True)
class Head:
    """An ellipsoid head, fitted to a set of measurements."""

    a_mm: float  # semi-axis, left-right
    b_mm: float  # semi-axis, front-back
    c_mm: float  # semi-axis, vertical
    measurements: Measurements

    def sagittal_arc(self) -> "Arc":
        """Nasion over the vertex to the inion, in the x = 0 plane."""
        return Arc(
            point=lambda t: np.array([0.0, self.b_mm * np.cos(t), self.c_mm * np.sin(t)]),
            speed=lambda t: np.hypot(self.b_mm * np.sin(t), self.c_mm * np.cos(t)),
            t0=0.0,
            t1=math.pi,
        )

    def coronal_arc(self) -> "Arc":
        """Left preauricular over the vertex to the right, in the y = 0 plane."""
        return Arc(
            point=lambda t: np.array([-self.a_mm * np.cos(t), 0.0, self.c_mm * np.sin(t)]),
            speed=lambda t: np.hypot(self.a_mm * np.sin(t), self.c_mm * np.cos(t)),
            t0=0.0,
            t1=math.pi,
        )

    def circumference_arc(self, z_mm: float) -> "Arc":
        """The horizontal loop around the head at height ``z_mm``.

        Starts at the front (+y) and runs anticlockwise seen from above, which
        is toward the subject's left. The 10-20 lateral chain is laid out along
        this loop.
        """
        scale = math.sqrt(max(1.0 - (z_mm / self.c_mm) ** 2, 1e-9))
        a, b = self.a_mm * scale, self.b_mm * scale
        return Arc(
            point=lambda t: np.array([-a * np.sin(t), b * np.cos(t), z_mm]),
            speed=lambda t: np.hypot(a * np.cos(t), b * np.sin(t)),
            t0=0.0,
            t1=2 * math.pi,
        )

    def project_to_surface(self, point: np.ndarray) -> np.ndarray:
        """Push a point radially onto the ellipsoid surface.

        Used to place electrodes that the 10-20 system defines as lying between
        two others: take the midpoint of the pair and lift it back onto the
        head, rather than leaving it floating inside.
        """
        axes = np.array([self.a_mm, self.b_mm, self.c_mm])
        norm = np.linalg.norm(point / axes)
        if norm == 0:
            return np.array([0.0, 0.0, self.c_mm])
        return point / norm


@dataclass(frozen=True)
class Arc:
    """A planar curve on the head, queryable by distance travelled along it."""

    point: object  # Callable[[float], np.ndarray]
    speed: object  # Callable[[float], float], |d(point)/dt|
    t0: float
    t1: float

    def length_mm(self) -> float:
        ts, lengths = self._table()
        return float(lengths[-1])

    def at_fraction(self, fraction: float) -> np.ndarray:
        """Point at ``fraction`` of the way along the arc, 0.0 to 1.0."""
        return self.at_distance(fraction * self.length_mm())

    def at_distance(self, distance_mm: float) -> np.ndarray:
        """Point at ``distance_mm`` measured along the curve from its start."""
        ts, lengths = self._table()
        t = float(np.interp(distance_mm, lengths, ts))
        return np.asarray(self.point(t), dtype=float)

    def _table(self) -> tuple[np.ndarray, np.ndarray]:
        ts = np.linspace(self.t0, self.t1, _ARC_STEPS)
        speeds = np.array([self.speed(t) for t in ts])
        # Cumulative trapezoid, starting at zero.
        steps = np.diff(ts) * 0.5 * (speeds[:-1] + speeds[1:])
        lengths = np.concatenate([[0.0], np.cumsum(steps)])
        return ts, lengths


def ellipse_perimeter(p: float, q: float) -> float:
    """Exact perimeter of an ellipse with semi-axes ``p`` and ``q``."""
    major, minor = max(p, q), min(p, q)
    if major == 0:
        return 0.0
    eccentricity_sq = 1.0 - (minor / major) ** 2
    return float(4.0 * major * ellipe(eccentricity_sq))


def fit(measurements: Measurements) -> Head:
    """Solve for the ellipsoid whose arcs match the measured head.

    Three equations, three unknowns:

        full perimeter of the (a, b) ellipse  == circumference
        half perimeter of the (b, c) ellipse  == nasion-inion arc
        half perimeter of the (a, c) ellipse  == preauricular arc

    Solved numerically because ellipse perimeters have no elementary inverse.
    """
    m = measurements

    def residuals(axes: np.ndarray) -> np.ndarray:
        a, b, c = np.abs(axes)
        return np.array(
            [
                ellipse_perimeter(a, b) - m.circumference_mm,
                0.5 * ellipse_perimeter(b, c) - m.nasion_inion_mm,
                0.5 * ellipse_perimeter(a, c) - m.preauricular_mm,
            ]
        )

    # Start from a sphere of the right circumference; the solve is well
    # behaved from there for any plausible head.
    guess = m.circumference_mm / (2 * math.pi)
    solution = least_squares(residuals, x0=np.array([guess, guess, guess]), method="lm")

    a, b, c = np.abs(solution.x)
    if not solution.success or max(abs(residuals(solution.x))) > 1.0:
        raise ValueError(
            "no ellipsoid fits these measurements within 1 mm. "
            "Check that all three were taken over the vertex and re-measure."
        )
    return Head(a_mm=float(a), b_mm=float(b), c_mm=float(c), measurements=m)
