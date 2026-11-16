// Virtual Teryx: a simple low-poly UTV that shows what the CAN bus says.
// Everything it shows comes from the dash state feed (/ws), so it works the
// same on the simulator, a replayed log or the real bus.
import * as THREE from "three";
import { OrbitControls } from "/vendor/three/OrbitControls.js";

const $ = id => document.getElementById(id);
const link = new TeryxLink();
let S = {};
link.onState(s => { S = s; });
link.onConnection(ok => { $("offline").hidden = ok; });

// ------------------------------------------------------------------ scene
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
$("view").appendChild(renderer.domElement);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 400);
camera.position.set(5.5, 3.2, 5.5);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0.9, 0);
controls.enableDamping = true;
controls.maxPolarAngle = Math.PI * 0.49;
controls.minDistance = 2.5;
controls.maxDistance = 30;

const hemi = new THREE.HemisphereLight(0xbfd6ff, 0x3a2f22, 1.2);
scene.add(hemi);
const sun = new THREE.DirectionalLight(0xfff1dd, 2.2);
sun.position.set(8, 12, 5);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -8, right: 8, top: 8, bottom: -8 });
scene.add(sun);

function setNight(on) {
  scene.background = new THREE.Color(on ? 0x05070a : 0x8fa9bf);
  scene.fog = new THREE.Fog(scene.background, on ? 12 : 30, on ? 60 : 140);
  hemi.intensity = on ? 0.08 : 1.2;
  sun.intensity = on ? 0.02 : 2.2;
  $("night").classList.toggle("on", on);
}
let night = false;
setNight(night);

// ground: a dirt track texture that scrolls with speed
const gtex = (() => {
  const c = document.createElement("canvas"); c.width = c.height = 256;
  const g = c.getContext("2d");
  g.fillStyle = "#5b4a36"; g.fillRect(0, 0, 256, 256);
  for (let i = 0; i < 900; i++) {
    g.fillStyle = `rgba(${30 + Math.random() * 60},${25 + Math.random() * 45},${15 + Math.random() * 30},${Math.random() * 0.6})`;
    g.fillRect(Math.random() * 256, Math.random() * 256, 2 + Math.random() * 5, 2 + Math.random() * 5);
  }
  g.fillStyle = "rgba(40,30,20,.5)"; g.fillRect(0, 70, 256, 18); g.fillRect(0, 168, 256, 18); // wheel ruts
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(30, 30);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
})();
const ground = new THREE.Mesh(new THREE.PlaneGeometry(240, 240),
  new THREE.MeshStandardMaterial({ map: gtex, roughness: 1 }));
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

// some scenery so you can tell you're moving
const scenery = new THREE.Group(); scene.add(scenery);
const treeMat = new THREE.MeshStandardMaterial({ color: 0x2f5a2e, flatShading: true });
const trunkMat = new THREE.MeshStandardMaterial({ color: 0x4a3524, flatShading: true });
for (let i = 0; i < 70; i++) {
  const t = new THREE.Group();
  const h = 2 + Math.random() * 3;
  const top = new THREE.Mesh(new THREE.ConeGeometry(0.9 + Math.random() * 0.6, h, 6), treeMat);
  top.position.y = h / 2 + 0.8; top.castShadow = true;
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.16, 0.9, 5), trunkMat);
  trunk.position.y = 0.45;
  t.add(top, trunk);
  const side = Math.random() < 0.5 ? -1 : 1;
  t.position.set(Math.random() * 200 - 100, 0, side * (5 + Math.random() * 40));
  scenery.add(t);
}

// ------------------------------------------------------------------ the UTV
// Axes: +x forward, +y up, +z right. Units are metres.
const M = (color, extra = {}) => new THREE.MeshStandardMaterial({ color, flatShading: true, roughness: 0.6, metalness: 0.1, ...extra });
const paint = M(0x3d5a2a);          // olive body, original colour scheme
const black = M(0x1a1c1e);
const frameMat = M(0x2b2f33, { metalness: 0.5, roughness: 0.4 });
const seatMat = M(0x222222);
const bodyMats = [paint, black, frameMat, seatMat];

