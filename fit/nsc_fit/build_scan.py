"""Build a scan-fitted frame at a chosen hair allowance.

    python3 -m nsc_fit.build_scan --scan ../scan/head.obj --circumference 640

Her contour comes from the scan; the circumference sets only how much hair the
frame expects to flatten. A LiDAR scan measures hair uncompressed — this one
reads about 800 mm around the ring line against 575 mm of tape on her scalp —
so building to the raw figure gives a frame nobody can print and that would
sit on her head like a lampshade.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


from . import head as head_mod
from . import meshcheck, scad_export, scanned, stlclean, ten_twenty

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nsc_fit.build_scan", description=__doc__)
    parser.add_argument("--scan", type=Path, required=True)
    parser.add_argument("--circumference", type=float, required=True,
                        help="mm around the ring line; her scalp measures 575")
    parser.add_argument("--gap", type=float, default=4.0, help="liner clearance, mm")
    parser.add_argument("--tape", type=float, nargs=3, default=(575, 350, 340),
                        metavar=("CIRC", "NI", "PA"))
    parser.add_argument("--out", type=Path, default=ROOT / "build" / "cap_frame.stl")
    parser.add_argument("--label", default="")
    parser.add_argument("--on-bed", action="store_true",
                        help="rest the exported frame on z = 0 for the slicer; "
                             "leave off when it has to line up with the head form")
    args = parser.parse_args(argv)

    scan = scanned.load(args.scan).scaled_to(args.circumference)
    fitted = head_mod.fit(head_mod.Measurements(*args.tape))
    sites = ten_twenty.montage(fitted)

    surface = ROOT / "build" / "scan_head.stl"
    scan.write_stl(surface, args.gap)
    scan.write_stl(ROOT / "build" / "head_form.stl", 0.0)

    params = ROOT / "cad" / "head_params.scad"
    scad_export.write_scan_params(
        scan, fitted, sites, params,
        stl_name=f"../build/{surface.name}", standoff_mm=args.gap,
    )
    if "nan" in params.read_text().lower():
        raise SystemExit("generated parameters contain NaN — refusing to build")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    label = args.label or f"{args.circumference:.0f}"
    # Binary STL, not ASCII. OpenSCAD writes ASCII coordinates to six
    # significant figures, which is enough to merge vertices that were
    # distinct in memory and manufacture non-manifold edges on the way out.
    subprocess.run(
        ["openscad", "--export-format", "binstl", "-D", 'part="frame"',
         "-D", f'size_label="{label}"', "-o", str(args.out),
         str(ROOT / "cad" / "cap_frame.scad")],
        check=True, capture_output=True,
    )

    if args.on_bed:
        stlclean.place_on_bed(args.out)

    report = meshcheck.check(args.out)
    extent = report.extent
    print(f"{args.out.name}: {extent[0]:.0f} x {extent[1]:.0f} x {extent[2]:.0f} mm")
    print(f"  hair allowance {(args.circumference - args.tape[0]) / 6.283:.1f} mm of thickness")
    print(f"  {report.triangles} triangles, {report.shells} shell, "
          f"volume {report.volume_cm3:.0f} cm3 (~{report.volume_cm3 * 1.27:.0f} g PETG solid)")
    print(f"  first layer {report.first_layer_mm2:.0f} mm2, "
          f"{report.overhang_pct:.1f}% of surface overhangs past 45 deg")
    print(f"  mesh: {report.verdict}")
    if not report.printable:
        raise SystemExit(f"refusing to hand over {args.out.name}: {report.verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
