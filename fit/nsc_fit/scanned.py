"""Her head, from the LiDAR scan, as a surface the CAD can be built on.

The ellipsoid model in `head.py` is fitted to three tape measurements. It gets
the size right and the shape approximately right, and for a marking template
that is enough — a tape follows the skull whatever shape it is.

A printed frame is different. It has to sit on the actual head, and an
ellipsoid is not the actual head: no brow, no occipital bump, perfect
left-right symmetry, and in this case no allowance for where the hair is thick
and where it is not. Scaling the ellipsoid up until it clears the hair gives a
bigger generic head, not hers.

This module takes the scan instead. The cranium is isolated, aligned to the
anatomical axes, and resampled into a polar height field r(theta, phi) centred
inside the skull — a representation that works because a cranium is
star-shaped from its own centre, and which makes "where is her surface in this
direction" a lookup instead of a ray cast.

The 10-20 layout still comes from the fitted ellipsoid, because the standard
is defined by arc percentages between bony landmarks and this scan has no
landmarks marked on it. Each site's direction from the head centre is taken
from the ellipsoid and the position is then read off her scanned surface in
that direction. The montage keeps its standard geometry; the frame gets her
actual contour.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import struct

from scipy.ndimage import gaussian_filter

# Polar grid resolution. 2 degrees is finer than the scan's own noise and
# keeps the lookup tables small.
THETA_STEPS = 64
PHI_STEPS = 180

# How far down from the crown the scan is trusted. Below this it stops being
# skull and becomes hair on shoulders, hoodie, and whatever was behind her.
# Far enough down that the lateral ring sits inside the modelled surface
# rather than on its rim, where the skirt below takes bites out of the bands.
MAX_THETA_DEG = 86.0


@dataclass
class ScannedHead:
    """A cranium as a polar height field, in millimetres, anatomically aligned.

    +x is her left, +y is her nose, +z is up. The origin is the centre the
    height field is measured from, not the landmark plane.
    """

    radius: np.ndarray          # (THETA_STEPS, PHI_STEPS), millimetres
    centre: np.ndarray          # origin in the aligned frame
    crown_z: float

    def surface(self, theta: float, phi: float) -> np.ndarray:
        """Point on her surface in the direction (theta from +z, phi azimuth)."""
        r = self._lookup(theta, phi)
        return self.centre + r * np.array(
            [math.sin(theta) * math.cos(phi), math.sin(theta) * math.sin(phi), math.cos(theta)]
        )

    def surface_towards(self, direction: np.ndarray) -> np.ndarray:
        """Point on her surface along an arbitrary direction from the centre."""
        d = np.asarray(direction, dtype=float)
        d = d / np.linalg.norm(d)
        return self.surface(math.acos(float(np.clip(d[2], -1, 1))), math.atan2(d[1], d[0]))

    def _lookup(self, theta: float, phi: float) -> float:
        """Bilinear sample of the height field, wrapping in phi."""
        t = np.clip(theta / math.radians(MAX_THETA_DEG), 0.0, 1.0) * (THETA_STEPS - 1)
        p = (phi % (2 * math.pi)) / (2 * math.pi) * PHI_STEPS

        t0, p0 = int(t), int(p)
        t1, p1 = min(t0 + 1, THETA_STEPS - 1), (p0 + 1) % PHI_STEPS
        ft, fp = t - t0, p - p0
        return float(
            self.radius[t0, p0] * (1 - ft) * (1 - fp)
            + self.radius[t1, p0] * ft * (1 - fp)
            + self.radius[t0, p1] * (1 - ft) * fp
            + self.radius[t1, p1] * ft * fp
        )

    def inflated_mesh(self, gap_mm: float) -> tuple[np.ndarray, np.ndarray]:
        """Her surface pushed out by ``gap_mm``, as a closed manifold mesh.

        Built as an apex, rings, a skirt and a floor. The crown needs a single
        apex vertex and a triangle fan: emitting a full ring at theta = 0 puts
        PHI_STEPS coincident vertices there and every triangle between them is
        degenerate, which is enough to make the whole solid non-manifold and
        unusable as a subtraction.
        """
        def point(theta: float, phi: float, r: float) -> np.ndarray:
            return self.centre + r * np.array(
                [math.sin(theta) * math.cos(phi), math.sin(theta) * math.sin(phi), math.cos(theta)]
            )

        thetas = [math.radians(MAX_THETA_DEG) * i / (THETA_STEPS - 1) for i in range(THETA_STEPS)]
        phis = [2 * math.pi * j / PHI_STEPS for j in range(PHI_STEPS)]

        verts = [point(0.0, 0.0, self.radius[0].mean() + gap_mm)]
        for i in range(1, THETA_STEPS):
            for j in range(PHI_STEPS):
                verts.append(point(thetas[i], phis[j], self.radius[i, j] + gap_mm))

        def ring(i: int, j: int) -> int:
            return 1 + (i - 1) * PHI_STEPS + (j % PHI_STEPS)

        faces = [[0, ring(1, j + 1), ring(1, j)] for j in range(PHI_STEPS)]
        for i in range(1, THETA_STEPS - 1):
            for j in range(PHI_STEPS):
                a, b = ring(i, j), ring(i, j + 1)
                c, d = ring(i + 1, j), ring(i + 1, j + 1)
                faces += [[a, b, d], [a, d, c]]

        # Skirt straight down from the bottom ring, then a floor, so the solid
        # is closed well below anything the frame reaches.
        floor_z = min(verts[ring(THETA_STEPS - 1, j)][2] for j in range(PHI_STEPS)) - 80.0
        skirt = len(verts)
        for j in range(PHI_STEPS):
            edge = verts[ring(THETA_STEPS - 1, j)]
            # Tapered inward, not dropped straight down. A vertical skirt keeps
            # the rim's full width all the way to the floor, and anything the
            # frame puts just below the rim lands inside it and is cut away.
            verts.append(np.array([edge[0] * 0.80, edge[1] * 0.80, floor_z]))
        for j in range(PHI_STEPS):
            a, b = ring(THETA_STEPS - 1, j), ring(THETA_STEPS - 1, j + 1)
            c, d = skirt + j, skirt + (j + 1) % PHI_STEPS
            faces += [[a, b, d], [a, d, c]]

        floor = len(verts)
        verts.append(np.array([self.centre[0], self.centre[1], floor_z]))
        for j in range(PHI_STEPS):
            # Wound opposite to the skirt quads above, which already use this
            # edge in the other direction; matching them duplicates every edge
            # around the rim and the solid stops being manifold.
            faces.append([skirt + (j + 1) % PHI_STEPS, floor, skirt + j])

        return np.array(verts), np.array(faces)

    def write_stl(self, path: str | Path, gap_mm: float) -> Path:
        """Write her surface, inflated by ``gap_mm``, as a binary STL.

        The frame subtracts this, so the inside of the print follows her
        contour at a uniform clearance instead of being a shell of an
        idealised head.

        Written relative to the head centre, matching the band paths. In the
        scan's own coordinates the head sits at her standing height, about
        1.5 m up; exporting that absolute position puts the surface a metre
        and a half away from the frame, and the subtraction quietly does
        nothing at all rather than failing.
        """
        verts, faces = self.inflated_mesh(gap_mm)
        verts = verts - self.centre
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            fh.write(b"nsc scanned head".ljust(80, b"\0"))
            fh.write(struct.pack("<I", len(faces)))
            for a, b, c in faces:
                p0, p1, p2 = verts[a], verts[b], verts[c]
                n = np.cross(p1 - p0, p2 - p0)
                length = np.linalg.norm(n)
                n = n / length if length else np.zeros(3)
                fh.write(struct.pack("<12fH", *n, *p0, *p1, *p2, 0))
        return path

    def direction_to(self, point: np.ndarray, origin: np.ndarray) -> np.ndarray:
        """Unit direction of ``point`` as seen from ``origin``."""
        d = np.asarray(point, dtype=float) - np.asarray(origin, dtype=float)
        return d / np.linalg.norm(d)


def symmetrize(radius: np.ndarray) -> np.ndarray:
    """Repair one-sided scan dropout by mirroring across the sagittal plane.

    A hand-held scan rarely closes evenly on both sides of a head, and where
    it thins out the reconstruction collapses inward. On this scan her
    right-front quadrant sits up to 17 mm inside its mirror image, smoothly
    across the whole region — a skull does not do that, a scanner losing
    tracking does. Left unrepaired it puts a visible dent in the frame.

    Each cell is replaced by the larger of itself and its mirror. Taking the
    larger rather than the average matters: a dropout is a spurious *inward*
    collapse, so the intact side carries the true radius, and erring outward
    gives a cap that is slightly loose rather than one that will not go on.

    The cost is that genuine left-right asymmetry is flattened too. For a cap
    that is the right trade — nobody wants a frame built around a scanner
    artifact — but it is why the repaired surface is no longer purely
    measured.
    """
    index = np.arange(radius.shape[1])
    # x -> -x maps azimuth phi to 180 - phi.
    mirrored = np.round(
        ((180.0 - index * 360.0 / radius.shape[1]) % 360.0) / 360.0 * radius.shape[1]
    ).astype(int) % radius.shape[1]
    return np.maximum(radius, radius[:, mirrored])


def load(
    path: str | Path,
    face_azimuth_deg: float | None = None,
    repair_dropout: bool = True,
) -> ScannedHead:
    """Read a scan and turn it into an aligned cranium height field.

    The face direction is found from the scan itself unless given. A forehead
    carries no hair and a scalp does, so the radius from the head's centre is
    smallest toward the face and largest toward the back. On this scan the two
    are 83 mm and 158 mm and sit 195 degrees apart, which is an unambiguous
    axis. Pass ``face_azimuth_deg`` to override it for a scan where that does
    not hold — a hat, a very short haircut, a half-finished scan.
    """
    verts, faces = _read_obj(Path(path))
    verts = _largest_component(verts, faces)
    verts = _to_z_up_mm(verts)
    verts = _crop_to_head(verts)

    if face_azimuth_deg is None:
        face_azimuth_deg = _detect_face_azimuth(verts)

    head = _height_field(_rotate_face_to_front(verts, face_azimuth_deg))
    if repair_dropout:
        head = ScannedHead(
            radius=gaussian_filter(
                symmetrize(head.radius), sigma=(1.0, 2.0), mode=("nearest", "wrap")
            ),
            centre=head.centre,
            crown_z=head.crown_z,
        )
    return head


def _to_z_up_mm(verts: np.ndarray) -> np.ndarray:
    """Scans export Y-up in metres; everything downstream is Z-up millimetres."""
    v = verts * 1000.0
    return np.column_stack([v[:, 0], -v[:, 2], v[:, 1]])


def _crop_to_head(verts: np.ndarray, radius_mm: float = 170.0, drop_mm: float = 240.0):
    """Keep the head, drop the room, the shoulders and the hoodie."""
    top = verts[verts[:, 2] > verts[:, 2].max() - 80]
    cx, cy = np.median(top[:, 0]), np.median(top[:, 1])
    d = np.hypot(verts[:, 0] - cx, verts[:, 1] - cy)
    keep = (d < radius_mm) & (verts[:, 2] > verts[:, 2].max() - drop_mm)
    out = verts[keep].copy()
    out[:, 0] -= cx
    out[:, 1] -= cy
    return out


def _detect_face_azimuth(verts: np.ndarray) -> float:
    """Azimuth of the thinnest side of the head, which is the face."""
    crown = verts[:, 2].max()
    band = verts[(verts[:, 2] > crown - 115) & (verts[:, 2] < crown - 45)]
    phi = np.degrees(np.arctan2(band[:, 1], band[:, 0])) % 360
    r = np.hypot(band[:, 0], band[:, 1])

    medians = []
    for deg in range(0, 360, 10):
        sel = r[(phi >= deg) & (phi < deg + 10)]
        medians.append((deg + 5, np.median(sel) if len(sel) > 4 else np.nan))
    medians = np.array(medians)
    valid = medians[~np.isnan(medians[:, 1])]
    return float(valid[np.argmin(valid[:, 1]), 0])


def _rotate_face_to_front(verts: np.ndarray, face_azimuth_deg: float) -> np.ndarray:
    """Spin the head about its own axis until the face points +y."""
    rotate = math.radians(90.0 - face_azimuth_deg)
    c, s = math.cos(rotate), math.sin(rotate)
    out = verts.copy()
    out[:, 0] = verts[:, 0] * c - verts[:, 1] * s
    out[:, 1] = verts[:, 0] * s + verts[:, 1] * c
    return out


def _read_obj(path: Path) -> tuple[np.ndarray, np.ndarray]:
    verts, faces = [], []
    for line in path.read_text().splitlines():
        if line.startswith("v "):
            verts.append([float(x) for x in line.split()[1:4]])
        elif line.startswith("f "):
            faces.append([int(t.split("/")[0]) - 1 for t in line.split()[1:4]])
    return np.array(verts), np.array(faces)


def _largest_component(verts: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Weld by position and keep the biggest connected piece.

    Scanners duplicate a vertex per UV island, so the raw indices describe a
    shell that is topologically shattered — without welding, the largest
    connected component of this scan is about 1% of the head.
    """
    import collections

    key = np.round(verts, 5)
    uniq, inverse = np.unique(key, axis=0, return_inverse=True)
    welded = inverse[faces]
    welded = welded[
        (welded[:, 0] != welded[:, 1])
        & (welded[:, 1] != welded[:, 2])
        & (welded[:, 0] != welded[:, 2])
    ]

    adjacency = collections.defaultdict(set)
    for a, b, c in welded:
        adjacency[a] |= {b, c}
        adjacency[b] |= {a, c}
        adjacency[c] |= {a, b}

    seen, best = set(), set()
    for start in adjacency:
        if start in seen:
            continue
        component, stack = set(), [start]
        while stack:
            node = stack.pop()
            if node in component:
                continue
            component.add(node)
            stack.extend(adjacency[node] - component)
        seen |= component
        if len(component) > len(best):
            best = component
    return uniq[sorted(best)]


