// The cap frame: the part that actually goes on a head.
//
// A closed ring around the head at Fpz/Oz level, braced by four arches — over
// the top, ear to ear, and the frontal and parietal chains — following the
// International 10-20 arcs of one specific person's skull.
//
// It carries eight electrode sockets at Fpz, F3, F4, C3, Cz, C4, P3 and P4,
// a seat for the PPG sensor on the left temple, and a pad for the electronics
// pod behind Oz. The three sockets wired first (F4, Cz, P3) carry a raised
// index nub so they can be found by hand without a drawing.
//
// Ring plus arches rather than separate front and rear bands: a band joined
// only at the midline is cantilevered and flexes, and an electrode that moves
// is an electrode whose data cannot be compared between sessions.
//
// It is generated, not drawn. `nsc_fit` fits an ellipsoid to three tape
// measurements and writes head_params.scad; this file sweeps bands along the
// paths in that file and hollows the inside to the same ellipsoid. Re-measure
// a different person, re-run the fit, and the frame changes shape to match.
//
// Regenerate head_params.scad before rendering:
//   make fit SUBJECT="subject A" CIRC=570 NI=370 PA=350
//
// Render:
//   openscad -D 'part="frame"'    -o frame.stl    cap_frame.scad
//   openscad -D 'part="headform"' -o headform.stl cap_frame.scad
//
// Print the frame whole, ring down, with supports under the two arches. Do not
// try to split it at the midline or the coronal plane: each arch lies exactly
// in one of those planes, so either cut slices an arch down its own length
// instead of across it. Splitting it properly means cutting transversely at
// the four band junctions with real joints, which is not designed yet — see
// docs/DESIGN_NOTES.md.

include <params.scad>
include <head_params.scad>

part = "preview";   // "frame", "headform", "coupon", "preview"

// Sacrificial feet for printing. The frame is a swept tube on a curved path,
// so no part of it is flat: ring-down it meets the plate at one tangent point
// with no first-layer area at all, and a brim has nothing to hold on to.
// Snip the necks and sand the four stubs after printing.
feet_on     = true;
foot_pad_d  = 18;    // footprint on the plate
foot_pad_h  = 0.6;
foot_neck_d = 3.5;   // thin enough to snap, thick enough to print
foot_neck_h = 3.0;

// Printed into the pod pad. Four frames a few percent apart are impossible to
// tell apart by eye once they are off the print bed.
size_label = "";

band_d      = 11.0;   // swept diameter of a band
liner_gap   = 2.5;    // clearance for the fabric liner and hair
trim_z      = 8.0;    // nothing hangs below this height above the landmarks

// The holder's hub plus a press-fit allowance. Equal diameters do not press
// together, they jam — tight_fit is what makes it an assembly rather than two
// parts that both measure 14.6 mm and refuse to meet.
socket_d    = carrier_d + tight_fit;
socket_h    = 7.0;
boss_d      = socket_d + 2 * wall + 2;
ppg_seat_d  = ppg_d + 2 * wall + 2 * clearance;  // matches sensor_puck body
collar_h    = 2.5;   // how far a phase-one socket stands above the others

pod_pad_l   = 46;
pod_pad_w   = 34;
pod_pad_t   = 5;

// How far the pad sinks into the bands, and how far it stands out past them.
// Named explicitly because three things have to agree about where its outer
// face is — the pad, the insert holes and the size badge — and the badge has
// already been written into the middle of the pad once by assuming.
//
// Keeping it shallow matters twice over: the pad is the backmost feature on
// the whole frame, so its proudness sets the longest dimension and decides
// which printers can take the part, and every millimetre it stands off the
// skull is lever arm for the pod's mass against the back of her neck.
pod_pad_sink  = 4.0;
pod_pad_proud = 1.5;

// The volume the frame is hollowed against.
//
// With a scan, this is her actual surface, already inflated by the liner gap
// when it was exported — so the inside of the print follows her contour,
// including the side where her hair is thicker. Without one, it falls back to
// the fitted ellipsoid, which is a generic head of the right size.
module head_solid(grow = 0) {
    if (is_undef(scan_stl))
        scale([head_axes[0] + grow, head_axes[1] + grow, head_axes[2] + grow]) sphere(r = 1);
    else
        import(scan_stl, convexity = 8);
}

