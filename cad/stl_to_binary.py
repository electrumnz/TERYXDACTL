"""Turn OpenSCAD's text STL files into binary STL (about 5x smaller).

    python3 cad/stl_to_binary.py cad/stl/*.stl
"""
import struct
import sys


def convert(path):
    with open(path, "rb") as f:
        head = f.read(5)
    if head != b"solid":
        return False  # already binary
    tris, normal, verts = [], None, []
    with open(path) as f:
        for line in f:
            w = line.split()
            if not w:
                continue
            if w[0] == "facet":
                normal, verts = tuple(map(float, w[2:5])), []
            elif w[0] == "vertex":
                verts.append(tuple(map(float, w[1:4])))
            elif w[0] == "endfacet":
                tris.append((normal, verts))
    with open(path, "wb") as f:
        f.write(b"Teryx OS printed part".ljust(80, b" "))
        f.write(struct.pack("<I", len(tris)))
        for n, v in tris:
            f.write(struct.pack("<12fH", *n, *v[0], *v[1], *v[2], 0))
    return True


if __name__ == "__main__":
    for p in sys.argv[1:]:
        convert(p)
