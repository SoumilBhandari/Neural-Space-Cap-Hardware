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
