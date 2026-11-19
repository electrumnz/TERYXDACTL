"""Kenwood KFC-2053MRB 8" marine coaxial, as its own model, for checking the
fit and for renders with or without the speaker in.

Real numbers (kenwood.com/usa/car/marine/kfc-2053mrb/spec.html, see
docs/speaker-pods.md): 180 mm cut-out, 86 mm mounting depth, 230 mm square
grille, 90 mm ferrite magnet.

GUESSES until Sam measures his (change them here, everything follows):
  GRILLE_PROUD  how far the grille stands out in front of the mounting face
  HOLE_XY       the 4 screw holes (corners of the square grille)
  CONE_D        cone + surround diameter
  BASKET_D      basket diameter just behind the mounting face (must pass the cut-out)

Coordinates: mounting face at Z=0, the speaker fires towards -Z, X right, Y up.

    python cad/sculpt/kenwood_kfc2053mrb.py out.stl
"""
import sys
import numpy as np
import manifold3d as mf

CUTOUT_D = 180.0
DEPTH = 86.0
GRILLE = 230.0
GRILLE_R = 20.0          # GUESS corner radius of the grille
GRILLE_PROUD = 25.0      # GUESS
MAGNET_D = 90.0
MAGNET_H = 20.0          # GUESS
BASKET_D = 176.0         # GUESS, a little under the cut-out
CONE_D = 166.0           # GUESS
HOLE_XY = 100.0          # GUESS: holes at (+-100, +-100)
HOLE_D = 4.5             # screw clearance in the grille
PILOT_D = 3.5            # pilot hole in the box for the self-tappers


def _rsq(w, r, h):
    cs = mf.CrossSection.square([w - 2 * r, w - 2 * r], True).offset(r, mf.JoinType.Round, 2, 96)
    return mf.Manifold.extrude(cs, h)


def holes():
    return [(sx * HOLE_XY, sy * HOLE_XY) for sx in (-1, 1) for sy in (-1, 1)]


def build():
    """The whole speaker as one solid (good enough for fit and renders)."""
    # grille: square plate at the mounting face, domed bars out to GRILLE_PROUD
    flange = _rsq(GRILLE, GRILLE_R, 6).translate([0, 0, -6])
    dome = mf.Manifold.sphere(1, 96).scale([CONE_D / 2 + 8, CONE_D / 2 + 8, GRILLE_PROUD - 6]).translate([0, 0, -6])
    dome = dome.trim_by_plane([0, 0, -1], 6)            # front half only
    shell = dome - dome.scale([0.97, 0.97, 0.85])
    bars = mf.Manifold()
    for r in np.arange(20, CONE_D / 2 + 8, 11):
        ring = mf.Manifold.cylinder(GRILLE_PROUD + 2, r + 1.5, r + 1.5, 96, True) - mf.Manifold.cylinder(GRILLE_PROUD + 4, r - 1.5, r - 1.5, 96, True)
        bars = bars + ring
    grille = flange + (shell ^ bars.translate([0, 0, -GRILLE_PROUD / 2]))
    grille = grille + mf.Manifold.sphere(22, 64).scale([1, 1, 0.6]).translate([0, 0, -10])   # tweeter
    for x, y in holes():
        grille = grille - mf.Manifold.cylinder(20, HOLE_D / 2, HOLE_D / 2, 32, True).translate([x, y, -3])
    # behind the face: basket tapering to the magnet
    basket = mf.Manifold.cylinder(DEPTH - MAGNET_H, BASKET_D / 2, MAGNET_D / 2 + 5, 96, False)
    magnet = mf.Manifold.cylinder(MAGNET_H, MAGNET_D / 2, MAGNET_D / 2, 96, False).translate([0, 0, DEPTH - MAGNET_H])
    return grille + basket + magnet


def behind():
    """Only the part that goes into the box (for the clearance check)."""
    return build().trim_by_plane([0, 0, 1], 0.5)


if __name__ == "__main__":
    import trimesh
    g = build().to_mesh()
    trimesh.Trimesh(np.asarray(g.vert_properties)[:, :3], np.asarray(g.tri_verts)).export(sys.argv[1] if len(sys.argv) > 1 else "kenwood_kfc2053mrb.stl")
