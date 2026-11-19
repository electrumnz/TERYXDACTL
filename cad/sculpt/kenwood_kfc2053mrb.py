"""Kenwood KFC-2053MRB 8" marine coaxial: the speaker as its own model, for
clash checks against the pod and for renders with or without it.

Published numbers (all in mm):
  cut-out        180   (7-1/16")            kenwood.com/usa/car/marine/kfc-2053mrb/spec.html
  mounting depth  86   (3-3/8", behind the mounting face)       same page
  size with grille 230 x 230, 113 deep (9-1/16" x 9-1/16" x 4-7/16")
                         Kenwood's "w_Gr" dimensions, kenwood.com/au (KFC-2053MRW, same body)
  magnet         8 oz ferrite              qualitymobilevideo.com listing
  The photos show a ROUND frame (230 across), a domed stainless mesh grille
  with spokes, a 1" dome tweeter on a centre pod, and 4 screws round the rim;
  it comes with speed clips (the screws grip clips on the edge of the hole).

So the grille stands 113 - 86 = 27 mm in front of the mounting face. That
part is no longer a guess.

STILL GUESSES (measure yours and change them here, the clash check follows):
  HOLE_PCD, HOLE_ANGLES   screw circle and angles
  FRAME_T, GRILLE_ID      how thick the flat rim is, where the grille starts
  MAGNET_D, MAGNET_H      size of an 8 oz ferrite (about 100 x 17 is typical)
  BASKET_*                basket shape between the rim and the magnet
  TERMINAL_*              where the terminals stick out

Coordinates: mounting face at Z=0, the speaker fires towards -Z, X right, Y up.

    python cad/sculpt/kenwood_kfc2053mrb.py out.stl            # detailed
    python cad/sculpt/kenwood_kfc2053mrb.py out.stl envelope   # clash solid
"""
import sys
import numpy as np
import manifold3d as mf

# ---- published
CUTOUT_D = 180.0
DEPTH = 86.0              # mounting face to the back of the magnet
FRAME_D = 230.0           # round frame, across
TOTAL_DEPTH = 113.0       # with grille
GRILLE_PROUD = TOTAL_DEPTH - DEPTH   # 27

# ---- guesses (see the docstring)
FRAME_T = 6.0             # flat rim thickness at the outside edge
GRILLE_ID = 192.0         # the domed grille starts inside this
HOLE_PCD = 210.0          # screw circle
HOLE_ANGLES = (45, 135, 225, 315)
HOLE_D = 4.5              # clearance hole in the rim
PILOT_D = 3.5             # pilot hole in the box for the screws
CONE_D = 170.0            # cone + surround the air comes off
TWEETER_POD_D = 52.0
MAGNET_D = 100.0
MAGNET_H = 17.0
BASKET_D = 176.0          # just behind the rim; must pass the 180 cut-out
TERMINAL_W, TERMINAL_R, TERMINAL_Z = 22.0, 88.0, (10.0, 28.0)

N = 128


def _cyl(h, r1, r2=None, z=0.0):
    return mf.Manifold.cylinder(h, r1, r1 if r2 is None else r2, N, False).translate([0, 0, z])


def _revolve(profile):
    """Solid of revolution from (r, z) points (r >= 0), closed on the axis."""
    p = np.asarray(profile, float)
    area = 0.5 * np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])
    if area < 0: p = p[::-1]                     # manifold wants counter-clockwise
    return mf.Manifold.revolve(mf.CrossSection([p.tolist()]), N)


def holes():
    r = HOLE_PCD / 2
    return [(r * np.cos(np.radians(a)), r * np.sin(np.radians(a))) for a in HOLE_ANGLES]


def _grille_profile(r):
    """Front of the grille dome (Z, negative is forward) at radius r."""
    R = GRILLE_ID / 2
    return -FRAME_T - (GRILLE_PROUD - FRAME_T) * np.sqrt(max(0.0, 1 - (r / R) ** 2))


def _front_envelope():
    rs = np.linspace(0, GRILLE_ID / 2, 40)
    prof = [(0.0, 0.0)] + [(r, _grille_profile(r)) for r in rs] + \
           [(FRAME_D / 2 - 4, -FRAME_T), (FRAME_D / 2, -FRAME_T + 2), (FRAME_D / 2, 0.0)]
    return _revolve(prof)


