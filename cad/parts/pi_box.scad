// Pi 5 box. part = "box", "lid" (the printed liner that hangs under the
// aluminium lid plate, or the old printed lid if pi_lid_metal = false) or
// "gasket" (TPU). The aluminium lid plate itself is a DXF: parts/pi_lid_2d.scad
include <../models.scad>
part = "box";

if (part == "box") pi_box_model();
else if (part == "lid") {
    if (pi_lid_metal) rotate([180, 0, 0]) pi_lid_model();
    else translate([0, 0, lid_t]) rotate([180, 0, 0]) pi_lid_model();
}
else if (part == "gasket") box_gasket(pi_box_in);
