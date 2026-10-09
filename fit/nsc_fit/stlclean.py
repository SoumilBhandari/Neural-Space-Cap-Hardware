"""Drop stray fragments from an exported STL.

CSG on a scanned surface leaves specks: where the pod pad meets the lateral
ring this frame picks up four loose shells of a few triangles each, none of
them larger than a quarter of a millimetre. A slicer ignores them, but they
make every connectivity check report the part as several pieces, which buries
the one result that matters — whether the frame itself is in one piece.

Keeping only the largest connected shell makes that check mean something.
"""

from __future__ import annotations

import collections
import re
import struct
from pathlib import Path

import numpy as np


def clean(
    path: str | Path,
    area_eps: float = 1e-9,
    drop_degenerate: bool = False,
    drop_duplicates: bool = False,
    drop_back_to_back: bool = False,
) -> dict[str, int]:
    """Make an exported STL fit to slice, in place.

    OpenSCAD's export of this frame is closed but far from tidy. A quarter of
    its triangles are exact duplicates, a few hundred have zero area, and a
    hundred or so sit in back-to-back pairs forming zero-thickness internal
    sheets. The duplicates and the degenerate ones are mostly harmless bloat,
    but the back-to-back pairs are the kind of thing that makes a slicer
    produce a shell with a hole in it, and none of them have any business in a
    file about to run for several hours on a printer.

    By default this only drops connected shells other than the largest, which
    is the one repair that is provably safe: a detached speck of four
    triangles cannot be holding anything together.

    The tidier-looking passes are off, and should stay off. OpenSCAD's export
    is ugly — a quarter of its triangles are exact duplicates and 33% of edges
    are shared by four or more faces — but it is **watertight**, and that is
    what a slicer needs. Deleting the duplicates tears holes, because in
    places two genuinely separate sheets of the surface occupy the same
    coordinates and the second copy is not redundant. Measured on this frame:
    removing duplicates took it from zero unpaired edges to 32, and removing
    back-to-back pairs made it worse again.

    A closed mesh with messy interior faces slices correctly. A mesh with
    holes does not. Proper repair of the interior is a job for a tool built
    for it — the slicer's own repair, or Meshmixer — not for this module.
    """
    path = Path(path)
    tris, normals = _read(path)
    before = len(tris)
    report = {"degenerate": 0, "back_to_back": 0, "duplicate": 0, "stray": 0}

    areas = np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1) / 2
    alive = areas >= area_eps if drop_degenerate else np.ones(len(tris), bool)
    report["degenerate"] = int((~alive).sum())

    keys = [_canonical(t) for t in np.round(tris, 4)]
    counts = collections.Counter(k for k, live in zip(keys, alive) if live)

    # A triangle and its mirror enclose no volume, but deleting them leaves a
    # gap in the shell unless something else closes it, which here it does not.
    doomed = (
        {k for k in counts if (k[0], k[2], k[1]) in counts} if drop_back_to_back else set()
    )
    seen: collections.Counter = collections.Counter()
    for i, (k, live) in enumerate(zip(keys, alive)):
        if not live:
            continue
        if k in doomed:
            alive[i] = False
            report["back_to_back"] += 1
            continue
        seen[k] += 1
        if drop_duplicates and seen[k] > 1:
            alive[i] = False
            report["duplicate"] += 1

    tris, normals = tris[alive], normals[alive]
    tris, normals, report["stray"] = _keep_largest(tris, normals)
    _write(path, tris, normals)
    report["kept"] = len(tris)
    report["removed"] = before - len(tris)
    return report


def _canonical(tri: np.ndarray) -> tuple:
    """Vertex triple rotated to a fixed start, preserving winding."""
    start = min(range(3), key=lambda i: tuple(tri[i]))
    return (tuple(tri[start]), tuple(tri[(start + 1) % 3]), tuple(tri[(start + 2) % 3]))


def _keep_largest(tris: np.ndarray, normals: np.ndarray):
    parent: dict[tuple, tuple] = {}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    keys = np.round(tris, 3)
    for tri in keys:
        corners = [tuple(c) for c in tri]
        for c in corners:
            parent.setdefault(c, c)
        for c in corners[1:]:
            a, b = find(corners[0]), find(c)
            if a != b:
                parent[a] = b

    counts = collections.Counter(find(c) for c in parent)
    if len(counts) <= 1:
        return tris, normals, 0
    biggest = counts.most_common(1)[0][0]
    keep = np.array([find(tuple(t[0])) == biggest for t in keys])
    return tris[keep], normals[keep], int((~keep).sum())


def largest_shell(path: str | Path) -> tuple[int, int]:
    """Rewrite ``path`` keeping only its biggest connected shell.

    Returns ``(shells_found, triangles_removed)``.
    """
    path = Path(path)
    tris, normals = _read(path)
    keys = np.round(tris, 3)

    parent: dict[tuple, tuple] = {}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for tri in keys:
        corners = [tuple(c) for c in tri]
        for c in corners:
            parent.setdefault(c, c)
        for c in corners[1:]:
            a, b = find(corners[0]), find(c)
            if a != b:
                parent[a] = b

    counts = collections.Counter(find(c) for c in parent)
    if len(counts) <= 1:
        return len(counts), 0

    biggest = counts.most_common(1)[0][0]
    keep = np.array([find(tuple(tri[0])) == biggest for tri in keys])
    _write(path, tris[keep], normals[keep])
    return len(counts), int((~keep).sum())


def _read(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    raw = Path(path).read_bytes()
    if raw[:5] == b"solid" and b"facet" in raw[:2048]:
        text = raw.decode("utf-8", "ignore")
        tris = np.array(
            [[float(x) for x in m] for m in re.findall(r"vertex (\S+) (\S+) (\S+)", text)]
        ).reshape(-1, 3, 3)
        normals = np.array(
            [[float(x) for x in m] for m in re.findall(r"facet normal (\S+) (\S+) (\S+)", text)]
        )
        return tris, normals

    count = struct.unpack("<I", raw[80:84])[0]
    tris = np.empty((count, 3, 3))
    normals = np.empty((count, 3))
    for i in range(count):
        chunk = struct.unpack("<12fH", raw[84 + i * 50 : 84 + (i + 1) * 50])
        normals[i] = chunk[0:3]
        tris[i] = np.array(chunk[3:12]).reshape(3, 3)
    return tris, normals


def _write(path: str | Path, tris: np.ndarray, normals: np.ndarray) -> None:
    with Path(path).open("wb") as fh:
        fh.write(b"nsc cleaned".ljust(80, b"\0"))
        fh.write(struct.pack("<I", len(tris)))
        for normal, tri in zip(normals, tris):
            fh.write(struct.pack("<12fH", *normal, *tri.reshape(-1), 0))