// True when the frame is being built on a scan rather than on an ellipsoid.
function on_scan() = !is_undef(scan_stl);

// Sweep a tube along a polyline by hulling consecutive spheres. Crude, but it
// follows an arbitrary 3D path exactly, which is the whole point here.
module sweep(path, d) {
    for (i = [0 : len(path) - 2]) {
        hull() {
            translate(path[i]) sphere(d = d);
            translate(path[i + 1]) sphere(d = d);
        }
    }
}

// A raised socket standing on the surface normal, which the sprung electrode
// holder press-fits into. mount is [name, position, rotation, phase_one].
module electrode_socket(mount) {
    translate(mount[1]) rotate(mount[2]) {
        translate([0, 0, -socket_h / 2]) cylinder(d = boss_d, h = socket_h + 3);
        // Index nub on the three sockets wired first, so whoever is fitting
        // the cap can find them by feel instead of counting round from Cz.
        // Phase-one sockets get a raised collar rather than a side nub.
        // A nub on the side of the boss points in whatever direction the
        // socket's local frame happens to face, which at Fpz and Cz is
        // straight into a band — present in the model, invisible and
        // unfeelable in the print. The collar extends along the socket axis,
        // away from the skull, where no band ever reaches.
        if (mount[3] == 1)
            translate([0, 0, socket_h / 2 + 3]) cylinder(d = boss_d, h = collar_h);
    }
}

module electrode_bore(mount) {
    translate(mount[1]) rotate(mount[2]) {
        translate([0, 0, -socket_h]) cylinder(d = socket_d, h = socket_h + 12);
    }
}

// Seat for the PPG sensor puck on the temple. Not an electrode: the site was
// chosen for the superficial temporal artery, not for cortex.
module ppg_seat() {
    translate(ppg_mount[0]) rotate(ppg_mount[1])
        translate([0, 0, -socket_h / 2]) cylinder(d = ppg_seat_d + 2 * wall, h = socket_h + 3);
}

module ppg_bore() {
    translate(ppg_mount[0]) rotate(ppg_mount[1])
        translate([0, 0, -socket_h]) cylinder(d = ppg_seat_d, h = socket_h + 12);
}

module pod_pad() {
    translate(pod_anchor[0]) rotate(pod_anchor[1])
        translate([0, 0, -pod_pad_sink])
            linear_extrude(pod_pad_sink + pod_pad_proud)
                offset(4) square([pod_pad_l - 8, pod_pad_w - 8], center = true);
}

// Raised lettering on the outside of the pod pad.
//
// The pad is extruded from -pod_pad_t/2 through pod_pad_t + 2, so its outer
// face sits at +pod_pad_t/2 + 2. Starting the text at pod_pad_t/2 — the
// obvious-looking number — buries it two millimetres inside solid plastic,
// where it renders, exports, and cannot be seen or felt.
module size_badge() {
    translate(pod_anchor[0]) rotate(pod_anchor[1])
        translate([0, -pod_pad_w / 2 + 6, pod_pad_proud])
            // The pad's local x runs along the band, so unrotated text reads
            // sideways to anyone holding the frame the right way up.
            rotate([0, 0, 90])
                linear_extrude(1.2)
                    text(size_label, size = 6.5, halign = "center", valign = "center",
                         font = "Helvetica:style=Bold");
}

module pod_pad_holes() {
    translate(pod_anchor[0]) rotate(pod_anchor[1])
        for (x = [-1, 1], y = [-1, 1])
            translate([x * (pod_pad_l / 2 - 6), y * (pod_pad_w / 2 - 6), -pod_pad_sink - 2])
                cylinder(d = insert_d, h = pod_pad_sink + pod_pad_proud + insert_h + 2);
}

module frame_solid() {
    difference() {
        union() {
            sweep(band_lateral, band_d);
            sweep(band_sagittal, band_d);
            sweep(band_coronal, band_d);
            sweep(band_frontal, band_d);
            sweep(band_parietal, band_d);
            for (m = mounts) electrode_socket(m);
            ppg_seat();
            pod_pad();
            if (size_label != "") size_badge();
        }

        // Hollow the inside to the head. On a scan the liner gap is already
        // baked into the exported surface, so inflating again here would
        // double it and leave the frame floating off her head.
        head_solid(on_scan() ? 0 : liner_gap);

        for (m = mounts) electrode_bore(m);
        ppg_bore();
        pod_pad_holes();

        // Trim anything hanging below the lowest band. On a scan this height
        // comes from the bands themselves: scan coordinates are measured from
        // a centre inside the skull, so the ellipsoid's fixed trim height cuts
        // through the middle of the head and leaves the ring in fragments.
        translate([0, 0, -200 + (on_scan() ? scan_trim_z : trim_z)])
            cube([600, 600, 400], center = true);
    }
}

