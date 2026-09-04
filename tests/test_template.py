"""Printable output: real millimetres, and nothing running off the page."""

import re

import pytest

from nsc_fit import head, template, ten_twenty


def _fitted(circ=570, ni=370, pa=350):
    fitted = head.fit(head.Measurements(circ, ni, pa))
    return fitted, ten_twenty.montage(fitted)


@pytest.mark.parametrize(
    "circ,ni,pa", [(500, 330, 320), (540, 350, 340), (570, 370, 350), (620, 400, 385)]
)
def test_nothing_runs_off_the_page(circ, ni, pa):
    """A strip printed past the page edge is not discovered until fitting day."""
    fitted, sites = _fitted(circ, ni, pa)
    for page in template.marking_template_pages(fitted, sites):
        bottoms = [
            float(y) + template.STRIP_H
            for y in re.findall(r'<rect class="cut"[^>]*y="([\d.]+)"', page)
        ]
        assert bottoms
        assert max(bottoms) <= template.PAGE_H - template.MARGIN


def test_pages_are_declared_in_millimetres():
    """The template is only usable if it prints at 1:1."""
    fitted, sites = _fitted()
    page = template.marking_template_pages(fitted, sites)[0]
    assert f'width="{template.PAGE_W}mm"' in page
    assert f'height="{template.PAGE_H}mm"' in page


def test_no_sliver_segments():
    """Even division, so no segment is too small to cut out and align."""
    for total in (200.0, 370.0, 549.0, 600.0):
        segments = template._segments(total)
        widths = [end - start for start, end, _ in segments]
        assert min(widths) > 40.0
        assert sum(widths) == pytest.approx(total)
        assert max(widths) <= template.SEG_MAX + 1e-6


def test_every_site_appears_on_the_template():
    fitted, sites = _fitted()
    pages = "".join(template.marking_template_pages(fitted, sites))
    for name in ("Fpz", "Fz", "Cz", "Pz", "Oz", "T7", "T8", "O1", "O2", "Fp1", "Fp2"):
        assert f">{name}<" in pages


def test_montage_map_places_every_site_inside_the_head_outline():
    _, sites = _fitted()
    svg = template.montage_map_svg(sites, highlight=ten_twenty.MINIMAL_MONTAGE)
    circles = re.findall(r'<circle class="pad[^"]*" cx="([\d.]+)" cy="([\d.]+)"', svg)
    assert len(circles) == len(sites)
    size = 165.0
    centre = size / 2
    for cx, cy in circles:
        offset = ((float(cx) - centre) ** 2 + (float(cy) - centre) ** 2) ** 0.5
        assert offset <= size / 2 - 15 + 0.01
