// Pi 5 box. part = "box", "lid", "cowl" (fan rain cover) or "gasket" (TPU)
include <../models.scad>
part = "box";

if (part == "box") pi_box_model();
else if (part == "lid") translate([0, 0, lid_t]) rotate([180, 0, 0]) pi_lid_model();
else if (part == "cowl" && pi_fan > 0) pi_cowl_model();
else if (part == "gasket") box_gasket(pi_box_in);
