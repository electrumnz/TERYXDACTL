# Sculpted T. rex speaker pod (concept 4)

With the speaker in:
![with speaker](../img/trex_pod_assembled.png)
Without the speaker, and pulled apart:
![without speaker](../img/trex_pod_exploded.png)

The head is a real sculpt, not CAD shapes: four views of concept 4 were made in
Higgsfield, then Hunyuan3D turned them into a watertight model
(`trex_head_ai.glb`). `trex_pod.py` turns that into a working, printable
speaker pod for the Kenwood KFC-2053MRB 8".

```
pip install numpy scipy scikit-image trimesh manifold3d rtree
python cad/sculpt/trex_pod.py                     # Bambu H2C, both nozzles (300 x 320)
python cad/sculpt/trex_pod.py --bed 256 256 256   # X1, P1, A1
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
| mask | Snout, upper teeth, eyes. Goes on last, over the speaker | Flat back on the bed, snout up |
| box | Sealed box: flat mounting plate with the 180 mm hole and 4 pilot holes, chin lug, gland and vent underneath | Front face on the bed. Open at the back, so any supports come out |
| seat | Solid block that closes the back of the box and holds the cage tube | Flat face down |
| cover | Back of the skull. Clamps the tube with 4 hidden M6 bolts | Flat face down |

The cage tube runs left to right through the back of the head, in a 1.5 mm
rubber strip, between the seat and the cover.

Air inside the box: **10.8 L** (`pod.gross_l` in `config/speaker_pods.yaml`;
the Pi's bass EQ is worked out from it).

## The speaker model and the clash check

![speaker](../img/kenwood_kfc2053mrb.png)

`kenwood_kfc2053mrb.py` is the speaker on its own: round 230 mm frame with
4 screws, domed mesh grille with spokes, tweeter pod, basket, 8 oz magnet,
terminals. Built from Kenwood's published sizes: 180 mm cut-out, 86 mm
mounting depth, 230 x 230 x 113 mm with the grille (so the grille stands
27 mm proud). `envelope()` is its solid outline, used for the clash check.

Every build `trex_pod.py` puts the outline in and checks it against every
part, then writes the result to `info.json` under `fit` and warns if it
fails. Now: no clashes, 6 mm to the box walls behind the face (2 mm through
the cut-out, which is Kenwood's own size), 2.9 mm from the grille to the
face, all 4 screws in plastic, 93% of the cone sees straight out of the
mouth (83% counting the teeth).

Still guesses, at the top of `kenwood_kfc2053mrb.py`: the screw circle,
the rim thickness, the magnet size, the basket shape and where the terminals
are. Measure yours and change them; the check follows.

## Sound

The throat is cut right through from the whole cone to the mouth at
45 degrees, so the face doesn't choke the speaker. The mouth is still deep
in front of the grille, which can add a small bump somewhere around 600 to
900 Hz. Measure it with a phone mic once it's in and notch it in the Pi EQ.

## Colours (AMS)

The 3MFs are painted: filament 1 body, 2 teeth (bone), 3 eyes (amber),
4 pupils (black). Open a 3MF in Bambu Studio, set those four filament slots
and slice. The teeth and eyes were picked out of the sculpt once by
`tools/label_*.py` (shape plus the colours in the concept views) and saved in
`trex_head_labels.npz`.

## Pieces (H2C, 300 x 320 bed)

mask 2, box 4, seat 4, cover 1. With the round grille pocket the lower jaw stays part of the mask.
Pieces join on flat upright cuts with 6 mm dowel holes (use 6 mm rod or
cut-off bolts) where there's room. Glue with ASA cement or epoxy.

**The box and the box-to-seat joint must be airtight**: glue all the way
round and run a bead of sealant inside before it closes up. A leaky box
loses the bass.

## Hardware per pod

- 4x M6 heat-set insert + M6x25 (cover to seat), heads under printed plugs
- 4x M5 heat-set insert + M5x35: 2 at the brow, 2 through the chin into
  the chin lug. Counterbores from the front, plug them after
- PG7 gland (speaker wire) and M12 vent, both underneath
- the speaker's own 4 screws into the 12 mm round mounting plate (3.5 mm pilot holes)
- 1.5 mm rubber strip round the cage tube

## Filament and slicer settings

- 3 walls everywhere. Box and seat: 15% gyroid infill. Mask and
  cover: 5% lightning infill (it only holds up the top skins).
- ASA for the walls and colours, ABS for infill: in Bambu Studio, Others >
  Filament for features > Sparse infill = the ABS slot. Print the seat
  blocks all in ABS, they're hidden.
- Roughly 2.7 kg per head: 1.8 kg ASA, 0.95 kg ABS, under 100 g of each
  colour. The slicer will give the real number.

## Still guesses

- The speaker's screw circle, magnet and basket (see above).
- `TUBE_D`: 47.6 mm. Measure your cage tube.
