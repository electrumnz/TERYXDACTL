// Teryx OS printed parts, drawn where they sit on the dash.
// z = 0 is the back face of the frame flange; the screen faces +z (towards
// the driver). The parts/ files turn these round for printing.

include <lib.scad>

// ---------------------------------------------------------------------------
// Front frame: a tray the screen drops into from the back
// ---------------------------------------------------------------------------
module frame_model() {
    difference() {
        union() {
            rbox(frame_out_w, frame_out_h, frame_D, frame_out_r);
            rbox(fl_w, fl_h, frame_flange_t, fl_r);
            // 45 degree support under the flange so it prints face down
            // without supports
            hull() {
                translate([0, 0, frame_flange_t - e]) rbox(fl_w, fl_h, e, fl_r);
                translate([0, 0, frame_flange_t + frame_flange_w]) rbox(frame_out_w, frame_out_h, e, frame_out_r);
            }
        }
        // pocket for the screen
        translate([0, 0, -1]) rbox(cav_w, cav_h, frame_D - frame_front_t + 1, cav_r);
        // window, bevelled outwards so the edge doesn't shade the picture
        translate([scr_view_off_x, scr_view_off_y, 0]) hull() {
            translate([0, 0, frame_D - frame_front_t - e]) rbox(scr_view_w, scr_view_h, e, 2);
            translate([0, 0, frame_D]) rbox(scr_view_w + 2 * frame_front_t, scr_view_h + 2 * frame_front_t, e + 1, 2 + frame_front_t);
        }
        // recess for the sun hood's back strip
        translate([0, 0, -e]) linear_extrude(hood_t + 0.2) intersection() {
            offset(delta = 0.3) hood_strip_2d();
            difference() { square(2000, center = true); rrect(frame_out_w, frame_out_h, frame_out_r); }
        }
        // heat-set inserts for the back plate bolts
        for (p = bp_bolts) translate([p[0], p[1], -e]) cylinder(d = m3_insert_d, h = hood_t + m3_insert_deep);
        // drain slots in the bottom wall, just behind the front lip
        for (x = [-cav_w / 4, cav_w / 4])
            translate([x - 10, -frame_out_h / 2 - 1, frame_D - frame_front_t - 4])
                cube([20, frame_wall + 2, 3]);
        // alignment pin holes across the seam
        if (frame_split) for (s = [-1, 1])
            translate([frame_split_x - 8, s * fl_mid_y, hood_t + (frame_flange_t - hood_t) / 2])
                rotate([0, 90, 0]) cylinder(d = pin_d + 0.2, h = 16, $fn = 16);
    }
}

// ---------------------------------------------------------------------------
// Back plate: clamps the screen in, carries the Pi box, bolts to the dash
// ---------------------------------------------------------------------------
amps_pts = [for (sx = [-1, 1]) for (sy = [-1, 1]) [dash_amps_pos[0] + sx * 19, dash_amps_pos[1] + sy * 15]];

module back_plate_model() {
    pib = [for (p = box_ear_pts(pi_box_in)) [p[0] + pi_box_pos[0], p[1] + pi_box_pos[1]]];
    difference() {
        translate([0, 0, -bp_t]) rbox(fl_w, fl_h, bp_t, fl_r);
        for (p = bp_bolts) translate([p[0], p[1], -bp_t - 1]) cylinder(d = m3_clear, h = bp_t + 2);
        translate([scr_cable_x, scr_cable_y, -bp_t - 1]) cylinder(d = scr_cable_d, h = bp_t + 2);
        if (scr_has_vesa) for (sx = [-1, 1], sy = [-1, 1])
            translate([sx * scr_vesa / 2, sy * scr_vesa / 2, -bp_t - 1]) cylinder(d = scr_vesa_clear, h = bp_t + 2);
        for (p = pib) translate([p[0], p[1], -bp_t - 1]) cylinder(d = ear_hole, h = bp_t + 2);
        for (p = dash_holes) translate([p[0], p[1], -bp_t - 1]) cylinder(d = dash_hole_d, h = bp_t + 2);
        if (dash_amps) for (p = amps_pts) translate([p[0], p[1], -bp_t - 1]) cylinder(d = m5_clear, h = bp_t + 2);
        if (bp_split) for (y = linspace(-fl_h / 2 + 20, fl_h / 2 - 20, 4))
            translate([bp_split_x - 8, y + 6, -bp_t / 2]) rotate([0, 90, 0]) cylinder(d = pin_d + 0.2, h = 16, $fn = 16);
    }
}

// ---------------------------------------------------------------------------
// Sun hood: top shade and side cheeks, held by its back strip
// ---------------------------------------------------------------------------
hood_z1  = frame_D + hood_reach;                   // front edge of the top
hood_len = hood_z1 / cos(hood_tilt);
hood_y0  = hood_in_h / 2;                          // underside of the top at the back

