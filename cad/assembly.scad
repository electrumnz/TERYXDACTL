// Everything put together, for a look in OpenSCAD (not for printing).
include <models.scad>
explode = 0;   // try 40 to pull the parts apart

color("DimGray") frame_model();
color([0.1, 0.1, 0.12]) translate([0, 0, frame_D - frame_front_t - gasket_t * 0.7 - scr_d]) rbox(scr_w, scr_h, scr_d, scr_r);
color([0.15, 0.4, 0.6]) translate([scr_view_off_x, scr_view_off_y, frame_D - frame_front_t - 0.5]) rbox(scr_view_w - 4, scr_view_h - 4, 0.5, 1);
color("Gray") translate([0, 0, explode]) hood_model();
color("SlateGray") translate([0, 0, -explode]) back_plate_model();
translate([pi_box_pos[0], pi_box_pos[1], -bp_t - 2 * explode]) mirror([0, 0, 1]) {
    color("DarkSlateGray") pi_box_model();
    color("SlateGray") translate([0, 0, box_out(pi_box_in)[2] + explode]) pi_lid_model();
    if (pi_fan > 0) color("Gray") translate([pi_pos[0], pi_pos[1], box_out(pi_box_in)[2] + lid_t + 2 * explode]) pi_cowl_model();
}
