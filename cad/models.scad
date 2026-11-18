// Teryx OS printed parts, drawn where they sit on the dash.
// z = 0 is the back face of the frame flange; the screen faces +z (towards
// the driver). The parts/ files turn these round for printing.

include <lib.scad>

// ---------------------------------------------------------------------------
// Dash panel: flat face with the cut-out, a rim round the back that boxes in
// the screen's body, and ribs to stop it flexing. The screen's bezel sits on
// the front; its clips clamp it from behind.
// ---------------------------------------------------------------------------
panel_back = frame_D - panel_t;          // z of the back face of the panel
clip_w = cut_w + 2 * clip_room;          // keep this area clear for the clips
clip_h = cut_h + 2 * clip_room;

module frame_ribs() {
    // ring round the clip area, then ribs out to the rim
    translate([0, 0, panel_back - rib_d]) linear_extrude(rib_d + e) {
        rring(clip_w + rib_t, clip_h + rib_t, 3, rib_t);
        difference() {
            union() {
                for (x = [-clip_w / 4, clip_w / 4]) translate([x - rib_t / 2, -fl_h / 2]) square([rib_t, fl_h]);
                translate([-fl_w / 2, -rib_t / 2]) square([fl_w, rib_t]);
                for (sx = [-1, 1], sy = [-1, 1])   // corner braces
                    translate([sx * clip_w / 2, sy * clip_h / 2]) rotate(sx * sy * 45) square([rib_t, 80], center = true);
            }
            rrect(clip_w, clip_h, 3);
        }
    }
}

module frame_model() {
    difference() {
        union() {
            difference() {
                rbox(fl_w, fl_h, frame_D, fl_r);
                translate([0, 0, -1]) rbox(fl_w - 2 * frame_wall, fl_h - 2 * frame_wall, panel_back + 1, fl_r - frame_wall);
            }
            intersection() {
                union() {
                    frame_ribs();
                    // bosses for the back plate bolts
                    for (p = bp_bolts) translate([p[0], p[1], 0]) cylinder(d = 10, h = frame_D);
                }
                rbox(fl_w, fl_h, frame_D, fl_r);
            }
        }
        // cut-out for the screen's body
        translate([0, 0, -1]) rbox(cut_w, cut_h, frame_D + 2, panel_cut_r);
        // shallow recess so the bezel sits square and the foam is protected
        translate([0, 0, frame_D - 1]) rbox(cav_w, cav_h, 2, cav_r);
        // recess for the sun hood's back strip
        translate([0, 0, -e]) linear_extrude(hood_t + 0.2) offset(delta = 0.3) hood_strip_2d();
        // heat-set inserts for the back plate bolts
        for (p = bp_bolts) translate([p[0], p[1], -e]) cylinder(d = m3_insert_d, h = hood_t + m3_insert_deep + 4);  // room for an M3 x 16
        // weep holes in the bottom of the rim
        for (x = [-fl_w / 4, fl_w / 4]) translate([x, -fl_h / 2 - 1, panel_back - 4]) rotate([-90, 0, 0]) cylinder(d = 4, h = frame_wall + 2);
        // alignment pin holes across the seam
        if (frame_split) for (s = [-1, 1], z = [panel_back / 3, 2 * panel_back / 3])
            translate([frame_split_x - 8, s * (fl_h / 2 - frame_wall / 2), z])
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
        // M4 nut pockets on the front face (the nuts end up behind the screen)
        for (p = pib) translate([p[0], p[1], -3.4]) cylinder(d = 8.1, h = 5, $fn = 6);
        for (p = dash_holes) translate([p[0], p[1], -bp_t - 1]) cylinder(d = dash_hole_d, h = bp_t + 2);
        if (dash_amps) for (p = amps_pts) translate([p[0], p[1], -bp_t - 1]) cylinder(d = m5_clear, h = bp_t + 2);
        if (dash_amps) for (p = amps_pts) translate([p[0], p[1], -4.2]) cylinder(d = 9.4, h = 5, $fn = 6);  // M5 nut pockets
        if (bp_split) for (y = linspace(-fl_h / 2 + 20, fl_h / 2 - 20, 4))
            translate([bp_split_x - 8, y + 6, -bp_t / 2]) rotate([0, 90, 0]) cylinder(d = pin_d + 0.2, h = 16, $fn = 16);
    }
}

