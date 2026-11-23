"""The real Pico firmware, built for the PC with a pin-level board model.

``main_pico.c`` and the chip drivers in ``firmware/control-box/src/pico`` compile
unchanged against the stand-in SDK in ``src/rig/sdk``. ``rig_board.c`` models the
RP2350 pins and the MCP23017, ADS1115, PCA9685 and MCP2515 chips at register level.
Time is virtual: the firmware only moves when :meth:`Firmware.run_ms` is called.
"""

from __future__ import annotations

import sys

import ctypes as C
import hashlib
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FW = ROOT / "firmware" / "control-box"
BUILD = ROOT / "build" / "rig"

SOURCES = [
    "src/rig/rig_board.c",
    "src/pico/main_pico.c", "src/pico/mcp2515.c", "src/pico/mcp23017.c",
    "src/pico/ads1115.c", "src/pico/pca9685.c",
    "src/core/controller.c", "src/core/settings.c", "src/core/lock.c",
    "src/core/sha256.c", "src/core/lights.c", "src/core/eps.c",
]

DEV_MCP23017, DEV_ADS1115, DEV_PCA9685 = 1, 2, 3
EXIT_REASONS = {0: None, 1: "stopped", 2: "watchdog", 3: "bootloader", 4: "returned"}
PIN_MODES = {0: "input", 1: "out", 2: "pwm", 3: "peripheral", 4: "adc"}


class BuildError(RuntimeError):
    pass


def compiler() -> str | None:
    if platform.system() == "Windows":
        return None  # needs pthreads; the CI runs the sim on Linux and macOS
    for cc in (os.environ.get("CC"), "cc", "gcc", "clang"):
        if cc and shutil.which(cc):
            return cc
    return None


def _version() -> tuple[str, str]:
    text = (ROOT / "firmware" / "VERSION").read_text().strip()
    major, _, minor = text.partition(".")
    return major, minor.split(".")[0] or "0"


