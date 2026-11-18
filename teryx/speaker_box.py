"""Speaker pod maths: sealed box sizing, response, and Thiele-Small from measurements.

    python -m teryx speakerbox                  check the pod in config/speaker_pods.yaml
    python -m teryx speakerbox --fs 52 --qts 0.8 --vas 30   try other numbers
    python -m teryx speakerbox --measure FILE   work out Fs, Qts, Vas from your own readings

Kenwood don't publish Thiele-Small numbers for the KFC-2053MRB, so the starting
numbers in config/speaker_pods.yaml are estimates. docs/speaker-pods.md shows how
to measure the real ones with a multimeter, a phone and a resistor, then this
tells you if the printed volume is still right and how much stuffing to use.

The model is the standard closed-box one (Small, "Closed-Box Loudspeaker
Systems", JAES 1972): a 2nd order high pass at fc with Q = Qtc, where
    alpha = Vas / Vb,  fc = fs * sqrt(1 + alpha),  Qtc = Qts * sqrt(1 + alpha).
Stuffing makes the box act bigger (Vb x fill_gain) and adds a little loss.
The amp's fixed 90 Hz high pass is another 2nd order high pass in front.
"""

from __future__ import annotations

import argparse
import cmath
import math
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "speaker_pods.yaml"

RHO = 1.204      # air density at 20 C, kg/m^3
C = 343.0        # speed of sound, m/s


@dataclass
class Driver:
    fs: float        # Hz
    qts: float
    vas_l: float     # litres

    def closed(self, vb_l: float, fill_gain: float = 1.0) -> tuple[float, float]:
        """(fc, Qtc) in a sealed box of vb_l litres net."""
        alpha = self.vas_l / (vb_l * fill_gain)
        k = math.sqrt(1 + alpha)
        return self.fs * k, self.qts * k

    def vb_for_qtc(self, qtc: float, fill_gain: float = 1.0) -> float | None:
        """Net litres for a target Qtc, or None if the driver's Qts is already above it."""
        if qtc <= self.qts:
            return None
        return self.vas_l / ((qtc / self.qts) ** 2 - 1) / fill_gain


def hp2(f: float, f0: float, q: float) -> complex:
    s = 1j * f / f0
    return s * s / (s * s + s / q + 1)


def response_db(f: float, fc: float, qtc: float, hpf_hz: float | None, hpf_q: float) -> float:
    h = hp2(f, fc, qtc)
    if hpf_hz:
        h *= hp2(f, hpf_hz, hpf_q)
    return 20 * math.log10(abs(h))


def summary(drv: Driver, vb_l: float, fill_gain: float, hpf_hz: float | None, hpf_q: float) -> dict:
    fc, qtc = drv.closed(vb_l, fill_gain)
    freqs = [20 * 10 ** (i / 100) for i in range(0, 301)]   # 20 Hz to 20 kHz
    db = [response_db(f, fc, qtc, hpf_hz, hpf_q) for f in freqs]
    peak = max(db)
    f3 = next((f for f, d in zip(freqs, db) if d >= -3), None)
    f10 = next((f for f, d in zip(freqs, db) if d >= -10), None)
    return {"fc": fc, "qtc": qtc, "peak_db": peak, "f3": f3, "f10": f10}


