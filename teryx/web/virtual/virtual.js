// Virtual Teryx: a detailed 2013 Teryx 750 that shows what the CAN bus says.
// Everything it shows comes from the dash state feed (/ws), so it works the
// same on the simulator, a replayed log or the real bus.
import * as THREE from "three";
import { OrbitControls } from "/vendor/three/OrbitControls.js";
import { RoomEnvironment } from "/vendor/three/RoomEnvironment.js";
import { mergeGeometries } from "/vendor/three/BufferGeometryUtils.js";
import { buildTeryx, DIMS, PAINTS } from "/virtual-static/teryx-model.js";

const $ = id => document.getElementById(id);
const link = new TeryxLink();
let S = {};
let OVR = null;   // for testing: window.teryxOverride({"light.front_1": 255, ...})
link.onState(s => { S = OVR ? { ...s, ...OVR } : s; });
window.teryxOverride = o => { OVR = o; S = { ...S, ...(o || {}) }; };
link.onConnection(ok => { $("offline").hidden = ok; });

// Pi 5 (or ?lite): lower pixel ratio and smaller shadow map
const params = new URLSearchParams(location.search);
const LITE = params.has("lite") || /aarch64|armv7|armv8|Raspbian|Raspberry/i.test(navigator.userAgent + " " + (navigator.platform || ""));

// ------------------------------------------------------------------ scene
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
renderer.setPixelRatio(Math.min(devicePixelRatio, LITE ? 1 : 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
$("view").appendChild(renderer.domElement);
const scene = new THREE.Scene();
// soft studio-style reflections on the paint and alloys
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 600);
camera.position.set(5.2, 2.6, 4.2);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0.85, 0);
controls.enableDamping = true;
controls.maxPolarAngle = Math.PI * 0.49;
controls.minDistance = 2.2;
controls.maxDistance = 30;

const hemi = new THREE.HemisphereLight(0xcfe0ff, 0x4a3b28, 0.9);
scene.add(hemi);
const sun = new THREE.DirectionalLight(0xfff1dd, 2.6);
sun.position.set(7, 12, 5);
sun.castShadow = true;
sun.shadow.mapSize.set(LITE ? 1024 : 2048, LITE ? 1024 : 2048);
sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.02;
Object.assign(sun.shadow.camera, { left: -4, right: 4, top: 4, bottom: -4, near: 1, far: 40 });
scene.add(sun);

// sky dome with a gradient, stars at night
const skyMat = new THREE.ShaderMaterial({
  side: THREE.BackSide, depthWrite: false, fog: false,
  uniforms: { top: { value: new THREE.Color() }, horizon: { value: new THREE.Color() }, ground: { value: new THREE.Color() } },
  vertexShader: "varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }",
  fragmentShader: `uniform vec3 top; uniform vec3 horizon; uniform vec3 ground; varying vec3 vP;
    void main(){ float h = vP.y; vec3 c = h > 0.0 ? mix(horizon, top, pow(h, 0.55)) : mix(horizon, ground, min(1.0, -h * 6.0));
    gl_FragColor = vec4(c, 1.0); }`,
});
const sky = new THREE.Mesh(new THREE.SphereGeometry(400, 32, 16), skyMat);
scene.add(sky);
const stars = (() => {
  const n = 900, pos = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    const a = Math.random() * Math.PI * 2, e = Math.asin(0.05 + Math.random() * 0.95);
    pos.set([Math.cos(a) * Math.cos(e) * 380, Math.sin(e) * 380, Math.sin(a) * Math.cos(e) * 380], i * 3);
  }
  const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  const p = new THREE.Points(g, new THREE.PointsMaterial({ color: 0xffffff, size: 1.6, sizeAttenuation: false, fog: false, transparent: true, opacity: 0.85 }));
  scene.add(p); return p;
})();

