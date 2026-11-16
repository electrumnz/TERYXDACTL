"""Lay the model over a reference photo to check the shape.

    python teryx/web/virtual/blender/overlay.py photo.png out.png \\
        --rear-axle 166,373 --front-axle 594,368 [--side right]

The photo should be a side-on shot. Give the pixel centres of the rear and
front wheels: the model is scaled so its 1930 mm wheelbase spans them, then
rendered with an orthographic camera and drawn over the photo (outline in
red, plus a 50/50 blend). Reference photos are other people's pictures, so
keep them and the overlays out of the repo.
"""
import argparse
import math
import os
import sys

import bpy  # noqa: I001  (bpy must load before mathutils)
from mathutils import Vector

ap = argparse.ArgumentParser()
ap.add_argument("photo")
ap.add_argument("out")
ap.add_argument("--rear-axle", required=True)
ap.add_argument("--front-axle", required=True)
ap.add_argument("--side", default="right", choices=["right", "left"])
ap.add_argument("--glb", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "teryx.glb"))
args = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])

from PIL import Image, ImageChops, ImageFilter  # noqa: E402

FX, RX, WHEEL_R, TRACK_F, TRACK_R = 0.965, -0.965, 0.33, 1.22, 1.24
photo = Image.open(args.photo).convert("RGB")
W, H = photo.size
(rx, ry), (fx, fy) = [tuple(map(float, a.split(","))) for a in (args.rear_axle, args.front_axle)]
ppm = math.hypot(fx - rx, fy - ry) / (FX - RX)          # pixels per metre
axle_px = (rx + fx) / 2, (ry + fy) / 2

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.abspath(args.glb))
objs = {o.name: o for o in bpy.context.scene.objects}
# wheels come centred on their axle: put four of them on the ute
for name, x, track in (("WheelF", FX, TRACK_F), ("WheelR", RX, TRACK_R)):
    src = objs[name]
    for s in (-1, 1):
        o = src.copy()
        bpy.context.scene.collection.objects.link(o)
        o.location = Vector((x, -s * track / 2, WHEEL_R))       # sim z -> Blender -y
        o.rotation_euler = (0, 0, 0)
        o.scale = (1, -s, 1)                                     # outer face away from the ute
    src.hide_render = True

cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = max(W, H) / ppm
cam = bpy.data.objects.new("cam", cam_data)
bpy.context.scene.collection.objects.link(cam)
# image centre in metres (front of the ute to the right of the photo)
cx = (FX + RX) / 2 + (W / 2 - axle_px[0]) / ppm
cy = WHEEL_R + (axle_px[1] - H / 2) / ppm
if args.side == "right":          # camera on the ute's right (+z sim = -y Blender) looking across
    cam.location = (cx, -20, cy)
    cam.rotation_euler = (math.pi / 2, 0, 0)
else:
    cam.location = (-cx, 20, cy)
    cam.rotation_euler = (math.pi / 2, 0, math.pi)
bpy.context.scene.camera = cam

sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 3
sun.rotation_euler = (0.9, 0.2, 0.6)
bpy.context.scene.collection.objects.link(sun)
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.6, 0.6, 0.6, 1)
bpy.context.scene.world = world

r = bpy.context.scene.render
r.engine = "CYCLES"
bpy.context.scene.cycles.samples = 8
bpy.context.scene.cycles.device = "CPU"
r.resolution_x, r.resolution_y = W, H
r.film_transparent = True
tmp = os.path.abspath(args.out) + ".model.png"
r.filepath = tmp
bpy.ops.render.render(write_still=True)

model = Image.open(tmp).convert("RGBA")
alpha = model.split()[3].point(lambda a: 255 if a > 40 else 0)
edge = ImageChops.difference(alpha.filter(ImageFilter.MaxFilter(3)), alpha.filter(ImageFilter.MinFilter(3)))
outline = photo.copy()
outline.paste((255, 30, 30), mask=edge)
blend = Image.blend(photo, Image.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, 255)), model).convert("RGB"), 0.5)
sheet = Image.new("RGB", (W * 3, H), "white")
sheet.paste(outline, (0, 0))
sheet.paste(blend, (W, 0))
sheet.paste(Image.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, 255)), model).convert("RGB"), (W * 2, 0))
sheet.save(args.out)
os.remove(tmp)
print("wrote", args.out)
