"""Command line: three measurements in, a fitted cap's worth of files out.

    python3 -m nsc_fit --circumference 570 --nasion-inion 370 --ear-to-ear 350 \
        --subject "subject A" --out build/

Writes a printable marking template, a montage map, and a CSV of 3D positions
for the CAD.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from . import head as head_mod
from . import scad_export
from . import template as template_mod
from . import ten_twenty


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nsc_fit", description=__doc__)
    parser.add_argument("--circumference", type=float, required=True, help="mm, through nasion and inion")
    parser.add_argument("--nasion-inion", type=float, required=True, help="mm, over the vertex")
    parser.add_argument("--ear-to-ear", type=float, required=True, help="mm, preauricular to preauricular")
    parser.add_argument("--subject", default="", help="label printed on the template")
    parser.add_argument("--out", type=Path, default=Path("build"), help="output directory")
    args = parser.parse_args(argv)

    measurements = head_mod.Measurements(
        circumference_mm=args.circumference,
        nasion_inion_mm=args.nasion_inion,
        preauricular_mm=args.ear_to_ear,
    )
    fitted = head_mod.fit(measurements)
    sites = ten_twenty.montage(fitted)

    args.out.mkdir(parents=True, exist_ok=True)
    stem = _slug(args.subject) or "head"

    pages = template_mod.marking_template_pages(fitted, sites, args.subject)
    template_paths = []
    for number, page in enumerate(pages, start=1):
        path = args.out / f"{stem}_marking_template_p{number}.svg"
        path.write_text(page)
        template_paths.append(path)

    map_path = args.out / f"{stem}_montage_map.svg"
    map_path.write_text(template_mod.montage_map_svg(sites, highlight=ten_twenty.MINIMAL_MONTAGE))

    csv_path = args.out / f"{stem}_positions.csv"
    rows = ten_twenty.as_rows(sites)
    with csv_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    scad_path = scad_export.write_head_params(
        fitted, sites, Path(__file__).resolve().parents[2] / "cad" / "head_params.scad"
    )

    z_ref, loop_len = ten_twenty.lateral_loop(fitted, sites)
    residual = ten_twenty.fit_residual_mm(fitted, sites)

    print(f"head model: a={fitted.a_mm:.1f} b={fitted.b_mm:.1f} c={fitted.c_mm:.1f} mm")
    print(f"lateral loop: {loop_len:.0f} mm at {z_ref:.0f} mm above the landmark plane")
    print(f"fit residual: {residual:.1f} mm", end="  ")
    print("(good)" if residual < 5.0 else "(HIGH — mark lateral sites by tape, not template)")
    for path in template_paths:
        print(f"wrote {path}")
    print(f"wrote {map_path}")
    print(f"wrote {csv_path}")
    print(f"wrote {scad_path}")
    return 0


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text.strip().lower()).strip("_")


if __name__ == "__main__":
    raise SystemExit(main())
