"""Printable output: a marking template and a montage map.

Two SVG files, both drawn in real millimetres so they print at 1:1.

The marking template is the one that gets used. It prints as paper strips that
wrap around a head; the tick marks fall on the 10-20 sites, and the person
fitting the cap marks through them with a skin pencil. This is how EEG labs
actually place electrodes, and it takes about four minutes once the three
measurements are taken.

The montage map is for the poster and for checking the montage at a glance
before anyone touches a head.
"""

from __future__ import annotations

import math

import numpy as np

from .head import Head
from .ten_twenty import LATERAL_LEFT, LATERAL_RIGHT, MIDLINE, Site, lateral_loop

# US Letter, in millimetres.
PAGE_W, PAGE_H = 215.9, 279.4
MARGIN = 12.0
STRIP_H = 22.0
ROW_GAP = 8.0

# Longest strip segment that fits the page width. The join tab is drawn inside
# the segment, so it costs no extra width.
SEG_MAX = PAGE_W - 2 * MARGIN - 2.0

_CSS = """
text { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; fill: #000; }
.cut { fill: none; stroke: #000; stroke-width: 0.3; }
.tick { stroke: #000; stroke-width: 0.5; }
.tick-major { stroke: #000; stroke-width: 0.9; }
.fold { fill: none; stroke: #999; stroke-width: 0.25; stroke-dasharray: 2 1.5; }
.site { font-size: 4.2px; font-weight: 700; }
.dist { font-size: 2.6px; fill: #666; }
.label { font-size: 3.6px; }
.head { font-size: 5.5px; font-weight: 700; }
.note { font-size: 3px; fill: #444; }
.outline { fill: none; stroke: #000; stroke-width: 0.6; }
.pad { fill: #fff; stroke: #000; stroke-width: 0.5; }
.pad-key { fill: #d8d8d8; stroke: #000; stroke-width: 0.8; }
"""


def marking_template_pages(head: Head, sites: dict[str, Site], subject: str = "") -> list[str]:
    """Cut-and-wrap templates for marking 10-20 sites on a head, one SVG per page.

    Three strips: the midline from nasion to inion, the coronal line from ear
    to ear, and the horizontal loop the lateral sites sit on. Strips wider than
    the page are split into equal segments with labelled join tabs, and the
    whole thing flows onto as many pages as it needs — a big head produces
    more segments, and silently running off the bottom of page one would not
    be discovered until someone tried to mark a head with it.
    """
    z_ref, loop_len = lateral_loop(head, sites)
    sag_len = head.sagittal_arc().length_mm()
    cor_len = head.coronal_arc().length_mm()

    strips = [
        (
            "Midline — nasion to inion, over the vertex",
            sag_len,
            [(name, MIDLINE[name] * sag_len) for name in ("Fpz", "Fz", "Cz", "Pz", "Oz")],
        ),
        (
            "Coronal — left ear to right ear, over the vertex",
            cor_len,
            [(name, f * cor_len) for name, f in sorted(_coronal_pairs(), key=lambda kv: kv[1])],
        ),
        (
            f"Lateral loop — around the head at Fpz/Oz level ({loop_len:.0f} mm)",
            loop_len,
            _loop_ticks(loop_len),
        ),
    ]

    # Flow title/segment blocks onto pages, keeping a title with its first
    # segment so a strip never starts with an orphaned heading.
    blocks: list[tuple[float, object]] = []
    for title, total, ticks in strips:
        segments = _segments(total)
        for index, segment in enumerate(segments):
            height = STRIP_H + 3.0 + (3.5 if index == 0 else 0.0)
            if index == len(segments) - 1:
                height += ROW_GAP - 3.0
            blocks.append((height, (title if index == 0 else None, segment, ticks, total)))

    pages: list[str] = []
    parts: list[str] = []
    y = 0.0
    # Blocks are drawn at y + MARGIN, so the top margin counts against the
    # limit as well as the bottom one.
    limit = PAGE_H - 2 * MARGIN - 8.0

    for height, block in blocks:
        if not parts or y + height > limit:
            if parts:
                pages.append(_page(_footer("".join(parts))))
            parts = [_header(head, subject, len(pages) + 1)]
            y = _HEADER_H
        title, segment, ticks, total = block
        if title is not None:
            parts.append(f'<text class="label" x="{MARGIN}" y="{y + MARGIN}">{_esc(title)}</text>')
            y += 3.5
        parts.append(_strip_segment(MARGIN, y + MARGIN, segment, ticks, total))
        y += height - (3.5 if title is not None else 0.0)

    if parts:
        pages.append(_page(_footer("".join(parts))))
    return pages