function setNight(on) {
  const fogC = new THREE.Color(on ? 0x070a10 : 0xb9cbd8);
  scene.fog = new THREE.Fog(fogC, on ? 10 : 40, on ? 70 : 230);
  skyMat.uniforms.top.value.setHex(on ? 0x02040a : 0x4f86c6);
  skyMat.uniforms.horizon.value.copy(fogC);
  skyMat.uniforms.ground.value.copy(fogC);
  scene.background = fogC;
  stars.visible = on;
  hemi.intensity = on ? 0.05 : 0.9;
  hemi.color.setHex(on ? 0x6b7fa8 : 0xcfe0ff);
  sun.intensity = on ? 0.06 : 2.6;
  sun.color.setHex(on ? 0x8fa6d6 : 0xfff1dd);
  scene.environmentIntensity = on ? 0.06 : 0.75;
  $("night").classList.toggle("on", on);
}
let night = params.has("night");
setNight(night);

// ------------------------------------------------------------------ ground
function noiseTex(size, base, specks, n, repeat) {
  const c = document.createElement("canvas"); c.width = c.height = size;
  const g = c.getContext("2d");
  g.fillStyle = base; g.fillRect(0, 0, size, size);
  for (let i = 0; i < n; i++) {
    const [r, gg, b, a] = specks();
    g.fillStyle = `rgba(${r},${gg},${b},${a})`;
    const s = 1 + Math.random() * 2;
    g.fillRect(Math.random() * size, Math.random() * size, s, s * (1 + Math.random() * 2));
  }
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(...repeat);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}
const grassTex = noiseTex(512, "#556a34", () => {
  const k = Math.random();
  return k < 0.7 ? [70 + Math.random() * 25, 92 + Math.random() * 30, 40 + Math.random() * 15, 0.35]
    : [125 + Math.random() * 30, 118 + Math.random() * 25, 70, 0.25];
}, 14000, [60, 60]);
const ground = new THREE.Mesh(new THREE.PlaneGeometry(400, 400),
  new THREE.MeshStandardMaterial({ map: grassTex, roughness: 1, envMapIntensity: 0.2 }));
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);
// dirt track with wheel ruts, runs along x
const trackTex = (() => {
  const c = document.createElement("canvas"); c.width = 256; c.height = 128;
  const g = c.getContext("2d");
  const grad = g.createLinearGradient(0, 0, 0, 128);
  grad.addColorStop(0, "rgba(95,78,55,0)"); grad.addColorStop(0.12, "rgba(110,90,62,1)");
  grad.addColorStop(0.88, "rgba(110,90,62,1)"); grad.addColorStop(1, "rgba(95,78,55,0)");
  g.fillStyle = grad; g.fillRect(0, 0, 256, 128);
  for (let i = 0; i < 4000; i++) {
    const y = 10 + Math.random() * 108, k = Math.random();
    g.fillStyle = `rgba(${80 + k * 50},${66 + k * 40},${46 + k * 28},${Math.random() * 0.45})`;
    g.fillRect(Math.random() * 256, y, 1 + Math.random() * 2, 1 + Math.random() * 1.5);
  }
  for (const y of [38, 90]) { g.fillStyle = "rgba(60,46,32,.55)"; g.fillRect(0, y - 7, 256, 14); }
  const t = new THREE.CanvasTexture(c);
  t.wrapS = THREE.RepeatWrapping; t.repeat.set(60, 1);
  t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
  return t;
})();
const track = new THREE.Mesh(new THREE.PlaneGeometry(400, 3.2),
  new THREE.MeshStandardMaterial({ map: trackTex, transparent: true, roughness: 1, envMapIntensity: 0.2, depthWrite: false }));
track.rotation.x = -Math.PI / 2; track.position.y = 0.005; track.receiveShadow = true;
scene.add(track);

// far hills (don't scroll: they're far enough away)
const hillMat = new THREE.MeshStandardMaterial({ color: 0x47613a, flatShading: true, roughness: 1 });
const hillGeo = new THREE.IcosahedronGeometry(1, 2);
{
  const hills = new THREE.InstancedMesh(hillGeo, hillMat, 26), m = new THREE.Matrix4(), q = new THREE.Quaternion();
  for (let i = 0; i < 26; i++) {
    const a = (i / 26) * Math.PI * 2 + Math.random() * 0.2;
    const d = 170 + Math.random() * 60, r = 40 + Math.random() * 50, h = 18 + Math.random() * 35;
    q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), Math.random() * 3);
    hills.setMatrixAt(i, m.compose(new THREE.Vector3(Math.cos(a) * d, -h * 0.25, Math.sin(a) * d), q, new THREE.Vector3(r, h, r * 0.8)));
  }
  scene.add(hills);
}