def _height_field(verts: np.ndarray) -> ScannedHead:
    """Resample the cranium into r(theta, phi), filling gaps and smoothing."""
    crown = verts[:, 2].max()
    # Centre low enough that the whole cranium is star-shaped from it, high
    # enough that the rim directions are not nearly tangent to the surface.
    centre = np.array([0.0, 0.0, crown - 110.0])

    rel = verts - centre
    r = np.linalg.norm(rel, axis=1)
    keep = r > 1e-6
    rel, r = rel[keep], r[keep]
    theta = np.arccos(np.clip(rel[:, 2] / r, -1, 1))
    phi = np.arctan2(rel[:, 1], rel[:, 0]) % (2 * math.pi)

    ti = (theta / math.radians(MAX_THETA_DEG) * (THETA_STEPS - 1)).round().astype(int)
    pi = (phi / (2 * math.pi) * PHI_STEPS).astype(int) % PHI_STEPS
    inside = (ti >= 0) & (ti < THETA_STEPS)
    ti, pi, r = ti[inside], pi[inside], r[inside]

    grid = np.full((THETA_STEPS, PHI_STEPS), np.nan)
    for i in range(THETA_STEPS):
        for j in range(PHI_STEPS):
            cell = r[(ti == i) & (pi == j)]
            if len(cell):
                # Median, not max: the hull of a hair strand is not the head.
                grid[i, j] = np.median(cell)

    grid = _fill_holes(grid)
    # Smooth across phi with wraparound; the scan is bumpy and a frame that
    # follows every bump in the hair would be unprintable and pointless.
    grid = gaussian_filter(grid, sigma=(2.0, 4.0), mode=("nearest", "wrap"))
    return ScannedHead(radius=grid, centre=centre, crown_z=crown)


def _fill_holes(grid: np.ndarray) -> np.ndarray:
    """Fill unsampled cells from their ring, then from the ring above."""
    out = grid.copy()
    for i in range(out.shape[0]):
        ring = out[i]
        if np.all(np.isnan(ring)):
            out[i] = out[i - 1] if i else np.nanmedian(out)
            continue
        idx = np.arange(len(ring))
        good = ~np.isnan(ring)
        # Interpolate around the circle, wrapping at the seam.
        out[i] = np.interp(idx, idx[good], ring[good], period=len(ring))
    return out


