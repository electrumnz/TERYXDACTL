// Relay box (8-channel relay board + BTS7960 drivers).
// part = "box", "lid", "gasket" (TPU) or "plate"
include <../models.scad>
part = "box";

if (part == "box") relay_box_model();
else if (part == "lid") translate([0, 0, lid_t]) rotate([180, 0, 0]) box_lid(rb_box_in);
else if (part == "gasket") box_gasket(rb_box_in);
else if (part == "plate") grid_plate(rb_box_in, relay_keep);