function box(w, h, d, mat, x, y, z, parent) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  m.position.set(x, y, z); m.castShadow = true; m.receiveShadow = true;
  (parent || ute).add(m);
  return m;
}
function tube(a, b, r, mat, parent) {
  const A = new THREE.Vector3(...a), B = new THREE.Vector3(...b);
  const len = A.distanceTo(B);
  const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, len, 8), mat);
  m.position.copy(A).add(B).multiplyScalar(0.5);
  m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), B.clone().sub(A).normalize());
  m.castShadow = true;
  (parent || ute).add(m);
  return m;
}

const rig = new THREE.Group(); scene.add(rig);        // follows terrain pitch
const ute = new THREE.Group(); rig.add(ute);          // body (bounces a little)

const WHEELBASE = 2.1, TRACK = 1.3, WHEEL_R = 0.34;
// chassis and body panels
box(2.7, 0.18, 1.0, frameMat, 0, 0.42, 0);                    // main frame
box(0.9, 0.32, 1.35, paint, 1.05, 0.72, 0);                   // bonnet
box(0.5, 0.3, 1.35, paint, 1.45, 0.62, 0).rotation.z = -0.35; // nose
box(0.18, 0.18, 1.5, black, 1.72, 0.48, 0);                   // front bumper
box(1.25, 0.12, 1.35, black, 0.0, 0.55, 0);                   // cab floor
box(0.1, 0.55, 1.35, black, 0.62, 0.85, 0);                   // firewall / dash
for (const z of [-0.33, 0.33]) {                              // seats
  box(0.5, 0.14, 0.5, seatMat, -0.2, 0.75, z);
  box(0.12, 0.55, 0.5, seatMat, -0.47, 1.05, z).rotation.z = 0.12;
}
for (const x of [WHEELBASE / 2, -WHEELBASE / 2]) {            // mudguards
  for (const z of [-1, 1]) box(0.85, 0.06, 0.32, paint, x, 0.82, z * 0.62);
}
// steering wheel and our dash screen
const sw = new THREE.Mesh(new THREE.TorusGeometry(0.17, 0.025, 6, 16), black);
sw.position.set(0.42, 1.08, -0.33); sw.rotation.y = Math.PI / 2; sw.rotation.x = 0.5; ute.add(sw);
const screenMat = new THREE.MeshStandardMaterial({ color: 0x111111, emissive: 0xff7a1a, emissiveIntensity: 0.6 });
box(0.03, 0.16, 0.26, screenMat, 0.57, 1.14, 0.02);

// roll cage
const C = 0.035;
const cageF = 0.62, cageR = -0.62, roofY = 1.85;
for (const z of [-0.66, 0.66]) {
  tube([cageF, 0.95, z], [cageF - 0.05, roofY, z * 0.95], C, frameMat);
  tube([cageR, 0.62, z], [cageR, roofY, z * 0.95], C, frameMat);
  tube([cageF - 0.05, roofY, z * 0.95], [cageR, roofY, z * 0.95], C, frameMat);
  tube([cageR, 1.2, z], [-1.25, 0.75, z], C, frameMat);      // rear braces
}
tube([cageF - 0.05, roofY, -0.63], [cageF - 0.05, roofY, 0.63], C, frameMat);
tube([cageR, roofY, -0.63], [cageR, roofY, 0.63], C, frameMat);
const roof = box(1.3, 0.04, 1.3, M(0x1a1c1e, { transparent: true, opacity: 0.85 }), 0, roofY + 0.04, 0);
bodyMats.push(roof.material);

// wheels
const tyreMat = M(0x151515, { roughness: 0.95 });
const hubMat = M(0x8a8f94, { metalness: 0.7, roughness: 0.3 });
const wheels = [];
for (const [x, z] of [[1, -1], [1, 1], [-1, -1], [-1, 1]]) {
  const w = new THREE.Group();
  const tyre = new THREE.Mesh(new THREE.CylinderGeometry(WHEEL_R, WHEEL_R, 0.27, 14), tyreMat);
  tyre.rotation.x = Math.PI / 2; tyre.castShadow = true; w.add(tyre);
  for (let i = 0; i < 14; i++) {                               // tread blocks
    const lug = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.04, 0.26), tyreMat);
    const a = (i / 14) * Math.PI * 2;
    lug.position.set(Math.cos(a) * WHEEL_R, Math.sin(a) * WHEEL_R, 0); lug.rotation.z = a;
    w.add(lug);
  }
  const hub = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.17, 0.28, 6), hubMat);
  hub.rotation.x = Math.PI / 2; w.add(hub);
  w.position.set(x * WHEELBASE / 2, WHEEL_R, z * TRACK / 2);
  rig.add(w);
  wheels.push({ g: w, front: x > 0 });
}

