// The real Pico firmware (pico.wasm, built from firmware/control-box by
// tools/build_rig_web.py) with the calls teryx/rig/webfw.py makes from Pyodide.
// One copy of the firmware: fresh() puts its memory back to how it loaded, so each
// boot is a clean power-up. Works in a web worker and in Node (for the CI check). ES module.
export async function makeRigFw(factory) {
  const M = await factory();
  const mem = () => M.HEAPU8;
  const pristine = mem().slice();          // memory the moment it loaded
  const scratch = M._malloc(64);
  const f64 = (p) => new Float64Array(M.HEAPU8.buffer, p, 1)[0];
  const i32 = (p) => new Int32Array(M.HEAPU8.buffer, p, 1)[0];
  const u32 = (p) => new Uint32Array(M.HEAPU8.buffer, p, 1)[0];
  const fw = {
    module: M,
    fresh() {
      mem().set(pristine);
      M._rig_init();
    },
    setPins: (...a) => M._rig_set_pins(...a),
    i2cAdd: (k, a) => M._rig_i2c_add(k, a),
    canAdd: (cs, hz) => M._rig_can_add(cs, hz),
    setWatchdogReboot: (y) => M._rig_set_watchdog_reboot(y),
    start: () => M._rig_start(),
    run(us) { M._rig_run_us(us); return M._rig_run_state(); },
    stop: () => M._rig_stop(),
    exitReason: () => M._rig_exit_reason(),
    nowUs: () => Number(M._rig_now_us()),
    errors: () => M.UTF8ToString(M._rig_errors()),
    pin(gp) {
      const mode = M._rig_pin(gp, scratch, scratch + 8, scratch + 16);
      return [mode, f64(scratch), f64(scratch + 8), i32(scratch + 16)];
    },
    pins(gps) { return Array.from(gps, (g) => fw.pin(g)); },
    pinIn: (gp, lv) => M._rig_pin_in(gp, lv),
    adcMv: (i, mv) => M._rig_adc_mv(i, mv),
    dieTemp: (c) => M._rig_die_temp(c),
    i2cPower: (i, on) => M._rig_i2c_power(i, on),
    reg: (i, r) => M._rig_i2c_reg(i, r),
    setReg: (i, r, v) => M._rig_i2c_set_reg(i, r, v),
    mcpIn: (i, port, mask, level) => M._rig_mcp_in(i, port, mask, level),
    adsMv: (i, ch, mv) => M._rig_ads_mv(i, ch, mv),
    pca(i, ch) { const d = M._rig_pca_duty(i, ch, scratch); return [d, f64(scratch)]; },
    pcaAll(i) {
      if (!M._rig_pca_totem(i)) return new Array(16).fill(0);
      const out = [];
      for (let ch = 0; ch < 16; ch++) out.push(M._rig_pca_duty(i, ch, scratch));
      return out;
    },
    pcaTotem: (i) => M._rig_pca_totem(i),
    canPower: (i, on) => M._rig_can_power(i, on),
    canAcked: (i, y) => M._rig_can_acked(i, y),
    canMode: (i) => M._rig_can_mode(i),
    canBitrate: (i) => M._rig_can_bitrate(i) >>> 0,
    canPush(i, id, ext, data) {
      const p = scratch + 32;
      const bytes = Array.from(data);  // a Uint8Array or a list
      M.HEAPU8.set(bytes.slice(0, 8), p);
      return M._rig_can_push(i, id, ext, Math.min(bytes.length, 8), p);
    },
    canPop(i) {
      const out = [];
      const d = scratch + 32;
      while (M._rig_can_pop(i, scratch, scratch + 4, scratch + 8, d)) {
        const n = i32(scratch + 8);
        out.push([u32(scratch), i32(scratch + 4), Array.from(M.HEAPU8.subarray(d, d + n))]);
      }
      return out;
    },
    canTxPending: (i) => M._rig_can_tx_pending(i),
    uartTake() {
      const n = 8192, p = M._malloc(n);
      const got = M._rig_uart_take(p, n);
      const s = new TextDecoder().decode(M.HEAPU8.slice(p, p + got));
      M._free(p);
      return s;
    },
    uartSend(s) {
      const n = s.length * 3 + 1, p = M._malloc(n);
      M.stringToUTF8(s, p, n);
      M._rig_uart_send(p);
      M._free(p);
    },
    flash() {
      const base = M._rig_flash_base(), n = M._rig_flash_size();
      return M.HEAPU8.slice(base, base + n);
    },
    loadFlash(data) { M.HEAPU8.set(data, M._rig_flash_base()); },
  };
  return fw;
}
