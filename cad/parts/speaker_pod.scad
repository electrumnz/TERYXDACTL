// Speaker pod for a Kenwood KFC-2053MRB 8" marine coaxial. Sealed, and it
// wraps round the roll-cage tube: the back of the pod is half of a "knuckle"
// round the tube, and a cover closes over the other half with 4 hidden M6
// bolts. A strip of rubber (Sam's) lines the bore.
//
// part = "pod"    print face down, ASA
//        "cover"  print split face down, ASA
//        "plug"   print 4 per pod, push into the bolt holes in the cover
//        "gasket" TPU, under the speaker's flange
//        "cavity" the air inside (only for the volume check in build.sh)
//        "assembly" preview with the tube
//
// Z = along the speaker's axis: 0 is the front face, +Z goes back to the
// cage. Y = up when it's fitted (ridge on top, gland and breather
// underneath). The tube runs along X (or Y with tube_along_x = false).
include <../lib.scad>
part = "pod";
$fn = 96;

z_neck  = pod_face_t + pod_neck_l;
z_waist = z_neck + pod_taper_l;
z_cone  = z_waist + (pod_waist_d - pod_pad_d) / 2;    // back of the 45 deg cone
w45     = pod_wall * 1.42;                             // wall measured square to the cone
roof_d  = 30;                                          // flat roof of the air space (bridges fine)
z_roof  = z_cone - w45 + (pod_pad_d - 2 * pod_wall - 2 * w45 - roof_d) / 2;

Rb = cage_tube_d / 2 + rubber_t;          // bore of the knuckle
Rk = Rb + knuckle_wall;                   // outside of the knuckle
zt = z_roof + knuckle_seat + Rb;          // tube centre
yb = Rb + 9;                              // bolt line each side of the tube
bx = [-(knuckle_w / 2 - 14), knuckle_w / 2 - 14];   // bolts along the tube
head_seat = 10;                           // cover material under each bolt head
pod_len = zt;                             // the pod part ends at the split
echo(str("POD length=", pod_len, " face=", pod_face_w, " overall=", zt + Rk,
         " bore=", 2 * Rb, " bolts M6x", ceil((head_seat + knuckle_gap + m6_insert_deep - 1) / 5) * 5));

module rsq(w, r, h) {      // rounded square slab, centred in X/Y, from z=0 up
  linear_extrude(h) offset(r) square(w - 2 * r, center = true);
}
module disc(d, z) { translate([0, 0, z]) cylinder(d = d, h = e); }

// in = how far in from the outside (0 = outside skin, pod_wall = inside skin)
module shape(in) {
  w = w45 * in / pod_wall;
  hull() {
    translate([0, 0, in > 0 ? pod_face_t : 0]) rsq(pod_face_w - 2 * in, pod_face_r - in, z_neck - (in > 0 ? pod_face_t : 0));
    disc(pod_waist_d - 2 * in, z_waist);
    disc(max(pod_pad_d - 2 * in - 2 * w, 2), z_cone - (in > 0 ? w : 0));
    // inside only: carry on at 45 deg to a small roof, so the top of the air
    // space prints without support (a flat 85 mm roof would sag)
    if (in > 0) disc(roof_d, z_roof);
  }
}
// the knuckle: a round bar along the tube, in pod coordinates
module knuckle_rot() { translate([0, 0, zt]) rotate([0, 0, tube_along_x ? 0 : 90]) children(); }
module bar(r, l) { rotate([0, 90, 0]) cylinder(r = r, h = l, center = true); }
module knuckle_half(front) {   // front = the pod side (z < zt)
  knuckle_rot() intersection() {
    bar(Rk, knuckle_w);
    translate([-knuckle_w, -2 * Rk, front ? -2 * Rk : knuckle_gap / 2]) cube([2 * knuckle_w, 4 * Rk, 2 * Rk - knuckle_gap / 2]);
  }
}
module bolt_spots() { knuckle_rot() for (x = bx, y = [-yb, yb]) translate([x, y, 0]) children(); }

module outside() {
  shape(0);
  hull() {            // the cone flows into the knuckle
    disc(pod_pad_d, z_cone - e);
    knuckle_half(true);
  }
}
module cavity() {
  difference() {
    shape(pod_wall);
    fins();
  }
}
// outside radius of the top skin at depth z (for the ridge and the bosses)
function r_top(z) = z < z_neck ? pod_face_w / 2
  : z < z_waist ? pod_face_w / 2 + (pod_waist_d - pod_face_w) / 2 * (z - z_neck) / pod_taper_l
  : pod_waist_d / 2 - (z - z_waist);

