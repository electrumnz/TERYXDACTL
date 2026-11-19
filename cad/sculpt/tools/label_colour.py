# Project the 4 concept views onto the AI mesh, save per-face colours (glTF coords)
import sys, numpy as np, trimesh
from PIL import Image
V = '/mnt/project-files/speaker-pods/concepts/v4-views/'
m = trimesh.load('cad/sculpt/trex_head_ai.glb').to_geometry()
c = m.triangles_center; n = m.face_normals; lo, hi = m.bounds
views = {  # name: (dir to camera, u axis, v axis(down))
  'front': (np.array([0,0,1.]), np.array([1,0,0.]), np.array([0,-1,0.])),
  'back':  (np.array([0,0,-1.]), np.array([-1,0,0.]), np.array([0,-1,0.])),
  'left':  (np.array([1.,0,0]), np.array([0,0,-1.]), np.array([0,-1,0.])),
  'right': (np.array([-1.,0,0]), np.array([0,0,1.]), np.array([0,-1,0.])),
}
acc = np.zeros((len(c), 3)); wsum = np.zeros(len(c))
for name, (d, u, v) in views.items():
    im = np.asarray(Image.open(V + name + '.png').convert('RGB')).astype(float)
    bg = np.median(np.r_[im[:5].reshape(-1,3), im[-5:].reshape(-1,3)], 0)
    fg = np.abs(im - bg).sum(2) > 40
    ys, xs = np.nonzero(fg); ib = (xs.min(), xs.max(), ys.min(), ys.max())
    pu, pv = c @ u, c @ v
    # mesh silhouette extents along u, v
    mu = (m.vertices @ u); mv = (m.vertices @ v)
    U = ib[0] + (pu - mu.min()) / (mu.max() - mu.min()) * (ib[1] - ib[0])
    Vv = ib[2] + (pv - mv.min()) / (mv.max() - mv.min()) * (ib[3] - ib[2])
    # visibility: cast from outside towards each face centre
    org = c + d * 5.0
    hit = m.ray.intersects_first(org, -d[None].repeat(len(c), 0))
    vis = hit == np.arange(len(c))
    w = np.clip(n @ d, 0, 1) ** 2 * vis
    col = im[np.clip(Vv.astype(int), 0, im.shape[0]-1), np.clip(U.astype(int), 0, im.shape[1]-1)]
    acc += col * w[:, None]; wsum += w
    print(name, ib, vis.mean())
col = np.where(wsum[:, None] > 1e-6, acc / np.maximum(wsum, 1e-9)[:, None], np.nan)
np.save('/tmp/trex_face_rgb.npy', col)
