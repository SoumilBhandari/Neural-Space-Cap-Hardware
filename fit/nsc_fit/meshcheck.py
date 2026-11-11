"""Check an exported STL the way a slicer will see it.

A slicer does not get OpenSCAD's indexed mesh. It gets a soup of triangles and
welds them back together by position, so two vertices that were distinct in
memory but sit at the same coordinates become one. A mesh can therefore be a
perfect manifold in the program that made it and arrive with thousands of
non-manifold edges, which is what happened to this frame: the indexed mesh
had every edge shared by exactly two triangles, and 45,689 of its 89,764
vertices were exactly coincident with another one.

So this welds by position first, exactly as a slicer does, and judges that.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import stlclean


@dataclass
class Report:
    triangles: int
    shells: int
    open_edges: int          # used by one triangle: a hole
    shared_edges: int        # used by more than two: surfaces touching
    degenerate: int
    volume_cm3: float
    extent: np.ndarray
    first_layer_mm2: float
    overhang_pct: float

    @property
    def printable(self) -> bool:
        return (self.shells == 1 and self.open_edges == 0 and self.shared_edges == 0
                and self.degenerate == 0 and self.volume_cm3 > 0)

    @property
    def verdict(self) -> str:
        if self.printable:
            return "watertight, manifold, one shell"
        problems = []
        if self.shells != 1:
            problems.append(f"{self.shells} separate shells")
        if self.open_edges:
            problems.append(f"{self.open_edges} open edges")
        if self.shared_edges:
            problems.append(f"{self.shared_edges} non-manifold edges")
        if self.degenerate:
            problems.append(f"{self.degenerate} zero-area triangles")
        if self.volume_cm3 <= 0:
            problems.append("inside-out")
        return "NOT PRINTABLE: " + ", ".join(problems)


def check(path: str | Path) -> Report:
    tris, _ = stlclean._read(path)
    tris = tris.astype(np.float32)          # what the file actually stores

    flat = tris.reshape(-1, 3)
    _, index = np.unique(flat, axis=0, return_inverse=True)
    faces = index.reshape(-1, 3)

    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    degenerate = int(((faces[:, 0] == faces[:, 1]) | (faces[:, 1] == faces[:, 2])
                      | (faces[:, 0] == faces[:, 2])).sum())
    edges = edges[edges[:, 0] != edges[:, 1]]
    key = np.sort(edges, axis=1)
    _, counts = np.unique(key, axis=0, return_counts=True)

    parent = np.arange(index.max() + 1)

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in key:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    shells = len({find(v) for v in np.unique(faces)})

    t = tris.astype(float)
    normal = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    area = np.linalg.norm(normal, axis=1) / 2
    volume = float(np.sum(np.einsum("ij,ij->i", t[:, 0], np.cross(t[:, 1], t[:, 2]))) / 6.0)

    z0 = flat[:, 2].min()
    nz = np.divide(normal[:, 2], 2 * area, out=np.zeros_like(area), where=area > 0)
    on_plate = (t[:, :, 2].max(axis=1) - z0) < 0.05
    # Facing more than 45 degrees below horizontal, and not sitting on the plate.
    hanging = (nz < -math_cos45) & ~on_plate

    return Report(
        triangles=len(tris),
        shells=shells,
        open_edges=int((counts == 1).sum()),
        shared_edges=int((counts > 2).sum()),
        degenerate=degenerate,
        volume_cm3=volume / 1000.0,
        extent=flat.max(axis=0) - flat.min(axis=0),
        first_layer_mm2=float(area[on_plate].sum()),
        overhang_pct=float(100.0 * area[hanging].sum() / area.sum()),
    )


math_cos45 = float(np.cos(np.radians(45.0)))