// ---------------------------------------------------------------------------
// Sun hood: top shade and side cheeks, held by its back strip
// ---------------------------------------------------------------------------
hood_z1  = frame_D + scr_bezel_t + hood_reach;     // front edge of the top
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
dac_hole_pts = dac_on ? [for (sx = [-1, 1], sy = [-1, 1]) [dac_pos[0] + sx * dac_holes[0] / 2, dac_pos[1] + sy * dac_holes[1] / 2]] : [];
pi_cable    = [scr_cable_x - pi_box_pos[0], scr_cable_y - pi_box_pos[1]];  // screen cable hole, box coords
// heads of the screen's wall-bracket bolts that end up under the Pi box
pi_vesa = scr_has_vesa ? [for (sx = [-1, 1], sy = [-1, 1]) let (p = [sx * scr_vesa / 2 - pi_box_pos[0], sy * scr_vesa / 2 - pi_box_pos[1]])
    if (abs(p[0]) < pi_box_in[0] / 2 + box_wall && abs(p[1]) < pi_box_in[1] / 2 + box_wall) p] : [];

// Micro HDMI cradle, box coords. The plug points -Y off the Pi's bottom edge.
hdmi_pos  = [pi_pos[0] - pi_board[0] / 2 + pi_hdmi0_x, pi_pos[1] - pi_board[1] / 2];  // socket mouth, board edge
hdmi_cz   = box_floor + pi_standoff + pi_pcb_t + hdmi_port_h / 2;   // height of the plug's centre line
hdmi_bed  = hdmi_cz - hdmi_plug[1] / 2 - hdmi_pad;                  // top of the cradle
hdmi_gap  = 0.5;          // clear of the board edge so the Pi still lifts out
hdmi_cheek = 1.8;
tie_w = 4.2; tie_h = 1.8; // tunnel for a 3.6 mm cable tie
hdmi_anchor_y = hdmi_pos[1] - hdmi_gap - hdmi_plug[2] - 9;          // cable tie anchor, past the plug

module hdmi_cradle() {
    L = hdmi_plug[2] - 2;
    W = hdmi_plug[0] + 1;                       // channel between the cheeks
    y0 = hdmi_pos[1] - hdmi_gap;                // end nearest the Pi
    translate([hdmi_pos[0], 0, 0]) difference() {
        union() {
            // bed under the plug
            translate([-W / 2 - hdmi_cheek, y0 - L, box_floor - e]) cube([W + 2 * hdmi_cheek, L, hdmi_bed - box_floor + e]);
            // cheeks either side, up to the plug's centre line, keep it square to the socket
            for (s = [-1, 1]) translate([s > 0 ? W / 2 : -W / 2 - hdmi_cheek, y0 - L, box_floor - e])
                cube([hdmi_cheek, L, hdmi_cz - box_floor + e]);
            // anchor for the second tie, round the cable
            translate([-5, hdmi_anchor_y - 4, box_floor - e]) cube([10, 8, hdmi_cz - hdmi_cable_d / 2 - box_floor + e]);
        }
        // tie tunnels along X, sitting on the floor
        translate([-50, y0 - L / 2 - tie_w / 2, box_floor - 2 * e]) cube([100, tie_w, tie_h]);
        translate([-50, hdmi_anchor_y - tie_w / 2, box_floor - 2 * e]) cube([100, tie_w, tie_h]);
        // shallow groove so the cable sits centred on the anchor
        translate([0, hdmi_anchor_y + 5, hdmi_cz]) rotate([90, 0, 0]) cylinder(d = hdmi_cable_d + 0.8, h = 10);
    }
}

