# What to measure

Every number below lives in [`measurements.scad`](measurements.scad). Change
it there, run `./cad/build.sh`, and print the fit test before anything big.

You need: digital calipers (or a good steel rule), a tape measure, masking
tape and a marker. Measure twice, write it down, and round **up** to the next
0.5 mm. The model already adds `fit` (0.6 mm) of clearance each side, so don't
add your own.

## 1. The screen (15 minutes, on the bench)

The listing gives the outside size (273 x 192 x 41) and the cut-out
(217 x 135). Check those, and measure the rest. Lay the screen face down on
a towel.

| Setting | How to measure it |
|---|---|
| `scr_w`, `scr_h` | Width and height of the front bezel |
| `scr_d` | Overall depth, front glass to the flat back of the case (not the plugs) |
| `scr_bezel_t` | Thickness of the front bezel only: the step from the glass to where the narrower body starts |
| `scr_r` | Corner radius of the bezel. A 10c coin is about 10 mm across (5 mm radius), 20c about 22 mm (11 mm radius). 0 if square |
| `panel_cut_w`, `panel_cut_h` | Width and height of the **body** behind the bezel, where the clips hook on. If it's bigger than 217 x 135, use the body size + 1 mm. The model adds `fit` on top |
| `clip_room` | Fit a clip and screw to the body. How far out from the body do they reach? Add 5 mm. The back of the panel is kept flat for this far round the cut-out |
| `scr_vesa`, `scr_vesa_clear` | Centre-to-centre spacing of the 4 wall-bracket holes on the back (75 or 100), and the thread (M4 = 4.5 clearance) |
| `scr_cable_x`, `scr_cable_y` | Looking at the **front** of the screen, where do the cables come out of the back? Measure from the centre of the back, right and up are plus |
| `scr_cable_d` | Hole size for the cables. Must pass the biggest plug (VGA plug is about 31 x 16 with its screws, HDMI about 21 x 11) |

While you're there, read the label on the power brick (volts and amps) and
check which video sockets are on the back (VGA only, or HDMI too). See
"About the screen" in [README.md](README.md).

## 2. Your printer

| Setting | |
|---|---|
| `bed_x`, `bed_y` | Usable bed size. Big parts get cut in two to fit |
| `m3_insert_d`, `m3_insert_deep` | Hole size and length printed on the heat-set insert packet |

## 3. The dash (20 minutes, on the Teryx)

The new screen covers the stock gauge cluster. Pull the cluster out and look
at how it was held in.

1. Decide where you want the **centre** of the new screen. Stick masking tape
   across the dash and mark that point with a cross.
2. For each bolt hole (or stud, or bracket hole) you can use, measure across
   (`x`, right is plus) and up (`y`, up is plus) from your cross to the
   centre of the hole. Do it looking at the dash from the driver's seat.
3. Put them in `dash_holes`, for example
   `dash_holes = [[-80, -45], [80, -45], [0, 50]];`
4. Measure the hole or stud size for `dash_hole_d` (M6 bolt = 6.5, M8 = 8.5,
   M5 = 5.5).
5. Check the back won't hit anything: the panel and rim are about 41 mm
   deep, the back plate is `bp_t` (6 mm) thick, and the Pi box sticks out
   52 mm behind that (more with the fan cowl). If there isn't room straight behind, change `pi_box_pos`
   to slide the box sideways or up.
6. Note the angle of the dash face. If the screen should tilt back more than
   the dash does, tell Claude and we'll add a wedge spacer.

Not sure yet? Leave `dash_amps = true`. That puts a standard AMPS hole
pattern (30 x 38 mm, M5) on the back plate, which fits RAM ball mounts and
most off-the-shelf brackets, so you can test it in the Teryx before making a
custom mount.

## 4. The sun hood

| Setting | |
|---|---|
| `hood_reach` | How far the top sticks out past the screen. 70 mm is a good start. Longer shades more but blocks more of your view over the dash |
| `hood_side_h` | How far down the side cheeks go |
| `hood_tilt` | Tips the top up so rain runs off the front |

## 5. The boxes

`cb_box_in` and `rb_box_in` are the **inside** sizes of the control box and
relay box. Lay the boards on a sheet of paper with gaps for wires and the gland
nuts (about 25 mm clear in front of the bottom wall), draw round them, and
measure. The grid plate has a hole every 10 mm so boards can go anywhere.

Measure your 8-channel relay board's mounting holes (`relay_holes`, centre to
centre) so its four holes line up exactly.

Measure your cable glands' thread size and set the `*_glands` lists. The hole
sizes for PG7, PG9, PG16, M16 and M20 are at the top of the box section.

## 6. Test fit, then print

1. Run `./cad/build.sh fit_test` and print `stl/fit_test_corner.stl`
   (about an hour and a half, 40 g). It's one corner of the panel with the
   corner of the cut-out.
2. Offer it up to the screen from the front. The body should slip through
   the cut-out corner with a little play, and the bezel corner should sit
   in the shallow recess.
3. Too tight? Make `fit` bigger by 0.2. Too loose? Smaller by 0.2. Wrong
   corner shape? Fix `scr_r`. Then print the real thing.
