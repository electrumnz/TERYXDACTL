// Back plate: clamps the screen into the frame, carries the Pi box and
// bolts to the dash. Prints flat.
// part = "whole", "left" or "right"
include <../models.scad>
part = "whole";

translate([0, 0, bp_t])
    if (part == "whole") back_plate_model();
    else half(bp_split_x, part == "left" ? -1 : 1) back_plate_model();
