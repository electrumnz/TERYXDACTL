"""Turn the AI T. rex head sculpt (concept 4) into a working, printable speaker pod.

    pip install numpy scipy scikit-image trimesh manifold3d rtree
    python cad/sculpt/trex_pod.py                 # 256 mm bed (X1, P1, A1)
    python cad/sculpt/trex_pod.py --bed 350 320 325   # H2D
    python cad/sculpt/trex_pod.py --scale 450     # smaller head

Writes cad/sculpt/out/: one .3mf per part with the colours painted on (open it in
Bambu Studio and pick a filament per colour), plus plain STLs and info.json.

The sculpt (trex_head_ai.glb) came from Hunyuan3D in Higgsfield, made from four
concept-4 views. trex_head_labels.npz says which of its triangles are teeth,
eyes and pupils (tools/label_*.py made it). This script:

  * scales it so the Kenwood 8" sits in the mouth, speaker axis on Z
  * MASK  = everything in front of the speaker's mounting face: snout, teeth,
            eyes, jaw. It goes on after the speaker, with a pocket on the back
            for the speaker's grille, held by 4 M5 bolts into inserts.
  * BOX   = the head behind the mounting face: a sealed box (the air inside is
            the speaker's box), flat front with the 180 mm hole, gland and vent
            underneath. The air space is shaped so it prints with no support
            inside (every ceiling leans at 45 deg).
  * COVER = the back of the skull. The cage tube runs left-right through the
            back of the head; the cover clamps it with 4 hidden M6 bolts.
Then each part is cut into pieces that fit the bed, with holes for 6 mm
dowels (or bits of filament/rod) to line them up when gluing.

Coordinates (mm): X right, Y up, Z back; Z=0 is the speaker's mounting face,
the speaker axis is the Z axis.
"""
import argparse, io, json, os, zipfile
import numpy as np
import trimesh
import manifold3d as mf
from scipy import ndimage
from scipy.spatial import cKDTree
from skimage import measure

HERE = os.path.dirname(os.path.abspath(__file__))
import sys; sys.path.insert(0, HERE)
import kenwood_kfc2053mrb as spk

# ---- where things are in the AI model (its own units, after turning it to face -Z)
AI_AXIS_Y = 0.341        # speaker centre height (from the speaker ring in the sculpt)
AI_BAFFLE_Z = -0.06      # the real speaker's mounting face goes here

# ---- real parts (mm)
SPK_CUTOUT = spk.CUTOUT_D      # the speaker itself is kenwood_kfc2053mrb.py
SPK_GRILLE = spk.GRILLE
SPK_PROUD = spk.GRILLE_PROUD
BAFFLE_T = 12.0          # solid mounting face (the speaker's screws bite in)
WALL = 4.5               # box wall
TUBE_D = 47.6            # cage tube (measure yours)
RUBBER = 1.5             # rubber strip round the tube
SEAT = 10.0              # solid between the air space and the tube
GAP = 2.0                # gap between box and cover so they squeeze the tube
M6_INSERT = (8.0, 13.0)  # hole d, depth for an M6 heat-set insert (cover bolts)
M5_INSERT = (6.4, 10.0)  # hole d, depth for an M5 heat-set insert (mask bolts)
GLAND_D = 12.5           # PG7 cable gland
VENT_D = 12.2            # M12 membrane vent
LUG_W, LUG_D = 60.0, 30.0   # chin lug half-width, depth
DOWEL = (6.3, 12.0)      # dowel hole d, depth each side of a cut
VOX = 1.5                # voxel size for the air space
THROAT_R = spk.CONE_D / 2 + 17        # the throat opens up to the whole cone (+ surround) at the grille

COLOURS = ["body", "teeth", "eyes", "pupils"]
HEX = {"body": "#6B5E4F", "teeth": "#EFE6CC", "eyes": "#E08A1E", "pupils": "#111111"}


# ----------------------------------------------------------------- helpers
def to_manifold(m):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                               tri_verts=np.asarray(m.faces, np.uint32)))


def to_trimesh(man):
    g = man.to_mesh()
    return trimesh.Trimesh(np.asarray(g.vert_properties)[:, :3], np.asarray(g.tri_verts), process=False)


