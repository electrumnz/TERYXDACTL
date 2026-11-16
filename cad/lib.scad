// Teryx OS printed parts: shared shapes and the sizes worked out from
// measurements.scad. Parts files `include` this; nothing here draws anything
// on its own.

include <measurements.scad>

$fn = 48;
e = 0.01;   // tiny overlap so cuts go cleanly through

// ---------------------------------------------------------------------------
// Worked-out sizes
// ---------------------------------------------------------------------------
cav_w = scr_w + 2 * fit;                 // locating recess for the bezel
cav_h = scr_h + 2 * fit;
cav_r = max(scr_r + fit, 0.5);

fl_w = cav_w + 2 * frame_flange_w;       // outline of the panel, rim and back plate
fl_h = cav_h + 2 * frame_flange_w;
fl_r = cav_r + frame_flange_w;

cut_w = panel_cut_w + 2 * fit;           // cut-out for the screen's body
cut_h = panel_cut_h + 2 * fit;

body_d  = scr_d - scr_bezel_t;           // depth of the body behind the panel
// Back of the rim to the front of the panel. The back plate then sits
// right on the back of the screen's case, where the wall-bracket holes are.
frame_D = panel_t + gasket_t * 0.7 + body_d;

bolt_in = 6;                             // rim bolts this far in from the edge
// Inner edge of the sun hood's back strip, just inside the rim bolts
frame_out_w = fl_w - 2 * (bolt_in + 5.5);
frame_out_h = fl_h - 2 * (bolt_in + 5.5);
frame_out_r = max(fl_r - bolt_in - 5.5, 1);

frame_split = fl_w > bed_x || fl_h > bed_y;
bp_split    = fl_w > bed_x || fl_h > bed_y;

// ---------------------------------------------------------------------------
// Little helpers
// ---------------------------------------------------------------------------
function linspace(a, b, n) = n < 2 ? [(a + b) / 2] : [for (i = [0 : n - 1]) a + (b - a) * i / (n - 1)];

// Nudge a position off a seam so a bolt never lands on a cut line.
function off_seam(x, seam, gap = 8) = abs(x - seam) < gap ? (x < seam ? seam - gap : seam + gap) : x;

module rrect(w, h, r) {
    rr = min(r, min(w, h) / 2 - e);
    if (rr <= 0) square([w, h], center = true);
    else offset(r = rr) square([w - 2 * rr, h - 2 * rr], center = true);
}

module rbox(w, h, d, r) { linear_extrude(d) rrect(w, h, r); }

// Ring following a rounded-rectangle outline, `width` wide, centred on it
module rring(w, h, r, width) {
    difference() {
        rrect(w + width, h + width, r + width / 2);
        rrect(w - width, h - width, max(r - width / 2, 0.1));
    }
}

// Keep only the left (side < 0) or right (side > 0) of x = at
module half(at, side, big = 2000) {
    intersection() {
        children();
        translate([side < 0 ? at - big : at, -big / 2, -big / 2]) cube(big);
    }
}

// ---------------------------------------------------------------------------
// Bolt positions round the frame flange
// ---------------------------------------------------------------------------
fl_mid_x = fl_w / 2 - bolt_in;                     // rim bolt line
fl_mid_y = fl_h / 2 - bolt_in;
fl_run_x = fl_w / 2 - fl_r;                         // straight part of each edge
fl_run_y = fl_h / 2 - fl_r;
n_x = max(2, ceil(2 * fl_run_x / 60) + 1);          // a bolt at least every 60 mm
n_y = max(2, ceil(2 * fl_run_y / 60) + 1);

// Holes for the back plate bolts (inserts go in from the back of the flange)
bp_bolts = concat(
    [for (x = linspace(-fl_run_x, fl_run_x, n_x)) for (s = [-1, 1])
        [off_seam(off_seam(off_seam(x, frame_split_x), bp_split_x), hood_split_x), s * fl_mid_y]],
    [for (y = linspace(-fl_run_y, fl_run_y, n_y)) for (s = [-1, 1]) [s * fl_mid_x, y]]
);

// Sun hood: its back strip covers the top and upper sides of the flange
hood_gap   = 0.8;
hood_low_y = fl_h / 2 - hood_side_h;
hood_in_w  = fl_w + 2 * hood_gap;        // inside of the hood shell
hood_in_h  = fl_h + 2 * hood_gap;
hood_out_w = hood_in_w + 2 * hood_t;
hood_split = hood_out_w > bed_x;

module hood_strip_2d() {
    difference() {
        intersection() {
            rrect(hood_out_w, hood_in_h + 2 * hood_t, fl_r + hood_gap + hood_t);
            translate([-1000, hood_low_y]) square(2000);
        }
        rrect(frame_out_w, frame_out_h, frame_out_r);
    }
}
function in_hood_strip(p) = p[1] > hood_low_y + 5;

// ---------------------------------------------------------------------------
// Sealed box with a gasket groove, corner lid bolts, glands and ears.
// Floor at z = 0, open top. `in` = inside size [x, y, height].
// ---------------------------------------------------------------------------
function box_out(in) = [in[0] + 2 * box_wall, in[1] + 2 * box_wall, in[2] + box_floor];
function box_boss_pts(in) = [for (sx = [-1, 1]) for (sy = [-1, 1]) [sx * (in[0] / 2 - 4.5), sy * (in[1] / 2 - 4.5)]];

