// Carrier for the PPG heart-rate sensor, with a light shroud.
//
// Two jobs. First, repeatable position: a sensor taped to a temple with a
// bandaid — which is how the Spring data was collected — sits somewhere
// slightly different every session, and that movement is indistinguishable
// from the subject's perfusion changing. This sews to the cap liner so the
// sensor returns to the same spot.
//
// Second, the shroud. PPG works by measuring light reflected back from
// blood under the skin, so any ambient light reaching the photodiode adds
// directly to the signal. A light leak at the temple looks exactly like a
// weak pulse, and no amount of filtering downstream separates the two.

include <params.scad>

shroud_h    = 3.0;     // how far the rim stands proud of the board face
body_d      = ppg_d + 2 * wall + 2 * clearance;
body_h      = ppg_h + floor_t + shroud_h;

module sensor_puck() {
    difference() {
        union() {
            cylinder(d = body_d, h = body_h);
            translate([0, 0, body_h - flange_t]) sew_ears();
        }

        // Board cavity, open at the top so the sensor drops in from behind.
        translate([0, 0, floor_t + shroud_h])
            cylinder(d = ppg_d + clearance, h = ppg_h + 1);

        // Optical window through to the skin.
        translate([0, 0, -1]) cylinder(d = ppg_window_d, h = floor_t + shroud_h + 2);

        // Cable exit with a strain-relief channel. Every wire that failed last
        // semester failed where it left a connector unsupported.
        translate([0, 0, floor_t + shroud_h + ppg_h / 2])
            rotate([0, 90, 0])
                cylinder(d = cable_d + clearance, h = body_d + 2, center = true);
    }
}

// Two flat ears with sew holes, rather than a full ring: the puck sits on a
// curved surface and a full flange would lift off the fabric at the sides.
module sew_ears() {
    for (side = [-1, 1]) {
        difference() {
            hull() {
                cylinder(d = body_d, h = flange_t);
                translate([side * (body_d / 2 + flange_w), 0, 0])
                    cylinder(d = flange_w * 2, h = flange_t);
            }
            translate([side * (body_d / 2 + flange_w), 0, -1])
                cylinder(d = sew_hole_d, h = flange_t + 2);
        }
    }
}

sensor_puck();