def cyl(r, h, axis="z", center=True, n=64):
    c = mf.Manifold.cylinder(h, r, r, n, center)
    if axis == "x": c = c.rotate([0, 90, 0])
    if axis == "y": c = c.rotate([-90, 0, 0])
    return c


def rounded_square(w, r, z0, z1):
    cs = mf.CrossSection.square([w - 2 * r, w - 2 * r], True).offset(r, mf.JoinType.Round, 2, 64)
    return mf.Manifold.extrude(cs, z1 - z0).translate([0, 0, z0])


def largest(man):
    parts = man.decompose()
    return max(parts, key=lambda p: p.volume()) if len(parts) > 1 else man


def ray_first(mesh, origins, direction):
    d = np.tile(np.asarray(direction, float), (len(origins), 1))
    loc, idx, _ = mesh.ray.intersects_location(origins, d, multiple_hits=False)
    out = np.full(len(origins), np.nan)
    out[idx] = np.einsum("ij,ij->i", loc - origins[idx], d[idx])
    return out


# ----------------------------------------------------------------- the head
def load_head(scale):
    m = trimesh.load(os.path.join(HERE, "trex_head_ai.glb")).to_geometry()
    v = np.asarray(m.vertices, float)
    # glTF: Y up, face towards +Z. Ours: face towards -Z (turn 180 about Y)
    v = np.c_[-v[:, 0], v[:, 1] - AI_AXIS_Y, -v[:, 2] - AI_BAFFLE_Z] * scale
    head = trimesh.Trimesh(v, m.faces, process=False)
    labels = np.load(os.path.join(HERE, "trex_head_labels.npz"))["labels"]
    assert len(labels) == len(head.faces)
    return head, labels


def air_space(head, lo, hi, zc1):
    """The air space: the head shrunk by WALL, from the back of the baffle to
    the seat block (zc1). It runs 2 mm past zc1 so the box is an open-backed
    shell: it prints face down with any inside supports still reachable, and
    the seat block glued on behind closes it."""
    glo = np.array([lo[0] - 3, lo[1] - 3, BAFFLE_T - 3]); ghi = np.array([hi[0] + 3, hi[1] + 3, zc1 + 5])
    shape = np.ceil((ghi - glo) / VOX).astype(int) + 1
    axes = [glo[i] + VOX * np.arange(shape[i]) for i in range(3)]
    P = np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, 3)
    inside = head.contains(P).reshape(shape)
    din = ndimage.distance_transform_edt(inside) * VOX
    X, Y, Z = np.meshgrid(*axes, indexing="ij")
    V = (din > WALL) & (Z > BAFFLE_T) & (Z < zc1 + 2)
    V = ndimage.binary_opening(V, iterations=1)
    lab, n = ndimage.label(V)
    if n > 1:
        V = lab == (np.argmax(np.bincount(lab.ravel())[1:]) + 1)
    f = ndimage.gaussian_filter(V.astype(float), 0.7)
    f = np.pad(f, 1)
    verts, faces, _, _ = measure.marching_cubes(f, 0.5, spacing=(VOX,) * 3)
    verts += glo - VOX
    cav = trimesh.Trimesh(verts, faces[:, ::-1], process=True)
    if cav.volume < 0: cav.invert()
    return cav


def mask_bolts(mask_t, box_t, n=4):
    """M5 bolts from the front of the mask into inserts in the box face, on a
    ring just outside the speaker's grille, where the mask is 15-80 mm thick
    and the box face has 8 mm of plastic round the insert. Picks n spots
    spread round the ring."""
    half = SPK_GRILLE / 2 + 3 + 9
    cand = []
    for x in np.arange(-200, 201, 2.0):
        for y in np.arange(-250, 251, 2.0):
            if max(abs(x), abs(y)) < half or max(abs(x), abs(y)) > half + 45: continue
            cand.append((x, y))
    cand = np.array(cand)
    o = np.c_[cand, np.full(len(cand), -400.0)]
    t = ray_first(mask_t, o, [0, 0, 1])
    thick = 400 - t
    ok0 = ~np.isnan(t) & (thick >= 12)

    def fits(r):
        ok = ok0.copy()
        for dx, dy in [(0, 0), (r, 0), (-r, 0), (0, r), (0, -r), (.7 * r, .7 * r), (-.7 * r, .7 * r), (.7 * r, -.7 * r), (-.7 * r, -.7 * r)]:
            ok &= box_t.contains(np.c_[cand[:, 0] + dx, cand[:, 1] + dy, np.full(len(cand), 6.0)])
            ok &= mask_t.contains(np.c_[cand[:, 0] + dx, cand[:, 1] + dy, np.full(len(cand), -3.0)])
        return ok
    ok = fits(8.0) | fits(6.0)      # 6 mm round the insert where the chin is thin
    C, T = cand[ok], thick[ok]
    if len(C) == 0: return []
    ang = np.arctan2(C[:, 1], C[:, 0])
    out = []
    for k in range(n):        # one per quarter, the spot nearest the quarter's corner
        a0 = np.pi / 4 + k * np.pi / 2
        d = np.abs(np.angle(np.exp(1j * (ang - a0))))
        sel = d < np.pi / 4
        if not sel.any(): continue
        i = np.where(sel)[0][np.argmin(d[sel] + 0.002 * np.hypot(*C[sel].T))]
        out.append((C[i, 0], C[i, 1], T[i]))
    return out


