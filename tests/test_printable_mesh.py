"""The meshes this code writes have to survive a slicer, not just OpenSCAD.

Each of these pins down something that sent a frame to the printer broken:
the scan head exported inside out, band tubes with open ends, and parts whose
first layer was not on the bed.
"""

import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from nsc_fit import meshcheck, scad_export, scanned

ROOT = Path(__file__).resolve().parents[1]


def dome(radius_mm=90.0):
    """A plain hemisphere standing in for a scan, so no real head is needed."""
    grid = np.full((scanned.THETA_STEPS, scanned.PHI_STEPS), radius_mm)
    return scanned.ScannedHead(grid, np.zeros(3), radius_mm)


def test_scan_head_is_exported_right_side_out(tmp_path):
    """Subtracting an inside-out head left 45,000 doubled vertices in the frame."""
    verts, faces = dome().inflated_mesh(4.0)
    assert scanned._signed_volume(verts, faces) > 0

    report = meshcheck.check(dome().write_stl(tmp_path / "head.stl", 4.0))
    assert report.printable, report.verdict


@pytest.mark.parametrize("closed", [True, False])
def test_band_tube_is_one_closed_solid(tmp_path, closed):
    angle = np.linspace(0, 2 * np.pi if closed else np.pi, 60, endpoint=not closed)
    path = np.column_stack([80 * np.cos(angle), 80 * np.sin(angle), 20 + 0 * angle])
    verts, faces = scad_export.tube_mesh(path, 5.0, closed=closed)
    report = meshcheck.check(scad_export.write_binary_stl(tmp_path / "tube.stl", verts, faces))
    assert report.printable, report.verdict
    assert report.volume_cm3 > 0


def test_ring_height_lookup_lands_on_the_requested_plane():
    """The ring is planar so it can sit on the bed; every point must be at one z."""
    scan = dome()
    for phi in np.linspace(0, 2 * np.pi, 12, endpoint=False):
        point = scan.point_at_height(phi, 25.0, standoff=6.0)
        assert point[2] == pytest.approx(25.0, abs=0.05)
        assert np.hypot(point[0], point[1]) > 80


@pytest.mark.skipif(shutil.which("openscad") is None, reason="needs OpenSCAD")
@pytest.mark.parametrize("source, defines", [
    ("electrode_holder.scad", []),
    ("sensor_puck.scad", []),
    ("electronics_pod.scad", ["-D", 'part="base"']),
    ("electronics_pod.scad", ["-D", 'part="lid"']),
    ("cap_frame.scad", ["-D", 'part="coupon"']),
])
def test_small_parts_print_flat_without_support(tmp_path, source, defines):
    out = tmp_path / "part.stl"
    subprocess.run(["openscad", "--export-format", "binstl", *defines, "-o", str(out),
                    str(ROOT / "cad" / source)], check=True, capture_output=True)
    report = meshcheck.check(out)
    assert report.printable, report.verdict
    assert report.first_layer_mm2 > 100
    assert report.overhang_pct < 2.0