module pi_box_model() {
    in = pi_box_in;
    difference() {
        union() {
            sealed_box(in, pi_glands);
            if (hdmi_clamp) hdmi_cradle();
            for (p = pi_hole_pts) translate([p[0], p[1], 0]) cylinder(d = 6.5, h = box_floor + pi_standoff);
            for (p = dac_hole_pts) translate([p[0], p[1], 0]) cylinder(d = 6.5, h = box_floor + dac_standoff);
            for (p = pi_vesa) translate([p[0], p[1], 0]) cylinder(d = 13, h = box_floor + 3);
        }
        // pockets underneath for the bolt heads (M4 socket head, 7 x 4 mm)
        for (p = pi_vesa) translate([p[0], p[1], -e]) cylinder(d = 8.5, h = 4.5);
        for (p = pi_hole_pts) translate([p[0], p[1], box_floor + pi_standoff - 5]) cylinder(d = m25_insert_d, h = 10);
        for (p = dac_hole_pts) translate([p[0], p[1], box_floor + dac_standoff - 5]) cylinder(d = m25_insert_d, h = 10);
        // screen cables come straight in through the floor, sealed with a
        // gasket against the back plate
        translate([pi_cable[0], pi_cable[1], -1]) cylinder(d = scr_cable_d, h = box_floor + 2);
        translate([pi_cable[0], pi_cable[1], -e]) linear_extrude(groove_d)
            difference() { circle(d = scr_cable_d + 6 + groove_w); circle(d = scr_cable_d + 6 - groove_w); }
        // SMA bulkheads for the 4G aerials, right-hand wall
        if (modem_on) for (h = sma_holes) translate([in[0] / 2 - 1, h[0], h[1]]) rotate([0, 90, 0]) {
            cylinder(d = sma_hole, h = box_wall + 2);
            // ID ring engraved on the outside face
            if (h[2] == 1) translate([0, 0, 1 + box_wall - 0.6]) difference() { cylinder(d = 17, h = 1); cylinder(d = 15, h = 1); }
        }
    }
}

// 4G board, its buck and capacitor on the inside of the lid (z < 0 hangs into
// the box). Printed with the lid.
modem_hole_pts = [for (sx = [-1, 1], sy = [-1, 1]) [modem_pos[0] + sx * modem_holes[0] / 2, modem_pos[1] + sy * modem_holes[1] / 2]];
module tie_pad(size, h) {   // pad with a cable-tie tunnel across it (along X), at the lid face
    difference() {
        translate([-size[0] / 2, -size[1] / 2, -h]) cube([size[0], size[1], h + e]);
        translate([-size[0] / 2 - 1, -tie_w / 2, -tie_h + e]) cube([size[0] + 2, tie_w, tie_h]);
    }
}
module modem_mount() {
    difference() {
        for (p = modem_hole_pts) translate([p[0], p[1], -modem_gap]) cylinder(d = 6, h = modem_gap + e);
        for (p = modem_hole_pts) translate([p[0], p[1], -modem_gap - 1]) cylinder(d = modem_hole_d, h = 5 + 1);
    }
    // buck: flat pad, tie round it
    translate([modem_buck_pos[0], modem_buck_pos[1], 0]) tie_pad([modem_buck[0] + 4, 8], 3.5);
    // capacitor: saddle with a groove, tie round it
    translate([modem_cap_pos[0], modem_cap_pos[1], 0]) difference() {
        rotate(90) tie_pad([modem_cap[0] + 4, modem_cap[1] - 6], 3.5 + modem_cap[0] / 3);
        translate([-modem_cap[1], 0, -3.5 - modem_cap[0] / 2]) rotate([0, 90, 0]) cylinder(d = modem_cap[0], h = 2 * modem_cap[1]);
    }
}

// Cradle for the video SSD on the inside of the lid (z < 0 hangs into the box). Two rails
// along the long sides, an end stop, the USB end open. Printed with the lid (rails up).
ssd_rail = 2.4;
ssd_depth = ssd_size[2] + 1.5;     // rails a bit deeper than the SSD so the tie goes under it
module ssd_cradle() {
    L = ssd_size[0]; W = ssd_size[1];
    translate([ssd_pos[0], ssd_pos[1], 0]) difference() {
        union() {
            for (sy = [-1, 1]) translate([-L / 2 - ssd_rail, sy > 0 ? W / 2 : -W / 2 - ssd_rail, -ssd_depth])
                cube([L + ssd_rail, ssd_rail, ssd_depth + e]);
            translate([-L / 2 - ssd_rail, -W / 2 - ssd_rail, -6]) cube([ssd_rail, W + 2 * ssd_rail, 6 + e]);  // end stop
        }
        // two cable-tie slots through both rails, just under the SSD
        for (x = [-L / 4, L / 4]) translate([x - 2.5, -W / 2 - ssd_rail - 1, -ssd_depth + 0.6]) cube([5, W + 2 * ssd_rail + 2, 2.2]);
    }
}