def chin_bolts(mask_t, box_t):
    """Two M5s from the front of the chin into the chin lug's front face."""
    z0 = -LUG_D
    best = []
    for sx in (-1, 1):
        cand = [(sx * x, y) for x in np.arange(15, LUG_W - 7, 2.0) for y in np.arange(-200, -SPK_GRILLE / 2 - 10, 2.0)]
        cand = np.array(cand)
        ok = np.ones(len(cand), bool)
        for dx, dy in [(0, 0), (7, 0), (-7, 0), (0, 7), (0, -7)]:
            ok &= box_t.contains(np.c_[cand[:, 0] + dx, cand[:, 1] + dy, np.full(len(cand), z0 + 6)])
            ok &= mask_t.contains(np.c_[cand[:, 0] + dx, cand[:, 1] + dy, np.full(len(cand), z0 - 3)])
        if not ok.any(): continue
        C = cand[ok]
        t = ray_first(mask_t, np.c_[C, np.full(len(C), -400.0)], [0, 0, 1])
        good = ~np.isnan(t)
        C, th = C[good], (400 + z0 - t[good])
        i = np.argmax(np.abs(C[:, 0]) * 0.5 + np.abs(C[:, 1] - np.median(C[:, 1])) * -1)
        best.append((C[i, 0], C[i, 1], z0, th[i]))
    return best


def open_throat(mask, head_t, labels, tree):
    """Cut a 45 deg funnel from the whole cone forward to the mouth, so no part
    of the cone fires into the back of the face. The funnel follows the
    mouth's own outline (seen from the front, looking through the teeth) and
    keeps 2 mm clear of every tooth so the teeth stay on."""
    mt = to_trimesh(mask)
    lab = paint(mt, head_t, labels, tree)
    body = mt.submesh([np.where(lab != 1)[0]], append=True)
    z0 = -(SPK_PROUD + 4)                       # face of the grille pocket
    g = np.arange(-THROAT_R - 3, THROAT_R + 3.01, VOX)
    X, Y = np.meshgrid(g, g, indexing="ij")
    o = np.c_[X.ravel(), Y.ravel(), np.full(X.size, -600.0)]
    t = ray_first(body, o, [0, 0, 1])
    M = (np.isnan(t) | (t - 600 >= z0 - 0.5)).reshape(X.shape)   # clear view to the pocket
    disk = np.hypot(X, Y) <= THROAT_R
    dist = ndimage.distance_transform_edt(~M) * VOX
    T = float(dist[disk].max())
    zs = np.arange(z0 + 1, z0 - T - VOX, -VOX)
    F = np.stack([disk & (dist <= T - (z0 - z)) for z in zs], -1)
    # keep clear of the teeth
    teeth = mt.submesh([np.where(lab == 1)[0]], append=True)
    if len(teeth.faces):
        pts, _ = trimesh.sample.sample_surface_even(teeth, 200000)
        ijk = np.round(np.c_[(pts[:, 0] - g[0]) / VOX, (pts[:, 1] - g[0]) / VOX, (zs[0] - pts[:, 2]) / VOX]).astype(int)
        ok = (ijk >= 0).all(1) & (ijk < F.shape).all(1)
        P = np.zeros(F.shape, bool); P[tuple(ijk[ok].T)] = True
        F &= ~ndimage.binary_dilation(P, iterations=2)
    f = np.pad(ndimage.gaussian_filter(F.astype(float), 0.6), 1)
    v, fc, _, _ = measure.marching_cubes(f, 0.5)
    v = (v - 1) * VOX
    v = np.c_[g[0] + v[:, 0], g[0] + v[:, 1], zs[0] - v[:, 2]]
    cut = trimesh.Trimesh(v, fc, process=True)
    if cut.volume < 0: cut.invert()
    out = mask - to_manifold(cut)
    keep = [p for p in out.decompose() if p.volume() > 1e5]      # drop crumbs, keep the jaw
    return mf.Manifold.batch_boolean(keep, mf.OpType.Add) if len(keep) > 1 else keep[0], round(T, 1)


