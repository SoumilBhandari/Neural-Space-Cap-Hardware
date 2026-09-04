// Shared parameters for the Neural Space Cap printed parts.
//
// Everything downstream reads from here, so a change to the print tolerance or
// the board dimensions propagates to every part instead of being re-typed.

$fn = 64;

// --- Print tolerances -------------------------------------------------------
// Measured on the team's printer with a fit-test coupon. Re-measure if the
// printer or filament changes; every press-fit in the project depends on it.
clearance      = 0.30;   // free-running fit, part slides in by hand
tight_fit      = 0.12;   // press fit, needs deliberate force
wall           = 2.0;    // general wall thickness, 4 perimeters at 0.5 mm
floor_t        = 1.6;

// --- Fasteners --------------------------------------------------------------
// M2 brass heat-set inserts. The pod gets opened many times over six weeks;
// screwing directly into printed plastic strips out after a handful of cycles.
insert_d       = 3.2;    // hole diameter for the insert to melt into
insert_h       = 4.0;
screw_d        = 2.2;    // clearance for an M2 shaft
screw_head_d   = 4.0;

// --- Head ------------------------------------------------------------------
// Local radius of curvature where the pod sits, from the fitted head model.
// Print `nsc_fit` output and use the c-axis value for the back of the head.
head_radius    = 95;

// --- Electrode -------------------------------------------------------------
// Standard 10 mm silver cup electrode, the type the team already purchased.
cup_d          = 10.0;
cup_h          = 4.0;
cable_d        = 2.2;

// --- PPG sensor ------------------------------------------------------------
// OpenBCI / PulseSensor round board.
ppg_d          = 15.8;
ppg_h          = 3.2;
ppg_window_d   = 9.0;

// --- Electronics -----------------------------------------------------------
// ESP32 devkit and a 500 mAh LiPo. Measure your own boards before printing.
board_l        = 52.0;
board_w        = 28.0;
board_h        = 13.0;
batt_l         = 37.0;
batt_w         = 25.0;
batt_h         = 6.0;

// Sew flange used wherever a part attaches to fabric.
flange_w       = 4.0;
flange_t       = 1.6;
sew_hole_d     = 2.0;
