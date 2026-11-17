// A 2013 Kawasaki Teryx 750 (two seater), built in code so the repo stays MIT.
// Sizes come from the 2013 Teryx 750 FI 4x4 spec sheet:
//   length 2954 mm, width 1486 mm, height 1925 mm, wheelbase 1930 mm,
//   ground clearance 295 mm, tyres 26x8-12 front / 26x10-12 rear,
//   bed 1123 wide x 831 long x 282 high.
// Axes: +x forward, +y up, +z right (driver sits on -z). Units are metres.
//
// Static parts are merged into one mesh per material so the whole ute is
// only a few dozen draw calls, which keeps a Pi 5 happy.
import * as THREE from "three";
import { mergeGeometries } from "/vendor/three/BufferGeometryUtils.js";

export const DIMS = {
  WHEELBASE: 1.93, TRACK_F: 1.22, TRACK_R: 1.24, WHEEL_R: 0.33,
  TYRE_W_F: 0.20, TYRE_W_R: 0.25, RIM_R: 0.155,
  FX: 0.965, RX: -0.965, ROOF_Y: 1.90,
};
const { WHEELBASE, TRACK_F, TRACK_R, WHEEL_R, FX, RX } = DIMS;

export const PAINTS = [
  { name: "Green", color: 0x3b5e2b },
  { name: "Black", color: 0x17191b },
  { name: "Red", color: 0x8e1a17 },
  { name: "Sand", color: 0x9a8762 },
  { name: "Lime", color: 0x5fae2e },
];

// ------------------------------------------------------------------ helpers
const V = (x, y, z) => new THREE.Vector3(x, y, z);
const UP = V(0, 1, 0);

// Collects geometry per material, then merges it into one mesh each.
class Batch {
  constructor() { this.map = new Map(); }
  add(geo, mat, { p = [0, 0, 0], r = [0, 0, 0], s = [1, 1, 1], q = null, m = null } = {}) {
    let g = geo.index ? geo.toNonIndexed() : geo.clone();
    for (const k of Object.keys(g.attributes)) if (!["position", "normal", "uv"].includes(k)) g.deleteAttribute(k);
    if (!g.attributes.uv) g.setAttribute("uv", new THREE.BufferAttribute(new Float32Array(g.attributes.position.count * 2), 2));
    const mx = m || new THREE.Matrix4().compose(V(...p), q || new THREE.Quaternion().setFromEuler(new THREE.Euler(r[0], r[1], r[2], r[3] || "XYZ")), V(...s));
    g.applyMatrix4(mx);
    if (!this.map.has(mat)) this.map.set(mat, []);
    this.map.get(mat).push(g);
    return this;
  }
  build(parent, { shadow = true } = {}) {
    const out = [];
    for (const [mat, list] of this.map) {
      const mesh = new THREE.Mesh(mergeGeometries(list), mat);
      mesh.castShadow = shadow; mesh.receiveShadow = true;
      parent.add(mesh); out.push(mesh);
    }
    this.map.clear();
    return out;
  }
}

// polyline with rounded corners, for cage and bumper tubes
function filletPath(pts, rad) {
  const P = pts.map(p => V(...p));
  const path = new THREE.CurvePath();
  let start = P[0].clone();
  for (let i = 1; i < P.length - 1; i++) {
    const a = P[i - 1], b = P[i], c = P[i + 1];
    const d1 = a.clone().sub(b), d2 = c.clone().sub(b);
    const r = Math.min(rad, d1.length() * 0.45, d2.length() * 0.45);
    const p1 = b.clone().add(d1.normalize().multiplyScalar(r));
    const p2 = b.clone().add(d2.normalize().multiplyScalar(r));
    if (start.distanceTo(p1) > 1e-4) path.add(new THREE.LineCurve3(start, p1));
    path.add(new THREE.QuadraticBezierCurve3(p1, b.clone(), p2));
    start = p2;
  }
  path.add(new THREE.LineCurve3(start, P[P.length - 1]));
  return path;
}
function bentTube(pts, r, bend = 0.12, radial = 8) {
  const path = filletPath(pts, bend);
  return new THREE.TubeGeometry(path, Math.max(8, Math.round(path.getLength() * 28)), r, radial, false);
}
// straight rod between two points
function rod(batch, a, b, r, mat, radial = 8) {
  const A = V(...a), B = V(...b);
  const len = A.distanceTo(B);
  const q = new THREE.Quaternion().setFromUnitVectors(UP, B.clone().sub(A).normalize());
  batch.add(new THREE.CylinderGeometry(r, r, len, radial, 1), mat, { p: A.add(B).multiplyScalar(0.5).toArray(), q });
}
function roundRect(w, h, r) {
  const s = new THREE.Shape(), x = -w / 2, y = -h / 2;
  r = Math.min(r, w / 2, h / 2);
  s.moveTo(x + r, y); s.lineTo(x + w - r, y); s.quadraticCurveTo(x + w, y, x + w, y + r);
  s.lineTo(x + w, y + h - r); s.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  s.lineTo(x + r, y + h); s.quadraticCurveTo(x, y + h, x, y + h - r);
  s.lineTo(x, y + r); s.quadraticCurveTo(x, y, x + r, y);
  return s;
}
// box with soft edges: w along x, h along y, d along z
function rbox(w, h, d, r = 0.03, bevel = 0.015) {
  const b = Math.min(bevel, d / 3, w / 4, h / 4);
  const g = new THREE.ExtrudeGeometry(roundRect(w - 2 * b, h - 2 * b, r), {
    depth: Math.max(0.001, d - 2 * b), bevelEnabled: true, bevelThickness: b, bevelSize: b,
    bevelSegments: 2, curveSegments: 4,
  });
  g.translate(0, 0, -(d - 2 * b) / 2);
  return g;
}
// side-profile panel: pts are [x, y] in the side view, extruded across z
function profile(pts, depth, bevel = 0.02, holes = []) {
  const s = new THREE.Shape(pts.map(([x, y]) => new THREE.Vector2(x, y)));
  holes.forEach(h => s.holes.push(h));
  const g = new THREE.ExtrudeGeometry(s, {
    depth: Math.max(0.001, depth - 2 * bevel), bevelEnabled: bevel > 0, bevelThickness: bevel,
    bevelSize: bevel, bevelSegments: 3, curveSegments: 18,
  });
  g.translate(0, 0, -(depth - 2 * bevel) / 2);
  return g;
}
// fender side panel with a wheel arch cut from its lower edge
function fenderShape(x0, x1, yb, topPts, cx, cy, ar) {
  const s = new THREE.Shape();
  const a = Math.asin(Math.min(0.99, (yb - cy) / ar));
  s.moveTo(x0, yb);
  topPts.forEach(([x, y]) => s.lineTo(x, y));
  s.lineTo(x1, yb);
  s.lineTo(cx + Math.cos(a) * ar, yb);
  s.absarc(cx, cy, ar, a, Math.PI - a, false);
  s.lineTo(x0, yb);
  return s;
}
function extrudeShape(shape, depth, bevel = 0.025) {
  const g = new THREE.ExtrudeGeometry(shape, {
    depth: Math.max(0.001, depth - 2 * bevel), bevelEnabled: true, bevelThickness: bevel,
    bevelSize: bevel * 0.8, bevelSegments: 3, curveSegments: 24,
  });
  g.translate(0, 0, -(depth - 2 * bevel) / 2);
  return g;
}

