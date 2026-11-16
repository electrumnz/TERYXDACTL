# What to measure

Every number below lives in [`measurements.scad`](measurements.scad). Change
it there, run `./cad/build.sh`, and print the fit test before anything big.

You need: digital calipers (or a good steel rule), a tape measure, masking
tape and a marker. Measure twice, write it down, and round **up** to the next
0.5 mm. The model already adds `fit` (0.6 mm) of clearance each side, so don't
add your own.

## 1. The screen (10 minutes, on the bench)

Lay the screen face down on a towel.

| Setting | How to measure it |
|---|---|
| `scr_w` | Full width of the housing, left edge to right edge. Measure at the top, middle and bottom and use the biggest |
| `scr_h` | Full height of the housing, same way |
| `scr_d` | Thickness from the front glass to the deepest point of the back (a bump or the cable boot counts, the cable itself doesn't). Lay it face down on a flat table and measure up to the highest point |
| `scr_r` | Corner radius. Hold a coin on the corner: a 10c coin is about 10 mm across (5 mm radius), 20c about 22 mm (11 mm radius). Or 0 if the corners are square |
| `scr_view_w`, `scr_view_h` | Turn it on with a white picture. Measure the lit area, then add 2 to 3 mm. The frame lip covers everything outside this |
| `scr_view_off_x`, `scr_view_off_y` | If the lit area isn't centred in the housing (often the bottom border is wider), measure how far the centre of the picture is from the centre of the housing. Right and up are plus |
| `scr_cable_x`, `scr_cable_y` | Looking at the **front** of the screen, where do the cables come out of the back? Measure from the centre of the back, right and up are plus |
| `scr_cable_d` | Hole size for the cables. Must pass the biggest plug (HDMI plug is about 21 x 11 mm, so 32 mm is plenty). Bigger if the screen has a fixed power lead with a plug on it |
| `scr_has_vesa`, `scr_vesa` | Are there 4 threaded holes in a square on the back? 75 mm or 100 mm apart? If so set `scr_has_vesa = true` and they get bolted through the back plate too |

Check the listing's spec sheet too if you can open it: look for "outline
dimension" and "active area". Use your own measurement if they differ.

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
5. Check the back of the frame won't hit anything: the back plate is
   `bp_t` (5 mm) thick and the Pi box sticks out 52 mm behind that (more with
   the fan cowl). If there isn't room straight behind, change `pi_box_pos`
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
   (about an hour, 25 g).
2. Push the corner of the screen into it. It should go in by hand with a
   little play, the lip should cover the edge without touching the picture,
   and the back of the screen should sit about level with the back of the
   flange.
3. Too tight? Make `fit` bigger by 0.2. Too loose? Smaller by 0.2. Wrong
   corner shape? Fix `scr_r`. Then print the real thing.