# Height consumed by the page header, measured from the top margin.
_HEADER_H = 32.0


def _header(head: Head, subject: str, page: int) -> str:
    m = head.measurements
    meta = (
        f"circumference {m.circumference_mm:.0f} mm · nasion-inion {m.nasion_inion_mm:.0f} mm · "
        f"ear-to-ear {m.preauricular_mm:.0f} mm"
    )
    if subject:
        meta = f"{subject} · {meta}"
    return (
        f'<text class="head" x="{MARGIN}" y="{MARGIN + 4}">'
        f"Neural Space Cap — 10-20 marking template (page {page})</text>"
        f'<text class="note" x="{MARGIN}" y="{MARGIN + 10}">{_esc(meta)}</text>'
        f'<text class="note" x="{MARGIN}" y="{MARGIN + 15}">'
        "Print at 100% — do not scale to fit. Check the ruler below before cutting.</text>"
        + _ruler(MARGIN, MARGIN + 22)
    )


def _footer(body: str) -> str:
    return body + (
        f'<text class="note" x="{MARGIN}" y="{PAGE_H - MARGIN}">'
        "Cut along the solid lines. Join segments at the matching letters, overlapping to the "
        "fold mark. Wrap, align the start landmark, and mark through each tick.</text>"
    )


def montage_map_svg(sites: dict[str, Site], highlight: tuple[str, ...] = ()) -> str:
    """A top-down map of the montage, drawn the way EEG montages are drawn.

    Radius is arc distance from the vertex, so the sites that sit low on the
    head land on the rim instead of bunching against the outline. Nose at the
    top, subject's left on the left.
    """
    size = 165.0
    cx = cy = size / 2
    radius = size / 2 - 15

    parts = [
        f'<circle class="outline" cx="{cx}" cy="{cy}" r="{radius}"/>',
        # Nose.
        f'<path class="outline" d="M {cx - 7} {cy - radius + 1.5} L {cx} {cy - radius - 9} '
        f'L {cx + 7} {cy - radius + 1.5}"/>',
        # Ears.
        f'<path class="outline" d="M {cx - radius - 0.5} {cy - 12} q -7 12 0 24"/>',
        f'<path class="outline" d="M {cx + radius + 0.5} {cy - 12} q 7 12 0 24"/>',
    ]

    # Scale so the lowest-sitting sites land on the rim rather than floating
    # inside it, which is how montage maps are conventionally drawn.
    max_rho = max(_rho(s.xyz_mm) for s in sites.values()) or 1.0

    for name in sorted(sites):
        x, y = _topo_xy(sites[name].xyz_mm, cx, cy, radius, max_rho)
        cls = "pad-key" if name in highlight else "pad"
        parts.append(f'<circle class="{cls}" cx="{x:.2f}" cy="{y:.2f}" r="6.5"/>')
        parts.append(
            f'<text class="site" x="{x:.2f}" y="{y + 1.5:.2f}" text-anchor="middle">{name}</text>'
        )

    if highlight:
        parts.append(
            f'<text class="note" x="4" y="{size - 3}">'
            f"Shaded: {', '.join(highlight)} — the minimum montage for the alpha-blocking test."
            "</text>"
        )

    return _page("".join(parts), width=size, height=size)


def _rho(xyz: np.ndarray) -> float:
    """Angle of a site away from the vertex, in radians."""
    x, y, z = xyz
    return math.atan2(math.hypot(x, y), max(float(z), 1e-9))


def _topo_xy(
    xyz: np.ndarray, cx: float, cy: float, radius: float, max_rho: float
) -> tuple[float, float]:
    """Project a 3D site to the flat map: radius from vertex, azimuth around."""
    r = min(_rho(xyz) / max_rho, 1.0) * radius
    azimuth = math.atan2(float(xyz[0]), float(xyz[1]))
    return cx + r * math.sin(azimuth), cy - r * math.cos(azimuth)


def _coronal_pairs() -> list[tuple[str, float]]:
    from .ten_twenty import CORONAL

    return list(CORONAL.items())


