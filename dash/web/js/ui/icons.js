// Simple stroke icons, 24x24, drawn for this dash. Use currentColor.
const P = {
  drive: '<circle cx="12" cy="13" r="8"/><path d="M12 13l4-4"/><path d="M6 17h12"/>',
  fourwd: '<rect x="4" y="3" width="4" height="6" rx="1"/><rect x="16" y="3" width="4" height="6" rx="1"/><rect x="4" y="15" width="4" height="6" rx="1"/><rect x="16" y="15" width="4" height="6" rx="1"/><path d="M8 6h8M8 18h8M12 6v12"/>',
  lights: '<path d="M9 6c-4 0-6 3-6 6s2 6 6 6h2V6H9z"/><path d="M14 8h7M14 12h7M14 16h7"/>',
  winch: '<rect x="3" y="7" width="10" height="10" rx="2"/><path d="M6 7v10M10 7v10"/><path d="M13 12h5l3 3-3 3"/><circle cx="18" cy="12" r="0.5"/>',
  tray: '<path d="M3 17h18"/><path d="M5 17l3-9 12 3-2 6"/><circle cx="7" cy="19" r="1.5"/><circle cx="17" cy="19" r="1.5"/>',
  camera: '<rect x="3" y="6" width="13" height="12" rx="2"/><path d="M16 10l5-3v10l-5-3"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/>',
  up: '<path d="M12 19V5M5 12l7-7 7 7"/>',
  down: '<path d="M12 5v14M5 12l7 7 7-7"/>',
  in: '<path d="M19 12H5M11 6l-6 6 6 6"/>',
  out: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 018 0v3"/>',
  unlock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 017.5-2"/>',
  wifi: '<path d="M2 9a15 15 0 0120 0"/><path d="M5 12.5a10 10 0 0114 0"/><path d="M8.5 16a5 5 0 017 0"/><circle cx="12" cy="19" r="1"/>',
  wifioff: '<path d="M2 9a15 15 0 0120 0" opacity=".3"/><path d="M5 12.5a10 10 0 0114 0" opacity=".3"/><path d="M8.5 16a5 5 0 017 0" opacity=".3"/><path d="M3 3l18 18"/>',
  mirror: '<path d="M12 3v18"/><path d="M8 7l-5 5 5 5V7zM16 7l5 5-5 5V7z"/>',
  grid: '<path d="M6 21l3-15M18 21l-3-15M5 15h14M7 9h10"/>',
  warn: '<path d="M12 3l10 18H2L12 3z"/><path d="M12 10v5M12 18v.5"/>',
  power: '<path d="M12 3v9"/><path d="M6.3 7a8 8 0 1011.4 0"/>',
  download: '<path d="M12 4v11M7 10l5 5 5-5"/><path d="M4 20h16"/>',
  bolt: '<path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z"/>',
  trips: '<path d="M4 20c0-6 4-6 8-8s8-2 8-8"/><circle cx="4" cy="20" r="1.5"/><circle cx="20" cy="4" r="1.5"/>',
  bell: '<path d="M6 16V11a6 6 0 0112 0v5l2 2H4l2-2z"/><path d="M10 21h4"/>',
  belloff: '<path d="M6 16V11a6 6 0 0112 0v5l2 2H4l2-2z" opacity=".35"/><path d="M10 21h4" opacity=".35"/><path d="M3 3l18 18"/>',
  eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  eyeoff: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z" opacity=".35"/><path d="M3 3l18 18"/>',
  backspace: '<path d="M8 5h12a1 1 0 011 1v12a1 1 0 01-1 1H8l-6-7 6-7z"/><path d="M11 9l6 6M17 9l-6 6"/>',
  shift: '<path d="M12 3l8 9h-4v8H8v-8H4l8-9z"/>',
  compass: '<circle cx="12" cy="12" r="9"/><path d="M15.5 8.5l-2 5-5 2 2-5 5-2z"/>',
  keyboard: '<rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h0M10 10h0M14 10h0M18 10h0M7 14h10"/>',
  reset: '<path d="M4 12a8 8 0 108-8H8"/><path d="M8 1L5 4l3 3"/>',
};

export function icon(name, cls = "") {
  return `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">${P[name] || ""}</svg>`;
}