// ------------------------------------------------------------------ materials
function makeMaterials() {
  const std = (color, o = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.6, metalness: 0.05, ...o });
  return {
    paint: std(PAINTS[0].color, { roughness: 0.32, metalness: 0.35 }),
    plastic: std(0x1c1e20, { roughness: 0.78 }),
    plasticGrey: std(0x34383c, { roughness: 0.7 }),
    cage: std(0x141617, { roughness: 0.42, metalness: 0.55 }),
    frame: std(0x24282b, { roughness: 0.5, metalness: 0.5 }),
    alloy: std(0x9aa0a6, { roughness: 0.3, metalness: 0.85 }),
    darkAlloy: std(0x3a3f44, { roughness: 0.35, metalness: 0.8 }),
    chrome: std(0xd8dde2, { roughness: 0.15, metalness: 1 }),
    rubber: std(0x121212, { roughness: 0.95 }),
    seat: std(0x232527, { roughness: 0.92 }),
    seatPanel: std(0x3a3e42, { roughness: 0.95 }),
    bed: std(0x1e2022, { roughness: 0.82 }),
    spring: std(0xb5261e, { roughness: 0.4, metalness: 0.4 }),
    shock: std(0xd9b62b, { roughness: 0.35, metalness: 0.6 }),
    motor: std(0x3f6f9a, { roughness: 0.4, metalness: 0.6 }),
    pack: std(0x2b2f33, { roughness: 0.6, metalness: 0.3 }),
    packLabel: std(0xff7a1a, { roughness: 0.5 }),
    orange: std(0xff7a1a, { roughness: 0.5 }),
    hook: std(0xd22a1a, { roughness: 0.4, metalness: 0.5 }),
    glass: std(0x0b0d10, { roughness: 0.1, metalness: 0.2 }),
  };
}

