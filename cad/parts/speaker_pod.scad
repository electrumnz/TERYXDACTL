// Speaker pod for a Kenwood KFC-2053MRB 8" marine coaxial, built as a T. rex
// head with the speaker in its open mouth (concept 4). Sealed, and it
// wraps round the roll-cage tube: the back of the pod is half of a "knuckle"
// round the tube, and a cover closes over the other half with 4 hidden M6
// bolts. A strip of rubber (Sam's) lines the bore.
//
// part = "pod"    print face down, ASA
//        "cover"  print split face down, ASA
//        "plug"   print 7 per pod, push into the bolt holes in the cover and jaw
//        "head", "head_teeth", "head_eyes", "head_pupils"
//                 the T. rex head that bolts on top, one STL per colour,
//                 print face (snout) down as one multi-colour object
//        "jaw", "jaw_teeth"
//                 lower jaw that bolts underneath, flat side down
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
// Armour look (concept 3, docs/speaker-pods.md): the body is faceted, an
// octagon with flats on top, bottom and sides. d = across the flats.
module disc(d, z) { translate([0, 0, z]) rotate([0, 0, 22.5]) cylinder(r = d / 2 / cos(22.5), h = e, $fn = 8); }

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
module bar8(r, l) { rotate([0, 90, 0]) rotate([0, 0, 22.5]) cylinder(r = r / cos(22.5), h = l, center = true, $fn = 8); }
module knuckle_half(front) {   // front = the pod side (z < zt)
  knuckle_rot() intersection() {
    bar8(Rk, knuckle_w);
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
// ---------------------------------------------------------------- T. rex head
// Concept 4 (docs/speaker-pods.md): the pod is a T. rex head and the speaker
// sits in its open mouth. The pod itself stays a plain sealed box; the head
// (snout, brows, eyes, upper teeth) and the lower jaw are separate prints that
// bolt on, so the bass maths never changes. Each comes as one STL per colour
// in the same place, for an AMS: load them together as one multi-part object.
//
// Spikes: chunky, raked back at 45 deg so they print without support (the
// pod and head print face down, so "back" is "up" on the printer).
// spike(base, normal angle a in the Y-Z plane (0 = straight up +Y, 45 = up and
// back), height h, base length l, thickness t)
module spike(p, a, h, l, t) {
  n  = [0, cos(a), sin(a)];
  bk = [0, -sin(a), cos(a)];                      // along the surface, towards the back
  tip = p + h * n + h * 1.05 * bk;               // raked back 45 deg or more
  hull() {
    for (s = [0, 1]) translate(p + (s * l - 2) * bk - 3 * n) cube([t, 0.1, 0.1], center = true);
    translate(p + (l + 2) * bk - 3 * n) cube([t * 0.6, 0.1, 0.1], center = true);
    translate(tip) cube([2, 0.1, 0.1], center = true);
  }
}
module spikes() {   // the ridge along the top, behind the head
  for (i = [0 : pod_spines - 1]) {
    z0 = z_head + 16 + 22 * i;
    on_cone = z0 > z_waist;
    h  = 36 - i * 4;
    spike([0, r_top(z0), z0], on_cone ? 45 : atan2(r_top(z_neck) - r_top(z_waist), pod_taper_l), h, h * 0.8, 14);
  }
}
module cover_spikes() {   // two more over the cage collar, so the ridge runs onto the bar
  knuckle_rot() rotate([0, 0, tube_along_x ? 0 : -90]) {
    spike([0, Rk, knuckle_gap / 2 + 4], 0, 30, 18, 13);
    spike([0, Rk * 0.86, Rk * 0.75], 45, 22, 15, 11);
  }
}
// Gills: four slots down each cheek, 2.6 mm deep in the 5 mm wall.
module gills() {
  intersection() {
    difference() { shape(0); shape(2.6); }
    for (i = [0 : 3]) hull() for (z = [pod_face_t + 6, z_neck - 4 + i * 4])
      translate([0, 78 - i * 18, z]) rotate([0, 90, 0]) cylinder(d = 7, h = 400, center = true, $fn = 16);
  }
}

y_top  = pod_face_w / 2;            // top of the pod = roof of the mouth
z_nose = -head_snout;               // front of the snout (and of the jaw)
z_head = 112;                       // back of the head
assert(y_top + head_h <= y_top + 80, "head too tall");

// Faceted shapes from a list of [x, y, z] points, mirrored left/right.
module pts(list) { hull() for (p = list, s = [-1, 1]) translate([s * p[0], p[1], p[2]]) cube(0.5, center = true); }

module head_shape() {
  H = head_h;
  pts([
    [80, y_top, z_nose], [124, y_top, 0], [124, y_top, 50], [60, y_top - 17, z_head],   // sits on the pod
    [70, y_top + 28, z_nose],                         // snout front
    [0, y_top + 42, -68],                             // nose bump
    [95, y_top + H * 0.64, -40],                      // bridge of the nose
    [116, y_top + H * 0.87, 5],                       // corner over the eye
    [110, y_top + H, 50],                             // top of the skull
    [75, y_top + H * 0.74, z_head],                   // back of the skull
  ]);
}
eye  = [103, y_top + 40, -10];      // eyeball centre (right side; mirrored)
eye_r = 16;
module brows() {   // angry ridge over each eye, swept back so it prints clean
  for (s = [-1, 1]) hull() for (p = [[88, y_top + 60, -46], [121, y_top + 70, -4],
                                      [100, y_top + 56, -8], [117, y_top + 80, 16],
                                      [92, y_top + 78, 34]])
    translate([s * p[0], p[1], p[2]]) cube(4, center = true);
}
module eye_balls() { for (s = [-1, 1]) translate([s * eye[0], eye[1], eye[2]]) sphere(r = eye_r, $fn = 48); }
module eye_sockets() { for (s = [-1, 1]) translate([s * (eye[0] + 12), eye[1], eye[2]]) sphere(r = 19.5, $fn = 48); }
module pupils() {   // upright slit on the outer skin of each eyeball
  for (s = [-1, 1]) intersection() {
    translate([s * eye[0], eye[1], eye[2]]) difference() { sphere(r = eye_r + e, $fn = 48); sphere(r = eye_r - 1.6, $fn = 48); }
    translate([s * (eye[0] + eye_r), eye[1], eye[2]]) scale([1, 1, 0.22]) rotate([0, 90, 0]) cylinder(r = 10, h = 2 * eye_r, center = true);
  }
}
module nostrils() {
  for (s = [-1, 1]) translate([s * 28, y_top + 16, z_nose - e]) scale([1.4, 1, 1]) cylinder(d = 9, h = 12);
}
// Teeth: hang from the roof of the mouth, raked back 45 deg (like real T. rex
// teeth, and it prints without support). Their tips stay spk_proud + 5 in
// front of the speaker's face.
module tooth(x, z, h, t = 13) {
  tip = [x, y_top - h, z + 1.05 * h];
  assert(tip[2] <= -spk_proud - 5, str("tooth at z=", z, " hits the speaker grille"));
  hull() {
    translate([x, y_top + 3, z]) cube([t, 0.1, 0.1], center = true);
    translate([x, y_top + 3, z + 0.9 * t]) cube([t * 0.6, 0.1, 0.1], center = true);
    translate([x, y_top - 0.5, z]) cube([t, 0.1, 0.1], center = true);
    translate([x, y_top - 0.5, z + 0.9 * t]) cube([t * 0.6, 0.1, 0.1], center = true);
    translate(tip) cube([1.5, 0.1, 0.1], center = true);
  }
}
function edge_x(z) = 80 + 44 * (z - z_nose) / head_snout;     // side of the mouth
up_front = [[-66, 26], [-44, 38], [-22, 24], [0, 28], [22, 24], [44, 38], [66, 26]];
module upper_teeth() {
  for (t = up_front) tooth(t[0], z_nose + 4, t[1]);
  for (s = [-1, 1], t = [[z_nose + 20, 28], [z_nose + 34, 20]]) tooth(s * (edge_x(t[0]) - 9), t[0], t[1], 11);
}
// head inserts: 3 M4 bolts come up from inside the pod (reach in through the
// speaker hole), through the top wall into heat-set inserts in the head
head_bolts = [[-85, 30], [85, 30], [0, 42]];
module head_bolt_spots() { for (b = head_bolts) translate([b[0], y_top, b[1]]) rotate([-90, 0, 0]) children(); }

module head_all() {      // the whole head in one colour, before the split
  difference() {
    union() { head_shape(); brows(); head_spikes(); }
    shape(-0.4);                                     // sits over the pod
    eye_sockets();
    nostrils();
    head_bolt_spots() translate([0, 0, -e]) cylinder(d = m4_insert_d, h = 10);
    translate([-200, y_top - 100, -200]) cube([400, 100, 400]);   // flat roof of the mouth
  }
}
module head_spikes() {
  spike([0, y_top + head_h - 1, 34], -8, 26, 20, 13);
  spike([0, y_top + head_h - 6, 68], 17, 30, 24, 14);
  spike([0, y_top + head_h - 15, 96], 17, 30, 24, 14);
}
module head_stone() { difference() { head_all(); upper_teeth(); eye_balls(); } }
module head_eyes()  { difference() { eye_balls(); pupils(); head_all(); } }
module head_pupils(){ difference() { pupils(); head_all(); } }
module head_teeth() { upper_teeth(); }

// Lower jaw: bolts under the front of the pod (3 M4 bolts up into inserts in
// the pads), chin out under the snout, teeth up in front of the speaker.
jaw_z  = [6, pod_neck_l + pod_face_t - 4];   // pads span this along Z
jaw_x  = [-60, 0, 60];
jaw_pad = 6;
jaw_d  = 38;                                  // jaw depth under the pod
module jaw_pads(grow = 0) {
  for (x = jaw_x) hull() {
    translate([x - 10 - grow, -y_top - jaw_pad - grow, jaw_z[0] + jaw_pad]) cube([20 + 2 * grow, jaw_pad + 2, 22 - jaw_pad + grow]);
    translate([x - 10 - grow, -y_top, jaw_z[0] - grow]) cube([20 + 2 * grow, 2, 22 + 2 * grow]);
  }
}
module jaw_holes() {
  for (x = jaw_x) translate([x, -y_top - jaw_pad - e, jaw_z[0] + 11]) rotate([-90, 0, 0]) cylinder(d = m4_insert_d, h = 9);
}
module jaw_shape() {
  yb = -y_top - jaw_d;
  pts([
    [80, -y_top, z_nose], [124, -y_top, 0], [124, -y_top, 46],
    [72, yb + 14, z_nose], [62, yb, z_nose + 18], [110, yb, -10], [104, yb, 46],
  ]);
}
module lower_tooth(x, z, h, t = 13) {
  tip = [x, -y_top + h, z + 0.25 * h];
  assert(tip[2] <= -spk_proud - 5, str("lower tooth at z=", z, " hits the speaker grille"));
  hull() {
    translate([x, -y_top - 3, z]) cube([t, 0.1, 0.1], center = true);
    translate([x, -y_top - 3, z + 0.9 * t]) cube([t * 0.6, 0.1, 0.1], center = true);
    translate(tip) cube([1.5, 0.1, 0.1], center = true);
  }
}
lo_front = [[-55, 30], [-33, 22], [-11, 26], [11, 26], [33, 22], [55, 30]];
module lower_teeth() {
  for (t = lo_front) lower_tooth(t[0], z_nose + 6, t[1]);
  for (s = [-1, 1], t = [[z_nose + 24, 22], [z_nose + 40, 16]]) lower_tooth(s * (edge_x(t[0]) - 10), t[0], t[1], 11);
}
module jaw_all() {
  difference() {
    jaw_shape();
    shape(-0.4);
    jaw_pads(0.4);
    for (x = jaw_x) translate([x, -y_top - jaw_d - e, jaw_z[0] + 11]) rotate([-90, 0, 0]) {
      cylinder(d = 4.5, h = jaw_d);
      cylinder(d = 11, h = jaw_d - jaw_pad - 8);      // counterbore, plugged
    }
  }
}
module jaw_stone() { difference() { jaw_all(); lower_teeth(); } }
module jaw_teeth() { lower_teeth(); }

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
      spikes();
      jaw_pads();
      under_boss(z_gland, x_gland, pod_gland);
      under_boss(z_vent, x_vent, pod_vent);
    }
    cavity();
    gills();
    jaw_holes();
    head_bolt_spots() translate([0, 0, -pod_wall - 1]) cylinder(d = m4_clear, h = pod_wall + 2);
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
    union() { knuckle_half(false); cover_spikes(); }
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

// head parts print face down (snout on the bed); jaw parts print flat side down
module head_print() { translate([0, 0, head_snout]) children(); }
module jaw_print()  { translate([0, 0, y_top + jaw_d]) rotate([90, 0, 0]) children(); }

if (part == "pod") pod();
else if (part == "cover") translate([0, 0, -zt - knuckle_gap / 2]) cover();
else if (part == "plug") plug();
else if (part == "head") head_print() head_stone();
else if (part == "head_teeth") head_print() head_teeth();
else if (part == "head_eyes") head_print() head_eyes();
else if (part == "head_pupils") head_print() head_pupils();
else if (part == "jaw") jaw_print() jaw_stone();
else if (part == "jaw_teeth") jaw_print() jaw_teeth();
else if (part == "gasket") gasket();
else if (part == "cavity") cavity();
else if (part == "assembly") rotate([90, 0, 0]) assembly();   // Z up for pictures, face towards +Y

module speaker() {   // rough look of the Kenwood, for pictures only
  color("#1c1c1c") translate([0, 0, -spk_proud]) difference() {
    rsq(spk_grille_w, 14, spk_proud);
    translate([0, 0, -e]) cylinder(d = 168, h = 6);
  }
  color("#2a2a2a") translate([0, 0, -spk_proud + 8]) cylinder(d1 = 60, d2 = 168, h = 2);
  color("#555") translate([0, 0, -spk_proud - 2]) sphere(d = 40);
}
module assembly() {
  stone = "#6b6458"; bone = "#e6dcc3";
  color(stone) pod();
  color("#3a3631") cover();
  color(stone) head_stone();
  color(bone) head_teeth();
  color("#d98a1c") head_eyes();
  color("#111") head_pupils();
  color(stone) jaw_stone();
  color(bone) jaw_teeth();
  speaker();
  color("#222", 0.8) knuckle_rot() bar(cage_tube_d / 2, knuckle_w + 260);
}
