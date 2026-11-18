// Pi box lid plate as a flat 2D outline (DXF), cut from 3 mm aluminium with
// the back plate. The finned heatsink bolts on its outside. Countersink the
// single hole near the middle of the Pi (the pillar screw) on the outside face.
include <../models.scad>
projection(cut = true) translate([0, 0, -lid_plate_t / 2]) pi_lid_plate_model();