def ts_from_impedance(re: float, points: list[tuple[float, float]], *, added_g: float | None = None,
                      fs_added: float | None = None, cone_d_mm: float | None = None) -> dict:
    """Thiele-Small from an impedance sweep (the classic method, see docs/speaker-pods.md).

    points: (Hz, ohms) readings around the bass peak. Vas needs the added-mass test:
    the peak frequency with `added_g` grams stuck on the cone, and the cone diameter
    (middle of the surround to middle of the surround)."""
    points = sorted(points)
    f_s, zmax = max(points, key=lambda p: p[1])
    r0 = zmax / re
    z12 = re * math.sqrt(r0)

    def cross(seq):
        for (fa, za), (fb, zb) in zip(seq, seq[1:]):
            if (za - z12) * (zb - z12) <= 0 and za != zb:
                return fa + (z12 - za) * (fb - fa) / (zb - za)
        raise ValueError("need readings on both sides of the peak, down to about "
                         f"{z12:.1f} ohm")

    below = [p for p in points if p[0] <= f_s]
    above = [p for p in points if p[0] >= f_s]
    f1 = cross(below)
    f2 = cross(above)
    fs = math.sqrt(f1 * f2)
    qms = fs * math.sqrt(r0) / (f2 - f1)
    qes = qms / (r0 - 1)
    qts = qms * qes / (qms + qes)
    out = {"re": re, "fs": fs, "zmax": zmax, "qms": qms, "qes": qes, "qts": qts}
    if added_g and fs_added and cone_d_mm:
        mms = added_g / 1000 / ((fs / fs_added) ** 2 - 1)           # kg
        cms = 1 / ((2 * math.pi * fs) ** 2 * mms)                     # m/N
        sd = math.pi * (cone_d_mm / 2000) ** 2                        # m^2
        out.update(mms_g=mms * 1000, cms=cms, sd_cm2=sd * 1e4, vas_l=RHO * C * C * sd * sd * cms * 1000)
    return out


def lt_db(f: float, fc: float, qtc: float, fp: float, qp: float) -> float:
    """Gain of a Linkwitz transform that turns a (fc, qtc) box into (fp, qp)."""
    return 20 * math.log10(abs(hp2(f, fp, qp) / hp2(f, fc, qtc)))


def plan_eq(cfg: dict, drv: Driver) -> dict:
    """The Linkwitz transform for this driver in this pod, with boost capped."""
    fc, qtc = drv.closed(cfg["pod"]["net_l"], cfg["fill"]["gain"])
    eq = cfg["eq"]
    fp, qp = float(eq["target_hz"]), float(eq["target_q"])
    freqs = [10 * 10 ** (i / 100) for i in range(0, 331)]
    while True:
        gains = [lt_db(f, fc, qtc, fp, qp) for f in freqs]
        if max(gains) <= eq["max_boost_db"] + 1e-6 or fp > 400:
            break
        fp *= 1.02
    return {"fc": fc, "qtc": qtc, "fp": fp, "qp": qp, "max_boost_db": max(gains), "max_cut_db": min(gains)}


def biquad(fs_rate: float, fc: float, qtc: float, fp: float, qp: float) -> dict:
    """Bilinear (pre-warped) biquad for the Linkwitz transform, normalised to a0 = 1."""
    def w(f):
        return 2 * fs_rate * math.tan(math.pi * f / fs_rate)
    k = 2 * fs_rate
    w0, wp = w(fc), w(fp)
    b = [k * k + k * w0 / qtc + w0 * w0, 2 * (w0 * w0 - k * k), k * k - k * w0 / qtc + w0 * w0]
    a = [k * k + k * wp / qp + wp * wp, 2 * (wp * wp - k * k), k * k - k * wp / qp + wp * wp]
    return {"b0": b[0] / a[0], "b1": b[1] / a[0], "b2": b[2] / a[0], "a0": 1.0, "a1": a[1] / a[0], "a2": a[2] / a[0]}


def biquad_db(c: dict, f: float, fs_rate: float) -> float:
    z = cmath.exp(-2j * math.pi * f / fs_rate)
    h = (c["b0"] + c["b1"] * z + c["b2"] * z * z) / (c["a0"] + c["a1"] * z + c["a2"] * z * z)
    return 20 * math.log10(abs(h))


PIPEWIRE = ROOT / "scripts" / "pipewire" / "50-teryx-pod-eq.conf"


