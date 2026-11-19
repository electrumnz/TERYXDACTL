import numpy as np, trimesh
m = trimesh.load('cad/sculpt/trex_head_ai.glb').to_geometry()
c = m.triangles_center; nrm = m.face_normals
lab = np.load('/tmp/trex_face_lab.npy')
for s in (1, -1):
    # outermost surface along x at each face's (y, z)
    org = np.c_[np.full(len(c), s * 1.0), c[:, 1], c[:, 2]]
    ell = ((c[:, 1] - 0.712) / 0.03) ** 2 + ((c[:, 2] - 0.10) / 0.045) ** 2
    cand = np.nonzero((ell < 1.0) & (s * c[:, 0] > 0.05))[0]
    hit = m.ray.intersects_first(org[cand], np.tile([-s, 0, 0.], (len(cand), 1)))
    vis = cand[hit == cand]
    lab[vis] = 2
    pup = vis[(np.abs(c[vis, 2] - 0.10) < 0.0075) & (np.abs(c[vis, 1] - 0.712) < 0.022)]
    lab[pup] = 3
    print('side', s, 'eye faces', len(vis), 'pupil', len(pup))
np.save('/tmp/trex_face_lab2.npy', lab)
for k, name in [(0, 'body'), (1, 'teeth'), (2, 'eye'), (3, 'pupil')]:
    sub = m.submesh([np.nonzero(lab == k)[0]], append=True); v = sub.vertices
    sub.vertices = np.c_[-v[:, 0], v[:, 1], -v[:, 2]] * 480; sub.export(f'/tmp/trex_lab_{name}.stl')
