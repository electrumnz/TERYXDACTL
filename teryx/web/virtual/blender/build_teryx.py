"""Build the virtual Teryx bodywork in Blender and export teryx.glb.

    pip install bpy==5.2.4            # Blender as a Python module (Python 3.13)
    python teryx/web/virtual/blender/build_teryx.py [out.glb]

Or from a normal Blender install:
    blender --background --python teryx/web/virtual/blender/build_teryx.py

It models a 2013 Kawasaki Teryx 750 two seater to the spec-sheet sizes
(length 2954, width 1486, height 1925, wheelbase 1930 mm; 26x8-12 front and
26x10-12 rear tyres; bed 1123 x 831 x 282 mm). Everything is drawn here from
scratch, no third-party meshes, so it's MIT like the rest of the repo.

Only the bodywork is in the GLB: body shell, cage, seats, dash, bed and
wheels. The moving mechanical bits (drivetrain, suspension, winch, light
bars and their beams) stay in teryx-model.js, which also swaps each GLB
material for its own material by name, so paint, see-through and the lights
keep working.

Coordinates: we work in the sim's frame (x forward, y up, z right, metres)
and convert to Blender's z-up here. The glTF exporter converts back.

Output nodes:  Body, Tray (pivot at -1.47, 0.84, 0), WheelF, WheelR
(wheels are centred on their axle, outer face toward +z).
"""
import math
import os
import sys

import bpy  # noqa: I001  (bpy must load before bmesh)
import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = next((a for a in sys.argv[1:] if a.endswith(".glb")), os.path.join(HERE, "..", "teryx.glb"))

FX, RX = 0.965, -0.965
TRACK_F, TRACK_R = 1.22, 1.24
WHEEL_R, RIM_R = 0.33, 0.155


def BV(x, y, z):
    """sim (x fwd, y up, z right) -> Blender (x fwd, y left, z up)"""
    return Vector((x, -z, y))


def SIM_TO_BL():
    return Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))


# ------------------------------------------------------------------ setup
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
coll = scene.collection

MATS = {}


def mat(name, rgb, metal=0.0, rough=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rough
    MATS[name] = m
    return m


# Names matter: teryx-model.js swaps these for its own materials.
mat("Paint", (0.10, 0.2, 0.07), 0.35, 0.3)
mat("Plastic", (0.02, 0.02, 0.022), 0, 0.75)
mat("PlasticGrey", (0.06, 0.065, 0.07), 0, 0.7)
mat("Cage", (0.012, 0.013, 0.014), 0.55, 0.4)
mat("Frame", (0.03, 0.035, 0.04), 0.5, 0.5)
mat("Seat", (0.025, 0.027, 0.03), 0, 0.9)
mat("SeatPanel", (0.06, 0.065, 0.07), 0, 0.95)
mat("Bed", (0.02, 0.022, 0.024), 0, 0.8)
mat("Rubber", (0.01, 0.01, 0.01), 0, 0.95)
mat("Alloy", (0.5, 0.52, 0.55), 0.85, 0.3)
mat("DarkAlloy", (0.06, 0.07, 0.08), 0.8, 0.35)
mat("Chrome", (0.8, 0.8, 0.8), 1.0, 0.15)
mat("Glass", (0.005, 0.006, 0.008), 0.2, 0.1)
mat("HeadLens", (0.6, 0.6, 0.6), 0.4, 0.1)
mat("TailLens", (0.3, 0.0, 0.0), 0.0, 0.2)

PARTS = {"Body": [], "Tray": [], "WheelF": [], "WheelR": []}


def link(name, bm, material, group="Body", subsurf=0, mods=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    ob.data.materials.append(MATS[material])
    for f in me.polygons:
        f.use_smooth = True
    for m in mods or []:
        m(ob)
    if subsurf:
        s = ob.modifiers.new("sub", "SUBSURF")
        s.levels = s.render_levels = subsurf
    PARTS[group].append(ob)
    return ob


def bm_xform(bm, pos=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), order="XYZ"):
    """transform a bmesh built in sim coords: scale, rotate (sim euler), move, then to Blender"""
    from mathutils import Euler
    m = Matrix.Diagonal((*scale, 1))
    m = Euler(rot, order).to_matrix().to_4x4() @ m
    m = Matrix.Translation(pos) @ m
    bm.transform(SIM_TO_BL() @ m)
    return bm


def rbox(w, h, d, r=0.02, seg=3):
    """rounded box in sim axes: w along x, h along y, d along z, centred"""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(w, h, d), verts=bm.verts)
    if r > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=min(r, w / 2.05, h / 2.05, d / 2.05),
                        segments=seg, profile=0.5, affect="EDGES", clamp_overlap=True)
    return bm