def fit_check(parts, head_t, labels, tree):
    """Put the real speaker model in and check it fits. Returns a dict; any
    'ok': False is a problem."""
    sp = spk.build()
    out = {}
    box, mask = parts["box"], parts["mask"]
    hit = (sp ^ box).volume() / 1e3
    out["speaker_vs_box_cm3"] = round(hit, 2)
    hitm = sum((sp ^ parts[k]).volume() for k in parts if k not in ("box",)) / 1e3
    out["speaker_vs_face_cm3"] = round(hitm, 2)
    box_t = to_trimesh(box)
    bt = to_trimesh(spk.behind())
    pts, _ = trimesh.sample.sample_surface_even(bt, 3000)
    pts = pts[pts[:, 2] > BAFFLE_T + 1]
    d = np.abs(trimesh.proximity.signed_distance(box_t, pts))
    out["basket_clearance_mm"] = round(float(d.min()), 1)
    hole_ok = [bool(all(box_t.contains([[x + dx, y + dy, BAFFLE_T / 2]])[0] for dx, dy in [(4, 0), (-4, 0), (0, 4), (0, -4)]))
               for x, y in spk.holes()]
    out["screw_holes_in_plastic"] = hole_ok
    # how much of the cone can see straight out of the mouth (teeth count as clear)
    mt = to_trimesh(mask)
    lab = paint(mt, head_t, labels, tree)
    body = mt.submesh([np.where(lab != 1)[0]], append=True)
    g = np.arange(-spk.CONE_D / 2, spk.CONE_D / 2 + 0.1, 3.0)
    X, Y = np.meshgrid(g, g); sel = np.hypot(X, Y) <= spk.CONE_D / 2
    o = np.c_[X[sel], Y[sel], np.full(sel.sum(), -SPK_PROUD - 1.0)]
    t = ray_first(body, o, [0, 0, -1])
    out["cone_open_pct"] = round(100 * float(np.isnan(t).mean()), 0)
    tt = ray_first(mt, o, [0, 0, -1])
    out["cone_open_pct_counting_teeth"] = round(100 * float(np.isnan(tt).mean()), 0)
    out["ok"] = bool(hit < 0.05 and hitm < 0.05 and out["basket_clearance_mm"] >= 3 and all(hole_ok))
    return out