// drivetrain (best seen with See-through on)
const shaftOff = M(0x555a60, { metalness: 0.6 });
const shaftOn = M(0xff7a1a, { emissive: 0xff7a1a, emissiveIntensity: 0.4 });
const motor = box(0.45, 0.3, 0.35, M(0x4a6b8a, { metalness: 0.5 }), -0.65, 0.42, 0);
const tcase = box(0.25, 0.22, 0.25, M(0x6b6f74, { metalness: 0.5 }), -0.25, 0.42, 0);
const rearShaft = tube([-0.65, 0.4, 0], [-WHEELBASE / 2, WHEEL_R, 0], 0.035, shaftOff);
const frontShaft = tube([-0.12, 0.4, 0], [WHEELBASE / 2 - 0.1, WHEEL_R + 0.02, 0], 0.035, shaftOff);
const frontDiff = box(0.22, 0.2, 0.26, M(0x6b6f74, { metalness: 0.5 }), WHEELBASE / 2, WHEEL_R + 0.02, 0);
const diffRing = new THREE.Mesh(new THREE.TorusGeometry(0.16, 0.025, 6, 24), shaftOff.clone());
diffRing.position.set(WHEELBASE / 2, WHEEL_R + 0.02, 0); diffRing.rotation.y = Math.PI / 2; rig.add(diffRing);
tube([WHEELBASE / 2, WHEEL_R, -TRACK / 2 + 0.1], [WHEELBASE / 2, WHEEL_R, TRACK / 2 - 0.1], 0.03, frameMat, rig);
tube([-WHEELBASE / 2, WHEEL_R, -TRACK / 2 + 0.1], [-WHEELBASE / 2, WHEEL_R, TRACK / 2 - 0.1], 0.03, frameMat, rig);
// 4WD actuator rod near the transfer case
const fwRod = box(0.2, 0.04, 0.04, M(0xdddddd, { metalness: 0.8 }), -0.25, 0.58, 0.18);
// diff lock actuator rod
const diffRod = box(0.15, 0.035, 0.035, M(0xdddddd, { metalness: 0.8 }), WHEELBASE / 2 - 0.12, WHEEL_R + 0.18, 0.12);

// tray: pivots at its back edge
const trayPivot = new THREE.Group(); trayPivot.position.set(-1.45, 0.82, 0); ute.add(trayPivot);
const trayMat = M(0x2f3a28);
box(1.0, 0.05, 1.3, trayMat, 0.5, 0, 0, trayPivot);
box(1.0, 0.3, 0.05, trayMat, 0.5, 0.16, -0.63, trayPivot);
box(1.0, 0.3, 0.05, trayMat, 0.5, 0.16, 0.63, trayPivot);
box(0.05, 0.3, 1.3, trayMat, 0.98, 0.16, 0, trayPivot);
box(0.05, 0.3, 1.3, trayMat, 0.02, 0.16, 0, trayPivot);       // tailgate
bodyMats.push(trayMat);
// tray actuator: barrel on the frame, rod to the tray floor
const actBarrel = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 0.3, 8), M(0x222222)); ute.add(actBarrel);
const actRod = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 1, 8), M(0xdddddd, { metalness: 0.8 })); ute.add(actRod);

// taillights, brake, trailer plug
const tailMat = new THREE.MeshStandardMaterial({ color: 0x400000, emissive: 0xff1010, emissiveIntensity: 0 });
for (const z of [-0.6, 0.6]) box(0.04, 0.08, 0.14, tailMat, -1.48, 0.7, z);
box(0.3, 0.06, 0.06, frameMat, -1.55, 0.38, 0);                // hitch
const plug = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.06, 10), black);
plug.rotation.z = Math.PI / 2; plug.position.set(-1.5, 0.48, 0.25); ute.add(plug);
const pinMats = { tail: new THREE.MeshBasicMaterial({ color: 0x331111 }), brake: new THREE.MeshBasicMaterial({ color: 0x331111 }) };
const pinT = new THREE.Mesh(new THREE.SphereGeometry(0.013, 6, 6), pinMats.tail); pinT.position.set(-1.535, 0.49, 0.23); ute.add(pinT);
const pinB = new THREE.Mesh(new THREE.SphereGeometry(0.013, 6, 6), pinMats.brake); pinB.position.set(-1.535, 0.49, 0.27); ute.add(pinB);