module gland_holes(in, glands) {
    n = len(glands);
    H = box_out(in)[2];
    for (i = [0 : n - 1])
        translate([-in[0] / 2 + in[0] * (i + 0.5) / n, -in[1] / 2 + e, box_floor + in[2] / 2 - 3])
            rotate([90, 0, 0]) cylinder(d = glands[i], h = box_wall + 2 * e);
}

function box_ear_pts(in) = [for (sx = [-1, 1]) for (y = [-in[1] / 2 + 14, in[1] / 2 - 14]) [sx * (box_out(in)[0] / 2 + ear_w / 2 - 1), y]];

module box_ears(in) {
    o = box_out(in);
    for (sx = [-1, 1]) for (y = [-in[1] / 2 + 14, in[1] / 2 - 14])
        translate([sx * (o[0] / 2 + ear_w / 2 - 1), y, 0])
            difference() {
                hull() {
                    translate([-sx * (ear_w / 2), -ear_w / 2 - 2, 0]) cube([e, ear_w + 4, box_floor + 4]);
                    cylinder(d = ear_w, h = box_floor + 1);
                }
                translate([0, 0, -e]) cylinder(d = ear_hole, h = 20);
            }
}

module sealed_box(in, glands, ears = true) {
    o = box_out(in);
    difference() {
        union() {
            rbox(o[0], o[1], o[2], box_r);
            if (ears) box_ears(in);
        }
        // inside
        translate([0, 0, box_floor]) rbox(in[0], in[1], in[2] + 1, box_r - box_wall);
        // gasket groove in the top of the wall
        translate([0, 0, o[2] - groove_d])
            linear_extrude(groove_d + 1) rring(in[0] + box_wall, in[1] + box_wall, box_r - box_wall / 2, groove_w);
        gland_holes(in, glands);
    }
    // corner bosses for the lid bolts (inside the seal)
    difference() {
        for (p = box_boss_pts(in)) translate([p[0], p[1], 0]) {
            cylinder(r = 5, h = o[2]);
            translate([p[0] < 0 ? -6 : 0, p[1] < 0 ? -6 : 0, 0]) cube([6, 6, o[2]]);
        }
        for (p = box_boss_pts(in)) translate([p[0], p[1], o[2] - m3_insert_deep - 2]) cylinder(d = m3_insert_d, h = 20);
    }
}

// Flat lid with a tongue that presses on the gasket. Built tongue-down at
// z = 0 to z = lid_t; flip it for printing.
module box_lid(in) {
    o = box_out(in);
    difference() {
        union() {
            rbox(o[0], o[1], lid_t, box_r);
            translate([0, 0, -1]) linear_extrude(1 + e)
                rring(in[0] + box_wall, in[1] + box_wall, box_r - box_wall / 2, groove_w - 0.6);
        }
        for (p = box_boss_pts(in)) translate([p[0], p[1], -2]) cylinder(d = m3_clear, h = 20);
    }
}

// Printed TPU gasket to sit in the groove (or use 2 mm foam cord instead)
module box_gasket(in) {
    linear_extrude(groove_d + 0.8) rring(in[0] + box_wall, in[1] + box_wall, box_r - box_wall / 2, groove_w - 0.3);
}

// ---------------------------------------------------------------------------
// Grid plate for loose boards, with four posts in the box floor to hold it
// ---------------------------------------------------------------------------
function grid_plate_size(in) = [in[0] - 2 * fit, in[1] - 2 * fit];
function grid_post_pts(in) = [for (sx = [-1, 1]) for (sy = [-1, 1]) [sx * (in[0] / 2 - 22), sy * (in[1] / 2 - 7)]];

module grid_posts(in) {
    for (p = grid_post_pts(in)) translate([p[0], p[1], 0]) difference() {
        cylinder(d = 9, h = box_floor + grid_post_h);
        translate([0, 0, box_floor + grid_post_h - m3_insert_deep]) cylinder(d = m3_insert_d, h = 20);
    }
}

// `keep` = list of [x, y, d] holes to add; grid holes too close to them are left out
module grid_plate(in, keep = []) {
    s = grid_plate_size(in);
    nx = floor((s[0] - 10) / grid_pitch);
    ny = floor((s[1] - 10) / grid_pitch);
    difference() {
        linear_extrude(grid_t) difference() {
            rrect(s[0], s[1], max(box_r - box_wall - fit, 0.5));
            // notches for the lid bosses in the corners
            for (p = box_boss_pts(in)) translate(p) circle(r = 5 + fit + 0.4);
        }
        for (p = grid_post_pts(in)) translate([p[0], p[1], -1]) cylinder(d = m3_clear, h = 10);
        for (h = keep) translate([h[0], h[1], -1]) cylinder(d = h[2], h = 10);
        for (i = [0 : nx], j = [0 : ny]) let (x = (i - nx / 2) * grid_pitch, y = (j - ny / 2) * grid_pitch)
            if (min([for (p = grid_post_pts(in)) norm([x, y] - p)]) > 7
                && (len(keep) == 0 || min([for (h = keep) norm([x, y] - [h[0], h[1]])]) > 5)
                && min([for (p = box_boss_pts(in)) norm([x, y] - p)]) > 8)
                translate([x, y, -1]) cylinder(d = grid_hole, h = 10, $fn = 12);
    }
}