// scenery tiles (trees, bush, tussock, rocks) that scroll with speed
const TILE = 80, TILES = 3;
const sceneryTiles = [];
{
  const coneG = new THREE.ConeGeometry(1, 1, 7); coneG.translate(0, 0.5, 0);
  const blobG = new THREE.IcosahedronGeometry(1, 1);
  const trunkG = new THREE.CylinderGeometry(0.1, 0.16, 1, 6); trunkG.translate(0, 0.5, 0);
  const rockG = new THREE.DodecahedronGeometry(1, 0);
  const tussockG = (() => {
    const a = new THREE.PlaneGeometry(0.9, 0.6); a.translate(0, 0.3, 0);
    const b = a.clone(); b.rotateY(Math.PI / 2);
    const c = a.clone(); c.rotateY(Math.PI / 4);
    return mergeGeometries([a, b, c]);
  })();
  const tussockTex = (() => {
    const c = document.createElement("canvas"); c.width = 128; c.height = 96;
    const g = c.getContext("2d");
    for (let i = 0; i < 70; i++) {
      const x0 = 64 + (Math.random() - 0.5) * 30, lean = (Math.random() - 0.5) * 110;
      g.strokeStyle = `rgb(${150 + Math.random() * 50},${125 + Math.random() * 40},${60 + Math.random() * 30})`;
      g.lineWidth = 1 + Math.random() * 1.5;
      g.beginPath(); g.moveTo(x0, 96); g.quadraticCurveTo(x0 + lean * 0.3, 50, x0 + lean, 8 + Math.random() * 40); g.stroke();
    }
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
  })();
  const pineMat = new THREE.MeshStandardMaterial({ color: 0x2a4a2a, flatShading: true, roughness: 0.9 });
  const bushMat = new THREE.MeshStandardMaterial({ color: 0x35552c, flatShading: true, roughness: 0.9 });
  const trunkMat = new THREE.MeshStandardMaterial({ color: 0x4a3524, flatShading: true });
  const rockMat = new THREE.MeshStandardMaterial({ color: 0x7c7a74, flatShading: true, roughness: 0.95 });
  const tussockMat = new THREE.MeshStandardMaterial({ map: tussockTex, alphaTest: 0.5, side: THREE.DoubleSide, roughness: 1 });
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler();
  const side = () => (Math.random() < 0.5 ? -1 : 1);
  for (let t = 0; t < TILES; t++) {
    const tile = new THREE.Group();
    tile.position.x = -TILE * (TILES / 2) + t * TILE + TILE / 2;
    const mk = (geo, mat, n, fn, shadow = true) => {
      const im = new THREE.InstancedMesh(geo, mat, n);
      for (let i = 0; i < n; i++) im.setMatrixAt(i, fn(i));
      im.castShadow = shadow; im.receiveShadow = true;
      tile.add(im);
    };
    const pines = [], bush = [];
    for (let i = 0; i < 18; i++) pines.push([Math.random() * TILE - TILE / 2, side() * (6 + Math.random() * 45), 0.7 + Math.random() * 0.6]);
    for (let i = 0; i < 26; i++) bush.push([Math.random() * TILE - TILE / 2, side() * (5 + Math.random() * 50), 0.6 + Math.random() * 0.9]);
    // pines: trunk + 3 stacked cones each
    mk(trunkG, trunkMat, pines.length, i => { const [x, z, k] = pines[i]; return m4.compose(new THREE.Vector3(x, 0, z), q.identity(), new THREE.Vector3(k, 1.2 * k, k)); });
    mk(coneG, pineMat, pines.length * 3, i => {
      const [x, z, k] = pines[Math.floor(i / 3)], l = i % 3;
      return m4.compose(new THREE.Vector3(x, (0.9 + l * 1.3) * k, z), q.identity(), new THREE.Vector3((1.5 - l * 0.4) * k, (2.4 - l * 0.3) * k, (1.5 - l * 0.4) * k));
    });
    // rounded native bush
    mk(blobG, bushMat, bush.length, i => {
      const [x, z, k] = bush[i];
      return m4.compose(new THREE.Vector3(x, 0.7 * k, z), q.setFromEuler(e.set(0, Math.random() * 3, 0)), new THREE.Vector3(1.4 * k, 1.0 * k, 1.3 * k));
    });
    mk(rockG, rockMat, 22, () => {
      const k = 0.15 + Math.random() * 0.5;
      return m4.compose(new THREE.Vector3(Math.random() * TILE - TILE / 2, k * 0.3, side() * (2.2 + Math.random() * 30)),
        q.setFromEuler(e.set(Math.random() * 3, Math.random() * 3, Math.random() * 3)), new THREE.Vector3(k, k * 0.6, k * 0.8));
    });
    mk(tussockG, tussockMat, 120, () => {
      const k = 0.6 + Math.random() * 0.8;
      return m4.compose(new THREE.Vector3(Math.random() * TILE - TILE / 2, 0, side() * (1.9 + Math.random() * 25)),
        q.setFromEuler(e.set(0, Math.random() * 3, 0)), new THREE.Vector3(k, k, k));
    }, false);
    scene.add(tile);
    sceneryTiles.push(tile);
  }
}