def pipewire_conf(cfg: dict) -> str:
    d = cfg["driver"]
    p = plan_eq(cfg, Driver(d["fs"], d["qts"], d["vas_l"]))
    rows = []
    for rate in (44100, 48000):
        c = biquad(rate, p["fc"], p["qtc"], p["fp"], p["qp"])
        rows.append("                    { rate = %d, %s }" % (rate, ", ".join(f"{k} = {c[k]:.10f}" for k in ("b0", "b1", "b2", "a0", "a1", "a2"))))
    return f"""# Teryx speaker pods: bass EQ (Linkwitz transform). GENERATED, do not edit:
# change config/speaker_pods.yaml and run `python -m teryx speakerbox --write`.
#
# Driver {d['name']} ({d['source']}): Fs {d['fs']} Hz, Qts {d['qts']}, Vas {d['vas_l']} L
# Pod {cfg['pod']['net_l']} L net with fill: fc {p['fc']:.1f} Hz, Qtc {p['qtc']:.2f}
# EQ turns that into fc {p['fp']:.1f} Hz, Q {p['qp']:.3f} (max boost {p['max_boost_db']:+.1f} dB, max cut {p['max_cut_db']:+.1f} dB)
#
# Makes a sound output called "Teryx speaker pods". scripts/audio-setup.sh copies
# this to ~/.config/pipewire/pipewire.conf.d/. Pick it in Settings > Audio and media.
context.modules = [
    {{ name = libpipewire-module-filter-chain
        args = {{
            node.description = "Teryx speaker pods"
            media.name       = "Teryx speaker pods"
            filter.graph = {{
                nodes = [
                    {{
                        type   = builtin
                        name   = pod_lt
                        label  = bq_raw
                        config = {{
                            coefficients = [
{chr(10).join(rows)}
                            ]
                        }}
                    }}
                ]
            }}
            audio.channels = 2
            audio.position = [ FL FR ]
            capture.props = {{
                node.name   = "teryx_pods"
                media.class = Audio/Sink
            }}
            playback.props = {{
                node.name    = "teryx_pods.out"
                node.passive = true
            }}
        }}
    }}
]
"""


def check(cfg: dict) -> list[str]:
    """Problems with the pod numbers (empty list = fine). Run by the tests."""
    out = []
    pod = cfg["pod"]
    net = pod["gross_l"] - cfg["driver"]["displacement_l"]
    if abs(net - pod["net_l"]) > 0.05:
        out.append(f"pod.net_l {pod['net_l']} should be gross_l - displacement_l = {net:.2f}")
    w = worst_case(cfg, pod["net_l"])
    d = cfg["driver"]
    p = plan_eq(cfg, Driver(d["fs"], d["qts"], d["vas_l"]))
    if p["max_boost_db"] > cfg["eq"]["max_boost_db"] + 0.01:
        out.append(f"EQ boosts {p['max_boost_db']:.1f} dB")
    if w["f3"] > 160:
        out.append(f"worst-case F3 {w['f3']:.0f} Hz: pod too small for these drivers")
    if PIPEWIRE.exists() and PIPEWIRE.read_text(encoding="utf-8") != pipewire_conf(cfg):
        out.append(f"{PIPEWIRE.relative_to(ROOT)} is stale: run python -m teryx speakerbox --write")
    elif not PIPEWIRE.exists():
        out.append(f"{PIPEWIRE.relative_to(ROOT)} missing: run python -m teryx speakerbox --write")
    return out


def load(path: Path = CONFIG) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def worst_case(cfg: dict, vb_l: float) -> dict:
    """Run every corner of the estimate ranges and return the worst peak and F3."""
    rng = cfg["driver"]["range"]
    fill = cfg["fill"]["gain"]
    amp = cfg["amp_hpf"]
    worst = {"peak_db": -99, "f3": 0, "case": None}
    for fs in rng["fs"]:
        for qts in rng["qts"]:
            for vas in rng["vas_l"]:
                s = summary(Driver(fs, qts, vas), vb_l, fill, amp["hz"], amp["q"])
                if s["peak_db"] > worst["peak_db"]:
                    worst.update(peak_db=s["peak_db"], case=(fs, qts, vas), qtc=s["qtc"])
                worst["f3"] = max(worst["f3"], s["f3"])
    return worst