# ----------------------------------------------------------------- build
def build(scale):
    head_t, labels = load_head(scale)
    assert head_t.is_watertight, "AI mesh not watertight"
    head = to_manifold(head_t)
    lo, hi = head_t.bounds
    info = {"scale": scale, "size_mm": (hi - lo).round(0).tolist()}

    # cage tube: left-right through the back of the skull
    Rb = TUBE_D / 2 + RUBBER
    tube_z = hi[2] - 0.24 * (hi[2] - lo[2])
    sec = head_t.section(plane_origin=[0, 0, tube_z], plane_normal=[0, 0, 1])
    tube_y = sec.vertices[:, 1].min() + 0.45 * np.ptp(sec.vertices[:, 1])
    bore = cyl(Rb, 2000, "x").translate([0, tube_y, tube_z])
    info.update(tube_y=round(float(tube_y), 1), tube_z=round(float(tube_z), 1))

    front = head.trim_by_plane([0, 0, -1], 0.0)
    back = head.trim_by_plane([0, 0, 1], 0.0)
    box = back.trim_by_plane([0, 0, -1], -(tube_z - GAP / 2))
    cover = back.trim_by_plane([0, 0, 1], tube_z + GAP / 2)

    zc1 = tube_z - Rb - SEAT
    cav_t = air_space(head_t, lo, hi, zc1)
    cav = largest(to_manifold(cav_t))
    info["air_gross_l"] = round(cav.trim_by_plane([0, 0, -1], -zc1).volume() / 1e6, 2)
    seat = box.trim_by_plane([0, 0, 1], zc1)
    box = box.trim_by_plane([0, 0, -1], -zc1)

    # mask: pocket for the speaker's grille; drops the AI speaker left in the mouth
    pocket = rounded_square(SPK_GRILLE + 6, 20, -(SPK_PROUD + 4), 0.5)
    mask = largest(front - pocket)
    # chin lug: below the speaker the joint face is only a few mm tall, so the
    # box takes the back 30 mm of the lower jaw; the mask bolts to its front
    lug = mf.Manifold.cube([2 * LUG_W, 200, LUG_D + 0.5]).translate([-LUG_W, -SPK_GRILLE / 2 - 3 - 200 - 2, -LUG_D])
    box = box + (front ^ lug)
    mask = largest(mask - lug)
    tree = cKDTree(head_t.triangles_center)
    mask, info["throat_depth_mm"] = open_throat(mask, head_t, labels, tree)

    # the head narrows at the bottom, so the speaker's lower screws would miss
    # the box: a flat mounting plate the size of the grille closes that gap
    plate = rounded_square(SPK_GRILLE + 12, spk.GRILLE_R + 6, 0, BAFFLE_T)
    box = box + plate
    box = box - cav - cyl(SPK_CUTOUT / 2, 4 * BAFFLE_T, "z")
    for x, y in spk.holes():                    # pilot holes for the speaker's screws
        box = box - cyl(spk.PILOT_D / 2, 2 * (BAFFLE_T - 2), "z").translate([x, y, 0])
    seat = seat - bore
    cover = cover - bore
    # dowels to line the seat block up on the box (glue + seal this joint)
    for q in dowel_spots(back.trim_by_plane([0, 0, -1], -(tube_z - GAP / 2)) - cav, 2, zc1):
        c = cyl(DOWEL[0] / 2, 2 * DOWEL[1], "z").translate(q.tolist())
        box = box - c; seat = seat - c

    # cover bolts: 4 x M6 along Z, each side of the tube
    pts = sec.vertices[np.abs(sec.vertices[:, 1] - tube_y) < 6]
    xm = np.abs(pts[:, 0]).max()
    yb = Rb + 10
    cb = [(sx * (xm - 28), tube_y + sy * yb) for sx in (-1, 1) for sy in (-1, 1)]
    for x, y in cb:
        seat = seat - cyl(M6_INSERT[0] / 2, 2 * M6_INSERT[1], "z").translate([x, y, tube_z - GAP / 2])
        cover = cover - cyl(3.3, 600, "z").translate([x, y, tube_z]) \
                      - cyl(5.6, 600, "z", False).translate([x, y, tube_z + GAP / 2 + 12])
    info["cover_bolts"] = "4 x M6x25, heads under plugs"

    # mask bolts: 4 x M5 from the front, heads under plugs
    mask_t, box_t = to_trimesh(mask), to_trimesh(box)
    mb = [(x, y, 0.0, t) for x, y, t in mask_bolts(mask_t, box_t) if y > 0]
    mb += chin_bolts(mask_t, box_t)
    lens = []
    for x, y, z0, thick in mb:
        L = max(l for l in (16, 20, 25, 30, 35) if l - 9 <= thick - 3)  # deep spots get a long counterbore
        h = L - 9                                         # head seat this far in front of the joint
        mask = mask - cyl(2.75, 2 * h + 2, "z").translate([x, y, z0]) \
                    - cyl(5.0, 300, "z", False).translate([x, y, z0 - h - 300])
        box = box - cyl(M5_INSERT[0] / 2, 2 * M5_INSERT[1], "z").translate([x, y, z0])
        lens.append(L)
    info["mask_bolts"] = [f"M5x{L} at x={x:.0f} y={y:.0f}" for (x, y, _, _), L in zip(mb, lens)]

    # gland and vent underneath the box, square to the bottom, with a flat spot-face
    box_t = to_trimesh(box)
    for (x, z, d) in [(30, 60, GLAND_D), (-30, 60, VENT_D)]:
        yb_ = lo[1] - 50 + ray_first(box_t, np.array([[x, lo[1] - 50, z]]), [0, 1, 0])[0]
        box = box - cyl(d / 2, 60, "y").translate([x, yb_ + 10, z]) \
                  - cyl(13, 50, "y", False).translate([x, yb_ - 49, z])
    info["under"] = "PG7 gland at x=+30, M12 vent at x=-30, both 60 mm behind the face"

    # the open throat leaves the lower jaw as its own piece (it bolts to the chin lug)
    mp = sorted(mask.decompose(), key=lambda p: -p.volume())
    parts = {"mask": mp[0]}
    if len(mp) > 1 and mp[1].volume() > 1e5: parts["jaw"] = mp[1]
    parts.update(box=largest(box), seat=largest(seat), cover=largest(cover))
    info["fit"] = fit_check(parts, head_t, labels, tree)
    return head_t, labels, parts, cav_t, info