def _loop_ticks(loop_len: float) -> list[tuple[str, float]]:
    """Tick positions around the lateral loop, starting and ending at Fpz."""
    ticks = [("Fpz", 0.0)]
    for name, f in sorted(LATERAL_LEFT.items(), key=lambda kv: kv[1]):
        ticks.append((name, f * loop_len))
    ticks.append(("Oz", 0.5 * loop_len))
    for name, f in sorted(LATERAL_RIGHT.items(), key=lambda kv: kv[1], reverse=True):
        ticks.append((name, (1.0 - f) * loop_len))
    return ticks


def _segments(total: float) -> list[tuple[float, float, str]]:
    """Split a strip into page-width pieces, each tagged with a join letter.

    Length is divided evenly rather than filled greedily. Greedy filling leaves
    a sliver at the end — a 370 mm strip becomes 184 + 184 + 2 — and a two
    millimetre paper tab is not something anyone can cut out or align.
    """
    letters = "ABCDEFGH"
    count = max(1, math.ceil(total / SEG_MAX))
    step = total / count
    return [(i * step, (i + 1) * step, letters[i % len(letters)]) for i in range(count)]


def _strip_segment(
    x0: float,
    y0: float,
    segment: tuple[float, float, str],
    ticks: list[tuple[str, float]],
    total: float,
) -> str:
    start, end, letter = segment
    width = end - start
    parts = [f'<rect class="cut" x="{x0}" y="{y0}" width="{width:.2f}" height="{STRIP_H}"/>']

    # Join tab at the end of every segment but the last.
    if end < total - 1e-6:
        parts.append(
            f'<line class="fold" x1="{x0 + width - 6:.2f}" y1="{y0}" '
            f'x2="{x0 + width - 6:.2f}" y2="{y0 + STRIP_H}"/>'
        )
        parts.append(
            f'<text class="dist" x="{x0 + width - 3:.2f}" y="{y0 + STRIP_H / 2:.2f}" '
            f'text-anchor="middle">{letter}</text>'
        )
    if start > 0:
        parts.append(
            f'<text class="dist" x="{x0 + 3:.2f}" y="{y0 + STRIP_H / 2:.2f}" '
            f'text-anchor="middle">{letter}</text>'
        )

    # Centimetre ticks for orientation while wrapping.
    first_cm = math.ceil(start / 10.0) * 10.0
    d = first_cm
    while d <= end + 1e-6:
        x = x0 + (d - start)
        parts.append(f'<line class="tick" x1="{x:.2f}" y1="{y0 + STRIP_H - 3}" x2="{x:.2f}" y2="{y0 + STRIP_H}"/>')
        d += 10.0

    for name, dist in ticks:
        if not (start - 1e-6 <= dist <= end + 1e-6):
            continue
        x = x0 + (dist - start)
        parts.append(f'<line class="tick-major" x1="{x:.2f}" y1="{y0}" x2="{x:.2f}" y2="{y0 + 11}"/>')
        # A tick sitting on a segment edge would otherwise hang its label off
        # the strip and get lost when the strip is cut out.
        label_x = min(max(x, x0 + 5.0), x0 + width - 5.0)
        parts.append(
            f'<text class="site" x="{label_x:.2f}" y="{y0 + 16}" text-anchor="middle">{name}</text>'
        )
        parts.append(
            f'<text class="dist" x="{label_x:.2f}" y="{y0 + 19.5}" text-anchor="middle">{dist:.0f}</text>'
        )
    return "".join(parts)


def _ruler(x0: float, y0: float) -> str:
    """A 100 mm check ruler. If this measures 100 mm, the page printed at 1:1."""
    parts = [
        f'<line class="tick-major" x1="{x0}" y1="{y0}" x2="{x0 + 100}" y2="{y0}"/>',
        f'<text class="note" x="{x0 + 103}" y="{y0 + 1.2}">100 mm — measure this first</text>',
    ]
    for i in range(11):
        x = x0 + i * 10
        parts.append(f'<line class="tick" x1="{x}" y1="{y0 - 2.5}" x2="{x}" y2="{y0 + 2.5}"/>')
    return "".join(parts)


def _page(body: str, width: float = PAGE_W, height: float = PAGE_H) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}mm" height="{height}mm" '
        f'viewBox="0 0 {width} {height}">'
        f"<style>{_CSS}</style>"
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#fff"/>'
        f"{body}</svg>"
    )


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