module hood_model() {
    intersection() { translate([-1000, -1000, 0]) cube(2000); difference() {
        union() {
            linear_extrude(hood_t) hood_strip_2d();
            // top
            translate([-hood_out_w / 2, hood_y0, 0]) rotate([-hood_tilt, 0, 0]) cube([hood_out_w, hood_t, hood_len]);
            // cheeks
            for (s = [-1, 1]) translate([s < 0 ? -hood_out_w / 2 : hood_in_w / 2, 0, 0])
                rotate([90, 0, 90]) linear_extrude(hood_t) polygon([
                    [hood_low_y, 0],
                    [hood_y0 + hood_t, 0],
                    [hood_y0 + hood_t + hood_z1 * tan(hood_tilt), hood_z1],
                    [hood_y0, hood_z1]
                ]);
        }
        for (p = bp_bolts) if (in_hood_strip(p)) translate([p[0], p[1], -1]) cylinder(d = m3_clear, h = hood_t + 2);
        if (hood_split) hood_splice_holes();
    } }
}

// Splice strip that bolts across the hood's seam (M3 bolts and nuts)
module hood_splice_holes() {
    translate([0, hood_y0, 0]) rotate([-hood_tilt, 0, 0])
        for (dx = [-12, 12], f = [0.3, 0.75]) translate([hood_split_x + dx, -5, hood_len * f]) rotate([-90, 0, 0]) cylinder(d = m3_clear, h = 20);
}

module hood_splice_model() {
    difference() {
        translate([0, hood_y0, 0]) rotate([-hood_tilt, 0, 0])
            translate([hood_split_x - 20, hood_t, hood_len * 0.15]) cube([40, 3, hood_len * 0.75]);
        hood_splice_holes();
    }
}

// ---------------------------------------------------------------------------
// Pi 5 box. Floor (z = 0) bolts flat to the back of the back plate.
// ---------------------------------------------------------------------------
pi_hole_pts = [for (sx = [-1, 1], sy = [-1, 1]) [pi_pos[0] + sx * pi_holes[0] / 2, pi_pos[1] + sy * pi_holes[1] / 2]];
pi_cable    = [scr_cable_x - pi_box_pos[0], scr_cable_y - pi_box_pos[1]];  // screen cable hole, box coords

module pi_box_model() {
    in = pi_box_in;
    difference() {
        union() {
            sealed_box(in, pi_glands);
            for (p = pi_hole_pts) translate([p[0], p[1], 0]) cylinder(d = 6.5, h = box_floor + pi_standoff);
        }
        for (p = pi_hole_pts) translate([p[0], p[1], box_floor + pi_standoff - 5]) cylinder(d = m25_insert_d, h = 10);
        // screen cables come straight in through the floor, sealed with a
        // gasket against the back plate
        translate([pi_cable[0], pi_cable[1], -1]) cylinder(d = scr_cable_d, h = box_floor + 2);
        translate([pi_cable[0], pi_cable[1], -e]) linear_extrude(groove_d)
            difference() { circle(d = scr_cable_d + 6 + groove_w); circle(d = scr_cable_d + 6 - groove_w); }
        // air vents, louvred so the outside opening points down
        for (sx = [-1, 1], y = linspace(-in[1] / 2 + 10, -4, 4))
            translate([sx * (in[0] / 2 + box_wall / 2), y, box_floor + in[2] / 2])
                rotate([0, 0, -sx * 35]) cube([box_wall * 3, 2.4, in[2] - 18], center = true);
    }
}

module pi_lid_model() {
    in = pi_box_in;
    difference() {
        box_lid(in);
        if (pi_fan > 0) translate([pi_pos[0], pi_pos[1], 0]) {
            for (sx = [-1, 1], sy = [-1, 1]) translate([sx * pi_fan_hole / 2, sy * pi_fan_hole / 2, -2]) cylinder(d = m3_clear, h = lid_t + 4);
            // grille
            intersection() {
                translate([0, 0, -2]) cylinder(d = pi_fan - 3, h = lid_t + 4);
                for (i = [-6 : 6], j = [-6 : 6]) translate([i * 4.5 + (j % 2) * 2.25, j * 3.9, -2]) cylinder(d = 3.4, h = lid_t + 4, $fn = 6);
            }
        }
    }
}

// Rain cowl over the fan, open at the bottom. The fan screws go through it,
// the lid and the fan. Drawn flange down at z = 0.
module pi_cowl_model() {
    w = pi_fan + 10;
    difference() {
        union() {
            translate([-w / 2, -w / 2, 0]) cube([w, w, 2]);
            translate([-w / 2, -w / 2, 0]) cube([w, w, 14]);
        }
        translate([-(w - 4) / 2, -w / 2 - 1, 2]) cube([w - 4, w - 1, 10]);  // open to -y (down)
        translate([0, 0, -1]) cylinder(d = pi_fan - 3, h = 4);
        for (sx = [-1, 1], sy = [-1, 1]) translate([sx * pi_fan_hole / 2, sy * pi_fan_hole / 2, -1]) cylinder(d = m3_clear, h = 4);
    }
}

// ---------------------------------------------------------------------------
// Control box and relay box
// ---------------------------------------------------------------------------
module control_box_model() { union() { sealed_box(cb_box_in, cb_glands); grid_posts(cb_box_in); } }
module relay_box_model()   { union() { sealed_box(rb_box_in, rb_glands); grid_posts(rb_box_in); } }

relay_c = [0, rb_box_in[1] / 2 - relay_board[1] / 2 - 14];
relay_keep = [for (sx = [-1, 1], sy = [-1, 1]) [relay_c[0] + sx * relay_holes[0] / 2, relay_c[1] + sy * relay_holes[1] / 2, grid_hole]];
