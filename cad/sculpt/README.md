# Sculpted T. rex speaker pod (concept 4)

![assembled](../img/trex_pod_assembled.png)
![exploded](../img/trex_pod_exploded.png)

The head is a real sculpt, not CAD shapes: four views of concept 4 were made in
Higgsfield, then Hunyuan3D turned them into a watertight model
(`trex_head_ai.glb`). `trex_pod.py` turns that into a working, printable
speaker pod for the Kenwood KFC-2053MRB 8".

```
pip install numpy scipy scikit-image trimesh manifold3d rtree
python cad/sculpt/trex_pod.py                     # 256 mm bed (X1, P1, A1)
python cad/sculpt/trex_pod.py --bed 350 320 325   # H2D
python cad/sculpt/trex_pod.py --scale 450         # smaller head
```

Output goes to `cad/sculpt/out/` (not in git, it's big): one `.3mf` per part
with the colours already painted on, `.print.stl` for every piece (already
turned the way up it prints), and `info.json` with the sizes and bolt list.

## Size

About 35 cm wide, 45 cm tall, 51 cm long (snout to back of skull) at the
default `--scale 480`. That's what it takes for the 230 mm grille to sit in
the mouth.

## The parts

| Part | What it is | Prints |
|---|---|---|
| mask | Snout, teeth, eyes, jaw. Everything in front of the speaker. Goes on last, over the speaker | Flat back on the bed, snout up. Supports inside the grille pocket |
| box | Sealed box: flat front with the 180 mm hole, chin lug, gland and vent underneath | Front face on the bed. Open at the back, so any supports come out |
| seat | Solid block that closes the back of the box and holds the cage tube | Flat face down |
| cover | Back of the skull. Clamps the tube with 4 hidden M6 bolts | Flat face down |

The cage tube runs left to right through the back of the head, in a 1.5 mm
rubber strip, between the seat and the cover.

Air inside the box: **10.8 L** (`pod.gross_l` in `config/speaker_pods.yaml`;
the Pi's bass EQ is worked out from it).

## Colours (AMS)

The 3MFs are painted: filament 1 body, 2 teeth (bone), 3 eyes (amber),
4 pupils (black). Open a 3MF in Bambu Studio, set those four filament slots
and slice. The teeth and eyes were picked out of the sculpt once by
`tools/label_*.py` (shape plus the colours in the concept views) and saved in
`trex_head_labels.npz`.

## Pieces (256 mm bed)

mask 5, box 4, seat 4, cover 2. Two of the mask pieces are thin cheek strips.
Pieces join on flat upright cuts with 6 mm dowel holes (use 6 mm rod or
cut-off bolts) where there's room. Glue with ASA cement or epoxy.

**The box and the box-to-seat joint must be airtight**: glue all the way
round and run a bead of sealant inside before it closes up. A leaky box
loses the bass.

## Hardware per pod

- 4x M6 heat-set insert + M6x25 (cover to seat), heads under printed plugs
- 4x M5 heat-set insert: 2x M5x16 at the brow, 2x M5x35 through the chin
  into the chin lug. Counterbores from the front, plug them after
- PG7 gland (speaker wire) and M12 vent, both underneath
- 4 speaker screws into the 12 mm front of the box
- 1.5 mm rubber strip round the cage tube

## Filament

Roughly 3.4 kg of ASA per head at 3 walls and 15% infill (the slicer will
give the real number), under 100 g of each colour.

## Still guesses

- `SPK_PROUD` (how far the grille stands out of the box face): 25 mm.
  Measure it, the grille pocket depends on it.
- `TUBE_D`: 47.6 mm. Measure your cage tube.
