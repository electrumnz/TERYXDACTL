// Back plate as a flat 2D outline (DXF), for having it cut from 3 mm
// aluminium instead of printing it. Stiffer, and the better choice for
// carrying a 2.8 kg screen off-road.
include <../models.scad>
projection(cut = true) translate([0, 0, bp_t / 2]) back_plate_model();
