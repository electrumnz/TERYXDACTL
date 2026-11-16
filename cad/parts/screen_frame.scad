// Front frame that holds the screen. Prints face down, no supports.
// part = "whole", "left" or "right" (cad/build.sh picks for you)
include <../models.scad>
part = "whole";

module printable() { translate([0, 0, frame_D]) rotate([0, 180, 0]) frame_model(); }

if (part == "whole") printable();
// rotate([0,180,0]) swaps left and right, so cut the model before turning it
else translate([0, 0, frame_D]) rotate([0, 180, 0]) half(frame_split_x, part == "left" ? -1 : 1) frame_model();
