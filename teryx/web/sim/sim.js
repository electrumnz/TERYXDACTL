// Sim panel: talks to /api/sim (works with `teryx run` and `teryx sim`).
const $ = id => document.getElementById(id);
let st = null, built = false;

async function post(cmd) {
  const r = await fetch("/api/sim", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cmd) });
  const j = await r.json();
  if (!j.ok) alert(j.error); else render(j);
}
function build(s) {
  s.scenarios.forEach(sc => {
    const b = document.createElement("button"); b.textContent = sc.label; b.dataset.v = sc.name; b.title = sc.help;
    b.onclick = () => post({ scenario: sc.name }); $("scenarios").appendChild(b);
  });
  s.shinegle_faults.forEach(f => $("sg-faults").appendChild(check(f, on => post({ shinegle_fault: [f, on] }), "sg-" + f)));
  s.bench_fault_names.forEach(f => $("bench-faults").appendChild(check(f, on => post({ bench_fault: [f, on] }), "bf-" + f)));
  ["shinegle", "controlbox"].forEach(l => $("links").appendChild(check(l + " sending", on => post({ link: [l, on] }), "ln-" + l)));
  s.input_names.forEach(n => {
    const row = document.createElement("div"); row.className = "inrow";
    row.innerHTML = `<span>${n}</span><div class="seg" id="in-${n}"><button data-v="auto">AUTO</button><button data-v="0">OFF</button><button data-v="1">ON</button></div>`;
    row.querySelectorAll("button").forEach(b => b.onclick = () =>
      post({ input: [n, b.dataset.v === "auto" ? null : b.dataset.v === "1"] }));
    $("inputs").appendChild(row);
  });
  [["throttle", "thr-v", v => Math.round(v * 100) + "%"], ["brake", "brk-v", v => Math.round(v * 100) + "%"],
   ["grade_pct", "grd-v", v => v + "%"]].forEach(([id, lab, f]) =>
    $(id).addEventListener("input", e => { $(lab).textContent = f(+e.target.value); post({ [id]: +e.target.value }); }));
  $("soc").addEventListener("change", e => post({ soc: +e.target.value }));
  $("ambient").addEventListener("input", e => { $("amb-v").textContent = e.target.value + "°"; post({ ambient: +e.target.value }); });
  $("speed_factor").addEventListener("input", e => { $("sf").textContent = e.target.value + "x"; post({ speed_factor: +e.target.value }); });
  $("cool").onclick = () => post({ cool_down: true });
  $("direction").querySelectorAll("button").forEach(b => b.onclick = () => post({ direction: b.dataset.v }));
  $("mode").querySelectorAll("button").forEach(b => b.onclick = () => post({ mode: b.dataset.v }));
  built = true;
}
function check(label, fn, id) {
  const l = document.createElement("label");
  l.innerHTML = `<input type="checkbox" id="${id}"> ${label}`;
  l.querySelector("input").onchange = e => fn(e.target.checked);
  return l;
}
function render(s) {
  st = s; if (!built) build(s);
  $("bus").textContent = "bus: " + s.bus + (s.controlbox ? "" : " (no fake control box)");
  document.querySelectorAll("#scenarios button").forEach(b => b.classList.toggle("on", b.dataset.v === s.scenario));
  const sc = s.scenarios.find(x => x.name === s.scenario); $("scenario-help").textContent = sc ? sc.help : "";
  document.querySelectorAll("#direction button").forEach(b => b.classList.toggle("on", b.dataset.v === s.driver.direction));
  document.querySelectorAll("#mode button").forEach(b => b.classList.toggle("on", b.dataset.v === s.driver.mode));
  s.shinegle_faults.forEach(f => $("sg-" + f).checked = s.manual_faults.includes(f));
  s.bench_fault_names.forEach(f => $("bf-" + f).checked = s.bench_faults.includes(f));
  ["shinegle", "controlbox"].forEach(l => $("ln-" + l).checked = s.links[l]);
  s.input_names.forEach(n => {
    const v = n in s.inputs ? (s.inputs[n] ? "1" : "0") : "auto";
    document.querySelectorAll(`#in-${CSS.escape(n)} button`).forEach(b => b.classList.toggle("on", b.dataset.v === v));
  });
  const m = s.mc, f = (v, d = 0) => (+v).toFixed(d);
  $("readout").textContent =
    `speed ${f(m["mc.speed"], 1)} km/h   SOC ${f(m["mc.soc"], 1)}%\n` +
    `pack ${f(m["mc.batt_v"], 1)} V  ${f(m["mc.batt_a"], 1)} A\n` +
    `motor ${f(m["mc.motor_temp"])}°  ctrl ${f(m["mc.ctrl_temp"])}°  batt ${f(m["mc.batt_temp"])}°\n` +
    `throttle ${f(s.driver.throttle * 100)}%  brake ${f(s.driver.brake * 100)}%  hill ${f(s.driver.grade_pct)}%\n` +
    `faults: ${m["mc.faults"].join(", ") || "none"}`;
}
async function poll() {
  try { render(await (await fetch("/api/sim")).json()); } catch (e) { /* server restarting */ }
  try { $("state").textContent = JSON.stringify(await (await fetch("/api/state")).json(), null, 1); } catch (e) {}
}
setInterval(poll, 500); poll();