// ------------------------------------------------------------------ the Teryx
const T = buildTeryx();
const { rig, ute, wheels, lightBars, interior, rearPods, drive, tray, winch } = T;
scene.add(rig);
const { WHEEL_R, FX } = DIMS;

// paint colour, remembered per browser
let paintIdx = 0;
try { paintIdx = Math.max(0, PAINTS.findIndex(p => p.name === localStorage.getItem("teryx.paint"))); } catch { /* no storage */ }
function applyPaint() {
  const p = PAINTS[paintIdx];
  T.setPaint(p.color);
  $("paint").textContent = "Paint: " + p.name;
  try { localStorage.setItem("teryx.paint", p.name); } catch { /* no storage */ }
}
applyPaint();
$("paint").onclick = () => { paintIdx = (paintIdx + 1) % PAINTS.length; applyPaint(); };

// the dash screen shows a tiny version of the real dash
const sctx = T.screen.canvas.getContext("2d");
function drawScreen(speed, online) {
  const c = sctx, W = 320, H = 200;
  c.fillStyle = "#0b0d0f"; c.fillRect(0, 0, W, H);
  if (!S["pico.online"] && !online) { c.fillStyle = "#333"; c.fillRect(0, 0, W, H); T.screen.tex.needsUpdate = true; return; }
  c.strokeStyle = "#262c32"; c.lineWidth = 10;
  c.beginPath(); c.arc(100, 110, 70, Math.PI * 0.75, Math.PI * 2.25); c.stroke();
  c.strokeStyle = "#ff7a1a";
  c.beginPath(); c.arc(100, 110, 70, Math.PI * 0.75, Math.PI * (0.75 + 1.5 * Math.min(1, speed / 60))); c.stroke();
  c.fillStyle = "#e8ecef"; c.font = "200 48px system-ui, sans-serif"; c.textAlign = "center";
  c.fillText(online ? speed.toFixed(0) : "--", 100, 122);
  c.font = "14px system-ui, sans-serif"; c.fillStyle = "#7d8891"; c.fillText("km/h", 100, 145);
  c.textAlign = "left"; c.font = "bold 16px system-ui, sans-serif";
  const soc = online ? Math.round(S["mc.soc"] || 0) : 0;
  c.fillStyle = "#7d8891"; c.fillText("BATT", 200, 50);
  c.fillStyle = "#262c32"; c.fillRect(200, 58, 100, 14);
  c.fillStyle = soc > 20 ? "#3ccf6e" : "#ff4d4d"; c.fillRect(200, 58, soc, 14);
  c.fillStyle = "#e8ecef"; c.fillText(soc + "%", 200, 92);
  c.fillStyle = "#ff7a1a"; c.fillText((S["act.4wd"] || "--").toUpperCase().replace("_", " "), 200, 128);
  c.fillStyle = "#7d8891"; c.fillText("DIFF " + (S["an.diff_pos"] ?? "--") + "%", 200, 156);
  T.screen.tex.needsUpdate = true;
}

