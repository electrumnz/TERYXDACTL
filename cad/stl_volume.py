"""Volume of a closed STL in litres (text or binary). Used by build.sh to check
the speaker pod's air volume against config/speaker_pods.yaml.

    python3 cad/stl_volume.py FILE.stl [EXPECTED_LITRES]
Exits 1 if EXPECTED is given and the volume is more than 3% off.
"""
import re
import struct
import sys


def triangles(path):
    data = open(path, "rb").read()
    if data[:5] == b"solid" and b"facet" in data[:400]:
        v = [tuple(map(float, m.groups())) for m in re.finditer(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)", data)]
        return [v[i:i + 3] for i in range(0, len(v), 3)]
    n = struct.unpack("<I", data[80:84])[0]
    out = []
    for i in range(n):
        f = struct.unpack("<12f", data[84 + i * 50:84 + i * 50 + 48])
        out.append((f[3:6], f[6:9], f[9:12]))
    return out


def litres(path):
    s = 0.0
    for a, b, c in triangles(path):
        s += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
              + a[2] * (b[0] * c[1] - b[1] * c[0]))
    return abs(s) / 6e6


if __name__ == "__main__":
    vol = litres(sys.argv[1])
    print(f"{sys.argv[1]}: {vol:.2f} L")
    if len(sys.argv) > 2:
        want = float(sys.argv[2])
        if abs(vol - want) > 0.03 * want:
            print(f"Expected {want} L. The pod's size changed: put the new volume in "
                  "config/speaker_pods.yaml (pod.gross_l and net_l) and run "
                  "python -m teryx speakerbox --write", file=sys.stderr)
            sys.exit(1)
