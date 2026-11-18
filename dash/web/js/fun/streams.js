// Streaming launcher. On the Pi, the dash server opens the service in its own full-screen
// Chromium window (separate profile, so logins stick) and shuts it the moment the Teryx
// isn't parked (teryx_dash/fun.py). On a laptop or the phone demo it just opens a new tab.
//
// DRM: everything except YouTube needs Widevine. See docs/fun.md for what's known to work on a Pi 5.
// No logos: names only, the services' artwork isn't ours to use.

export const STREAMS = [
  { id: "youtube", name: "YouTube", url: "https://www.youtube.com/", drm: false },
  { id: "netflix", name: "Netflix", url: "https://www.netflix.com/", drm: true },
  { id: "disney", name: "Disney+", url: "https://www.disneyplus.com/", drm: true },
  { id: "prime", name: "Prime Video", url: "https://www.primevideo.com/", drm: true },
  { id: "neon", name: "Neon", url: "https://www.neontv.co.nz/", drm: true },
  { id: "tvnz", name: "TVNZ+", url: "https://www.tvnz.co.nz/", drm: true },
  { id: "threenow", name: "ThreeNow", url: "https://www.threenow.co.nz/", drm: true },
  { id: "spotify", name: "Spotify", url: "https://open.spotify.com/", drm: true },
];

/** Ask the dash server to open a stream. Falls back to a browser tab when there's no Pi behind the dash. */
export async function openStream(s, demo) {
  if (!demo) {
    try {
      const r = await fetch("/api/fun/watch", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ id: s.id }) });
      const j = await r.json().catch(() => ({}));
      if (r.status === 409) return { ok: false, why: j.error || "Park up first." };
      if (r.ok && j.window) return { ok: true, window: true };
      if (r.ok) { window.open(s.url, "_blank", "noopener"); return { ok: true, window: false }; }
      return { ok: false, why: j.error || `Server said ${r.status}` };
    } catch {}
  }
  window.open(s.url, "_blank", "noopener");
  return { ok: true, window: false };
}

export async function closeStream() {
  try { await fetch("/api/fun/close", { method: "POST" }); } catch {}
}
