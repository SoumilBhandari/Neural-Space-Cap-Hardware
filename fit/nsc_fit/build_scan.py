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

import numpy as np

from . import head as head_mod
from . import scad_export, scanned, stlclean, ten_twenty

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
    subprocess.run(
        ["openscad", "-D", 'part="frame"', "-D", f'size_label="{label}"',
         "-o", str(args.out), str(ROOT / "cad" / "cap_frame.scad")],
        check=True, capture_output=True,
    )

    report = stlclean.clean(args.out)
    tris, _ = stlclean._read(args.out)
    extent = tris.reshape(-1, 3).max(0) - tris.reshape(-1, 3).min(0)
    longest = max(extent[0], extent[1])

    print(f"{args.out.name}: {extent[0]:.0f} x {extent[1]:.0f} x {extent[2]:.0f} mm")
    print(f"  hair allowance {(args.circumference - args.tape[0]) / 6.283:.1f} mm of thickness")
    noise = {k: v for k, v in report.items() if k not in ("kept", "removed") and v}
    if noise:
        print("  cleaned: " + ", ".join(f"{v} {k.replace('_', ' ')}" for k, v in noise.items()))
    # Solid volume by the divergence theorem, so the print estimate is the
    # part's own material rather than its bounding box.
    v = tris
    volume = abs(float(np.sum(np.einsum("ij,ij->i", v[:, 0], np.cross(v[:, 1], v[:, 2]))))) / 6.0
    print(f"  solid volume {volume / 1000:.0f} cm3  (~{volume / 1000 * 1.27:.0f} g PETG at 100%)")

    for bed, name in ((220, "220 x 220"), (256, "256 x 256"), (325, "Bambu H2D 325 x 320")):
        room = bed - longest
        verdict = (
            f"fits, {room:.0f} mm spare" if room >= 10
            else "too tight" if room >= 0 else "does not fit"
        )
        print(f"  {name}: {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
