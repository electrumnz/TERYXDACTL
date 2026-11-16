// Sun hood. Prints standing on its back strip, no supports.
// part = "whole", "left", "right" or "splice"
include <../models.scad>
part = "whole";

if (part == "whole") hood_model();
else if (part == "splice") translate([0, 0, -hood_t]) rotate([90, 0, 0]) rotate([hood_tilt, 0, 0]) translate([0, -hood_y0, 0]) hood_splice_model();
else half(hood_split_x, part == "left" ? -1 : 1) hood_model();
