import sys, numpy as np, trimesh
from scipy import ndimage
r = float(sys.argv[1]) if len(sys.argv) > 1 else 0.025
m = trimesh.load('cad/sculpt/trex_head_ai.glb').to_geometry()
lo = np.array([-0.28, 0.0, 0.0]); hi = np.array([0.28, 0.58, 0.52]); p = 0.003
shape = np.ceil((hi - lo) / p).astype(int) + 1
axes = [lo[i] + p * np.arange(shape[i]) for i in range(3)]
P = np.stack(np.meshgrid(*axes, indexing='ij'), -1).reshape(-1, 3)
inside = m.contains(P).reshape(shape)
er = ndimage.distance_transform_edt(inside) * p > r
opened = ndimage.distance_transform_edt(~er) * p <= r
dout = ndimage.distance_transform_edt(~opened) * p
c = m.triangles_center
idx = np.round((c - lo) / p).astype(int)
inb = np.all((idx >= 0) & (idx < shape), 1)
d = np.zeros(len(c)); d[inb] = dout[tuple(idx[inb].T)]
zone = (np.abs(c[:, 0]) < 0.25) & (c[:, 1] > 0.03) & (c[:, 1] < 0.53) & (c[:, 2] > 0.06)
lab = ((d > 0.006) & zone).astype(int)
import trimesh.graph as tg
comps = tg.connected_components(m.face_adjacency[lab[m.face_adjacency].all(1)], nodes=np.nonzero(lab)[0])
col = np.load('/tmp/trex_face_rgb.npy'); L = np.nanmean(col, 1) / 255
keep = np.zeros_like(lab)
for cc in comps:
    if len(cc) > 150:
        l = np.nanmedian(L[cc])
        if l > 0.35: keep[cc] = 1
        else: print('drop', len(cc), round(float(l), 2))
lab = keep; np.save('/tmp/trex_face_lab.npy', lab); print('teeth faces', lab.sum(), 'regions', sum(len(cc) > 150 for cc in comps))
for k, name in [(0, 'body'), (1, 'teeth')]:
    sub = m.submesh([np.nonzero(lab == k)[0]], append=True); v = sub.vertices
    sub.vertices = np.c_[-v[:, 0], v[:, 1], -v[:, 2]] * 480; sub.export(f'/tmp/trex_lab_{name}.stl')
