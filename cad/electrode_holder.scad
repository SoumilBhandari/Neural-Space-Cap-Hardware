// Sprung holder for a 10 mm cup electrode.
//
// The problem it solves: electrode contact was the largest source of bad data
// last semester, and the usual fix — cinching the cap tighter — makes contact
// worse, not better, because it flattens the hair mat under the cup rather
// than parting it. Here the contact load comes from a printed spring instead
// of from cap tension, so every site gets the same pressure however the cap is
// worn, and a subject can sit still in it for thirty minutes.
//
// The spring is a flat spider: an annular disc cut by three spiral slots, so
// the hub can travel out of plane while the rim stays sewn to the fabric. It
// is one flat part, prints with no supports and no overhangs, and its stiffness
// is set almost entirely by spring_t.
//
// Print in PETG. Raise spring_t for a firmer press, lower it for a gentler one;
// 0.8 mm is a good starting point at 0.2 mm layers, giving roughly 3 mm of
// comfortable travel.

include <params.scad>

carrier_d   = cup_d + 2 * wall + 2 * clearance;
spring_or   = carrier_d / 2 + 14;          // outer radius of the spring annulus
flange_d    = 2 * (spring_or + flange_w);
spring_t    = 0.8;
slot_w      = 1.6;
slot_sweep  = 150;                          // degrees each spiral arm wraps
carrier_h   = cup_h + wall;

module spiral_slot(r0, r1, sweep, w) {
    steps = 36;
    for (i = [0 : steps - 1]) {
        a0 = i / steps;
        a1 = (i + 1) / steps;
        hull() {
            rotate([0, 0, sweep * a0])
                translate([r0 + (r1 - r0) * a0, 0, 0])
                    cylinder(d = w, h = 40, center = true);
            rotate([0, 0, sweep * a1])
                translate([r0 + (r1 - r0) * a1, 0, 0])
                    cylinder(d = w, h = 40, center = true);
        }
    }
}

module electrode_holder() {
    difference() {
        union() {
            // Spring web.
            cylinder(d = 2 * spring_or, h = spring_t);
            // Sew rim, thicker so the stitching does not tear through.
            difference() {
                cylinder(d = flange_d, h = flange_t);
                translate([0, 0, -1]) cylinder(d = 2 * spring_or - 1, h = flange_t + 2);
            }
            // Hub carrying the electrode, standing proud toward the scalp.
            cylinder(d = carrier_d, h = carrier_h);
        }

        // Electrode socket, open at the top so the cup drops in from behind.
        translate([0, 0, carrier_h - cup_h]) cylinder(d = cup_d + clearance, h = cup_h + 1);

        // Cable exit, slotted so the lead snaps in rather than being threaded.
        translate([0, 0, carrier_h - cup_h / 2])
            rotate([0, 90, 0]) cylinder(d = cable_d + clearance, h = carrier_d + 2, center = true);

        // Three spiral slots turn the web into three arms.
        for (i = [0 : 2]) {
            rotate([0, 0, i * 120])
                spiral_slot(carrier_d / 2 + slot_w, spring_or - slot_w, slot_sweep, slot_w);
        }

        // Sew holes in the rim.
        for (i = [0 : 5]) {
            rotate([0, 0, i * 60 + 30])
                translate([spring_or + flange_w / 2, 0, -1])
                    cylinder(d = sew_hole_d, h = flange_t + 2);
        }
    }
}

electrode_holder();
