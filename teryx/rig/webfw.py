"""The real Pico firmware in a web browser (the phone sim on GitHub Pages).

Same methods as :class:`teryx.rig.firmware.Firmware`, but the firmware is the
WebAssembly build (``dash/web/rig/pico.wasm``, made by ``tools/build_rig_web.py``
from the same C files) and the calls go through ``rigfw`` in the web worker
(``dash/web/rig/worker.js``). Python here runs in Pyodide.

The browser has one copy of the firmware. Making a new ``WebFirmware`` puts its
memory back to how it was the moment it loaded, so every boot is a clean power-up,
like a new copy of the library on the PC.
"""

from __future__ import annotations

import js  # Pyodide: the worker's globals
from pyodide.ffi import to_js

from .firmware import EXIT_REASONS, PIN_MODES


def _py(x):
    return x.to_py() if hasattr(x, "to_py") else x


class WebFirmware:
    def __init__(self, lib_path=None):
        self.js = js.rigfw
        self.js.fresh()
        self.started = False

    def set_pins(self, spi=(2, 3, 4), i2c=(26, 27), uart=(0, 1)) -> None:
        self.js.setPins(*spi, *i2c, *uart)

    def add_i2c(self, kind: int, addr: int) -> int:
        return self.js.i2cAdd(kind, addr)

    def add_can(self, cs_pin: int, osc_hz: int = 8_000_000) -> int:
        return self.js.canAdd(cs_pin, osc_hz)

    def watchdog_reboot(self, yes: bool) -> None:
        self.js.setWatchdogReboot(int(yes))

    def start(self) -> None:
        self.js.start()
        self.started = True

    def run_us(self, us: int) -> bool:
        return self.js.run(int(us)) != 3

    def stop(self) -> None:
        if self.started:
            self.js.stop()
            self.started = False

    def close(self) -> None:
        self.stop()

    @property
    def exit_reason(self):
        return EXIT_REASONS.get(self.js.exitReason())

    @property
    def now_ms(self) -> float:
        return self.js.nowUs() / 1000.0

    @property
    def errors(self) -> list[str]:
        return [e for e in str(self.js.errors()).splitlines() if e]

    def pin(self, gp: int):
        mode, v, hz, pu = _py(self.js.pin(gp))
        return PIN_MODES.get(mode, "input"), v, hz, bool(pu)

    def pins(self, gps: list[int]) -> dict:
        """All at once: one call into JavaScript instead of one per pin."""
        out = _py(self.js.pins(to_js(list(gps))))
        return {gp: (PIN_MODES.get(m, "input"), v, hz, bool(pu)) for gp, (m, v, hz, pu) in zip(gps, out)}

    def pin_in(self, gp: int, level) -> None:
        self.js.pinIn(gp, -1 if level is None else int(bool(level)))

    def adc_mv(self, adc_input: int, mv: float) -> None:
        self.js.adcMv(adc_input, float(mv))

    def die_temp(self, c: float) -> None:
        self.js.dieTemp(float(c))

    def i2c_power(self, dev: int, on: bool) -> None:
        self.js.i2cPower(dev, int(on))

    def reg(self, dev: int, r: int) -> int:
        return self.js.reg(dev, r)

    def set_reg(self, dev: int, r: int, v: int) -> None:
        self.js.setReg(dev, r, v)

    def mcp_in(self, dev: int, port: int, mask: int, level: int) -> None:
        self.js.mcpIn(dev, port, mask, level)

    def ads_mv(self, dev: int, ch: int, mv: float) -> None:
        self.js.adsMv(dev, ch, float(mv))

    def pca(self, dev: int, ch: int):
        d, hz = _py(self.js.pca(dev, ch))
        return d, hz

    def pca_all(self, dev: int) -> list[float]:
        return list(_py(self.js.pcaAll(dev)))

    def pca_totem(self, dev: int) -> bool:
        return bool(self.js.pcaTotem(dev))

    def can_power(self, chip: int, on: bool) -> None:
        self.js.canPower(chip, int(on))

    def can_acked(self, chip: int, yes: bool) -> None:
        self.js.canAcked(chip, int(yes))

    def can_mode(self, chip: int) -> int:
        return self.js.canMode(chip)

    def can_bitrate(self, chip: int) -> int:
        return self.js.canBitrate(chip)

    def can_push(self, chip: int, can_id: int, data: bytes, ext: bool = False) -> bool:
        return bool(self.js.canPush(chip, can_id, int(ext), to_js(bytes(data[:8]))))

    def can_pop(self, chip: int):
        for cid, ext, data in _py(self.js.canPop(chip)):
            yield cid, bool(ext), bytes(data)

    def can_tx_pending(self, chip: int) -> int:
        return self.js.canTxPending(chip)

    def uart_take(self) -> str:
        return str(self.js.uartTake())

    def uart_send(self, text: str) -> None:
        self.js.uartSend(text)

    def flash(self) -> bytes:
        return bytes(_py(self.js.flash()))

    def load_flash(self, data: bytes) -> None:
        self.js.loadFlash(to_js(bytes(data)))
