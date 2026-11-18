// Everything put together, for a look in OpenSCAD (not for printing).
include <models.scad>
explode = 0;   // try 40 to pull the parts apart

color("DimGray") frame_model();
// the screen: bezel on the front of the panel, body through the cut-out
color([0.1, 0.1, 0.12]) translate([0, 0, frame_D]) rbox(scr_w, scr_h, scr_bezel_t, scr_r);
color([0.1, 0.1, 0.12]) translate([0, 0, frame_D - body_d]) rbox(panel_cut_w - 1, panel_cut_h - 1, body_d, 1);
color([0.15, 0.4, 0.6]) translate([0, 0, frame_D + scr_bezel_t]) rbox(217, 135, 0.3, 1);
color("Gray") translate([0, 0, explode]) hood_model();
color("SlateGray") translate([0, 0, -explode]) back_plate_model();
translate([pi_box_pos[0], pi_box_pos[1], -bp_t - 2 * explode]) mirror([0, 0, 1]) {
    color("DarkSlateGray") pi_box_model();
    color("SlateGray") translate([0, 0, box_out(pi_box_in)[2] + explode]) pi_lid_model();
    if (pi_lid_metal) {
        color("Silver") pi_pillar_model();
        color("Gainsboro") translate([0, 0, box_out(pi_box_in)[2] + 2 * explode]) pi_lid_plate_model();
        color([0.12, 0.12, 0.13]) translate([0, 0, box_out(pi_box_in)[2] + lid_plate_t + 3 * explode]) pi_heatsink_model();
    }
}