// ------------------------------------------------------------------ build
export function buildTeryx() {
  const M = makeMaterials();
  const rig = new THREE.Group();     // follows terrain pitch: wheels, axles
  const ute = new THREE.Group();     // sprung body (bounces a little)
  rig.add(ute);
  const B = new Batch();             // static mechanical bits (frame, suspension, hitch...)
  const BB = new Batch();            // bodywork: replaced by the Blender model (teryx.glb) when it loads
  const bodyGroup = new THREE.Group(); ute.add(bodyGroup);

  // ---------------- frame, floor, skid plate
  for (const z of [-0.3, 0.3]) {
    B.add(bentTube([[1.42, 0.46, z * 0.85], [1.1, 0.4, z], [-1.2, 0.4, z], [-1.44, 0.5, z * 0.9]], 0.028, 0.15), M.frame);
  }
  for (const x of [1.05, 0.45, -0.25, -0.75, -1.3]) rod(B, [x, 0.4, -0.3], [x, 0.4, 0.3], 0.022, M.frame);
  B.add(rbox(1.9, 0.03, 0.9, 0.08, 0.01), M.darkAlloy, { p: [0.15, 0.33, 0] });            // skid plate
  BB.add(rbox(1.16, 0.035, 1.22, 0.04, 0.01), M.plastic, { p: [0.0, 0.445, 0] });           // floor pan
  // ribbed floor mat
  for (let i = 0; i < 9; i++) BB.add(new THREE.BoxGeometry(0.4, 0.012, 0.02), M.plasticGrey, { p: [0.22, 0.47, -0.52 + i * 0.03 + (i > 4 ? 0.55 : 0)] });
  // rocker / sill panels under the door openings
  for (const s of [-1, 1]) {
    BB.add(profile([[-0.62, 0.36], [0.5, 0.36], [0.56, 0.42], [0.52, 0.56], [-0.6, 0.56]], 0.09, 0.02), M.plastic, { p: [0, 0, s * 0.62] });
  }

  // ---------------- front end: bonnet, nose, grille, headlights
  // bonnet + nose in one side profile, extruded across the middle
  const hood = [[0.5, 0.48], [1.28, 0.48], [1.46, 0.56], [1.48, 0.66], [1.43, 0.78], [1.32, 0.86],
    [1.0, 0.93], [0.72, 0.99], [0.56, 1.0], [0.5, 0.96]];
  BB.add(profile(hood, 0.94, 0.045), M.paint);
  // centre bonnet ridge and vents
  BB.add(profile([[0.62, 0.99], [1.0, 0.94], [1.28, 0.87], [1.0, 0.955], [0.62, 1.01]], 0.32, 0.012), M.paint);
  for (const s of [-1, 1]) BB.add(rbox(0.18, 0.012, 0.12, 0.02, 0.004), M.plastic, { p: [0.88, 0.968, s * 0.3], r: [0, 0, -0.17] });
  // front fenders with arches and black flares
  const fFender = fenderShape(0.46, 1.46, 0.5,
    [[0.48, 0.92], [0.56, 0.97], [0.8, 0.95], [1.05, 0.9], [1.3, 0.83], [1.42, 0.74], [1.47, 0.62]],
    FX, 0.36, 0.41);
  for (const s of [-1, 1]) {
    BB.add(extrudeShape(fFender, 0.27, 0.035), M.paint, { p: [0, 0, s * 0.585] });
    const flare = new THREE.TorusGeometry(0.43, 0.035, 6, 28, Math.PI - 0.5);
    BB.add(flare, M.plastic, { p: [FX, 0.36, s * 0.68], r: [0, 0, 0.25], s: [1, 1, 2.6] });
    BB.add(rbox(0.5, 0.05, 0.3, 0.02, 0.01), M.plastic, { p: [FX - 0.05, 0.5, s * 0.5] });   // inner guard
  }
  // grille surround and grille
  BB.add(profile([[1.44, 0.5], [1.5, 0.52], [1.52, 0.68], [1.47, 0.72], [1.44, 0.68]], 0.78, 0.02), M.plastic);
  for (let i = 0; i < 6; i++) BB.add(new THREE.BoxGeometry(0.02, 0.014, 0.62), M.plasticGrey, { p: [1.515, 0.55 + i * 0.025, 0] });
  BB.add(new THREE.BoxGeometry(0.01, 0.16, 0.66), M.glass, { p: [1.5, 0.61, 0] });
  // headlight housings in the nose corners (lens lights up separately)
  const headMat = new THREE.MeshStandardMaterial({ color: 0x2a2c2e, emissive: 0xfff2d6, emissiveIntensity: 0.2, roughness: 0.1, metalness: 0.4 });
  const headLens = new THREE.Group(); bodyGroup.add(headLens);
  for (const s of [-1, 1]) {
    // swept housing following the nose slope, lens and reflector inside it
    const hq = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, s * -0.28, -0.42, "YXZ"));
    BB.add(rbox(0.05, 0.1, 0.25, 0.03, 0.012), M.plastic, { p: [1.475, 0.755, s * 0.31], q: hq });
    const lens = new THREE.Mesh(rbox(0.02, 0.075, 0.22, 0.025, 0.006), headMat);
    lens.position.set(1.497, 0.765, s * 0.31); lens.quaternion.copy(hq);
    headLens.add(lens);
    BB.add(new THREE.SphereGeometry(0.03, 12, 8), M.chrome, { p: [1.5, 0.77, s * 0.27], s: [0.4, 1, 1] });
  }

  // ---------------- front brush guard, winch plate
  BB.add(bentTube([[1.36, 0.46, -0.42], [1.56, 0.46, -0.42], [1.6, 0.76, -0.34], [1.6, 0.76, 0.34], [1.56, 0.46, 0.42], [1.36, 0.46, 0.42]], 0.022, 0.1), M.cage);
  rod(BB, [1.59, 0.62, -0.38], [1.59, 0.62, 0.38], 0.018, M.cage);
  for (const s of [-1, 1]) rod(BB, [1.6, 0.76, s * 0.16], [1.585, 0.47, s * 0.16], 0.016, M.cage);
  B.add(rbox(0.26, 0.02, 0.5, 0.02, 0.006), M.darkAlloy, { p: [1.34, 0.41, 0] });         // winch plate
  B.add(rbox(0.04, 0.09, 0.18, 0.01, 0.005), M.alloy, { p: [1.49, 0.45, 0] });            // hawse fairlead
  B.add(new THREE.BoxGeometry(0.05, 0.02, 0.1), M.glass, { p: [1.505, 0.45, 0] });

  // ---------------- dash, steering, our 10.1" screen
  BB.add(profile([[0.36, 0.86], [0.44, 1.0], [0.56, 1.03], [0.6, 0.98], [0.56, 0.46], [0.5, 0.46], [0.46, 0.72]], 1.26, 0.03), M.plastic);
  BB.add(rbox(0.06, 0.12, 0.32, 0.02, 0.01), M.plasticGrey, { p: [0.4, 0.84, 0.32], r: [0, 0, -0.5] });  // glovebox lid
  rod(BB, [0.38, 1.04, 0.42], [0.38, 1.04, 0.18], 0.014, M.cage);                                        // passenger grab bar
  for (const z of [0.42, 0.18]) rod(BB, [0.38, 1.04, z], [0.46, 0.97, z], 0.014, M.cage);
  // steering wheel (driver on -z)
  const SW = { x: 0.3, y: 1.02, z: -0.3 };
  const swq = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, Math.PI / 2, 0.55, "YXZ"));
  const swg = new THREE.TorusGeometry(0.17, 0.022, 8, 28);
  BB.add(swg, M.rubber, { p: [SW.x, SW.y, SW.z], q: swq });
  for (const a of [0, 2.2, -2.2]) {
    const sp = new THREE.BoxGeometry(0.16, 0.03, 0.012); sp.translate(0.08, 0, 0);
    const q = swq.clone().multiply(new THREE.Quaternion().setFromAxisAngle(V(0, 0, 1), a - Math.PI / 2));
    BB.add(sp, M.plasticGrey, { p: [SW.x, SW.y, SW.z], q });
  }
  BB.add(new THREE.CylinderGeometry(0.05, 0.05, 0.05, 16), M.plasticGrey, { p: [SW.x, SW.y, SW.z], q: swq.clone().multiply(new THREE.Quaternion().setFromAxisAngle(V(1, 0, 0), Math.PI / 2)) });
  rod(BB, [SW.x + 0.02, SW.y - 0.02, SW.z], [0.52, 0.86, SW.z], 0.022, M.plastic);
  // pedals
  for (const [z, w] of [[-0.36, 0.06], [-0.24, 0.09]]) BB.add(rbox(0.02, 0.1, w, 0.01, 0.004), M.darkAlloy, { p: [0.47, 0.56, z], r: [0, 0, 0.5] });
  // screen in a printed bezel, with sun hood
  const screenCanvas = document.createElement("canvas");
  screenCanvas.width = 320; screenCanvas.height = 200;
  const screenTex = new THREE.CanvasTexture(screenCanvas);
  screenTex.colorSpace = THREE.SRGBColorSpace;
  const screenMat = new THREE.MeshStandardMaterial({ color: 0x000000, emissive: 0xffffff, emissiveMap: screenTex, emissiveIntensity: 0.9, roughness: 0.2 });
  const SC = { x: 0.42, y: 1.29, z: -0.28 };
  const scq = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, -Math.PI / 2, 0.25, "YXZ"));
  B.add(rbox(0.29, 0.21, 0.045, 0.02, 0.01), M.plastic, { p: [SC.x + 0.025, SC.y, SC.z], q: scq.clone().multiply(new THREE.Quaternion().setFromAxisAngle(V(0, 1, 0), 0)) });
  B.add(profile([[-0.15, 0.1], [0.15, 0.1], [0.15, 0.11], [-0.15, 0.11]], 0.12, 0.004), M.plastic, { p: [SC.x - 0.03, SC.y + 0.0, SC.z], q: scq.clone().multiply(new THREE.Quaternion().setFromAxisAngle(V(1, 0, 0), Math.PI / 2)).multiply(new THREE.Quaternion().setFromAxisAngle(V(1, 0, 0), -Math.PI / 2)) });
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(0.235, 0.147), screenMat);
  screen.position.set(SC.x - 0.0, SC.y, SC.z); screen.quaternion.copy(scq);
  screen.translateZ(0.024);
  ute.add(screen);
  // sun hood over the screen
  B.add(rbox(0.12, 0.012, 0.3, 0.01, 0.004), M.plastic, { p: [SC.x - 0.03, SC.y + 0.115, SC.z], r: [0, 0, -0.12] });

  // ---------------- seats (bucket seats with integrated headrests)
  for (const z of [-0.3, 0.3]) {
    BB.add(rbox(0.36, 0.26, 0.42, 0.02, 0.01), M.plastic, { p: [-0.18, 0.59, z] });                   // seat box
    BB.add(rbox(0.48, 0.1, 0.46, 0.06, 0.03), M.seat, { p: [-0.16, 0.77, z], r: [0, 0, 0.05] });      // cushion
    BB.add(rbox(0.36, 0.03, 0.26, 0.05, 0.01), M.seatPanel, { p: [-0.14, 0.825, z], r: [0, 0, 0.05] });
    for (const s of [-1, 1]) BB.add(rbox(0.42, 0.08, 0.07, 0.03, 0.025), M.seat, { p: [-0.16, 0.83, z + s * 0.2], r: [0, 0, 0.05] });
    const back = { p: [-0.42, 1.08, z], r: [0, 0, 0.16] };
    BB.add(rbox(0.1, 0.56, 0.46, 0.05, 0.03), M.seat, back);
    BB.add(rbox(0.03, 0.4, 0.26, 0.05, 0.01), M.seatPanel, { p: [-0.37, 1.04, z], r: [0, 0, 0.16] });
    for (const s of [-1, 1]) BB.add(rbox(0.13, 0.42, 0.07, 0.03, 0.025), M.seat, { p: [-0.39, 1.0, z + s * 0.21], r: [0, 0, 0.16] });
    BB.add(rbox(0.1, 0.17, 0.3, 0.05, 0.03), M.seat, { p: [-0.49, 1.43, z], r: [0, 0, 0.16] });       // headrest
  }
  // centre console between the seats
  BB.add(rbox(0.5, 0.2, 0.12, 0.03, 0.015), M.plasticGrey, { p: [-0.12, 0.62, 0] });
  // battery pack hidden under the seats (EV conversion)
  const pack = new Batch();

  // ---------------- roll cage
  const C = 0.023;
  for (const s of [-1, 1]) {
    // A-pillar sweeping up into the roof rail and down the B-pillar
    BB.add(bentTube([[0.5, 0.96, s * 0.66], [0.38, 1.5, s * 0.645], [0.18, 1.86, s * 0.63], [-0.52, 1.87, s * 0.63],
      [-0.6, 1.74, s * 0.64], [-0.63, 0.58, s * 0.66]], C, 0.16), M.cage);
    // hip bolster / door bar
    BB.add(bentTube([[0.46, 0.8, s * 0.66], [0.3, 0.96, s * 0.7], [-0.1, 0.98, s * 0.71], [-0.6, 0.96, s * 0.67]], 0.016, 0.12), M.cage);
    // rear braces down to the frame behind the seats
    BB.add(bentTube([[-0.6, 1.62, s * 0.64], [-0.7, 1.2, s * 0.6], [-0.66, 0.6, s * 0.42]], 0.018, 0.2), M.cage);
    // feet of the cage
    BB.add(rbox(0.08, 0.04, 0.08, 0.01, 0.006), M.frame, { p: [-0.63, 0.57, s * 0.66] });
  }
  rod(BB, [0.2, 1.855, -0.63], [0.2, 1.855, 0.63], C, M.cage);          // front roof bar
  rod(BB, [-0.53, 1.87, -0.63], [-0.53, 1.87, 0.63], C, M.cage);        // rear roof bar
  rod(BB, [-0.63, 1.2, -0.66], [-0.63, 1.2, 0.66], 0.02, M.cage);       // shoulder bar
  rod(BB, [-0.15, 1.875, -0.63], [-0.15, 1.875, 0.63], 0.016, M.cage);  // roof mid bar
  // moulded roof
  BB.add(rbox(0.86, 0.035, 1.34, 0.12, 0.015), M.plastic, { p: [-0.17, 1.91, 0] });
  for (let i = -3; i <= 3; i++) BB.add(new THREE.BoxGeometry(0.7, 0.012, 0.03), M.plastic, { p: [-0.17, 1.93, i * 0.16] });
  // brackets for the rear floods, off the outside of the rear cage mounting plates
  for (const s of [-1, 1]) rod(B, [-0.61, 0.62, s * 0.69], [-0.61, 0.66, s * 0.75], 0.01, M.frame);

  // ---------------- rear fenders (body colour), rear panel, hitch, plug
  const rFender = fenderShape(-1.48, -0.62, 0.48,
    [[-1.46, 0.8], [-1.3, 0.83], [-0.7, 0.83], [-0.62, 0.78]], RX, 0.36, 0.42);
  for (const s of [-1, 1]) {
    BB.add(extrudeShape(rFender, 0.24, 0.03), M.paint, { p: [0, 0, s * 0.62] });
    BB.add(new THREE.TorusGeometry(0.44, 0.032, 6, 28, Math.PI - 0.4), M.plastic, { p: [RX, 0.36, s * 0.72], r: [0, 0, 0.2], s: [1, 1, 2.6] });
    BB.add(rbox(0.6, 0.05, 0.36, 0.02, 0.01), M.plastic, { p: [RX, 0.78, s * 0.48] });
  }
  BB.add(profile([[-1.49, 0.62], [-1.44, 0.6], [-1.44, 0.8], [-1.49, 0.79]], 0.98, 0.015), M.plastic);  // rear panel under the bed
  BB.add(bentTube([[-1.3, 0.42, -0.5], [-1.52, 0.42, -0.5], [-1.52, 0.42, 0.5], [-1.3, 0.42, 0.5]], 0.022, 0.08), M.cage);  // rear bumper
  for (const s of [-1, 1]) rod(BB, [-1.5, 0.42, s * 0.3], [-1.44, 0.62, s * 0.3], 0.016, M.cage);
  B.add(rbox(0.26, 0.06, 0.06, 0.01, 0.006), M.frame, { p: [-1.56, 0.43, 0] });     // receiver
  B.add(rbox(0.1, 0.05, 0.05, 0.01, 0.006), M.alloy, { p: [-1.68, 0.43, 0] });      // ball mount
  B.add(new THREE.SphereGeometry(0.03, 12, 8), M.chrome, { p: [-1.7, 0.48, 0] });
  const plugQ = new THREE.Quaternion().setFromAxisAngle(V(0, 0, 1), Math.PI / 2);
  B.add(new THREE.CylinderGeometry(0.035, 0.035, 0.06, 14), M.plastic, { p: [-1.49, 0.5, 0.25], q: plugQ });
  const pinMats = {
    tail: new THREE.MeshBasicMaterial({ color: 0x331111 }),
    brake: new THREE.MeshBasicMaterial({ color: 0x331111 }),
  };
  const pinT = new THREE.Mesh(new THREE.SphereGeometry(0.01, 8, 6), pinMats.tail); pinT.position.set(-1.522, 0.51, 0.235); ute.add(pinT);
  const pinB = new THREE.Mesh(new THREE.SphereGeometry(0.01, 8, 6), pinMats.brake); pinB.position.set(-1.522, 0.51, 0.265); ute.add(pinB);

  // ---------------- suspension (double A-arms, coilovers) all four corners
  const arms = (x, track, inZ) => {
    for (const s of [-1, 1]) {
      const kz = s * (track / 2 - 0.13);
      for (const [y0, y1] of [[0.36, 0.3], [0.52, 0.46]]) {
        rod(B, [x + 0.14, y0, s * inZ], [x, y1, kz], 0.014, M.frame, 6);
        rod(B, [x - 0.14, y0, s * inZ], [x, y1, kz], 0.014, M.frame, 6);
      }
      B.add(rbox(0.07, 0.24, 0.06, 0.01, 0.006), M.darkAlloy, { p: [x, 0.38, kz] });    // knuckle
      // coilover from lower arm up to the frame
      const a = V(x - 0.04, 0.33, kz - s * 0.08), b = V(x - 0.02, 0.86, s * 0.34);
      const len = a.distanceTo(b), q = new THREE.Quaternion().setFromUnitVectors(UP, b.clone().sub(a).normalize());
      const mid = a.clone().lerp(b, 0.5);
      B.add(new THREE.CylinderGeometry(0.022, 0.022, len, 10), M.shock, { p: mid.toArray(), q });
      const helix = new THREE.Curve();
      helix.getPoint = (t, out = new THREE.Vector3()) => out.set(Math.cos(t * 7 * Math.PI * 2) * 0.045, (t - 0.5) * len * 0.7, Math.sin(t * 7 * Math.PI * 2) * 0.045);
      B.add(new THREE.TubeGeometry(helix, 90, 0.008, 5, false), M.spring, { p: mid.toArray(), q });
    }
  };
  arms(FX, TRACK_F, 0.2);
  arms(RX, TRACK_R, 0.2);
  B.build(ute);
  BB.build(bodyGroup);

  // ---------------- drivetrain (stands out in See-through)
  const shaftOff = new THREE.MeshStandardMaterial({ color: 0x5a6066, metalness: 0.7, roughness: 0.35 });
  const shaftOn = new THREE.MeshStandardMaterial({ color: 0xff7a1a, emissive: 0xff7a1a, emissiveIntensity: 0.45, metalness: 0.3, roughness: 0.4 });
  const P = new Batch();
  // motor (7.5 kW) under the seats, axis along x
  const motorQ = new THREE.Quaternion().setFromAxisAngle(V(0, 0, 1), Math.PI / 2);
  P.add(new THREE.CylinderGeometry(0.12, 0.12, 0.3, 24), M.motor, { p: [-0.3, 0.5, 0], q: motorQ });
  for (let i = 0; i < 9; i++) P.add(new THREE.BoxGeometry(0.28, 0.012, 0.012), M.motor, { p: [-0.3, 0.5 + Math.cos(i * 0.7) * 0.125, Math.sin(i * 0.7) * 0.125] });
  P.add(new THREE.CylinderGeometry(0.1, 0.1, 0.04, 20), M.darkAlloy, { p: [-0.13, 0.5, 0], q: motorQ });
  P.add(rbox(0.14, 0.09, 0.1, 0.01, 0.006), M.darkAlloy, { p: [-0.3, 0.64, 0.05] });     // terminal box
  for (const z of [0.02, 0.08]) rod(P, [-0.3, 0.68, z], [-0.62, 0.7, z * 2], 0.008, M.orange, 6);  // HV cables
  // transfer case behind the motor
  P.add(rbox(0.2, 0.2, 0.26, 0.04, 0.02), M.darkAlloy, { p: [-0.6, 0.46, 0.04] });
  // rear diff and front diff
  P.add(rbox(0.22, 0.2, 0.24, 0.05, 0.02), M.darkAlloy, { p: [RX, WHEEL_R + 0.03, 0] });
  P.add(rbox(0.2, 0.18, 0.24, 0.05, 0.02), M.darkAlloy, { p: [FX, WHEEL_R + 0.03, 0] });
  // battery pack under the bed (72 V)
  P.add(rbox(0.56, 0.24, 0.8, 0.03, 0.015), M.pack, { p: [-1.0, 0.64, 0] });
  P.add(new THREE.BoxGeometry(0.4, 0.01, 0.2), M.packLabel, { p: [-1.0, 0.765, 0] });
  P.add(rbox(0.2, 0.14, 0.2, 0.02, 0.01), M.pack, { p: [0.1, 0.56, 0.3] });               // controller
  const driveMeshes = P.build(ute);

  // spinning shafts: a group aimed along the shaft, child spins about local y
  function shaft(a, b, r, parent) {
    const A = V(...a), Bv = V(...b);
    const g = new THREE.Group();
    g.position.copy(A).add(Bv).multiplyScalar(0.5);
    g.quaternion.setFromUnitVectors(UP, Bv.clone().sub(A).normalize());
    const len = A.distanceTo(Bv);
    const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, len, 10), shaftOff);
    const mark = new THREE.Mesh(new THREE.BoxGeometry(r * 0.8, len * 0.9, r * 0.8), M.orange);
    mark.position.x = r * 0.75;
    const spin = new THREE.Group(); spin.add(m, mark); g.add(spin);
    for (const end of [-1, 1]) {                       // CV boots / UJs
      const j = new THREE.Mesh(new THREE.SphereGeometry(r * 1.8, 10, 6), M.rubber);
      j.position.y = end * (len / 2 - r); spin.add(j);
    }
    parent.add(g);
    return { g, spin, m };
  }
  const rearShaft = shaft([-0.7, 0.44, 0.04], [RX + 0.1, WHEEL_R + 0.03, 0], 0.028, ute);
  const frontShaft = shaft([-0.5, 0.44, 0.12], [FX - 0.1, WHEEL_R + 0.03, 0.02], 0.026, ute);
  const halfF = [-1, 1].map(s => shaft([FX, WHEEL_R, s * 0.1], [FX, WHEEL_R, s * (TRACK_F / 2 - 0.12)], 0.02, rig));
  const halfR = [-1, 1].map(s => shaft([RX, WHEEL_R, s * 0.1], [RX, WHEEL_R, s * (TRACK_R / 2 - 0.13)], 0.022, rig));
  const motorShaft = shaft([-0.12, 0.5, 0], [-0.5, 0.48, 0.04], 0.03, ute);
  const diffRing = new THREE.Mesh(new THREE.TorusGeometry(0.15, 0.022, 8, 32),
    new THREE.MeshStandardMaterial({ color: 0x553311, emissive: 0xff7a1a, emissiveIntensity: 0, metalness: 0.4, roughness: 0.4 }));
  diffRing.position.set(FX, WHEEL_R + 0.03, 0); diffRing.rotation.y = Math.PI / 2; ute.add(diffRing);
  const rodMat = M.chrome;
  const fwRod = new THREE.Mesh(new THREE.CylinderGeometry(0.014, 0.014, 0.2, 8), rodMat);
  fwRod.rotation.z = Math.PI / 2; fwRod.position.set(-0.6, 0.6, 0.18); ute.add(fwRod);
  const fwBody = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.18, 10), M.plastic);
  fwBody.rotation.z = Math.PI / 2; fwBody.position.set(-0.78, 0.6, 0.18); ute.add(fwBody);
  const diffRod = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.15, 8), rodMat);
  diffRod.rotation.z = Math.PI / 2; diffRod.position.set(FX - 0.14, WHEEL_R + 0.17, 0.12); ute.add(diffRod);
  const diffBody = new THREE.Mesh(new THREE.CylinderGeometry(0.022, 0.022, 0.16, 10), M.plastic);
  diffBody.rotation.z = Math.PI / 2; diffBody.position.set(FX - 0.3, WHEEL_R + 0.17, 0.12); ute.add(diffBody);

  // ---------------- wheels: lathe tyres with lugs, 12" alloys
  function wheelGeo(width) {
    const R = WHEEL_R, rr = DIMS.RIM_R, h = width / 2;
    const tyreB = new Batch();
    const prof = [[rr, -h + 0.01], [R - 0.06, -h - 0.012], [R - 0.022, -h + 0.004], [R - 0.004, -h + 0.03],
      [R, -h + 0.06], [R, h - 0.06], [R - 0.004, h - 0.03], [R - 0.022, h - 0.004], [R - 0.06, h + 0.012], [rr, h - 0.01]]
      .map(([x, y]) => new THREE.Vector2(x, y));
    const tyre = new THREE.LatheGeometry(prof, 40);
    tyre.rotateX(Math.PI / 2);
    tyreB.add(tyre, M.rubber);
    const N = 20;
    for (let i = 0; i < N; i++) {
      for (const side of [-1, 1]) {
        const a = (i + (side > 0 ? 0.5 : 0)) / N * Math.PI * 2;
        const lug = new THREE.BoxGeometry(0.016, 0.034, width * 0.4);
        tyreB.add(lug, M.rubber, { p: [Math.cos(a) * (R + 0.003), Math.sin(a) * (R + 0.003), side * width * 0.24], r: [side * 0.4, 0, a, "ZYX"] });
      }
      const a = (i + 0.25) / N * Math.PI * 2;      // shoulder lugs
      for (const side of [-1, 1]) tyreB.add(new THREE.BoxGeometry(0.03, 0.028, 0.03), M.rubber, { p: [Math.cos(a) * (R - 0.022), Math.sin(a) * (R - 0.022), side * (h - 0.004)], r: [0, 0, a] });
    }
    // rim barrel, dished face, 6 spokes, hub, lug nuts. Outer face is +z.
    const barrel = new THREE.CylinderGeometry(rr, rr, width - 0.03, 32, 1, true); barrel.rotateX(Math.PI / 2);
    tyreB.add(barrel, M.darkAlloy);
    const face = new THREE.LatheGeometry([[rr + 0.012, 0], [rr, -0.012], [0.06, -0.04], [0.05, -0.03]].map(([x, y]) => new THREE.Vector2(x, y)), 32);
    face.rotateX(Math.PI / 2);
    // spokes
    for (let i = 0; i < 6; i++) {
      const a = i / 6 * Math.PI * 2;
      const sp = new THREE.BoxGeometry(rr - 0.05, 0.03, 0.022); sp.translate((rr - 0.05) / 2 + 0.05, 0, 0);
      tyreB.add(sp, M.alloy, { p: [0, 0, h - 0.04], r: [0, -0.2, a] });
    }
    tyreB.add(new THREE.TorusGeometry(rr - 0.004, 0.012, 6, 32), M.alloy, { p: [0, 0, h - 0.018] });
    tyreB.add(new THREE.CylinderGeometry(0.055, 0.06, 0.05, 20), M.alloy, { p: [0, 0, h - 0.06], r: [Math.PI / 2, 0, 0] });
    tyreB.add(new THREE.CylinderGeometry(0.03, 0.03, 0.02, 12), M.chrome, { p: [0, 0, h - 0.03], r: [Math.PI / 2, 0, 0] });
    for (let i = 0; i < 4; i++) {
      const a = i / 4 * Math.PI * 2 + 0.4;
      tyreB.add(new THREE.CylinderGeometry(0.008, 0.008, 0.02, 6), M.chrome, { p: [Math.cos(a) * 0.045, Math.sin(a) * 0.045, h - 0.03], r: [Math.PI / 2, 0, 0] });
    }
    // dark inner of the rim so you can't see through it
    tyreB.add(new THREE.CircleGeometry(rr, 24), M.frame, { p: [0, 0, -0.01] });
    tyreB.add(new THREE.CircleGeometry(rr, 24), M.frame, { p: [0, 0, -0.01], r: [0, Math.PI, 0] });
    face.dispose();
    return tyreB;
  }
  const wheels = [];
  for (const [x, s] of [[FX, -1], [FX, 1], [RX, -1], [RX, 1]]) {
    const front = x > 0, width = front ? DIMS.TYRE_W_F : DIMS.TYRE_W_R, track = front ? TRACK_F : TRACK_R;
    const w = new THREE.Group();
    w.position.set(x, WHEEL_R, s * track / 2);
    const mirror = new THREE.Group(); mirror.scale.z = s;      // outer face points away from the ute
    wheelGeo(width).build(mirror);
    w.add(mirror);
    rig.add(w);
    wheels.push({ g: w, front, mirror });
  }

  // ---------------- cargo bed (dumps about its rear edge)
  const trayPivot = new THREE.Group(); trayPivot.position.set(-1.47, 0.84, 0); ute.add(trayPivot);
  const T = new Batch();
  const BL = 0.86, BW = 1.2, BH = 0.3;
  T.add(rbox(BL, 0.04, BW, 0.03, 0.012), M.bed, { p: [BL / 2, 0, 0] });                     // floor
  for (let i = 0; i < 7; i++) T.add(new THREE.BoxGeometry(BL - 0.1, 0.014, 0.03), M.plasticGrey, { p: [BL / 2, 0.024, -0.45 + i * 0.15] });
  for (const s of [-1, 1]) {
    T.add(rbox(BL, BH, 0.05, 0.02, 0.015), M.bed, { p: [BL / 2, BH / 2, s * (BW / 2 - 0.025)] });  // sides
    T.add(rbox(BL + 0.02, 0.05, 0.1, 0.02, 0.015), M.bed, { p: [BL / 2, BH, s * (BW / 2 - 0.03)] }); // top rail
    for (const x of [0.1, BL / 2, BL - 0.1]) T.add(rbox(0.06, 0.04, 0.06, 0.01, 0.005), M.plasticGrey, { p: [x, BH + 0.02, s * (BW / 2 - 0.03)] }); // stake pockets / tie downs
    for (const x of [0.25, 0.6]) T.add(rbox(0.04, BH - 0.06, 0.02, 0.01, 0.005), M.bed, { p: [x, BH / 2, s * (BW / 2 + 0.005)] });  // outer ribs
  }
  T.add(rbox(0.05, BH + 0.03, BW, 0.02, 0.015), M.bed, { p: [BL - 0.025, BH / 2 + 0.01, 0] }); // front wall
  T.add(rbox(0.05, BH - 0.02, BW - 0.12, 0.02, 0.015), M.bed, { p: [0.03, BH / 2, 0] });     // tailgate
  T.add(rbox(0.02, 0.04, 0.3, 0.01, 0.006), M.plasticGrey, { p: [0.0, BH - 0.06, 0] });     // tailgate handle
  for (const s of [-1, 1]) T.add(rbox(0.04, 0.12, 0.04, 0.01, 0.006), M.plastic, { p: [0.03, 0.08, s * 0.57] });  // taillight housings
  const trayBody = new THREE.Group(); trayPivot.add(trayBody);
  T.build(trayBody);
  const tailMat = new THREE.MeshStandardMaterial({ color: 0x400000, emissive: 0xff0000, emissiveIntensity: 0, roughness: 0.2 });
  for (const s of [-1, 1]) {
    const l = new THREE.Mesh(new THREE.BoxGeometry(0.012, 0.1, 0.05), tailMat);
    l.position.set(0.005, 0.08, s * 0.57); trayBody.add(l);
  }
  // tray actuator: barrel on the frame, rod to the bed floor (updated each frame)
  const actBarrel = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.3, 12), M.plastic); ute.add(actBarrel);
  const actRod = new THREE.Mesh(new THREE.CylinderGeometry(0.014, 0.014, 1, 8), M.chrome); ute.add(actRod);
  const tray = { pivot: trayPivot, actBarrel, actRod, base: V(-0.72, 0.5, 0.42), tipLocal: V(0.62, -0.02, 0.42) };

  // ---------------- winch (drum spins, cable pays out)
  const drum = new THREE.Group(); drum.position.set(1.36, 0.46, 0); ute.add(drum);
  const db = new Batch();
  db.add(new THREE.CylinderGeometry(0.055, 0.055, 0.26, 16), M.rubber, { r: [Math.PI / 2, 0, 0] });
  db.add(new THREE.BoxGeometry(0.02, 0.112, 0.262), M.orange);
  db.add(new THREE.TorusGeometry(0.06, 0.01, 6, 16), M.darkAlloy, { p: [0, 0, 0.12] });
  db.build(drum);
  const wb = new Batch();
  wb.add(new THREE.CylinderGeometry(0.065, 0.065, 0.16, 16), M.plastic, { p: [1.36, 0.46, -0.22], r: [Math.PI / 2, 0, 0] });  // motor
  wb.add(rbox(0.13, 0.13, 0.12, 0.02, 0.01), M.plastic, { p: [1.36, 0.46, 0.2] });                                              // gearbox
  wb.add(rbox(0.1, 0.06, 0.12, 0.01, 0.006), M.hook, { p: [1.36, 0.555, 0.2] });                                                // clutch lever
  for (const z of [-0.14, 0.14]) wb.add(rbox(0.14, 0.14, 0.012, 0.01, 0.004), M.darkAlloy, { p: [1.36, 0.46, z] });
  wb.build(ute);
  const cable = new THREE.Mesh(new THREE.CylinderGeometry(0.005, 0.005, 1, 5), M.chrome); ute.add(cable);
  const hook = new THREE.Mesh(new THREE.TorusGeometry(0.03, 0.01, 6, 12, Math.PI * 1.5), M.hook);
  hook.rotation.y = Math.PI / 2; ute.add(hook);
  const winchGlow = new THREE.PointLight(0xff7a1a, 0, 1.4); winchGlow.position.set(1.51, 0.65, 0); ute.add(winchGlow);
  const winch = { drum, cable, hook, glow: winchGlow, x: 1.52, y: 0.45 };

  // ---------------- lights: 4 bars in the front grille, interior bar, 2 rear floods on the cage plates
  let fadeTex = null;
  function beamFade() {          // beams fade out away from the lamp
    if (fadeTex) return fadeTex;
    const c = document.createElement("canvas"); c.width = 4; c.height = 128;
    const g = c.getContext("2d"), gr = g.createLinearGradient(0, 0, 0, 128);
    gr.addColorStop(0, "#fff"); gr.addColorStop(0.35, "#777"); gr.addColorStop(1, "#000");
    g.fillStyle = gr; g.fillRect(0, 0, 4, 128);
    return (fadeTex = new THREE.CanvasTexture(c));
  }
  // style: "bar" (with mounting feet), "slim" (single-row bar in the grille), "pod" (flood)
  function makeLight(x, y, z, w, dir, color = 0xfff2d6, angle = 0.5, dist = 40, style = "bar") {
    const pod = style === "pod", slim = style === "slim";
    const mat = new THREE.MeshStandardMaterial({ color: 0x222222, emissive: color, emissiveIntensity: 0 });
    const g = new THREE.Group(); g.position.set(x, y, z); ute.add(g);
    const lb = new Batch();
    if (pod) {
      lb.add(rbox(0.06, 0.1, 0.1, 0.02, 0.01), M.plastic);
      lb.add(new THREE.BoxGeometry(0.03, 0.06, 0.05), M.plastic, { p: [0.04, -0.07, 0] });
    } else if (slim) {
      lb.add(rbox(0.03, 0.03, w, 0.008, 0.006), M.plastic);
    } else {
      lb.add(rbox(0.07, 0.075, w, 0.015, 0.008), M.plastic);
      for (let i = 0; i < Math.round(w / 0.02); i++) lb.add(new THREE.BoxGeometry(0.05, 0.006, 0.004), M.plasticGrey, { p: [-0.01, 0.04, -w / 2 + 0.01 + i * 0.02] });  // fins
      lb.add(new THREE.BoxGeometry(0.02, 0.03, 0.02), M.frame, { p: [0, -0.05, -w / 2 + 0.03] });
      lb.add(new THREE.BoxGeometry(0.02, 0.03, 0.02), M.frame, { p: [0, -0.05, w / 2 - 0.03] });
    }
    lb.build(g, { shadow: false });
    const lens = new THREE.Mesh(new THREE.PlaneGeometry(pod ? 0.08 : w - 0.02, pod ? 0.08 : slim ? 0.018 : 0.05), mat);
    const d = V(...dir).normalize();
    lens.lookAt(d); lens.position.copy(d).multiplyScalar(pod ? 0.032 : slim ? 0.017 : 0.037);
    g.add(lens);
    const spot = new THREE.SpotLight(color, 0, dist, angle, 0.6, 1);
    spot.position.set(x, y, z);
    spot.target.position.set(x + dir[0], y + dir[1], z + dir[2]);
    ute.add(spot, spot.target);
    const len = Math.min(dist, 7);
    const beamMat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0, alphaMap: beamFade(),
      blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide, fog: true });
    const beam = new THREE.Mesh(new THREE.ConeGeometry(Math.tan(angle) * len, len, 20, 1, true), beamMat);
    beam.geometry.translate(0, -len / 2, 0);
    beam.position.set(x, y, z);
    beam.quaternion.setFromUnitVectors(V(0, -1, 0), d);
    ute.add(beam);
    return { mat, spot, mesh: g, beamMat };
  }
  // Sam's Teryx: four slim bars stacked in the gaps of the front grille, front_1 at the top
  const FRONT_Y = [0.835, 0.785, 0.735, 0.685];
  const lightBars = FRONT_Y.map(y => makeLight(1.345, y, 0, 0.56, [10, -0.3, 0], 0xfff2d6, 0.4, 45, "slim"));
  const interior = makeLight(-0.15, 1.85, 0, 0.18, [0, -1, 0], 0xffe1b0, 1.1, 4);
  interior.mesh.rotation.z = Math.PI / 2;
  // Sam's Teryx: rear floods bolt to the outside of the rear roll cage mounting plates,
  // aimed back and a little out past the rear tyres ("rear pods" on the dash)
  const rearPods = [-1, 1].map(s => makeLight(-0.61, 0.71, s * 0.77, 0.1, [-10, -1.2, s * 3.5], 0xffffff, 0.7, 18, "pod"));
  // stock headlights get a real beam at night
  const headSpot = new THREE.SpotLight(0xfff2d6, 0, 30, 0.45, 0.5, 1);
  headSpot.position.set(1.35, 0.9, 0); headSpot.target.position.set(10, -0.6, 0);
  ute.add(headSpot, headSpot.target);

  const bodyMats = [M.paint, M.plastic, M.plasticGrey, M.cage, M.seat, M.seatPanel, M.bed, M.frame];

  // Swap the code-drawn bodywork for the Blender model (teryx.glb). Its
  // materials are matched by name to ours, so paint, see-through and the
  // lamps all keep working. If the GLB never loads, the code version stays.
  function useGlb(gltf) {
    const byName = {
      Paint: M.paint, Plastic: M.plastic, PlasticGrey: M.plasticGrey, Cage: M.cage, Frame: M.frame,
      Seat: M.seat, SeatPanel: M.seatPanel, Bed: M.bed, Rubber: M.rubber, Alloy: M.alloy,
      DarkAlloy: M.darkAlloy, Chrome: M.chrome, Glass: M.glass, HeadLens: headMat, TailLens: tailMat,
    };
    const prep = obj => {
      obj.traverse(o => {
        if (!o.isMesh) return;
        o.material = byName[o.material.name] || o.material;
        o.castShadow = true; o.receiveShadow = true;
      });
      return obj;
    };
    const get = name => gltf.scene.getObjectByName(name);
    const body = get("Body"), trayG = get("Tray"), wf = get("WheelF"), wr = get("WheelR");
    if (!body || !trayG || !wf || !wr) throw new Error("teryx.glb is missing a part");
    bodyGroup.visible = false;
    ute.add(prep(body));
    trayBody.visible = false;
    prep(trayG).position.set(0, 0, 0);          // origin is already on the hinge
    trayPivot.add(trayG);
    for (const w of wheels) {
      w.mirror.children.forEach(c => { c.visible = false; });
      const m = prep((w.front ? wf : wr).clone());
      m.position.set(0, 0, 0);
      w.mirror.add(m);
    }
  }

  return {
    rig, ute, M, bodyMats, wheels, lightBars, interior, rearPods,
    head: { mat: headMat, spot: headSpot }, tailMat, pinMats,
    screen: { mat: screenMat, canvas: screenCanvas, tex: screenTex },
    drive: { rearShaft, frontShaft, halfF, halfR, motorShaft, diffRing, fwRod, diffRod, shaftOn, shaftOff, driveMeshes },
    tray, winch, useGlb,
    setPaint(hex) { M.paint.color.setHex(hex); },
  };
}
