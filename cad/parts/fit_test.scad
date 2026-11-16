// Quick test print: one corner of the front frame (about an hour).
// Checks the screen's corner radius, depth, lip and insert holes before you
// commit to the full print.
include <../models.scad>

translate([0, 0, frame_D]) rotate([0, 180, 0]) intersection() {
    frame_model();
    translate([fl_w / 2 - 70, fl_h / 2 - 70, -1]) cube([100, 100, 200]);
}