// A hollow form of the same fitted head, for dry-fitting the frame, routing
// cable, and photographing the build without booking a person for an hour.
// Print at form_scale = 0.5 for a desk model; 1.0 is a real print of a real
// head and will take most of a day and most of a spool.
form_scale = 1.0;
form_wall  = 3.0;

module head_form() {
    scale(form_scale) difference() {
        intersection() {
            head_solid(0);
            translate([0, 0, 200]) cube(400, center = true);   // keep z >= 0
        }
        head_solid(-form_wall);
        // Marks at the three fitted sites, so a dry fit can be checked against
        // where the electrodes are actually supposed to land.
        for (m = mounts)
            translate(m[1]) rotate(m[2]) translate([0, 0, -2]) cylinder(d = 4, h = 6);
        translate(ppg_mount[0]) rotate(ppg_mount[1]) translate([0, 0, -2]) cylinder(d = 6, h = 6);
    }
}

function floor_z() = on_scan() ? scan_trim_z : trim_z;

// One foot: a wide pad tapering up to a thin neck that snaps off.
//
// The pad is deliberately built below the floor and cut flat by the same trim
// plane the frame uses. Deriving a plate height from the ring instead leaves
// the pads hanging in mid-air a few millimetres up, which is what the first
// attempt did — the part still had zero first-layer area and would still have
// failed, while looking like it had feet.
module foot(point) {
    pad_top = floor_z() + foot_pad_h;
    translate([point[0], point[1], floor_z() - 5])
        cylinder(d = foot_pad_d, h = 5 + foot_pad_h);
    hull() {
        translate([point[0], point[1], pad_top - 0.1]) cylinder(d = foot_pad_d, h = 0.1);
        // Terminate on a ball centred on the band's own centreline rather
        // than on a column stopping short of it. Where the band is swept
        // about a centreline lying on the head — as it is without a scan —
        // the hollowing cuts its lower half away, and a column reaching only
        // to the centreline ends in the gap that leaves. The feet printed,
        // looked right, and were not attached to anything.
        translate(point) sphere(d = foot_neck_d);
    }
}

module print_feet() {
    difference() {
        union() { for (f = feet) foot(f); }
        translate([0, 0, -200 + floor_z()]) cube([600, 600, 400], center = true);
    }
}

// A thumb-sized coupon carrying one electrode socket and one insert boss.
// Print it in the corner of the plate first: it takes a few minutes and tells
// you whether the cup electrode presses in and whether the heat-set insert
// seats, before committing six hours to a frame built on the same numbers.
module fit_coupon() {
    difference() {
        union() {
            cube([46, 26, 4], center = true);
            translate([-11, 0, 0]) cylinder(d = boss_d, h = socket_h + 2, center = true);
            translate([13, 0, 0]) cylinder(d = insert_d + 2 * wall + 2, h = 6, center = true);
        }
        translate([-11, 0, -10]) cylinder(d = socket_d, h = 30);
        translate([13, 0, -1]) cylinder(d = insert_d, h = insert_h + 2);
        // Which numbers this coupon was cut with, so a drawer full of them
        // stays meaningful.
        translate([0, -9.5, 2]) linear_extrude(0.8)
            text(str(socket_d, "/", insert_d), size = 3.2, halign = "center",
                 valign = "center", font = "Helvetica:style=Bold");
    }
}

// Feet exist only on a scan build. The reference ellipsoid frame has its
// bands swept about centrelines lying on the surface, so hollowing cuts away
// the lower half and a neck thin enough to snap cannot reach what is left.
if (part == "frame") { frame_solid(); if (feet_on && !is_undef(feet)) print_feet(); }
else if (part == "coupon") fit_coupon();
else if (part == "headform") head_form();
else {
    // Preview: the frame sitting on a ghost of the head it was fitted to.
    frame_solid();
    %head_solid(0);
}