module fins() {   // longitudinal fins on the inside wall, clear of the speaker's basket
  for (i = [0 : pod_fins - 1]) rotate([0, 0, 360 / pod_fins * (i + 0.5)])
    intersection() {
      translate([0, -pod_fin_t / 2, pod_face_t + 6]) cube([pod_face_w, pod_fin_t, z_waist - pod_face_t - 6]);
      difference() { shape(pod_wall - e); shape(pod_wall + pod_fin_h); }
    }
}
module ridge() {   // T. rex dorsal ridge: plates at 45 deg so they print without support
  span = z_cone - z_neck - 20;
  for (i = [0 : pod_spines - 1]) {
    z0 = z_neck + 10 + span * i / pod_spines;
    l  = 46 - i * 5;
    h  = 30 - i * 4;
    y0 = r_top(z0 + l / 2) - 4;
    translate([0, y0, z0]) rotate([0, 90, 0])
      linear_extrude(5, center = true) polygon([[0, 0], [-l, 0], [-l * 0.62, h + 4]]);
  }
}
// boss underneath (on the taper) for a gland or breather, square to the axis
module under_boss(z, x, d) {
  r = r_top(z);
  translate([x, -r + pod_wall, z]) rotate([90, 0, 0]) cylinder(d = d + 12, h = pod_wall + 8);
}
module under_hole(z, x, d) {
  r = r_top(z);
  translate([x, -r + pod_wall + 20, z]) rotate([90, 0, 0]) cylinder(d = d, h = 40);
}
z_gland = z_neck + 30;
z_vent  = z_neck + 70;
x_gland = 22;              // off to one side of the bottom centre line
x_vent  = -22;

module pod() {
  difference() {
    union() {
      outside();
      ridge();
      under_boss(z_gland, x_gland, pod_gland);
      under_boss(z_vent, x_vent, pod_vent);
    }
    cavity();
    translate([0, 0, -e]) cylinder(d = spk_cutout, h = pod_face_t + 2 * e);
    under_hole(z_gland, x_gland, pod_gland);
    under_hole(z_vent, x_vent, pod_vent);
    // tube channel (solid knuckle_seat between it and the air inside, so it stays sealed)
    knuckle_rot() bar(Rb, knuckle_w + 2);
    translate([0, 0, zt]) cylinder(r = 2 * Rk, h = 2 * Rk);       // everything past the split
    // M6 heat-set inserts from the split face
    bolt_spots() translate([0, 0, -m6_insert_deep]) cylinder(d = m6_insert_d, h = m6_insert_deep + e);
    // drip edge round the face so water runs off the front, not back over the shell
    translate([0, 0, -e]) difference() {
      rsq(pod_face_w + 2, pod_face_r + 1, 1.2);
      translate([0, 0, -e]) rsq(pod_face_w - 3, pod_face_r - 1.5, 2);
    }
  }
}
module cover() {   // in pod coordinates
  difference() {
    knuckle_half(false);
    knuckle_rot() bar(Rb, knuckle_w + 2);
    bolt_spots() {
      cylinder(d = 6.5, h = 3 * Rk, center = true);
      translate([0, 0, knuckle_gap / 2 + head_seat]) cylinder(d = 11, h = 2 * Rk);   // counterbore, plugged
    }
  }
}
module plug() {    // push-fit cap for a counterbore, a little proud then sanded flush
  cylinder(d = 10.8, h = 6);
  translate([0, 0, 6]) cylinder(d1 = 10.8, d2 = 10.2, h = 1);
}
module gasket() {   // sits under the speaker's square flange
  linear_extrude(pod_gasket_t) difference() {
    offset(12) square(spk_grille_w - 6 - 24, center = true);
    circle(d = spk_cutout + 4);
  }
}

if (part == "pod") pod();
else if (part == "cover") translate([0, 0, -zt - knuckle_gap / 2]) cover();
else if (part == "plug") plug();
else if (part == "gasket") gasket();
else if (part == "cavity") cavity();
else if (part == "assembly") {
  color("#56603f") pod();
  color("#4b5537") cover();
  color("silver", 0.5) knuckle_rot() bar(cage_tube_d / 2, knuckle_w + 200);
}
