"""The fitted head must reproduce the measurements it was fitted from."""

import math

import numpy as np
import pytest

from nsc_fit import head


@pytest.mark.parametrize(
    "circ,ni,pa",
    [(500, 330, 320), (540, 350, 340), (570, 370, 350), (600, 390, 375), (620, 400, 385)],
)
def test_fit_reproduces_the_measurements(circ, ni, pa):
    """Round-trip: measure the model and get the input numbers back."""
    fitted = head.fit(head.Measurements(circ, ni, pa))
    assert head.ellipse_perimeter(fitted.a_mm, fitted.b_mm) == pytest.approx(circ, abs=1.0)
    assert fitted.sagittal_arc().length_mm() == pytest.approx(ni, abs=1.0)
    assert fitted.coronal_arc().length_mm() == pytest.approx(pa, abs=1.0)


def test_a_symmetric_head_comes_out_symmetric():
    """Equal front-back and ear-to-ear arcs must give a circular plan view."""
    fitted = head.fit(head.Measurements(560, 360, 360))
    assert fitted.a_mm == pytest.approx(fitted.b_mm, abs=0.5)


def test_arc_fractions_are_monotonic_and_land_on_the_surface():
    fitted = head.fit(head.Measurements(570, 370, 350))
    arc = fitted.sagittal_arc()
    previous = None
    for f in np.linspace(0.0, 1.0, 11):
        point = arc.at_fraction(f)
        on_surface = (
            (point[0] / fitted.a_mm) ** 2
            + (point[1] / fitted.b_mm) ** 2
            + (point[2] / fitted.c_mm) ** 2
        )
        assert on_surface == pytest.approx(1.0, abs=1e-6)
        if previous is not None:
            assert point[1] < previous[1]  # travelling from the nose backwards
        previous = point


def test_ellipse_perimeter_matches_a_circle():
    assert head.ellipse_perimeter(50, 50) == pytest.approx(2 * math.pi * 50)


def test_nonsense_measurements_are_rejected():
    with pytest.raises(ValueError):
        head.Measurements(-1, 360, 360)


def test_centimetres_are_caught():
    """The mistake that actually happens: 57 typed instead of 570."""
    with pytest.raises(ValueError, match="units"):
        head.Measurements(57, 37, 35)


def test_inconsistent_arcs_are_caught():
    """A tape that slipped off the vertex gives an arc that is not head-shaped."""
    with pytest.raises(ValueError, match="not a head shape"):
        head.Measurements(560, 260, 360)