def add_box(name, w, h, d, material, pos, rot=(0, 0, 0), r=0.02, seg=3, group="Body", order="XYZ"):
    bm = rbox(w, h, d, r, seg)
    bm_xform(bm, pos, rot, order=order)
    return link(name, bm, material, group)


def cyl(r, depth, seg=24, r2=None, cap=True):
    """cylinder along sim y, centred"""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=seg, radius1=r,
                          radius2=r if r2 is None else r2, depth=depth)
    # create_cone builds along z; turn it to sim y (which after BV is Blender z) - nothing to do,
    # because bm_xform maps sim y -> Blender z. So express it in sim coords: rotate z->y.
    bm.transform(Matrix.Rotation(-math.pi / 2, 4, "X"))
    return bm


def lathe(profile, seg=48):
    """spin [(radius, axial)] around the sim z axis (wheel axle)"""
    bm = bmesh.new()
    verts = [bm.verts.new((r, 0, a)) for r, a in profile]
    edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]
    bmesh.ops.spin(bm, geom=verts + edges, cent=(0, 0, 0), axis=(0, 0, 1), dvec=(0, 0, 0),
                   angle=2 * math.pi, steps=seg, use_merge=True, use_duplicate=False)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def fillet(pts, rad):
    """polyline with rounded corners, sampled"""
    P = [Vector(p) for p in pts]
    out = [P[0]]
    for i in range(1, len(P) - 1):
        a, b, c = P[i - 1], P[i], P[i + 1]
        d1, d2 = a - b, c - b
        r = min(rad, d1.length * 0.45, d2.length * 0.45)
        p1, p2 = b + d1.normalized() * r, b + d2.normalized() * r
        for k in range(9):
            t = k / 8
            out.append((1 - t) ** 2 * p1 + 2 * (1 - t) * t * b + t * t * p2)
    out.append(P[-1])
    return out


