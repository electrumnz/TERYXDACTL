// Pico 2 control box. part = "box", "lid", "gasket" (TPU) or "plate"
include <../models.scad>
part = "box";

if (part == "box") control_box_model();
else if (part == "lid") translate([0, 0, lid_t]) rotate([180, 0, 0]) box_lid(cb_box_in);
else if (part == "gasket") box_gasket(cb_box_in);
else if (part == "plate") grid_plate(cb_box_in);
