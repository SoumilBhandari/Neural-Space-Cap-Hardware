// The cap frame: the part that actually goes on a head.
//
// A closed ring around the head at Fpz/Oz level, braced by two arches — over
// the top and ear to ear — following the International 10-20 arcs of one
// specific person's skull. It carries electrode sockets at O1, O2 and Fp1 and
// a pad for the electronics pod behind Oz.
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

part = "preview";   // "frame", "headform", "preview"

band_d      = 11.0;   // swept diameter of a band
liner_gap   = 2.5;    // clearance for the fabric liner and hair
trim_z      = 8.0;    // nothing hangs below this height above the landmarks

socket_d    = cup_d + 2 * wall + 2 * clearance;   // matches the holder hub
socket_h    = 7.0;
boss_d      = socket_d + 2 * wall + 2;

pod_pad_l   = 46;
pod_pad_w   = 34;
pod_pad_t   = 5;

module head_solid(grow = 0) {
    scale([head_axes[0] + grow, head_axes[1] + grow, head_axes[2] + grow]) sphere(r = 1);
}

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
// holder press-fits into.
module electrode_socket(mount) {
    translate(mount[0]) rotate(mount[1]) {
        translate([0, 0, -socket_h / 2]) cylinder(d = boss_d, h = socket_h + 3);
    }
}

module electrode_bore(mount) {
    translate(mount[0]) rotate(mount[1]) {
        translate([0, 0, -socket_h]) cylinder(d = socket_d, h = socket_h + 12);
    }
}

module pod_pad() {
    translate(pod_anchor[0]) rotate(pod_anchor[1])
        translate([0, 0, -pod_pad_t / 2])
            linear_extrude(pod_pad_t + 2)
                offset(4) square([pod_pad_l - 8, pod_pad_w - 8], center = true);
}

module pod_pad_holes() {
    translate(pod_anchor[0]) rotate(pod_anchor[1])
        for (x = [-1, 1], y = [-1, 1])
            translate([x * (pod_pad_l / 2 - 6), y * (pod_pad_w / 2 - 6), -pod_pad_t])
                cylinder(d = insert_d, h = pod_pad_t + insert_h + 2);
}

module frame_solid() {
    difference() {
        union() {
            sweep(band_lateral, band_d);
            sweep(band_sagittal, band_d);
            sweep(band_coronal, band_d);
            electrode_socket(mount_O1);
            electrode_socket(mount_O2);
            electrode_socket(mount_Fp1);
            pod_pad();
        }

        // Hollow the inside to the head, plus room for the liner and hair.
        head_solid(liner_gap);

        electrode_bore(mount_O1);
        electrode_bore(mount_O2);
        electrode_bore(mount_Fp1);
        pod_pad_holes();

        // Trim anything hanging below the landmark plane.
        translate([0, 0, -200 + trim_z]) cube([600, 600, 400], center = true);
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
        for (m = [mount_O1, mount_O2, mount_Fp1])
            translate(m[0]) rotate(m[1]) translate([0, 0, -2]) cylinder(d = 4, h = 6);
    }
}

if (part == "frame") frame_solid();
else if (part == "headform") head_form();
else {
    // Preview: the frame sitting on a ghost of the head it was fitted to.
    frame_solid();
    %head_solid(0);
}