def _back_envelope():
    """Everything behind the mounting face: basket, magnet, terminals."""
    prof = [(0.0, 0.0), (BASKET_D / 2, 0.0), (BASKET_D / 2, 10.0),
            (MAGNET_D / 2 + 6, DEPTH - MAGNET_H - 4), (MAGNET_D / 2, DEPTH - MAGNET_H),
            (MAGNET_D / 2, DEPTH - 3), (MAGNET_D / 2 - 3, DEPTH), (0.0, DEPTH)]
    back = _revolve(prof)
    term = mf.Manifold.cube([TERMINAL_W, 14, TERMINAL_Z[1] - TERMINAL_Z[0]]) \
        .translate([-TERMINAL_W / 2, TERMINAL_R - 14, TERMINAL_Z[0]])
    return back + term.rotate([0, 0, -90])        # terminals at 3 o'clock


def envelope():
    """Solid outline of the whole speaker: use this for clash checks."""
    return _front_envelope() + _back_envelope()


def behind():
    return _back_envelope()


def build():
    """Detailed speaker for renders (fits inside envelope())."""
    # flat rim with the 4 screw holes
    rim = _revolve([(GRILLE_ID / 2 - 2, 0.0), (FRAME_D / 2, 0.0), (FRAME_D / 2, -FRAME_T + 2),
                    (FRAME_D / 2 - 4, -FRAME_T), (GRILLE_ID / 2 - 2, -FRAME_T)])
    for x, y in holes():
        rim = rim - _cyl(30, HOLE_D / 2, z=-15).translate([x, y, 0])
        rim = rim - _cyl(5, 4.5, z=-FRAME_T - 4).translate([x, y, 0])      # screw head recess
    # mesh dome: thin shell, with spokes and two rings on top
    rs = np.linspace(0, GRILLE_ID / 2, 40)
    outer = _revolve([(0.0, 0.0)] + [(r, _grille_profile(r) + 2.0) for r in rs] + [(GRILLE_ID / 2, 0.0)])
    inner = _revolve([(0.0, 1.0)] + [(r, _grille_profile(r) + 3.6) for r in rs[:-1]] + [(GRILLE_ID / 2 - 2, 1.0)])
    mesh = outer - inner
    shell = _front_envelope() - outer           # the 2 mm layer the spokes live in
    spokes = mf.Manifold()
    for k in range(8):
        spokes = spokes + mf.Manifold.cube([GRILLE_ID / 2, 7, 40]).translate([0, -3.5, -40]).rotate([0, 0, k * 45 + 22.5])
    for r in (GRILLE_ID / 2 * 0.45, GRILLE_ID / 2 * 0.75):
        spokes = spokes + (_cyl(40, r + 3, z=-40) - _cyl(40, r - 3, z=-40))
    grille = mesh + (shell ^ spokes)
    # tweeter pod in the middle
    tw = mf.Manifold.sphere(TWEETER_POD_D / 2, N).scale([1, 1, 0.55]).translate([0, 0, _grille_profile(0) + 16])
    tw = tw.trim_by_plane([0, 0, -1], 0)
    # behind: basket with 4 windows, magnet, back plate, terminals
    back = _back_envelope()
    hollow = _revolve([(0.0, 3.0), (BASKET_D / 2 - 3, 3.0), (BASKET_D / 2 - 3, 10.0),
                       (MAGNET_D / 2 + 3, DEPTH - MAGNET_H - 6), (0.0, DEPTH - MAGNET_H - 6)])
    windows = mf.Manifold()
    for k in range(4):
        windows = windows + mf.Manifold.cube([BASKET_D, 46, DEPTH - MAGNET_H - 26]).translate([0, -23, 16]).rotate([0, 0, k * 90 + 45])
    ring = _cyl(DEPTH, BASKET_D / 2 + 5) - _cyl(DEPTH, 30.0)      # leave the centre pole
    back = back - hollow - (windows ^ ring)
    cone = _revolve([(0.0, 6.0), (CONE_D / 2, 2.0), (CONE_D / 2, 4.0), (22.0, 40.0), (0.0, 40.0)])
    return rim + grille + tw + back + cone


def to_trimesh(m):
    import trimesh
    g = m.to_mesh()
    return trimesh.Trimesh(np.asarray(g.vert_properties)[:, :3], np.asarray(g.tri_verts))


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "kenwood_kfc2053mrb.stl"
    m = envelope() if "envelope" in sys.argv[2:] else build()
    to_trimesh(m).export(out)
    t = to_trimesh(envelope())
    print("envelope size", np.ptp(t.vertices, axis=0).round(1), "volume behind face L", round(behind().volume() / 1e6, 2))