def build(force: bool = False) -> Path:
    """Compile the firmware + board model into a shared library (cached by source hash)."""
    cc = compiler()
    if cc is None:
        raise BuildError("no C compiler (or Windows): the system sim needs cc/gcc/clang and pthreads")
    files = [FW / s for s in SOURCES]
    headers = sorted((FW / "src").rglob("*.h"))
    h = hashlib.sha256()
    for f in files + headers + [ROOT / "firmware" / "VERSION"]:
        h.update(f.read_bytes())
    ext = ".dylib" if platform.system() == "Darwin" else ".so"
    out = BUILD / f"libteryx_rig_{h.hexdigest()[:12]}{ext}"
    if out.exists() and not force:
        return out
    BUILD.mkdir(parents=True, exist_ok=True)
    major, minor = _version()
    cmd = [cc, "-O1", "-g", "-std=gnu11", "-fPIC", "-shared", "-fvisibility=hidden",
           "-Wall", "-Wextra", "-Wno-unused-parameter",
           *(["-Werror"] if sys.platform.startswith("linux") else []),   # clang on macOS warns differently
           f"-I{FW / 'src/rig/sdk'}", f"-I{FW / 'src/core'}",
           "-Dmain=pico_main", f"-DFW_VERSION_MAJOR={major}", f"-DFW_VERSION_MINOR={minor}",
           *map(str, files), "-lpthread", "-o", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise BuildError(f"firmware build failed:\n{r.stderr}")
    return out


class Firmware:
    """One Pico. Each instance loads its own copy of the library, so its statics
    (the firmware's whole RAM) start clean, like a real power-up."""

    def __init__(self, lib_path: Path | None = None):
        src = Path(lib_path or build())
        self._tmp = tempfile.TemporaryDirectory(prefix="teryx-rig-")
        dst = Path(self._tmp.name) / src.name
        shutil.copy(src, dst)
        L = self.lib = C.CDLL(str(dst))
        L.rig_run_us.argtypes = [C.c_uint64]
        L.rig_now_us.restype = C.c_uint64
        L.rig_errors.restype = C.c_char_p
        L.rig_pin.argtypes = [C.c_int, C.POINTER(C.c_double), C.POINTER(C.c_double), C.POINTER(C.c_int)]
        L.rig_adc_mv.argtypes = [C.c_int, C.c_double]
        L.rig_die_temp.argtypes = [C.c_double]
        L.rig_ads_mv.argtypes = [C.c_int, C.c_int, C.c_double]
        L.rig_pca_duty.argtypes = [C.c_int, C.c_int, C.POINTER(C.c_double)]
        L.rig_pca_duty.restype = C.c_double
        L.rig_can_bitrate.restype = C.c_uint32
        L.rig_can_push.argtypes = [C.c_int, C.c_uint32, C.c_int, C.c_int, C.POINTER(C.c_uint8)]
        L.rig_can_pop.argtypes = [C.c_int, C.POINTER(C.c_uint32), C.POINTER(C.c_int),
                                  C.POINTER(C.c_int), C.POINTER(C.c_uint8)]
        L.rig_uart_take.argtypes = [C.c_char_p, C.c_size_t]
        L.rig_uart_take.restype = C.c_size_t
        L.rig_uart_send.argtypes = [C.c_char_p]
        L.rig_flash_base.restype = C.POINTER(C.c_uint8)
        L.rig_flash_size.restype = C.c_size_t
        L.rig_init()
        self.started = False

    # ------------------------------------------------------------ set up, before start()
    def set_pins(self, spi=(2, 3, 4), i2c=(26, 27), uart=(0, 1)) -> None:
        self.lib.rig_set_pins(*spi, *i2c, *uart)

    def add_i2c(self, kind: int, addr: int) -> int:
        return self.lib.rig_i2c_add(kind, addr)

    def add_can(self, cs_pin: int, osc_hz: int = 8_000_000) -> int:
        return self.lib.rig_can_add(cs_pin, osc_hz)

    def watchdog_reboot(self, yes: bool) -> None:
        self.lib.rig_set_watchdog_reboot(int(yes))

    # ------------------------------------------------------------ run
    def start(self) -> None:
        self.lib.rig_start()
        self.started = True

    def run_us(self, us: int) -> bool:
        """Run the firmware for ``us`` of virtual time. False once it has stopped."""
        return self.lib.rig_run_us(int(us)) != 3

    def stop(self) -> None:
        if self.started:
            self.lib.rig_stop()
            self.started = False

    def close(self) -> None:
        self.stop()
        self._tmp.cleanup()

    @property
    def exit_reason(self) -> str | None:
        return EXIT_REASONS.get(self.lib.rig_exit_reason())

    @property
    def now_ms(self) -> float:
        return self.lib.rig_now_us() / 1000.0

    @property
    def errors(self) -> list[str]:
        return [e for e in self.lib.rig_errors().decode().splitlines() if e]

    # ------------------------------------------------------------ pins and chips
    def pin(self, gp: int) -> tuple[str, float, float, bool]:
        """(mode, value, pwm_hz, pull_up). value is 0/1 for out, duty 0-1 for pwm."""
        v, hz, pu = C.c_double(), C.c_double(), C.c_int()
        mode = self.lib.rig_pin(gp, C.byref(v), C.byref(hz), C.byref(pu))
        return PIN_MODES.get(mode, "input"), v.value, hz.value, bool(pu.value)

    def pin_in(self, gp: int, level: int | None) -> None:
        self.lib.rig_pin_in(gp, -1 if level is None else int(bool(level)))

    def adc_mv(self, adc_input: int, mv: float) -> None:
        self.lib.rig_adc_mv(adc_input, float(mv))

    def die_temp(self, c: float) -> None:
        self.lib.rig_die_temp(float(c))

    def i2c_power(self, dev: int, on: bool) -> None:
        self.lib.rig_i2c_power(dev, int(on))

    def reg(self, dev: int, r: int) -> int:
        return self.lib.rig_i2c_reg(dev, r)

    def set_reg(self, dev: int, r: int, v: int) -> None:
        self.lib.rig_i2c_set_reg(dev, r, v)

    def mcp_in(self, dev: int, port: int, mask: int, level: int) -> None:
        self.lib.rig_mcp_in(dev, port, mask, level)

    def ads_mv(self, dev: int, ch: int, mv: float) -> None:
        self.lib.rig_ads_mv(dev, ch, float(mv))

    def pca(self, dev: int, ch: int) -> tuple[float, float]:
        hz = C.c_double()
        d = self.lib.rig_pca_duty(dev, ch, C.byref(hz))
        return d, hz.value

    def pca_totem(self, dev: int) -> bool:
        return bool(self.lib.rig_pca_totem(dev))

    def can_power(self, chip: int, on: bool) -> None:
        self.lib.rig_can_power(chip, int(on))

    def can_acked(self, chip: int, yes: bool) -> None:
        self.lib.rig_can_acked(chip, int(yes))

    def can_mode(self, chip: int) -> int:
        return self.lib.rig_can_mode(chip)

    def can_bitrate(self, chip: int) -> int:
        return self.lib.rig_can_bitrate(chip)

    def can_push(self, chip: int, can_id: int, data: bytes, ext: bool = False) -> bool:
        buf = (C.c_uint8 * 8)(*data[:8])
        return bool(self.lib.rig_can_push(chip, can_id, int(ext), len(data[:8]), buf))

    def can_pop(self, chip: int):
        """Frames the chip has put on the bus: yields (id, ext, data)."""
        cid, ext, dlc, buf = C.c_uint32(), C.c_int(), C.c_int(), (C.c_uint8 * 8)()
        while self.lib.rig_can_pop(chip, C.byref(cid), C.byref(ext), C.byref(dlc), buf):
            yield cid.value, bool(ext.value), bytes(buf[: dlc.value])

    def can_tx_pending(self, chip: int) -> int:
        return self.lib.rig_can_tx_pending(chip)

    def uart_take(self) -> str:
        buf = C.create_string_buffer(8192)
        n = self.lib.rig_uart_take(buf, 8192)
        return buf.raw[:n].decode(errors="replace")

    def uart_send(self, text: str) -> None:
        self.lib.rig_uart_send(text.encode())

    # flash survives a Pico reset or power cut (settings and the vehicle lock live there)
    def flash(self) -> bytes:
        n = self.lib.rig_flash_size()
        return C.string_at(self.lib.rig_flash_base(), n)

    def load_flash(self, data: bytes) -> None:
        C.memmove(self.lib.rig_flash_base(), data, len(data))