// ------------------------------------------------------------------ controls
const views = {
  front: [4.6, 2.0, 3.4], side: [0.1, 1.4, 6.2], rear: [-5.2, 2.4, 2.6], top: [0.01, 8.5, 0.01],
};
document.querySelectorAll("[data-cam]").forEach(b => b.onclick = () => {
  const p = views[b.dataset.cam];
  camera.position.set(p[0], p[1], p[2]);
  controls.target.set(0, 0.85, 0);
});
let follow = true;
$("follow").onclick = () => { follow = !follow; $("follow").classList.toggle("on", follow); };
let xray = false;
function setXray(on) {
  xray = on; $("xray").classList.toggle("on", xray);
  T.bodyMats.forEach(m => { m.transparent = xray; m.opacity = xray ? 0.14 : 1; m.depthWrite = !xray; m.needsUpdate = true; });
}
$("xray").onclick = () => setXray(!xray);
$("night").onclick = () => { night = !night; setNight(night); };
window.addEventListener("keydown", e => {
  if (e.key === "n") $("night").click();
  if (e.key === "x") $("xray").click();
  if (e.key === "p") $("paint").click();
});
if (params.has("xray")) setXray(true);
const cam0 = params.get("cam");
if (cam0 && views[cam0]) camera.position.set(...views[cam0]);
else if (cam0 && cam0.split(",").length === 3) camera.position.set(...cam0.split(",").map(Number));

function resize() {
  const w = innerWidth, h = innerHeight;
  renderer.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix();
}
addEventListener("resize", resize); resize();