# ----------------------------------------------------------------- colours
def paint(part_t, head_t, labels, tree):
    """Label each triangle of a finished part from the nearest triangle of the
    sculpt; new faces (cuts, holes) are body colour."""
    d, i = tree.query(part_t.triangles_center, k=1)
    lab = labels[i].copy()
    nrm_ok = np.einsum("ij,ij->i", part_t.face_normals, head_t.face_normals[i]) > 0.8
    lab[(d > 0.8) | ~nrm_ok] = 0
    return lab


# ----------------------------------------------------------------- splitting


def split_to_bed(man, bed, name):
    """Cut with planes square to X and Y until each piece fits the bed (every
    part prints along Z, so the cuts are upright walls with no overhang).
    Dowel holes on every cut."""
    pieces, cuts = [man], []
    while True:
        out, done = [], True
        for p in pieces:
            bb = np.array(p.bounding_box()); lo, hi = bb[:3], bb[3:]
            size = hi - lo
            if size[0] <= bed[0] - 4 and size[1] <= bed[1] - 4:
                out.append(p); continue
            done = False
            ax = 0 if size[0] / bed[0] >= size[1] / bed[1] else 1
            n = int(np.ceil(size[ax] / (bed[ax] - 4)))
            nv = [0.0, 0.0, 0.0]; nv[ax] = 1.0
            # try cut spots round the even split; keep the one that leaves the
            # fewest loose bits (a cut through a thin cheek or a tooth tip
            # leaves crumbs), then the biggest smallest bit
            even = lo[ax] + size[ax] / n
            span = (bed[ax] - 4) - size[ax] / n
            best = None
            for at in np.linspace(even - min(span, 60), even + min(span, 60), 13):
                if at - lo[ax] > bed[ax] - 4: continue
                a = p.trim_by_plane([-c for c in nv], -at)     # keeps the low side
                b = p.trim_by_plane(nv, at)                    # keeps the high side
                bits = [x.volume() for z in (a, b) for x in z.decompose()]
                score = (len(bits), -min(bits) if bits else 0)
                if best is None or score < best[0]: best = (score, at, a, b)
            _, at, a, b = best
            cuts.append((ax, float(at)))
            for q in dowel_spots(p, ax, at):
                c = cyl(DOWEL[0] / 2, 2 * DOWEL[1], "xyz"[ax]).translate(q.tolist())
                a = a - c; b = b - c
            out += [x for z in (a, b) for x in z.decompose() if x.volume() > 500]
        pieces = out
        if done: break
    return pieces, cuts


def dowel_spots(p, ax, at):
    t = to_trimesh(p)
    b = t.bounds
    other = [i for i in range(3) if i != ax]
    g0 = np.arange(b[0][other[0]] + 8, b[1][other[0]] - 8, 6)
    g1 = np.arange(b[0][other[1]] + 8, b[1][other[1]] - 8, 6)
    G0, G1 = np.meshgrid(g0, g1, indexing="ij")
    P = np.zeros((G0.size, 3)); P[:, ax] = at; P[:, other[0]] = G0.ravel(); P[:, other[1]] = G1.ravel()
    ok = t.contains(P)
    # need 7 mm of material round the hole, both sides of the cut
    for dv in [(7, 0), (-7, 0), (0, 7), (0, -7)]:
        Q = P.copy(); Q[:, other[0]] += dv[0]; Q[:, other[1]] += dv[1]
        for s in (-DOWEL[1], DOWEL[1]):
            R = Q.copy(); R[:, ax] += s; ok &= t.contains(R)
    C = P[ok]
    if len(C) == 0: return []
    # spread: farthest-point picks, max 3
    pick = [C[np.argmax(C[:, other[0]])]]
    while len(pick) < 3:
        dd = np.min([np.linalg.norm(C - q, axis=1) for q in pick], axis=0)
        if dd.max() < 40: break
        pick.append(C[np.argmax(dd)])
    return pick