def report(cfg: dict, drv: Driver | None = None) -> str:
    d = cfg["driver"]
    drv = drv or Driver(d["fs"], d["qts"], d["vas_l"])
    vb = cfg["pod"]["net_l"]
    fill = cfg["fill"]["gain"]
    amp = cfg["amp_hpf"]
    lines = [f"Driver: Fs {drv.fs:g} Hz, Qts {drv.qts:g}, Vas {drv.vas_l:g} L"]
    lines.append(f"Pod net volume: {vb:g} L (fill makes it act like {vb * fill:.1f} L)")
    lines.append("")
    lines.append("  net L   fc Hz   Qtc    peak dB  F3 Hz (with the amp's 90 Hz high pass)")
    for v in sorted({4, 6, 8, 10, 12, 15, 20, vb}):
        s = summary(drv, v, fill, amp["hz"], amp["q"])
        mark = "  <- this pod" if v == vb else ""
        lines.append(f"  {v:5.1f}  {s['fc']:6.0f}  {s['qtc']:5.2f}  {s['peak_db']:+6.1f}  {s['f3']:6.0f}{mark}")
    for q in (0.707, 0.9, 1.1):
        v = drv.vb_for_qtc(q, fill)
        lines.append(f"Qtc {q:g} needs " + (f"{v:.1f} L net" if v else "an impossible box (Qts is higher)"))
    p = plan_eq(cfg, drv)
    lines.append("")
    lines.append(f"Pi EQ: reshape fc {p['fc']:.0f} Hz / Qtc {p['qtc']:.2f} into {p['fp']:.0f} Hz / Q {p['qp']:.3f}"
                 f" (max boost {p['max_boost_db']:+.1f} dB, max cut {p['max_cut_db']:+.1f} dB)")
    lines.append("With the EQ:  Hz    dB (pod + EQ + amp high pass)")
    for f in (50, 63, 80, 90, 100, 125, 160, 200, 315, 1000):
        db = (response_db(f, p["fc"], p["qtc"], amp["hz"], amp["q"]) + lt_db(f, p["fc"], p["qtc"], p["fp"], p["qp"]))
        lines.append(f"            {f:4d}  {db:+5.1f}")
    w = worst_case(cfg, vb)
    lines.append("")
    lines.append(f"Worst corner of the estimate ranges (no EQ): peak {w['peak_db']:+.1f} dB at Fs/Qts/Vas {w['case']},"
                 f" F3 up to {w['f3']:.0f} Hz. Measure the speaker and the EQ fixes the peak.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m teryx speakerbox", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fs", type=float)
    ap.add_argument("--qts", type=float)
    ap.add_argument("--vas", type=float, help="litres")
    ap.add_argument("--measure", type=Path, help="YAML file of readings, see docs/speaker-pods.md")
    ap.add_argument("--write", action="store_true", help="rewrite scripts/pipewire/50-teryx-pod-eq.conf")
    ap.add_argument("--check", action="store_true", help="only check (CI)")
    ap.add_argument("--volume", type=float, help="cavity litres from the CAD; fail if it is not pod.gross_l")
    a = ap.parse_args(argv)
    cfg = load()
    if a.volume is not None:
        want = cfg["pod"]["gross_l"]
        print(f"Pod air volume from the CAD: {a.volume:.2f} L (config says {want} L)")
        if abs(a.volume - want) > 0.03 * want:
            print("Volume changed: update pod.gross_l and pod.net_l in config/speaker_pods.yaml, then --write")
            return 1
        return 0
    if a.write:
        PIPEWIRE.parent.mkdir(parents=True, exist_ok=True)
        PIPEWIRE.write_text(pipewire_conf(cfg), encoding="utf-8")
        print(f"wrote {PIPEWIRE.relative_to(ROOT)}")
    problems = check(cfg)
    for p in problems:
        print("PROBLEM:", p)
    if a.check:
        return 1 if problems else 0
    d = cfg["driver"]
    if a.measure:
        m = yaml.safe_load(a.measure.read_text(encoding="utf-8"))
        res = ts_from_impedance(m["re"], [tuple(p) for p in m["points"]], added_g=m.get("added_g"),
                                fs_added=m.get("fs_added"), cone_d_mm=m.get("cone_d_mm"))
        print("Measured: " + ", ".join(f"{k} {v:.3g}" for k, v in res.items()))
        if "vas_l" not in res:
            print("No Vas yet (do the added-mass step); using the estimate for Vas.")
        drv = Driver(res["fs"], res["qts"], res.get("vas_l", d["vas_l"]))
    else:
        drv = Driver(a.fs or d["fs"], a.qts or d["qts"], a.vas or d["vas_l"])
    print(report(cfg, drv))
    return 0