// ------------------------------------------------------------------ animate
const lerp = (a, b, k) => a + (b - a) * k;
let wheelAngle = 0, drumAngle = 0, shaftAngle = 0, travel = 0;
let cableLen = 0.02;           // metres paid out
let trayAngle = 0, pitch = 0, bounce = 0, roll = 0;
let last = performance.now(), lastScreen = 0;
let fpsN = 0, fpsT = performance.now();
const TRAY_MAX = THREE.MathUtils.degToRad(48);
const v3 = new THREE.Vector3();
const yAxis = new THREE.Vector3(0, 1, 0);

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
  grassTex.offset.x = (travel / 5) % 1;
  trackTex.offset.x = (travel / (400 / 60)) % 1;
  const span = TILE * TILES;
  sceneryTiles.forEach(t => {
    t.position.x -= v * dt;
    if (t.position.x < -span / 2) t.position.x += span;
    if (t.position.x > span / 2) t.position.x -= span;
  });

  // hill: pitch the whole rig, and a bit of trail bounce and body roll
  const grade = S["sim.grade_pct"] || 0;
  pitch = lerp(pitch, Math.atan(grade / 100), dt * 2);
  rig.rotation.z = pitch;
  const k = Math.min(1, speed / 20);
  bounce = speed > 1 ? (Math.sin(now / 90) * 0.01 + Math.sin(now / 37) * 0.004) * k : 0;
  roll = speed > 1 ? Math.sin(now / 260) * 0.008 * k : 0;
  ute.position.y = bounce; ute.rotation.x = roll;

  // drivetrain
  const fw = S["act.4wd"] || "unknown";
  const in4 = fw === "4wd" || fw === "to_2wd";
  const turning = Math.abs(v) > 0.05;
  shaftAngle += (v * dt) / WHEEL_R * 4;
  const on = (s, lit) => { s.m.material = lit ? drive.shaftOn : drive.shaftOff; };
  on(drive.motorShaft, turning); on(drive.rearShaft, turning);
  drive.halfR.forEach(s => on(s, turning));
  on(drive.frontShaft, in4 && turning); drive.halfF.forEach(s => on(s, in4 && turning));
  drive.motorShaft.spin.rotation.y = shaftAngle;
  drive.rearShaft.spin.rotation.y = shaftAngle;
  drive.halfR.forEach(s => { s.spin.rotation.y = wheelAngle; });
  if (in4) { drive.frontShaft.spin.rotation.y = shaftAngle; drive.halfF.forEach(s => { s.spin.rotation.y = wheelAngle; }); }
  drive.fwRod.position.x = lerp(drive.fwRod.position.x, -0.6 + (fw === "4wd" || fw === "to_4wd" ? 0.07 : -0.02), dt * 4);
  const diff = (S["an.diff_pos"] || 0) / 100;
  drive.diffRing.material.emissiveIntensity = diff * 1.2;
  drive.diffRing.scale.setScalar(0.7 + diff * 0.5);
  drive.diffRod.position.x = FX - 0.14 + diff * 0.05;

  // tray
  trayAngle = lerp(trayAngle, ((S["act.tray_pct"] || 0) / 100) * TRAY_MAX, dt * 6);
  tray.pivot.rotation.z = trayAngle;      // front edge lifts, hinge at the back
  const tip = tray.tipLocal.clone().applyEuler(tray.pivot.rotation).add(tray.pivot.position);
  const len = tray.base.distanceTo(tip);
  const dirv = tip.clone().sub(tray.base).normalize();
  const q = new THREE.Quaternion().setFromUnitVectors(yAxis, dirv);
  tray.actBarrel.position.copy(tray.base).addScaledVector(dirv, 0.15); tray.actBarrel.quaternion.copy(q);
  tray.actRod.scale.y = Math.max(0.05, len - 0.15);
  tray.actRod.position.copy(tray.base).addScaledVector(dirv, 0.15 + (len - 0.15) / 2); tray.actRod.quaternion.copy(q);

  // winch
  const wIn = S["winch.in"], wOut = S["winch.out"];
  const wRate = wIn ? -0.8 : wOut ? 0.8 : 0;
  cableLen = Math.max(0.02, Math.min(8, cableLen + wRate * dt));
  drumAngle += wRate * dt / 0.055;
  winch.drum.rotation.z = drumAngle;
  const hx = winch.x + cableLen, hy = winch.y - Math.min(0.4, cableLen * 0.05);
  winch.hook.position.set(hx + 0.02, hy - 0.03, 0);
  const cl = Math.hypot(hx - 1.5, hy - 0.46);
  winch.cable.scale.y = cl; winch.cable.position.set((hx + 1.5) / 2, (hy + 0.46) / 2, 0);
  winch.cable.rotation.z = Math.PI / 2 + Math.atan2(hy - 0.46, hx - 1.5);
  winch.glow.intensity = S["winch.armed"] ? (wIn || wOut ? 1.5 + Math.sin(now / 60) * 0.5 : 0.4) : 0;

  // lights (levels are what the control box is actually outputting, effects included)
  ["light.front_1", "light.front_2", "light.front_3", "light.front_4"].forEach((key, i) => {
    const lvl = (S[key] || 0) / 255;
    lightBars[i].mat.emissiveIntensity = lvl * 6;
    lightBars[i].spot.intensity = lvl * 120;
    lightBars[i].beamMat.opacity = lvl * (night ? 0.022 : 0.008);
  });
  const inl = (S["light.interior"] || 0) / 255;
  interior.mat.emissiveIntensity = inl * 4; interior.spot.intensity = inl * 8;
  interior.beamMat.opacity = inl * (night ? 0.08 : 0.02);
  const rear = S["light.rear"] ? 1 : 0;
  rearPods.forEach(p => { p.mat.emissiveIntensity = rear * 6; p.spot.intensity = rear * 80;
    p.beamMat.opacity = rear * (night ? 0.035 : 0.01); });
  const brake = S["mc.brake"] || S["in.brake"];
  T.tailMat.emissiveIntensity = brake ? 1.6 : (S["trailer.tail"] || night ? 0.5 : 0.05);
  T.head.mat.emissiveIntensity = night ? 3 : 0.15;
  T.head.spot.intensity = night ? 40 : 0;
  T.pinMats.tail.color.setHex(S["trailer.tail"] ? 0xff3030 : 0x331111);
  T.pinMats.brake.color.setHex(S["trailer.brake"] ? 0xff3030 : 0x331111);
  T.screen.mat.emissiveIntensity = S["pico.online"] || online ? (night ? 0.7 : 1.0) : 0.05;
  if (now - lastScreen > 250) { lastScreen = now; drawScreen(speed, online); }

  // camera follow keeps the ute in view while orbiting
  if (follow) { v3.set(0, 0.85 + bounce, 0); controls.target.lerp(v3, 0.2); }
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

  fpsN++;
  if (now - fpsT > 1000) {
    $("fps").textContent = `${Math.round(fpsN * 1000 / (now - fpsT))} fps · ${renderer.info.render.calls} draws`;
    window.__teryxStats = { fps: fpsN * 1000 / (now - fpsT), calls: renderer.info.render.calls, tris: renderer.info.render.triangles };
    fpsN = 0; fpsT = now;
  }
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
