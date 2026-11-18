// Speaker pod for a Kenwood KFC-2053MRB 8" marine coaxial. Sealed.
// part = "pod" (print face down, ASA or PETG), "gasket" (TPU), "cavity"
// (the air inside, only used by the volume check, not for printing)
//
// Z = along the speaker's axis: 0 is the front face, +Z goes back towards the
// mounting pad. Y = up when it's on the cage (the ridge is on top, the cable
// gland and breather underneath).
include <../lib.scad>
part = "pod";
$fn = 96;

pod_len = pod_face_t + pod_neck_l + pod_taper_l + (pod_waist_d - pod_pad_d) / 2 + pod_pad_t;
echo(str("POD length=", pod_len, " face=", pod_face_w));

module rsq(w, r, h) {      // rounded square slab, centred in X/Y, from z=0 up
  linear_extrude(h) offset(r) square(w - 2 * r, center = true);
}
module disc(d, z) { translate([0, 0, z]) cylinder(d = d, h = e); }

z_neck  = pod_face_t + pod_neck_l;
z_waist = z_neck + pod_taper_l;
z_cone  = z_waist + (pod_waist_d - pod_pad_d) / 2;    // back of the 45 deg cone

// in = how far in from the outside (0 = outside skin, pod_wall = inside skin)
module shape(in) {
  w = pod_wall * 1.42 * in / pod_wall;                // wall measured square to the 45 deg cone
  hull() {
    translate([0, 0, in > 0 ? pod_face_t : 0]) rsq(pod_face_w - 2 * in, pod_face_r - in, z_neck - (in > 0 ? pod_face_t : 0));
    disc(pod_waist_d - 2 * in, z_waist);
    disc(max(pod_pad_d - 2 * in - 2 * w, 2), z_cone - (in > 0 ? w : 0));
  }
}
module outside() {
  shape(0);
  translate([0, 0, z_cone - e]) cylinder(d = pod_pad_d, h = pod_pad_t);
}
module cavity() {
  difference() {
    shape(pod_wall);
    fins();
  }
}
// outside radius of the top skin at depth z (for the ridge)
function r_top(z) = z < z_neck ? pod_face_w / 2
  : z < z_waist ? pod_face_w / 2 + (pod_waist_d - pod_face_w) / 2 * (z - z_neck) / pod_taper_l
  : pod_waist_d / 2 - (z - z_waist);

module fins() {   // longitudinal fins on the inside wall, clear of the speaker's basket
  for (i = [0 : pod_fins - 1]) rotate([0, 0, 360 / pod_fins * (i + 0.5)])
    intersection() {
      translate([0, -pod_fin_t / 2, pod_face_t + 6]) cube([pod_face_w, pod_fin_t, z_waist + 25 - pod_face_t]);
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
    // M6 heat-set inserts in the back pad (blind, so no leak), plus a cable-tie slot
    for (s = [-1, 1]) translate([s * pod_mount_dx / 2, 0, pod_len - m6_insert_deep]) cylinder(d = m6_insert_d, h = m6_insert_deep + e);
    // drip edge round the face so water runs off the front, not back over the shell
    translate([0, 0, -e]) difference() {
      rsq(pod_face_w + 2, pod_face_r + 1, 1.2);
      translate([0, 0, -e]) rsq(pod_face_w - 3, pod_face_r - 1.5, 2);
    }
  }
}
module gasket() {   // sits under the speaker's square flange
  linear_extrude(pod_gasket_t) difference() {
    offset(12) square(spk_grille_w - 6 - 24, center = true);
    circle(d = spk_cutout + 4);
  }
}

if (part == "pod") pod();
else if (part == "gasket") gasket();
else if (part == "cavity") cavity();