# ----------------------------------------------------------------- 3MF
def paint_code(state):
    """Bambu/Prusa per-triangle colour code for a whole (unsplit) triangle."""
    if state == 0: return ""
    if state < 3: return "%X" % (state << 2)
    return "%XC" % (state - 3)


def write_3mf(path, objects):
    """objects: list of (name, trimesh, labels 0..3). Labels become painted
    filament colours 1..4 (body = filament 1)."""
    model = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
             'xmlns:slic3rpe="http://schemas.slic3r.org/3mf/2017/06">',
             '<metadata name="Application">teryx trex_pod.py</metadata>', '<resources>']
    build = []
    x_off = 0.0
    for oid, (name, m, lab) in enumerate(objects, start=1):
        model.append(f'<object id="{oid}" type="model" name="{name}"><mesh><vertices>')
        v = m.vertices - [m.bounds[0][0], m.bounds[0][1], m.bounds[0][2]]
        model += [f'<vertex x="{a:.4f}" y="{b:.4f}" z="{c:.4f}"/>' for a, b, c in v]
        model.append('</vertices><triangles>')
        for (a, b, c), s in zip(m.faces, lab):
            code = paint_code(int(s) + 1 if s else 0)
            extra = f' paint_color="{code}" slic3rpe:mmu_segmentation="{code}"' if code else ""
            model.append(f'<triangle v1="{a}" v2="{b}" v3="{c}"{extra}/>')
        model.append('</triangles></mesh></object>')
        build.append(f'<item objectid="{oid}" transform="1 0 0 0 1 0 0 0 1 {x_off:.1f} 0 0"/>')
        x_off += np.ptp(m.vertices[:, 0]) + 10
    model += ['</resources>', '<build>'] + build + ['</build>', '</model>']
    ct = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", "\n".join(model))


def orient_for_print(m, name):
    """Turn a part so its print direction is +Z and it sits on Z=0."""
    m = m.copy()
    if name == "mask":                       # back face (Z=0) on the bed, snout up
        m.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [0, 1, 0]))
    m.apply_translation([0, 0, -m.bounds[0][2]])
    return m


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=float, default=480)
    ap.add_argument("--bed", type=float, nargs=3, default=[300, 320, 320],
                    help="default: Bambu H2C printing with both nozzles (300 x 320 x 325)")
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--no-split", action="store_true")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    for f in os.listdir(a.out):
        if f.endswith((".print.stl", ".3mf")): os.remove(os.path.join(a.out, f))
    head_t, labels, parts, cav_t, info = build(a.scale)
    tree = cKDTree(head_t.triangles_center)
    cav_t.export(os.path.join(a.out, "trex_air_space.stl"))
    info["bed"] = a.bed; info["pieces"] = {}
    for name, man in parts.items():
        whole = to_trimesh(man)
        whole.export(os.path.join(a.out, f"trex_{name}.stl"))
        lab = paint(whole, head_t, labels, tree)
        np.save(os.path.join(a.out, f"trex_{name}_labels.npy"), lab.astype(np.uint8))
        info[f"{name}_size_mm"] = np.ptp(whole.vertices, axis=0).round(0).tolist()
        pieces = [man] if a.no_split else split_to_bed(man, a.bed, name)[0]
        objs = []
        for i, p in enumerate(pieces, 1):
            t = to_trimesh(p)
            pl = paint(t, head_t, labels, tree)
            t2 = orient_for_print(t, name)
            nm = f"{name}_{i}" if len(pieces) > 1 else name
            t2.export(os.path.join(a.out, f"trex_{nm}.print.stl"))
            objs.append((nm, t2, pl))
        write_3mf(os.path.join(a.out, f"trex_{name}.3mf"), objs)
        info["pieces"][name] = len(pieces)
    with open(os.path.join(a.out, "info.json"), "w") as f:
        json.dump(info, f, indent=1)
    print(json.dumps(info, indent=1))


if __name__ == "__main__":
    main()
