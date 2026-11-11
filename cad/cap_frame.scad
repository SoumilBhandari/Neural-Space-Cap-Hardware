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
badge_depth   = 2 * layer_h;
badge_size    = 4.0;

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
    // The three sockets wired first stand collar_h taller than the rest, so
    // whoever is fitting the cap can find them by feel. One cylinder, not a
    // boss with a second cylinder stacked on it: two solids meeting on a
    // shared face are exactly the kind of contact that comes out of a union
    // as coincident vertices and then reads as non-manifold in a slicer.
    tall = socket_h + 3 + (mount[3] == 1 ? collar_h : 0);
    translate(mount[1]) rotate(mount[2])
        translate([0, 0, -socket_h / 2]) cylinder(d = boss_d, h = tall);
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

// Size lettering cut into the outside of the pod pad.
//
// The pad is extruded from -pod_pad_t/2 through pod_pad_t + 2, so its outer
// face sits at +pod_pad_t/2 + 2. Starting the text at pod_pad_t/2 — the
// obvious-looking number — buries it two millimetres inside solid plastic,
// where it renders, exports, and cannot be seen or felt.
module size_badge() {
    translate(pod_anchor[0]) rotate(pod_anchor[1])
        // Engraved, two layers deep. It used to stand 1.2 mm proud, and on a
        // face tilted 62 degrees every stroke of every digit had its own
        // little overhang. The slicer grew a support tip for them, could not
        // route it down past the pad, and reported a lost branch. A cut this
        // shallow needs no support at all.
        //
        // The cutter starts badge_depth inside the face and runs out past
        // it, so it never ends on the face itself.
        // Centred in the strip of pad left clear between its edge and the
        // sagittal band, and sized to fit there. At 6.5 mm the number ran
        // off the edge on one side and under the band on the other.
        translate([0, -(pod_pad_w / 2 + band_d / 2) / 2, pod_pad_proud - badge_depth])
            // The pad's local x runs along the band, so unrotated text reads
            // sideways to anyone holding the frame the right way up.
            rotate([0, 0, 90])
                linear_extrude(badge_depth + 1)
                    text(size_label, size = badge_size, halign = "center", valign = "center",
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
            if (on_scan()) {
                // One closed tube mesh per band, generated with the fit. The
                // hull-chain sweep below shares a sphere between neighbouring
                // hulls, and those coincident surfaces survive the union.
                for (f = band_files) import(f, convexity = 10);
            } else {
                sweep(band_lateral, band_d);
                sweep(band_sagittal, band_d);
                sweep(band_coronal, band_d);
                sweep(band_frontal, band_d);
                sweep(band_parietal, band_d);
            }
            for (m = mounts) electrode_socket(m);
            ppg_seat();
            pod_pad();
        }

        // Hollow the inside to the head. On a scan the liner gap is already
        // baked into the exported surface, so inflating again here would
        // double it and leave the frame floating off her head.
        head_solid(on_scan() ? 0 : liner_gap);

        for (m = mounts) electrode_bore(m);
        ppg_bore();
        pod_pad_holes();
        if (size_label != "") size_badge();

        // Slice everything off flat at the build plate. On a scan this plane
        // sits 3.8 mm below the ring's centreline, which leaves the ring a
        // flat underside to print on all the way round and keeps every part
        // of it within 45 degrees of vertical.
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

// A thumb-sized coupon carrying one electrode socket and one insert boss.
// Print it in the corner of the plate first: it takes a few minutes and tells
// you whether the cup electrode presses in and whether the heat-set insert
// seats, before committing a whole frame print to the same numbers.
module fit_coupon() {
    // Everything starts on z = 0 so the whole coupon sits on the bed. The
    // bosses used to be centred on the plate, which left the plate floating
    // a few millimetres up.
    plate_t = 4;
    insert_boss_h = insert_h + floor_t;
    difference() {
        union() {
            translate([0, 0, plate_t / 2]) cube([46, 26, plate_t], center = true);
            translate([-11, 0, 0]) cylinder(d = boss_d, h = socket_h + 2);
            translate([13, 0, 0]) cylinder(d = insert_d + 2 * wall + 2, h = insert_boss_h);
        }
        translate([-11, 0, -1]) cylinder(d = socket_d, h = socket_h + 4);
        // Blind from the top, the way the insert goes into the pod pad.
        translate([13, 0, floor_t]) cylinder(d = insert_d, h = insert_h + 1);
        // Which numbers this coupon was cut with, so a drawer full of them
        // stays meaningful. Engraved three layers deep into the top face.
        // Kept to the insert end of the plate, clear of the socket boss.
        translate([11, -9.5, plate_t - 0.6]) linear_extrude(1)
            text(str(socket_d, "/", insert_d), size = 3.0, halign = "center",
                 valign = "center", font = "Helvetica:style=Bold");
    }
}

if (part == "frame") frame_solid();
else if (part == "coupon") fit_coupon();
else if (part == "headform") head_form();
else {
    // Preview: the frame sitting on a ghost of the head it was fitted to.
    frame_solid();
    %head_solid(0);
}
