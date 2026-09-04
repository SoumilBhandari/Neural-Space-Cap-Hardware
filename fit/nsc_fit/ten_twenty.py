"""International 10-20 electrode positions for a measured head.

The 10-20 system places electrodes at fixed percentages along arcs between
four bony landmarks — nasion, inion, and the two preauricular points — so the
same site name lands on the same piece of cortex across different skulls. That
is the whole point: O1 on one person and O1 on another are comparable.

Which sites matter for this project:

    O1, O2, Oz   Occipital. Where alpha lives. These are the electrodes that
                 make the eyes-closed / eyes-open validation test work, and
                 the Spring team never had them.
    Fp1, Fp2     Frontal pole. Easy to place, no hair, but they see every
                 blink and eye movement. Useful as artifact references.
    C3, Cz, C4   Central. Motor activity.
    T7, T8       Temporal. Also where jaw clenching shows up.

A minimal useful montage for this build is O1, O2, Fp1, plus a reference at
the mastoid or earlobe. Start there.

Approximations, stated plainly: positions on the midline and coronal chains
are exact percentages of the measured arcs. The lateral chain runs along a
horizontal loop taken at the mean height of Fpz and Oz, which is the usual
tape-measure practice. Sites the standard defines as lying between two others
(F3, F4, P3, P4) are placed at the surface midpoint of their neighbours. All
are within a few millimetres, which is inside the tolerance of a fabric cap.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .head import Head

# Fractions along the nasion-to-inion arc, measured from the nasion.
MIDLINE = {"Fpz": 0.10, "Fz": 0.30, "Cz": 0.50, "Pz": 0.70, "Oz": 0.90}

# Fractions along the left-to-right preauricular arc, from the left ear.
CORONAL = {"T7": 0.10, "C3": 0.30, "Cz": 0.50, "C4": 0.70, "T8": 0.90}

# Fractions around the horizontal loop from Fpz, going toward the subject's
# left. The right side mirrors these.
LATERAL_LEFT = {"Fp1": 0.05, "F7": 0.15, "T7": 0.25, "P7": 0.35, "O1": 0.45}
LATERAL_RIGHT = {"Fp2": 0.05, "F8": 0.15, "T8": 0.25, "P8": 0.35, "O2": 0.45}

# Sites the standard defines as lying between two others.
INTERPOLATED = {"F3": ("F7", "Fz"), "F4": ("F8", "Fz"), "P3": ("P7", "Pz"), "P4": ("P8", "Pz")}

# The smallest montage that supports the alpha-blocking validation test.
MINIMAL_MONTAGE = ("O1", "O2", "Fp1")


@dataclass(frozen=True)
class Site:
    """One electrode position."""

    name: str
    xyz_mm: np.ndarray
    arc: str  # which measured arc it is marked along
    distance_mm: float  # distance along that arc from its start landmark

    @property
    def hemisphere(self) -> str:
        if self.name.endswith("z"):
            return "midline"
        return "left" if int(self.name[-1]) % 2 == 1 else "right"


def montage(head: Head) -> dict[str, Site]:
    """Compute every 10-20 site this project uses, for a fitted head."""
    sites: dict[str, Site] = {}

    sagittal = head.sagittal_arc()
    sag_len = sagittal.length_mm()
    for name, fraction in MIDLINE.items():
        sites[name] = Site(name, sagittal.at_fraction(fraction), "sagittal", fraction * sag_len)

    coronal = head.coronal_arc()
    cor_len = coronal.length_mm()
    for name, fraction in CORONAL.items():
        if name == "Cz":
            continue  # Already placed from the sagittal arc; the two agree exactly.
        sites[name] = Site(name, coronal.at_fraction(fraction), "coronal", fraction * cor_len)

    # The lateral loop is taken at the mean height of Fpz and Oz, which is what
    # a tape measured "through Fpz and Oz" actually follows.
    z_ref = float((sites["Fpz"].xyz_mm[2] + sites["Oz"].xyz_mm[2]) / 2.0)
    loop = head.circumference_arc(z_ref)
    loop_len = loop.length_mm()

    for name, fraction in LATERAL_LEFT.items():
        if name in sites:
            continue  # T7 is already fixed by the coronal arc, which is exact.
        sites[name] = Site(name, loop.at_fraction(fraction), "circumference", fraction * loop_len)
    for name, fraction in LATERAL_RIGHT.items():
        if name in sites:
            continue
        # Same distance from Fpz, the other way round the loop.
        sites[name] = Site(
            name, loop.at_fraction(1.0 - fraction), "circumference", fraction * loop_len
        )

    for name, (left, right) in INTERPOLATED.items():
        midpoint = (sites[left].xyz_mm + sites[right].xyz_mm) / 2.0
        sites[name] = Site(name, head.project_to_surface(midpoint), "interpolated", float("nan"))

    return sites


def as_rows(sites: dict[str, Site]) -> list[dict[str, object]]:
    """Flatten a montage into rows for CSV export or a CAD import."""
    rows = []
    for name in sorted(sites):
        site = sites[name]
        x, y, z = site.xyz_mm
        rows.append(
            {
                "site": name,
                "hemisphere": site.hemisphere,
                "x_mm": round(float(x), 2),
                "y_mm": round(float(y), 2),
                "z_mm": round(float(z), 2),
                "marked_along": site.arc,
                "distance_mm": round(site.distance_mm, 1) if site.distance_mm == site.distance_mm else "",
            }
        )
    return rows


def lateral_loop(head: Head, sites: dict[str, Site]) -> "tuple[float, float]":
    """Height and length of the horizontal loop the lateral chain is marked on.

    This loop is shorter than the measured head circumference, because it sits
    at Fpz/Oz height rather than down at the nasion. The template needs the
    loop's own length, not the circumference, or every lateral tick lands in
    the wrong place.
    """
    z_ref = float((sites["Fpz"].xyz_mm[2] + sites["Oz"].xyz_mm[2]) / 2.0)
    return z_ref, head.circumference_arc(z_ref).length_mm()


def fit_residual_mm(head: Head, sites: dict[str, Site]) -> float:
    """How far the model disagrees with itself about where T7 belongs.

    The 10-20 standard fixes T7 twice over: 10% up the coronal arc, and 25%
    around the lateral loop. On a real skull those coincide by construction. On
    an ellipsoid fitted to three numbers they land a millimetre or two apart,
    and how far apart is a direct measure of how ellipsoid-like this particular
    head is.

    Under about 5 mm, mark from the template and stop worrying. Above that,
    the head deviates enough from the model that the lateral sites should be
    marked by tape from the landmarks directly, not read off the template.
    """
    z_ref, _ = lateral_loop(head, sites)
    from_loop = head.circumference_arc(z_ref).at_fraction(LATERAL_LEFT["T7"])
    return float(np.linalg.norm(sites["T7"].xyz_mm - from_loop))
