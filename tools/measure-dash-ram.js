// Measures how much memory the dash uses in Chromium, so we can size the dash computer.
//
//   1. Start the dash:   PYTHONPATH=dash/server python -m teryx run --scenario trail --ui dash/web
//   2. Run this:         node tools/measure-dash-ram.js
//
// Needs Node, Playwright (npm i playwright) and ffmpeg. On the real dash computer, pass
// CHROMIUM=/usr/bin/chromium to use the system browser with its GPU.
//
// It opens the dash at 1280x800, walks every screen, opens the camera (a fake one), then
// decodes 20 s of 1280x720 30 fps H.264 with WebCodecs and draws it, the same way the
// CarPlay screen does. It prints the memory of the whole browser (all its processes) at
// each step. PSS is the fair number: shared pages are split between the processes.
const { chromium } = require('playwright');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const URL = process.env.TERYX_DASH_URL || 'http://localhost:8080/';

function browserMemory(rootPid) {
  const rows = execFileSync('ps', ['-e', '-o', 'pid=,ppid=']).toString().trim().split('\n')
    .map((l) => l.trim().split(/\s+/));
  const kids = {};
  for (const [p, pp] of rows) (kids[pp] = kids[pp] || []).push(p);
  const todo = [String(rootPid)];
  let pss = 0, rss = 0, procs = 0;
  while (todo.length) {
    const p = todo.pop();
    (kids[p] || []).forEach((k) => todo.push(k));
    try {
      const s = fs.readFileSync(`/proc/${p}/smaps_rollup`, 'utf8');
      pss += +s.match(/Pss:\s+(\d+)/)[1];
      rss += +s.match(/Rss:\s+(\d+)/)[1];
      procs++;
    } catch (e) { /* process went away */ }
  }
  return { procs, pss_mb: Math.round(pss / 1024), rss_mb: Math.round(rss / 1024) };
}

(async () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'teryx-ram-'));
  const clip = path.join(tmp, 'test.h264');
  execFileSync('ffmpeg', ['-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=size=1280x720:rate=30',
    '-t', '20', '-c:v', 'libx264', '-profile:v', 'baseline', '-bsf:v', 'h264_mp4toannexb', '-f', 'h264', clip]);

  const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM || undefined,
    args: ['--autoplay-policy=no-user-gesture-required', '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream'],
  });
  const pid = execFileSync('pgrep', ['-f', '-o', 'remote-debugging-pipe']).toString().trim();
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  await page.route('**/__teryx_test.h264', (r) => r.fulfill({ body: fs.readFileSync(clip) }));
  const out = {};

  await page.goto(URL, { waitUntil: 'networkidle' });
  await page.waitForTimeout(15000);
  out.drive_screen = browserMemory(pid);

  for (const s of ['lights', 'drivetrain', 'winch', 'tray', 'camera', 'media', 'trips', 'settings', 'drive']) {
    await page.goto(`${URL}?screen=${s}`);
    await page.waitForTimeout(4000);
  }
  out.after_every_screen = browserMemory(pid);

  await page.goto(`${URL}?screen=camera`);
  await page.waitForTimeout(8000);
  out.camera_open = browserMemory(pid);

  await page.goto(URL, { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  out.carplay_like_video = await page.evaluate(async () => {
    const buf = new Uint8Array(await (await fetch('/__teryx_test.h264')).arrayBuffer());
    const nals = [];
    let i = 0, start = -1;
    while (i < buf.length - 3) {
      if (buf[i] === 0 && buf[i + 1] === 0 && buf[i + 2] === 1) {
        if (start >= 0) nals.push(buf.subarray(start, i));
        start = i; i += 3;
      } else i++;
    }
    nals.push(buf.subarray(start));
    const frames = [];
    let cur = [];
    for (const n of nals) {
      const t = n[3] & 0x1f;
      cur.push(n);
      if (t === 1 || t === 5) { frames.push({ key: t === 5, data: cur }); cur = []; }
    }
    const c = document.createElement('canvas');
    c.width = 1280; c.height = 720;
    c.style = 'position:fixed;top:0;left:0;z-index:99999';
    document.body.appendChild(c);
    const g = c.getContext('2d');
    let shown = 0;
    const dec = new VideoDecoder({ output: (f) => { g.drawImage(f, 0, 0); f.close(); shown++; }, error: (e) => console.log(e) });
    dec.configure({ codec: 'avc1.42E01F', optimizeForLatency: true });
    for (let k = 0; k < frames.length; k++) {
      const len = frames[k].data.reduce((a, b) => a + b.length, 0);
      const data = new Uint8Array(len);
      let o = 0;
      for (const x of frames[k].data) { data.set(x, o); o += x.length; }
      dec.decode(new EncodedVideoChunk({ type: frames[k].key ? 'key' : 'delta', timestamp: k * 33333, data }));
      await new Promise((r) => setTimeout(r, 33));
    }
    await dec.flush();
    return { frames_sent: frames.length, frames_shown: shown };
  });
  out.after_video = browserMemory(pid);

  console.log(JSON.stringify(out, null, 1));
  await browser.close();
  fs.rmSync(tmp, { recursive: true, force: true });
})();