// winch on the front bumper, with a cable and hook
const drum = new THREE.Group(); drum.position.set(1.78, 0.52, 0); ute.add(drum);
const drumBody = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 0.3, 10), M(0x222222)); drumBody.rotation.x = Math.PI / 2; drum.add(drumBody);
const drumStripe = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.15, 0.31), M(0xff7a1a)); drumStripe.position.y = 0.0; drum.add(drumStripe);
box(0.12, 0.16, 0.12, M(0x333333), 1.78, 0.52, -0.24);         // motor end
box(0.12, 0.16, 0.12, M(0x333333), 1.78, 0.52, 0.24);          // gearbox end
const cable = new THREE.Mesh(new THREE.CylinderGeometry(0.008, 0.008, 1, 5), M(0x999999, { metalness: 0.8 })); ute.add(cable);
const hook = box(0.06, 0.1, 0.03, M(0xff3a1a, { metalness: 0.5 }), 1.9, 0.5, 0);
const winchGlow = new THREE.PointLight(0xff7a1a, 0, 1.2); winchGlow.position.set(1.9, 0.7, 0); ute.add(winchGlow);

// light bars: 4 on the roof front edge, 1 interior, 2 rear pods
const lightBars = [];
function makeLight(x, y, z, w, dir, color = 0xfff2d6, angle = 0.5, dist = 40) {
  const mat = new THREE.MeshStandardMaterial({ color: 0x222222, emissive: color, emissiveIntensity: 0 });
  const mesh = box(0.07, 0.08, w, mat, x, y, z);
  const spot = new THREE.SpotLight(color, 0, dist, angle, 0.6, 1);
  spot.position.set(x, y, z);
  spot.target.position.set(x + dir[0], y + dir[1], z + dir[2]);
  ute.add(spot, spot.target);
  // a soft visible beam so you can see the light at a glance
  const len = Math.min(dist, 7);
  const beamMat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0,
    blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
  const beam = new THREE.Mesh(new THREE.ConeGeometry(Math.tan(angle) * len, len, 20, 1, true), beamMat);
  beam.geometry.translate(0, -len / 2, 0);           // apex at the light
  beam.position.set(x, y, z);
  beam.quaternion.setFromUnitVectors(new THREE.Vector3(0, -1, 0), new THREE.Vector3(...dir).normalize());
  ute.add(beam);
  return { mat, spot, mesh, beamMat };
}
const FRONT_Z = [-0.48, -0.16, 0.16, 0.48];
FRONT_Z.forEach(z => lightBars.push(makeLight(cageF - 0.02, roofY + 0.1, z, 0.28, [10, -2.2, z * 4], 0xfff2d6, 0.32, 45)));
const interior = makeLight(0, roofY - 0.06, 0, 0.18, [0, -1, 0], 0xffe1b0, 1.1, 4);
interior.mesh.rotation.z = Math.PI / 2;
const rearPods = [-0.55, 0.55].map(z => makeLight(cageR - 0.05, roofY - 0.1, z, 0.1, [-10, -3, z * 3], 0xffffff, 0.6, 18));
// headlights (always on dim at night, part of the stock harness)
const headMat = new THREE.MeshStandardMaterial({ color: 0x333333, emissive: 0xfff2d6, emissiveIntensity: 0.2 });
for (const z of [-0.45, 0.45]) box(0.04, 0.08, 0.2, headMat, 1.62, 0.72, z);

// ------------------------------------------------------------------ controls
const views = {
  front: [5.5, 2.4, 3.5], side: [0.2, 1.6, 7], rear: [-6, 2.6, 2.5], top: [0.01, 9, 0.01],
};
document.querySelectorAll("[data-cam]").forEach(b => b.onclick = () => {
  const p = views[b.dataset.cam];
  camera.position.set(p[0], p[1], p[2]);
  controls.target.set(0, 0.9, 0);
});
let follow = true;
$("follow").onclick = () => { follow = !follow; $("follow").classList.toggle("on", follow); };
let xray = false;
$("xray").onclick = () => {
  xray = !xray; $("xray").classList.toggle("on", xray);
  bodyMats.forEach(m => { m.transparent = xray || m === roof.material; m.opacity = xray ? 0.18 : (m === roof.material ? 0.85 : 1); m.depthWrite = !xray; });
};
$("night").onclick = () => { night = !night; setNight(night); };
window.addEventListener("keydown", e => { if (e.key === "n") $("night").click(); if (e.key === "x") $("xray").click(); });

