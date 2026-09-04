"""Montage geometry: symmetry, ordering, and the model's own consistency."""

import numpy as np
import pytest

from nsc_fit import head, ten_twenty


@pytest.fixture
def sites():
    return ten_twenty.montage(head.fit(head.Measurements(570, 370, 350)))


def test_left_and_right_sites_mirror_each_other(sites):
    for left, right in [("O1", "O2"), ("Fp1", "Fp2"), ("T7", "T8"), ("C3", "C4"), ("P3", "P4")]:
        mirrored = sites[left].xyz_mm * np.array([-1, 1, 1])
        assert mirrored == pytest.approx(sites[right].xyz_mm, abs=0.5)


def test_midline_sites_sit_on_the_midline(sites):
    for name in ("Fpz", "Fz", "Cz", "Pz", "Oz"):
        assert sites[name].xyz_mm[0] == pytest.approx(0.0, abs=1e-6)


def test_cz_is_the_vertex(sites):
    """Cz is fixed twice over, by both measured arcs, and they must agree."""
    fitted = head.fit(head.Measurements(570, 370, 350))
    from_sagittal = fitted.sagittal_arc().at_fraction(0.5)
    from_coronal = fitted.coronal_arc().at_fraction(0.5)
    assert from_sagittal == pytest.approx(from_coronal, abs=0.01)
    assert sites["Cz"].xyz_mm == pytest.approx(from_sagittal, abs=0.01)


def test_midline_runs_front_to_back_in_order(sites):
    order = [sites[n].xyz_mm[1] for n in ("Fpz", "Fz", "Cz", "Pz", "Oz")]
    assert order == sorted(order, reverse=True)


def test_occipital_sites_are_behind_the_centre(sites):
    """The alpha-blocking test depends on O1 and O2 actually being occipital."""
    for name in ten_twenty.MINIMAL_MONTAGE:
        assert name in sites
    assert sites["O1"].xyz_mm[1] < 0
    assert sites["O2"].xyz_mm[1] < 0
    assert sites["Fp1"].xyz_mm[1] > 0


def test_hemisphere_labels():
    fitted = head.fit(head.Measurements(560, 360, 360))
    s = ten_twenty.montage(fitted)
    assert s["O1"].hemisphere == "left"
    assert s["O2"].hemisphere == "right"
    assert s["Oz"].hemisphere == "midline"


@pytest.mark.parametrize(
    "circ,ni,pa", [(500, 330, 320), (540, 350, 340), (570, 370, 350), (620, 400, 385)]
)
def test_model_agrees_with_itself_about_t7(circ, ni, pa):
    """T7 is over-determined; the disagreement is the model's error bar.

    Above 5 mm the tool tells the operator to mark by tape instead, so the
    value has to stay small across the range of heads we expect to fit.
    """
    fitted = head.fit(head.Measurements(circ, ni, pa))
    s = ten_twenty.montage(fitted)
    assert ten_twenty.fit_residual_mm(fitted, s) < 5.0
