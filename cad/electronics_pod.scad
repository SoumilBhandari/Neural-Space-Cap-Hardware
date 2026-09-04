// Two-piece enclosure for the ESP32, the SD card and the LiPo.
//
// Sits low at the back of the head, where a hard helmet has clearance and the
// mass does not lever on the neck. The underside is cut to the head's local
// radius so it sits flat against the cap instead of rocking on one edge.
//
// Two rules drove the design:
//
//   The USB port and the SD slot are reachable without opening the shell or
//   taking the cap off. If reflashing means disassembly, nobody reflashes, and
//   firmware stops improving after the first build.
//
//   M2 heat-set inserts, not self-tapping screws into plastic. This gets
//   opened many times over six weeks; a printed thread strips out in about
//   five cycles and then the part is scrap.
//
// Render one part at a time:
//   openscad -D 'part="base"' -o base.stl electronics_pod.scad
//   openscad -D 'part="lid"'  -o lid.stl  electronics_pod.scad

include <params.scad>

part = "both";   // "base", "lid", or "both" for a preview

// OpenSCAD resolves a forward reference to undef rather than reordering, so
// every derived value here must come after the values it is built from.
post_d  = insert_d + 2 * wall;
bay_l   = max(board_l, batt_l) + 2 * clearance + post_d;
bay_w   = board_w + batt_w + 3 * clearance;
bay_h   = max(board_h, batt_h);
pod_l   = bay_l + 2 * wall;
pod_w   = bay_w + 2 * wall;
base_h  = floor_t + bay_h;

module head_curve() {
    // The volume to remove from the underside so the pod matches the skull.
    // Tangent at z = 0, so the floor keeps its full thickness at the centre
    // and only the edges are relieved.
    translate([0, 0, -head_radius])
        rotate([90, 0, 0])
            cylinder(r = head_radius, h = pod_w + 10, center = true);
}

module screw_posts() {
    for (x = [-1, 1], y = [-1, 1]) {
        translate([x * (pod_l / 2 - post_d / 2 - 0.2), y * (pod_w / 2 - post_d / 2 - 0.2), 0])
            children();
    }
}

// Solid columns standing in the bay corners. Without these the insert holes
// would be drilled through 2 mm of side wall into open air, and the inserts
// would have nothing to grip.
module corner_posts() {
    screw_posts() cylinder(d = post_d, h = base_h);
}

module pod_base() {
    // Order matters: the bay is cut from the shell first, then the corner
    // posts are added back, then the head curve and the insert holes are
    // applied to the whole thing. Adding the posts before the bay cut simply
    // deletes them, which is exactly what the first version of this part did.
    difference() {
        union() {
            difference() {
                translate([-pod_l / 2, -pod_w / 2, 0]) cube([pod_l, pod_w, base_h]);

                // Component bay.
                translate([-bay_l / 2, -bay_w / 2, floor_t]) cube([bay_l, bay_w, bay_h + 1]);

                // USB and SD access on the short end, reachable with the pod closed.
                translate([pod_l / 2 - wall - 1, -6, floor_t + 1]) cube([wall + 2, 12, 8]);
                translate([pod_l / 2 - wall - 1, 8, floor_t + 1]) cube([wall + 2, 14, 3.5]);

                // Cable gland for the sensor loom.
                translate([-pod_l / 2 - 1, 0, floor_t + 4])
                    rotate([0, 90, 0]) cylinder(d = 6, h = wall + 2);

                // Status LED light pipe: a 3 mm hole plugged with clear filament.
                translate([-pod_l / 2 + 8, -pod_w / 2 - 1, floor_t + 4])
                    rotate([-90, 0, 0]) cylinder(d = 3, h = wall + 2);
            }
            corner_posts();
        }

        head_curve();
        screw_posts() translate([0, 0, base_h - insert_h])
            cylinder(d = insert_d, h = insert_h + 1);
    }
}

module pod_lid() {
    difference() {
        union() {
            translate([-pod_l / 2, -pod_w / 2, 0]) cube([pod_l, pod_w, wall]);
            // Lip that locates the lid in the bay so it cannot sit skewed.
            translate([0, 0, wall])
                linear_extrude(2)
                    offset(-wall - clearance)
                        square([pod_l, pod_w], center = true);
        }
        screw_posts() {
            translate([0, 0, -1]) cylinder(d = screw_d, h = wall + 5);
            translate([0, 0, -0.1]) cylinder(d1 = screw_head_d, d2 = screw_d, h = 1.4);
        }
    }
}

if (part == "base") pod_base();
else if (part == "lid") pod_lid();
else {
    pod_base();
    translate([0, pod_w + 10, 0]) pod_lid();
}