def tube(name, pts, r, material="Cage", bend=0.12, group="Body", sides=10):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = max(1, sides // 4 - 1)
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    pp = fillet(pts, bend)
    sp.points.add(len(pp) - 1)
    for i, p in enumerate(pp):
        sp.points[i].co = (*BV(*p), 1)
    ob = bpy.data.objects.new(name, cu)
    coll.objects.link(ob)
    ob.data.materials.append(MATS[material])
    PARTS[group].append(ob)
    return ob


def rod(name, a, b, r, material="Cage", group="Body", seg=10):
    return tube(name, [a, b], r, material, 0, group, seg)


def loft(rings, close_front=True):
    """rings: list of lists of sim points, same length each; quads between rings"""
    bm = bmesh.new()
    vr = [[bm.verts.new(BV(*p)) for p in ring] for ring in rings]
    for a, b in zip(vr, vr[1:]):
        for i in range(len(a) - 1):
            bm.faces.new((a[i], a[i + 1], b[i + 1], b[i]))
    if close_front:
        bm.faces.new(vr[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def boolean_cut(ob, cutter_bm, name="cut"):
    me = bpy.data.meshes.new(name)
    cutter_bm.to_mesh(me)
    cutter_bm.free()
    c = bpy.data.objects.new(name, me)
    coll.objects.link(c)
    c.hide_render = True
    m = ob.modifiers.new("bool", "BOOLEAN")
    m.operation = "DIFFERENCE"
    m.solver = "FLOAT"     # EXACT drops the whole open shell
    m.object = c
    return c


CUTTERS = []


def arch_cutter(cx, cy, r, z0, z1):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=48, radius1=r, radius2=r, depth=z1 - z0)
    # along Blender z -> needs to be along sim z (Blender -y)
    bm.transform(Matrix.Translation(BV(cx, cy, (z0 + z1) / 2)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    return bm


# ------------------------------------------------------------------ front body shell
# Measured off a side-on photo of a 2012-13 Teryx 750 (scaled by the wheelbase):
# the nose is short and tall, the cowl sits about 1.1 m up, and the guards are
# a high band over the wheels with lots of tyre showing underneath.
SECTIONS = [
    # x,    ht,    hf,    w,     hb      (hood centre, guard top, half width, skirt bottom)
    (0.48, 1.095, 1.110, 0.730, 0.64),
    (0.66, 1.065, 1.085, 0.740, 0.66),
    (0.86, 1.025, 1.045, 0.745, 0.68),
    (1.04, 0.975, 0.995, 0.742, 0.68),
    (1.16, 0.925, 0.940, 0.728, 0.67),
    (1.24, 0.865, 0.872, 0.690, 0.64),
    (1.29, 0.790, 0.790, 0.620, 0.61),
    (1.315, 0.720, 0.715, 0.540, 0.60),
]
CREASE = {2: 0.5, 5: 0.4, 8: 0.6, 10: 0.5}   # profile point -> crease: bonnet ridge, hood edge, guard top


def half_profile(ht, hf, w, hb):
    # raised centre ridge, bonnet a touch lower than the guards, guards fall away to a skirt
    return [(0.0, ht + 0.028), (0.07, ht + 0.026), (0.12, ht + 0.004), (0.16, ht), (0.27, ht - 0.012),
            (0.31, ht - 0.022), (0.36, hf - 0.03), (0.42, hf - 0.004), (w - 0.08, hf), (w - 0.035, hf - 0.008),
            (w - 0.006, hf - 0.04), (w, hf - 0.1), (w - 0.006, hb + 0.08), (w - 0.012, hb + 0.03), (w - 0.03, hb)]


rings = []
for x, ht, hf, w, hb in SECTIONS:
    hp = half_profile(ht, hf, w, hb)
    left = [(x, y, -z) for z, y in reversed(hp[1:])]
    right = [(x, y, z) for z, y in hp]
    rings.append(left + right)
shell_bm = loft(rings)
shell_bm.verts.index_update()
crease = shell_bm.edges.layers.float.new("crease_edge")
nh = len(half_profile(1, 1, 0.7, 0.5))
for e in shell_bm.edges:      # crease the long edges that run front to back along the key lines
    i0, i1 = e.verts[0].index, e.verts[1].index
    ring_len = 2 * nh - 1
    a, b = i0 % ring_len, i1 % ring_len
    if a == b:
        k = abs(a - (nh - 1))
        if k in CREASE:
            e[crease] = CREASE[k]
shell = link("FrontShell", shell_bm, "Paint", subsurf=2)
sol = shell.modifiers.new("solid", "SOLIDIFY")
sol.thickness = 0.012
sol.offset = -1
ARCH_F = (0.33, 0.53)          # centre height, radius of the front guard arch
for s in (-1, 1):
    z0, z1 = (0.34, 0.85) if s > 0 else (-0.85, -0.34)
    CUTTERS.append(boolean_cut(shell, arch_cutter(FX, ARCH_F[0], ARCH_F[1], z0, z1), f"archF{s}"))


# wheel-well liners and flares
def arch_liner(cx, name, z_in, z_out, r=0.54, a0=0.3, cy=0.33, a1=None):
    bm = bmesh.new()
    n = 28
    a_start, a_end = a0, math.pi - (a0 if a1 is None else a1)
    rows = []
    for zz in (z_in, z_out):
        rows.append([bm.verts.new(BV(cx + math.cos(a_start + (a_end - a_start) * i / n) * r,
                                     cy + math.sin(a_start + (a_end - a_start) * i / n) * r, zz)) for i in range(n + 1)])
    for i in range(n):
        bm.faces.new((rows[0][i], rows[0][i + 1], rows[1][i + 1], rows[1][i]))
    inner = [bm.verts.new(BV(cx + math.cos(a_start + (a_end - a_start) * i / n) * (r + 0.1),
                             cy + math.sin(a_start + (a_end - a_start) * i / n) * (r + 0.1), z_in)) for i in range(n + 1)]
    for i in range(n):
        bm.faces.new((rows[0][i], inner[i], inner[i + 1], rows[0][i + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = link(name, bm, "Plastic")
    so = ob.modifiers.new("solid", "SOLIDIFY")
    so.thickness = 0.006
    return ob


def flare(cx, z, name, r=0.53, a0=0.35, width=0.07, thick=0.03, cy=0.33, group="Body", material="Plastic", a1=None):
    """plastic lip around the arch edge"""
    bm = bmesh.new()
    n = 36
    s = 1 if z > 0 else -1
    prof = [(-0.004, 0.0), (0.0, thick * 0.7), (width * 0.5, thick), (width, thick * 0.4), (width, 0.0)]
    rows = []
    for i in range(n + 1):
        a = a0 + (math.pi - a0 - (a0 if a1 is None else a1)) * i / n
        c, sn = math.cos(a), math.sin(a)
        rows.append([bm.verts.new(BV(cx + c * (r + ro), cy + sn * (r + ro), z + s * (zo - width * 0.5))) for zo, ro in prof])
    for i in range(n):
        for j in range(len(prof) - 1):
            bm.faces.new((rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return link(name, bm, material, group)


for s in (-1, 1):
    # the guard runs from the cowl (x 0.48) to the nose (x 1.28), so the arch stops there
    arch_liner(FX, f"linerF{s}", s * 0.36, s * 0.72, a0=0.95, a1=0.5)
    flare(FX, s * 0.72, f"flareF{s}", r=0.53, a0=0.95, a1=0.55, width=0.05, thick=0.02)

# front grille block and lower bumper (black), headlights in the bonnet nose
add_box("grilleBlock", 0.16, 0.3, 0.82, "Plastic", (1.25, 0.53, 0), r=0.035)
add_box("grilleMesh", 0.02, 0.16, 0.6, "Glass", (1.333, 0.56, 0), r=0.004, seg=1)
for i in range(5):
    add_box(f"slat{i}", 0.03, 0.012, 0.58, "PlasticGrey", (1.34, 0.5 + i * 0.03, 0), r=0.004, seg=1)
add_box("chinSpoiler", 0.12, 0.08, 0.7, "Plastic", (1.3, 0.41, 0), rot=(0, 0, 0.3), r=0.025)
for s in (-1, 1):
    add_box(f"vent{s}", 0.2, 0.018, 0.12, "Plastic", (0.9, 1.047, s * 0.24), rot=(0, 0, -0.2), r=0.008)
for s in (-1, 1):
    # headlights sit in the nose face either side of the bonnet ridge, in black surrounds
    rot = (0, s * -0.2, -0.55)
    add_box(f"headHousing{s}", 0.07, 0.15, 0.22, "Plastic", (1.3, 0.76, s * 0.24), rot=rot, r=0.03, order="YXZ")
    add_box(f"headLens{s}", 0.05, 0.11, 0.18, "HeadLens", (1.318, 0.764, s * 0.24), rot=rot, r=0.025, order="YXZ")
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=0.035)
    bm_xform(bm, (1.335, 0.765, s * 0.24), scale=(0.45, 1, 1))
    link(f"reflector{s}", bm, "Chrome")

# low front bash bar
tube("brushGuard", [(1.2, 0.42, -0.44), (1.4, 0.42, -0.44), (1.45, 0.64, -0.36), (1.45, 0.64, 0.36),
                    (1.4, 0.42, 0.44), (1.2, 0.42, 0.44)], 0.022, bend=0.09)
rod("bgMid", (1.43, 0.53, -0.4), (1.43, 0.53, 0.4), 0.018)
for s in (-1, 1):
    rod(f"bgUp{s}", (1.45, 0.64, s * 0.16), (1.41, 0.43, s * 0.16), 0.016)

# ------------------------------------------------------------------ floor, sills, dash, steering
add_box("floor", 1.16, 0.035, 1.22, "Plastic", (0.0, 0.445, 0), r=0.01, seg=1)
for i in range(8):
    for s in (-1, 1):
        add_box(f"floorRib{i}{s}", 0.42, 0.012, 0.02, "PlasticGrey", (0.22, 0.468, s * (0.18 + i * 0.035)), r=0.004, seg=1)


def extrude_profile(name, pts, z0, z1, material, bevel=0.02, group="Body"):
    bm = bmesh.new()
    a = [bm.verts.new(BV(x, y, z0)) for x, y in pts]
    b = [bm.verts.new(BV(x, y, z1)) for x, y in pts]
    n = len(pts)
    bm.faces.new(a)
    bm.faces.new(list(reversed(b)))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if bevel:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=3, profile=0.5, affect="EDGES", clamp_overlap=True)
    return link(name, bm, material, group)


for s in (-1, 1):
    # tall black lower side panel with a step up under the seat (from the side photo)
    extrude_profile(f"sill{s}", [(-0.6, 0.32), (0.48, 0.32), (0.55, 0.4), (0.54, 0.62), (0.3, 0.64), (0.06, 0.62),
                                 (-0.12, 0.72), (-0.6, 0.73)], s * 0.575, s * 0.665, "Plastic", 0.02)
extrude_profile("dash", [(0.3, 0.95), (0.36, 1.12), (0.46, 1.19), (0.56, 1.17), (0.6, 1.1), (0.56, 0.46),
                         (0.5, 0.46), (0.42, 0.8)], -0.63, 0.63, "Plastic", 0.03)
add_box("dashTop", 0.12, 0.025, 1.18, "PlasticGrey", (0.47, 1.19, 0), rot=(0, 0, -0.1), r=0.01)
add_box("glovebox", 0.05, 0.14, 0.34, "PlasticGrey", (0.34, 0.98, 0.3), rot=(0, 0, -0.45), r=0.02)
tube("grabBar", [(0.4, 1.12, 0.43), (0.33, 1.2, 0.43), (0.33, 1.2, 0.17), (0.4, 1.12, 0.17)], 0.014, bend=0.04)
# steering wheel on the driver's side (-z), column into the dash
SW = (0.2, 1.16, -0.3)
bm = bmesh.new()
bmesh.ops.create_circle(bm, cap_ends=False, segments=32, radius=0.17)
ring_pts = [v.co.copy() for v in bm.verts]
bm.free()
cu_pts = []
from mathutils import Euler
swm = Euler((0, math.pi / 2, 0.45), "YXZ").to_matrix()
for p in ring_pts + [ring_pts[0]]:
    q = swm @ Vector((p.x, p.y, 0))
    cu_pts.append((SW[0] + q.x, SW[1] + q.y, SW[2] + q.z))
tube("steerRim", cu_pts, 0.021, "Rubber", bend=0, sides=10)
for a in (math.pi / 2, math.pi / 2 + 2.2, math.pi / 2 - 2.2):
    q = swm @ Vector((math.cos(a) * 0.16, math.sin(a) * 0.16, 0))
    rod(f"spoke{a:.1f}", SW, (SW[0] + q.x, SW[1] + q.y, SW[2] + q.z), 0.012, "PlasticGrey")
bm = cyl(0.05, 0.05, 20)
bm.transform(Matrix.Rotation(math.pi / 2, 4, "Z"))
bm_xform(bm, SW, (0, 0, 0.45 - math.pi / 2))
link("hub", bm, "PlasticGrey")
rod("column", (SW[0] + 0.02, SW[1] - 0.02, SW[2]), (0.45, 1.0, SW[2]), 0.024, "Plastic")
for z, w in ((-0.36, 0.06), (-0.24, 0.09)):
    add_box(f"pedal{z}", 0.02, 0.1, w, "DarkAlloy", (0.47, 0.56, z), rot=(0, 0, 0.5), r=0.006)

# ------------------------------------------------------------------ seats
for z in (-0.3, 0.3):
    t = f"{z:+.1f}"
    add_box("seatBox" + t, 0.36, 0.26, 0.42, "Plastic", (-0.18, 0.59, z), r=0.02)
    seat = add_box("cushion" + t, 0.48, 0.1, 0.46, "Seat", (-0.16, 0.775, z), rot=(0, 0, 0.05), r=0.045, seg=4)
    add_box("cushionPanel" + t, 0.36, 0.03, 0.25, "SeatPanel", (-0.14, 0.83, z), rot=(0, 0, 0.05), r=0.012)
    for s in (-1, 1):
        add_box(f"bolster{t}{s}", 0.44, 0.09, 0.075, "Seat", (-0.16, 0.835, z + s * 0.2), rot=(s * 0.12, 0, 0.05), r=0.035, seg=4)
    add_box("back" + t, 0.1, 0.56, 0.46, "Seat", (-0.42, 1.08, z), rot=(0, 0, 0.16), r=0.045, seg=4)
    add_box("backPanel" + t, 0.03, 0.4, 0.25, "SeatPanel", (-0.368, 1.04, z), rot=(0, 0, 0.16), r=0.012)
    for s in (-1, 1):
        add_box(f"wing{t}{s}", 0.14, 0.44, 0.075, "Seat", (-0.385, 1.0, z + s * 0.205), rot=(-s * 0.18, 0, 0.16), r=0.035, seg=4)
    add_box("headrest" + t, 0.1, 0.18, 0.3, "Seat", (-0.49, 1.43, z), rot=(0, 0, 0.16), r=0.045, seg=4)
    # seat belt buckle and strap
    add_box("belt" + t, 0.01, 0.5, 0.05, "Plastic", (-0.36, 1.05, z - 0.17 if z < 0 else z + 0.17), rot=(0.5 if z < 0 else -0.5, 0, 0.16), r=0.003, seg=1)
add_box("console", 0.5, 0.2, 0.12, "PlasticGrey", (-0.12, 0.62, 0), r=0.03)

# ------------------------------------------------------------------ roll cage and roof
C = 0.023
for s in (-1, 1):
    # straight raked A-pillar from the cowl to the roof, roof rail, upright B-pillar
    tube(f"cageSide{s}", [(0.55, 1.1, s * 0.66), (0.1, 1.88, s * 0.63), (-0.55, 1.89, s * 0.63),
                          (-0.6, 1.76, s * 0.64), (-0.6, 0.62, s * 0.66)], C, bend=0.13)
    tube(f"hipBar{s}", [(0.5, 0.95, s * 0.665), (0.3, 1.0, s * 0.7), (-0.1, 1.0, s * 0.71), (-0.58, 0.98, s * 0.67)], 0.016, bend=0.12)
    tube(f"brace{s}", [(-0.58, 1.6, s * 0.64), (-0.66, 1.2, s * 0.6), (-0.64, 0.66, s * 0.42)], 0.018, bend=0.2)
    add_box(f"cageFoot{s}", 0.08, 0.04, 0.08, "Frame", (-0.6, 0.61, s * 0.66), r=0.008)
    add_box(f"aFoot{s}", 0.07, 0.04, 0.07, "Frame", (0.55, 1.09, s * 0.66), r=0.008)
rod("roofFront", (0.1, 1.88, -0.63), (0.1, 1.88, 0.63), C)
rod("roofRear", (-0.55, 1.89, -0.63), (-0.55, 1.89, 0.63), C)
rod("shoulderBar", (-0.6, 1.2, -0.66), (-0.6, 1.2, 0.66), 0.02)
rod("roofMid", (-0.22, 1.89, -0.63), (-0.22, 1.89, 0.63), 0.016)
roof = add_box("roof", 0.8, 0.04, 1.36, "Plastic", (-0.23, 1.93, 0), r=0.018, seg=3)
for i in range(-3, 4):
    add_box(f"roofRib{i}", 0.64, 0.014, 0.035, "Plastic", (-0.23, 1.952, i * 0.16), r=0.006, seg=2)

# ------------------------------------------------------------------ rear fenders, rear panel, bumper
for s in (-1, 1):
    arch_liner(RX, f"linerR{s}", s * 0.5, s * 0.72, r=0.55, a0=0.75)
add_box("rearPanel", 0.05, 0.16, 0.98, "Plastic", (-1.465, 0.62, 0), r=0.015)
tube("rearBumper", [(-1.3, 0.42, -0.5), (-1.53, 0.42, -0.5), (-1.53, 0.42, 0.5), (-1.3, 0.42, 0.5)], 0.022, bend=0.08)
for s in (-1, 1):
    rod(f"rbUp{s}", (-1.52, 0.42, s * 0.3), (-1.45, 0.62, s * 0.3), 0.016)

# ------------------------------------------------------------------ cargo bed (Tray group, pivot at its back edge)
P0 = (-1.47, 0.84, 0)


def tb(name, w, h, d, material, x, y, z, rot=(0, 0, 0), r=0.015, seg=3):
    return add_box(name, w, h, d, material, (P0[0] + x, P0[1] + y, z), rot, r, seg, group="Tray")


BL, BW, BH = 0.86, 1.2, 0.3
tb("bedFloor", BL, 0.04, BW, "Bed", BL / 2, 0, 0, r=0.012)
for i in range(7):
    tb(f"bedRib{i}", BL - 0.1, 0.016, 0.035, "PlasticGrey", BL / 2, 0.026, -0.45 + i * 0.15, r=0.006, seg=2)
for s in (-1, 1):
    tb(f"bedSide{s}", BL, BH, 0.05, "Bed", BL / 2, BH / 2, s * (BW / 2 - 0.025))
    tb(f"bedRail{s}", BL + 0.06, 0.05, 0.17, "Paint", BL / 2 + 0.01, BH + 0.005, s * 0.635, r=0.02)
    for x in (0.12, BL / 2, BL - 0.1):
        tb(f"tie{s}{x:.2f}", 0.05, 0.03, 0.05, "PlasticGrey", x, BH + 0.035, s * 0.6, r=0.008)
    tb(f"tailLens{s}", 0.02, 0.15, 0.06, "TailLens", -0.052, -0.02, s * 0.635, r=0.008)
    tb(f"tailBezel{s}", 0.02, 0.17, 0.08, "Plastic", -0.046, -0.02, s * 0.635, r=0.008)


def bed_skin(z0, z1, name):
    """one side of the bed: top rail down to a skirt, the rear guard arch cut in"""
    cx, cy, r = RX, 0.33, 0.55
    yb = 0.74
    a = math.asin((yb - cy) / r)
    pts = [(-0.57, 1.14), (-1.5, 1.14), (-1.52, 0.8), (-1.48, yb)]
    xr = cx - math.cos(a) * r
    pts.append((xr, yb))
    n = 22
    for i in range(1, n):
        t = (math.pi - a) - (math.pi - 2 * a) * i / n
        pts.append((cx + math.cos(t) * r, cy + math.sin(t) * r))
    pts += [(cx + math.cos(a) * r, yb), (-0.57, yb)]
    extrude_profile(name, pts, z0, z1, "Paint", 0.02, group="Tray")


for s in (-1, 1):
    bed_skin(s * 0.585, s * 0.715, f"bedSkin{s}")
    flare(RX, s * 0.705, f"flareR{s}", r=0.55, a0=0.75, width=0.04, thick=0.018, group="Tray", material="Paint")
tb("tailSkin", 0.04, 0.38, 1.18, "Paint", -0.04, 0.12, 0, r=0.02)
tb("bedFront", 0.05, BH + 0.04, BW, "Bed", BL - 0.025, BH / 2 + 0.015, 0)
tb("tailgate", 0.05, BH - 0.02, BW - 0.14, "Bed", 0.03, BH / 2, 0)
tb("tailgateHandle", 0.025, 0.045, 0.24, "Plastic", -0.07, BH - 0.08, 0, r=0.01)
for s in (-1, 1):
    tb(f"bedHinge{s}", 0.06, 0.05, 0.08, "Frame", 0.0, -0.03, s * 0.4, r=0.008)

# ------------------------------------------------------------------ wheels (centred on the axle, outer face +z)
def build_wheel(group, width):
    R, rr, h = WHEEL_R, RIM_R, width / 2
    # tyre carcass with rounded shoulders and bulging sidewall
    prof = [(rr + 0.004, -h + 0.012), (rr + 0.03, -h - 0.004), (R - 0.08, -h - 0.016), (R - 0.04, -h - 0.01),
            (R - 0.016, -h + 0.008), (R - 0.006, -h + 0.03), (R - 0.004, -h + 0.06), (R - 0.004, h - 0.06),
            (R - 0.006, h - 0.03), (R - 0.016, h - 0.008), (R - 0.04, h + 0.01), (R - 0.08, h + 0.016),
            (rr + 0.03, h + 0.004), (rr + 0.004, h - 0.012)]
    bm = lathe(prof, 56)
    bm.transform(SIM_TO_BL())
    link(group + "Tyre", bm, "Rubber", group)
    # tread: staggered chevron lugs plus shoulder blocks
    N = 22
    for i in range(N):
        for side in (-1, 1):
            a = (i + (0.5 if side > 0 else 0)) / N * 2 * math.pi
            bm = rbox(0.032, 0.024, width * 0.4, 0.006, 2)
            bm.transform(Matrix.Rotation(side * 0.42, 4, "X"))       # chevron angle
            bm.transform(Matrix.Rotation(a, 4, "Z"))
            bm.transform(Matrix.Translation((math.cos(a) * (R + 0.006), math.sin(a) * (R + 0.006), side * width * 0.23)))
            bm.transform(SIM_TO_BL())
            link(f"{group}lug{i}{side}", bm, "Rubber", group)
            a2 = (i + 0.25 + (0.5 if side > 0 else 0)) / N * 2 * math.pi
            bm = rbox(0.036, 0.034, 0.04, 0.008, 2)
            bm.transform(Matrix.Rotation(a2, 4, "Z"))
            bm.transform(Matrix.Translation((math.cos(a2) * (R - 0.024), math.sin(a2) * (R - 0.024), side * (h - 0.002))))
            bm.transform(SIM_TO_BL())
            link(f"{group}shoulder{i}{side}", bm, "Rubber", group)
    # 12" alloy: barrel, lip, dished face, 6 split spokes, hub cap, nuts
    bm = lathe([(rr, -h + 0.02), (rr - 0.006, -h + 0.03), (rr - 0.006, h - 0.03), (rr, h - 0.02), (rr + 0.012, h - 0.012), (rr + 0.012, h - 0.004)], 48)
    bm.transform(SIM_TO_BL())
    link(group + "Barrel", bm, "DarkAlloy", group)
    bm = lathe([(rr - 0.004, h - 0.03), (rr - 0.03, h - 0.045), (0.07, h - 0.06), (0.055, h - 0.05), (0.0, h - 0.05)], 48)
    bm.transform(SIM_TO_BL())
    link(group + "Face", bm, "DarkAlloy", group)
    for i in range(6):
        a = i / 6 * 2 * math.pi
        for off in (-0.1, 0.1):
            bm = rbox(rr - 0.06, 0.018, 0.02, 0.006, 2)
            bm.transform(Matrix.Translation(((rr - 0.06) / 2 + 0.055, 0, 0)))
            bm.transform(Matrix.Rotation(-0.22, 4, "Y"))
            bm.transform(Matrix.Rotation(a + off, 4, "Z"))
            bm.transform(Matrix.Translation((0, 0, h - 0.035)))
            bm.transform(SIM_TO_BL())
            link(f"{group}spoke{i}{off}", bm, "Alloy", group)
    bm = lathe([(rr + 0.012, h - 0.004), (rr + 0.006, h + 0.002), (rr - 0.008, h - 0.004)], 48)
    bm.transform(SIM_TO_BL())
    link(group + "Lip", bm, "Alloy", group)
    bm = lathe([(0.065, h - 0.06), (0.06, h - 0.02), (0.045, h - 0.008), (0.0, h - 0.006)], 24)
    bm.transform(SIM_TO_BL())
    link(group + "Cap", bm, "Alloy", group)
    for i in range(4):
        a = i / 4 * 2 * math.pi + 0.4
        bm = cyl(0.009, 0.02, 6)
        bm.transform(Matrix.Rotation(math.pi / 2, 4, "X"))
        bm.transform(Matrix.Translation((math.cos(a) * 0.075, math.sin(a) * 0.075, h - 0.03)))
        bm.transform(SIM_TO_BL())
        link(f"{group}nut{i}", bm, "Chrome", group)
    # dark disc inside so you can't see through the rim
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=24, radius=rr - 0.005)
    bm.transform(Matrix.Translation((0, 0, -0.01)))
    bm.transform(SIM_TO_BL())
    link(group + "Inner", bm, "Frame", group)


build_wheel("WheelF", 0.20)
build_wheel("WheelR", 0.25)

# ------------------------------------------------------------------ bake each group into one object
dg = bpy.context.evaluated_depsgraph_get()
dg.update()
OUT_OBJS = []
for group, objs in PARTS.items():
    mats = []
    big = bmesh.new()
    for ob in objs:
        m = ob.active_material
        if m not in mats:
            mats.append(m)
        idx = mats.index(m)
        ev = ob.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(ev)
        tmp = bmesh.new()
        tmp.from_mesh(me)
        tmp.transform(ob.matrix_world)
        for f in tmp.faces:
            f.material_index = idx
        tmp.to_mesh(me)
        tmp.free()
        big.from_mesh(me)
        bpy.data.meshes.remove(me)
    bmesh.ops.remove_doubles(big, verts=big.verts, dist=1e-6)
    for f in big.faces:
        f.smooth = True
    for e in big.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(48):
            e.smooth = False
    me = bpy.data.meshes.new(group)
    big.to_mesh(me)
    big.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(group, me)
    coll.objects.link(ob)
    if group == "Tray":   # put the origin on the hinge so the bed tips about it
        me.transform(Matrix.Translation(-BV(*P0)))
        ob.location = BV(*P0)
    OUT_OBJS.append(ob)
    print(f"{group}: {len(me.polygons)} faces, {len(mats)} materials")

for ob in list(coll.objects):
    ob.select_set(ob in OUT_OBJS)
bpy.context.view_layer.objects.active = OUT_OBJS[0]
bpy.ops.export_scene.gltf(filepath=os.path.abspath(OUT), export_format="GLB", use_selection=True,
                          export_apply=True, export_texcoords=False, export_normals=True,
                          export_materials="EXPORT", export_yup=True, export_extras=False)
print("wrote", os.path.abspath(OUT), os.path.getsize(OUT), "bytes")
