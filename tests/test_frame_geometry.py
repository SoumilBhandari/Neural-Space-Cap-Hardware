"""Checks against the rendered frame STL, not just the generated numbers.

These catch a class of mistake the data-level tests cannot see: geometry that
is present in the model but swallowed by other geometry. The index nub on the
phase-one sockets was originally placed 1.5 mm inside the boss radius, so it
existed, rendered, and was completely invisible and unfeelable.

Skipped when OpenSCAD is not installed, so the suite still runs on a laptop
that only has the Python side.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from nsc_fit import head, scad_export, ten_twenty

CAD = Path(__file__).resolve().parents[1] / "cad"

# Must match cap_frame.scad / params.scad.
SOCKET_D = 10 + 2 * 2.0 + 2 * 0.30
BOSS_D = SOCKET_D + 2 * 2.0 + 2
COLLAR_H = 2.5

pytestmark = pytest.mark.skipif(shutil.which("openscad") is None, reason="OpenSCAD not installed")


@pytest.fixture(scope="module")
def frame(tmp_path_factory):
    """Render the frame for a known head and return its vertices."""
    tmp = tmp_path_factory.mktemp("frame")
    fitted = head.fit(head.Measurements(570, 370, 350))
    sites = ten_twenty.montage(fitted)
    scad_export.write_head_params(fitted, sites, CAD / "head_params.scad")

    stl = tmp / "frame.stl"
    subprocess.run(
        ["openscad", "-D", 'part="frame"', "-o", str(stl), str(CAD / "cap_frame.scad")],
        check=True,
        capture_output=True,
    )
    text = stl.read_text(errors="ignore")
    vertices = np.array(
        [[float(v) for v in t] for t in re.findall(r"vertex\s+(\S+)\s+(\S+)\s+(\S+)", text)]
    )
    return fitted, sites, vertices


def test_only_phase_one_sockets_carry_a_raised_collar(frame):
    """F4, Cz and P3 must stand proud of the other sockets, and nothing else.

    Measured along the socket's own outward axis rather than radially. Radial
    extent cannot discriminate: a socket sitting on a band — Fpz and Cz both
    do — has band material out beyond the boss radius in some direction, so a
    radial test reports a collar on every one of them.
    """
    fitted, sites, vertices = frame
    heights = {
        name: _axial_reach(fitted, sites[name].xyz_mm, vertices)
        for name in ten_twenty.MONTAGE_V1
    }
    plain = [h for n, h in heights.items() if n not in ten_twenty.PHASE_1]
    raised = [h for n, h in heights.items() if n in ten_twenty.PHASE_1]

    assert min(raised) > max(plain) + 1.5, (
        f"collars not distinguishable: raised {sorted(raised)}, plain {sorted(plain)}"
    )


def test_the_frame_is_one_connected_piece(frame):
    """A band that fails to meet the ring would print as loose fragments."""
    _, _, vertices = frame
    keys = [tuple(np.round(v, 3)) for v in vertices]
    parent: dict[tuple, tuple] = {}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(0, len(keys), 3):
        triangle = keys[i : i + 3]
        for k in triangle:
            parent.setdefault(k, k)
        for k in triangle[1:]:
            a, b = find(triangle[0]), find(k)
            if a != b:
                parent[a] = b

    assert len({find(k) for k in parent}) == 1


def _axial_reach(fitted, position: np.ndarray, vertices: np.ndarray) -> float:
    """How far material stands out along the socket's outward axis.

    Restricted to vertices inside the socket's own radius so neighbouring
    bands, which run across the head rather than out from it, are excluded.
    """
    axes = np.array([fitted.a_mm, fitted.b_mm, fitted.c_mm])
    axis = position / axes**2
    axis = axis / np.linalg.norm(axis)

    offsets = vertices - position
    along = offsets @ axis
    radial = np.linalg.norm(offsets - np.outer(along, axis), axis=1)
    inside = radial < BOSS_D / 2 + 0.5
    if not inside.any():
        return 0.0
    return float(along[inside].max())
