"""The generated OpenSCAD must contain what cap_frame.scad expects."""

import re

import numpy as np
import pytest

from nsc_fit import head, scad_export, ten_twenty


@pytest.fixture
def generated(tmp_path):
    fitted = head.fit(head.Measurements(570, 370, 350))
    sites = ten_twenty.montage(fitted)
    path = scad_export.write_head_params(fitted, sites, tmp_path / "head_params.scad")
    return fitted, sites, path.read_text()


def test_every_symbol_the_frame_uses_is_defined(generated):
    """cap_frame.scad reads these by name; a missing one silently becomes undef."""
    _, _, text = generated
    for symbol in (
        "head_axes",
        "band_lateral",
        "band_sagittal",
        "band_coronal",
        "mount_O1",
        "mount_O2",
        "mount_Fp1",
        "pod_anchor",
    ):
        assert re.search(rf"^{symbol} = ", text, re.M), f"{symbol} missing"


def test_the_lateral_ring_closes(generated):
    """An open ring leaves a gap one step wide that no one notices until slicing."""
    _, _, text = generated
    points = _points(text, "band_lateral")
    assert points[0] == pytest.approx(points[-1], abs=1e-6)


def test_band_points_lie_on_the_head(generated):
    fitted, _, text = generated
    axes = np.array([fitted.a_mm, fitted.b_mm, fitted.c_mm])
    for band in ("band_lateral", "band_sagittal", "band_coronal"):
        for point in _points(text, band):
            assert np.sum((point / axes) ** 2) == pytest.approx(1.0, abs=1e-3)


def test_mount_rotations_point_outward(generated):
    """rotate([0, elevation, azimuth]) must map +Z onto the outward normal."""
    fitted, sites, text = generated
    axes = np.array([fitted.a_mm, fitted.b_mm, fitted.c_mm])
    for name in ("O1", "O2", "Fp1"):
        position, rotation = _mount(text, f"mount_{name}")
        elevation, azimuth = np.radians(rotation[1]), np.radians(rotation[2])
        rotated = np.array(
            [
                np.sin(elevation) * np.cos(azimuth),
                np.sin(elevation) * np.sin(azimuth),
                np.cos(elevation),
            ]
        )
        expected = position / axes**2
        expected = expected / np.linalg.norm(expected)
        assert rotated == pytest.approx(expected, abs=1e-3)
        assert position == pytest.approx(sites[name].xyz_mm, abs=1e-3)


def _points(text: str, name: str) -> np.ndarray:
    triples = _triples(text, name)
    return np.array([[float(v) for v in t.split(",")] for t in triples])


def _mount(text: str, name: str) -> tuple[np.ndarray, np.ndarray]:
    position, rotation = _triples(text, name)[:2]
    return (
        np.array([float(v) for v in position.split(",")]),
        np.array([float(v) for v in rotation.split(",")]),
    )


def _triples(text: str, name: str) -> list[str]:
    """The innermost bracketed groups of an OpenSCAD vector assignment."""
    body = re.search(rf"^{name} = (\[.*\]);$", text, re.M).group(1)
    return re.findall(r"\[([^\[\]]+)\]", body.replace(" ", ""))