function resize() {
  const w = innerWidth, h = innerHeight;
  renderer.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix();
}
addEventListener("resize", resize); resize();

// ------------------------------------------------------------------ animate
const lerp = (a, b, k) => a + (b - a) * k;
let wheelAngle = 0, drumAngle = 0, shaftAngle = 0, travel = 0;
let cableLen = 0.12;           // metres paid out
let trayAngle = 0, pitch = 0, bounce = 0;
let last = performance.now();
const TRAY_MAX = THREE.MathUtils.degToRad(48);
const v3 = new THREE.Vector3();

function tag(text, cls) { return `<span class="tag ${cls || ""}">${text}</span>`; }

function frame(now) {
  const dt = Math.min(0.1, (now - last) / 1000); last = now;
  const online = S["mc.online"];
  const dir = { forward: 1, reverse: -1 }[S["mc.direction"]] || (S["mc.rpm"] < 0 ? -1 : S["mc.rpm"] > 0 ? 1 : 0);
  const speed = online ? (S["mc.speed"] || 0) : 0;
  const v = (speed / 3.6) * (dir || 1) * (speed > 0 ? 1 : 0);

  // movement: wheels spin, ground and scenery scroll past
  travel += v * dt;
  wheelAngle -= (v * dt) / WHEEL_R;
  wheels.forEach(w => { w.g.rotation.z = wheelAngle; });
  gtex.offset.x = (travel / 8) % 1;
  scenery.children.forEach(t => { t.position.x -= v * dt; if (t.position.x < -100) t.position.x += 200; if (t.position.x > 100) t.position.x -= 200; });

  // hill: pitch the whole rig, and a bit of trail bounce
  const grade = S["sim.grade_pct"] || 0;
  pitch = lerp(pitch, Math.atan(grade / 100), dt * 2);
  rig.rotation.z = pitch;
  bounce = speed > 1 ? Math.sin(now / 90) * 0.012 * Math.min(1, speed / 20) : 0;
  ute.position.y = bounce;

  // drivetrain
  const fw = S["act.4wd"] || "unknown";
  const in4 = fw === "4wd" || fw === "to_2wd";
  shaftAngle += (v * dt) / WHEEL_R * 4;
  rearShaft.material = Math.abs(v) > 0.05 ? shaftOn : shaftOff;
  frontShaft.material = in4 ? shaftOn : shaftOff;
  if (in4) frontShaft.rotation.y = shaftAngle;
  fwRod.position.x = lerp(fwRod.position.x, -0.25 + (fw === "4wd" || fw === "to_4wd" ? 0.08 : -0.02), dt * 4);
  const diff = (S["an.diff_pos"] || 0) / 100;
  diffRing.material.color.setHSL(0.07, 1, 0.2 + diff * 0.35);
  diffRing.material.emissive = diffRing.material.emissive || new THREE.Color();
  diffRing.material.emissive.setHex(0xff7a1a); diffRing.material.emissiveIntensity = diff * 0.8;
  diffRing.scale.setScalar(0.7 + diff * 0.5);
  diffRod.position.x = WHEELBASE / 2 - 0.12 + diff * 0.05;

  // tray
  trayAngle = lerp(trayAngle, ((S["act.tray_pct"] || 0) / 100) * TRAY_MAX, dt * 6);
  trayPivot.rotation.z = trayAngle;      // front edge lifts, hinge at the back
  const base = new THREE.Vector3(-0.75, 0.55, 0.3);
  const tip = new THREE.Vector3(0.55, -0.02, 0.3).applyEuler(trayPivot.rotation).add(trayPivot.position);
  const len = base.distanceTo(tip);
  const dirv = tip.clone().sub(base).normalize();
  const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dirv);
  actBarrel.position.copy(base).addScaledVector(dirv, 0.15); actBarrel.quaternion.copy(q);
  actRod.scale.y = Math.max(0.05, len - 0.15);
  actRod.position.copy(base).addScaledVector(dirv, 0.15 + (len - 0.15) / 2); actRod.quaternion.copy(q);

  // winch
  const wIn = S["winch.in"], wOut = S["winch.out"];
  const wRate = wIn ? -0.8 : wOut ? 0.8 : 0;
  cableLen = Math.max(0.12, Math.min(8, cableLen + wRate * dt));
  drumAngle += wRate * dt / 0.07;
  drum.rotation.z = drumAngle;
  hook.position.set(1.8 + cableLen, 0.42, 0);
  cable.scale.y = cableLen; cable.position.set(1.8 + cableLen / 2, 0.47, 0); cable.rotation.z = Math.PI / 2;
  winchGlow.intensity = S["winch.armed"] ? (wIn || wOut ? 1.5 + Math.sin(now / 60) * 0.5 : 0.4) : 0;

  // lights (levels are what the control box is actually outputting, effects included)
  const keys = ["light.front_1", "light.front_2", "light.front_3", "light.front_4"];
  keys.forEach((k, i) => {
    const lvl = (S[k] || 0) / 255;
    lightBars[i].mat.emissiveIntensity = lvl * 6;
    lightBars[i].spot.intensity = lvl * 120;
    lightBars[i].beamMat.opacity = lvl * (night ? 0.05 : 0.015);
  });
  const inl = (S["light.interior"] || 0) / 255;
  interior.mat.emissiveIntensity = inl * 4; interior.spot.intensity = inl * 8;
  interior.beamMat.opacity = inl * (night ? 0.08 : 0.02);
  const rear = S["light.rear"] ? 1 : 0;
  rearPods.forEach(p => { p.mat.emissiveIntensity = rear * 6; p.spot.intensity = rear * 80;
    p.beamMat.opacity = rear * (night ? 0.06 : 0.015); });
  const brake = S["mc.brake"] || S["in.brake"];
  tailMat.emissiveIntensity = brake ? 3 : (S["trailer.tail"] ? 0.8 : 0.15);
  headMat.emissiveIntensity = night ? 2 : 0.2;
  pinMats.tail.color.setHex(S["trailer.tail"] ? 0xff3030 : 0x331111);
  pinMats.brake.color.setHex(S["trailer.brake"] ? 0xff3030 : 0x331111);
  screenMat.emissiveIntensity = S["pico.online"] ? 0.9 : 0.1;

  // camera follow keeps the ute in view while orbiting
  if (follow) { v3.set(0, 0.9 + bounce, 0); controls.target.lerp(v3, 0.2); }
  controls.update();
  renderer.render(scene, camera);

  // HUD
  $("spd").textContent = online ? speed.toFixed(0) : "--";
  $("dir").textContent = { forward: "D", reverse: "R", neutral: "N" }[S["mc.direction"]] || "-";
  $("fw").textContent = fw.toUpperCase().replace("_", " ");
  $("diff").textContent = (S["an.diff_pos"] ?? "--") + "%";
  $("tray").textContent = (S["act.tray"] || "--") + " " + Math.round(S["act.tray_pct"] || 0) + "%";
  $("winch").textContent = wIn ? "IN" : wOut ? "OUT" : S["winch.armed"] ? "ARMED" : "OFF";
  $("soc").textContent = online ? Math.round(S["mc.soc"]) + "%" : "--";
  $("pow").textContent = online ? ((S["mc.batt_v"] * S["mc.batt_a"]) / 1000).toFixed(1) + " kW" : "--";
  const tags = [];
  if (!online) tags.push(tag("MOTOR OFFLINE", "bad"));
  if (!S["pico.online"]) tags.push(tag("BOX OFFLINE", "bad"));
  if (S["mc.limp"]) tags.push(tag("LIMP", "warn"));
  if (brake) tags.push(tag("BRAKE", "on"));
  if (S["light.rear"]) tags.push(tag("REAR PODS", "on"));
  if (S["trailer.tail"]) tags.push(tag("TRAILER TAIL", "on"));
  if (S["trailer.brake"]) tags.push(tag("TRAILER BRAKE", "on"));
  if (S["winch.isolator"]) tags.push(tag("WINCH POWER", "on"));
  if (S["light.effect"] && S["light.effect"] !== "none") tags.push(tag("FX " + S["light.effect"].toUpperCase(), "on"));
  (S["mc.faults"] || []).forEach(f => tags.push(tag(f.replace(/_/g, " ").toUpperCase(), "bad")));
  (S["pico.faults"] || []).forEach(f => tags.push(tag(f.replace(/_/g, " ").toUpperCase(), "warn")));
  if (S["sim.scenario"]) tags.push(tag("SIM " + S["sim.scenario"].toUpperCase()));
  $("tags").innerHTML = tags.join("");

  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