// Lid. With pi_lid_metal (the default) the lid is a 3 mm aluminium plate (DXF)
// with the heatsink on top, and this printed liner hangs under it, held up by
// the heatsink screws. The liner carries the SSD cradle and the 4G board and has
// a big window over the Pi, so the aluminium pillar can reach the plate (and a
// second one from the AI HAT's chip later). Without pi_lid_metal it's the old
// printed lid with the same mounts and no window.
// Drawn with the lid face at z = 0 and everything hanging below it.
liner_corner = 12;      // notch for the lid bolt bosses in the box corners
lw_x = [-54, 18];       // liner window over the Pi, box coordinates
lw_y = [0, 47];
module pi_lid_mounts() {
    if (ssd_on) ssd_cradle();
    if (modem_on) modem_mount();
}
module pi_liner_model() {
    in = pi_box_in;
    s = [in[0] - 2 * fit, in[1] - 2 * fit];
    difference() {
        translate([0, 0, -liner_t]) linear_extrude(liner_t) difference() {
            rrect(s[0], s[1], max(box_r - box_wall - fit, 0.5));
            for (sx = [-1, 1], sy = [-1, 1]) translate([sx * s[0] / 2, sy * s[1] / 2]) square(2 * liner_corner, center = true);
            translate([lw_x[0], lw_y[0]]) square([lw_x[1] - lw_x[0], lw_y[1] - lw_y[0]]);
        }
        for (p = hs_screws) translate([p[0], p[1], -liner_t - 1]) cylinder(d = m3_clear, h = liner_t + 2);
    }
    translate([0, 0, -liner_t]) pi_lid_mounts();
}
module pi_lid_model() {
    if (pi_lid_metal) pi_liner_model();
    else { box_lid(pi_box_in); pi_lid_mounts(); }
}

// Aluminium lid plate, drawn from z = 0 (box side) to lid_plate_t. Cut from the
// DXF (parts/pi_lid_2d.scad). Countersink the pillar hole on the outside by hand.
module pi_lid_plate_model() {
    o = box_out(pi_box_in);
    difference() {
        rbox(o[0], o[1], lid_plate_t, box_r);
        for (p = box_boss_pts(pi_box_in)) translate([p[0], p[1], -1]) cylinder(d = m3_clear, h = lid_plate_t + 2);
        for (p = hs_screws) translate([p[0], p[1], -1]) cylinder(d = m3_clear, h = lid_plate_t + 2);
        translate([soc_pos[0], soc_pos[1], -1]) cylinder(d = m3_clear, h = lid_plate_t + 2);
    }
}

// Not printed: bought parts, drawn for the assembly view and for the sums.
module pi_heatsink_model() {
    n = 12;     // GUESS fin count, only for the picture
    translate([hs_pos[0], hs_pos[1], 0]) {
        translate([-hs_size[0] / 2, -hs_size[1] / 2, 0]) cube([hs_size[0], hs_size[1], hs_base]);
        for (i = [0 : n - 1]) translate([-hs_size[0] / 2 + (i + 0.5) * hs_size[0] / n - 0.9, -hs_size[1] / 2, 0])
            cube([1.8, hs_size[1], hs_size[2]]);
    }
}
// Top of the Pi chip, from the box floor's underside
soc_top = box_floor + pi_standoff + pi_pcb_t + soc_h;
// Pillar length: from the squashed pad on the chip up to the lid plate
pillar_len = box_out(pi_box_in)[2] - soc_top - (pad_t - pad_squash);
echo(str("PILLAR length=", pillar_len, " mm (cut a 20 x 20 aluminium bar to this, CHECK on the real parts)"));
module pi_pillar_model() {
    translate([soc_pos[0] - pillar_w / 2, soc_pos[1] - pillar_w / 2, soc_top]) {
        color("Pink") cube([pillar_w, pillar_w, pad_t - pad_squash]);
        translate([0, 0, pad_t - pad_squash]) cube([pillar_w, pillar_w, pillar_len]);
    }
}

// ---------------------------------------------------------------------------
// Control box and relay box
// ---------------------------------------------------------------------------
module control_box_model() { union() { sealed_box(cb_box_in, cb_glands); grid_posts(cb_box_in); } }
module relay_box_model()   { union() { sealed_box(rb_box_in, rb_glands); grid_posts(rb_box_in); } }

relay_c = [0, rb_box_in[1] / 2 - relay_board[1] / 2 - 14];
relay_keep = [for (sx = [-1, 1], sy = [-1, 1]) [relay_c[0] + sx * relay_holes[0] / 2, relay_c[1] + sy * relay_holes[1] / 2, grid_hole]];
