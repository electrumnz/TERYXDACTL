// Teryx OS: every measurement the printed parts are built from.
//
// All sizes are in millimetres. Change a number here, run cad/build.sh and
// every STL updates. Numbers marked GUESS have not been measured yet; see
// cad/MEASURING.md for how to measure each one.
//
// Directions: X = left/right across the dash, Y = up/down, and the screen
// faces the driver.

// ---------------------------------------------------------------------------
// Printer
// ---------------------------------------------------------------------------
bed_x = 250;            // usable bed width (Bambu P1/A1 = 256, Ender 3 = 220)
bed_y = 250;            // usable bed depth

// ---------------------------------------------------------------------------
// Fasteners
// ---------------------------------------------------------------------------
m3_clear       = 3.4;   // M3 bolt clearance hole
m3_insert_d    = 4.0;   // hole for an M3 brass heat-set insert (check the packet)
m3_insert_deep = 5.7;   // insert length + a bit
m3_head_d      = 6.2;   // M3 socket head, for counterbores
m25_insert_d   = 3.6;   // hole for an M2.5 heat-set insert (Pi standoffs)
m4_clear       = 4.5;   // M4 bolt clearance hole
m5_clear       = 5.5;   // M5 bolt clearance hole (AMPS mount)
pin_d          = 2.0;   // 1.75 mm filament used as alignment pins at split seams
fit            = 0.6;   // gap each side between a part and the thing it holds

// ---------------------------------------------------------------------------
// Touch screen: 10.1" 1280x800 industrial panel-mount monitor, metal case,
// 2.8 kg. It has a thin front bezel, and its body goes through a cut-out
// and is clamped from behind with the supplied clips and screws. It also
// has a wall-bracket (VESA style) pattern on the back.
//
// LISTING = from the AliExpress listing ("Monitor Size 273*192*41mm",
// "Hole Size 217*135mm"). Check these with calipers before the big print.
// GUESS = not on the listing at all; measure it.
// ---------------------------------------------------------------------------
scr_w      = 273;   // LISTING front bezel width
scr_h      = 192;   // LISTING front bezel height
scr_d      = 41;    // LISTING overall depth, front glass to the back of the case
scr_r      = 4;     // GUESS bezel corner radius (0 for square corners)
scr_bezel_t = 6;    // GUESS thickness of the front bezel (the part that sits
                    //       in front of the panel)

// Panel cut-out the body goes through. Must be a little bigger than the
// body behind the bezel. The listing gives 217 x 135; if the body measures
// bigger than that, use the body size (fit is added on top).
panel_cut_w = 217;  // LISTING
panel_cut_h = 135;  // LISTING
panel_cut_r = 1;
clip_room   = 25;   // GUESS clear flat area kept behind the panel round the
                    //       cut-out for the clips and their screws

// Where the cables leave the back of the screen, measured from the centre
// of the back. A hole this size goes through the back plate.
scr_cable_x = 0;        // GUESS + = right when looking at the screen from the front
scr_cable_y = -35;      // GUESS + = up
scr_cable_d = 38;       // big enough to pass the plugs (a VGA plug is about 31 x 16)

// Wall-bracket holes on the back of the screen. These carry most of the
// weight, so bolt them through the back plate.
scr_has_vesa   = true;
scr_vesa       = 75;    // GUESS 75 or 100 square (measure hole centres)
scr_vesa_clear = 4.5;   // GUESS M4 bolts (check the thread)

gasket_t = 2;           // foam tape between the bezel and the panel

// ---------------------------------------------------------------------------
// Dash panel: a flat face with the cut-out, and a deep rim behind it that
// boxes in the screen's body. The back plate closes the back.
// ---------------------------------------------------------------------------
panel_t        = 5;     // panel thickness (the clips take about 1 to 8 mm)
frame_wall     = 4;     // rim wall thickness
frame_flange_w = 12;    // how far the panel sticks out past the bezel
rib_t          = 3;     // stiffening ribs on the back of the panel
rib_d          = 10;    // how far the ribs stand off the panel
frame_split_x  = 0;     // where it is cut if it is too big for the bed

// ---------------------------------------------------------------------------
// Back plate (bolts to the rim, the screen's wall-bracket holes, the Pi box
// and the dash). This carries the screen's weight.
// ---------------------------------------------------------------------------
bp_t       = 6;         // thickness
bp_split_x = 60;        // cut line if too big; kept away from the frame cut so
                        // the two seams overlap and hold each other

// How the back plate fixes to the Teryx. Measure the stock gauge cluster's
// bolt holes (or wherever you will bolt it) relative to where you want the
// centre of the new screen. List as many as you like.
dash_holes   = [[-128, -80], [128, -80], [-128, 80], [128, 80]];  // GUESS
// Keep these outside the screen's body (about +-110 x +-68) so the nuts can go
// on the front of the back plate before the panel goes on.
dash_hole_d  = 6.5;     // GUESS M6 clearance
// Also add a standard AMPS pattern (30 x 38 mm, M5), handy for a RAM ball
// mount or an off-the-shelf bracket while the real mount is worked out.
dash_amps     = true;
dash_amps_pos = [0, 80];   // above the screen body and the Pi box; M5 nuts sit
                           // in hex pockets on the front of the plate

// ---------------------------------------------------------------------------
// Sun hood
// ---------------------------------------------------------------------------
hood_reach  = 70;       // how far the top sticks out past the screen's bezel
hood_tilt   = 8;        // degrees the top tips up from level (sheds water)
hood_side_h = 110;      // how far down the side cheeks run
hood_t      = 2.6;      // wall thickness. Its back strip is clamped between
                        // the frame flange and the back plate, so no extra bolts
hood_split_x = -60;     // cut line if too big for the bed

// ---------------------------------------------------------------------------
// Sealed boxes, shared settings
// ---------------------------------------------------------------------------
box_wall   = 4.0;       // wide enough for the gasket groove
box_floor  = 3.0;
box_r      = 6;         // outside corner radius
lid_t      = 3.0;
groove_w   = 1.8;       // gasket groove (2 mm foam cord, or the printed TPU gasket)
groove_d   = 1.6;
ear_w      = 12;        // mounting ears
ear_hole   = 4.5;       // M4

// Cable gland hole sizes (check your glands)
PG7  = 12.5;            // 3-6.5 mm cable
PG9  = 15.2;            // 4-8 mm cable
M16  = 16.2;
M20  = 20.2;
PG16 = 22.5;            // 10-14 mm cable, or a multi-hole insert

// ---------------------------------------------------------------------------
// Pi 5 box (bolts on the back plate, behind the screen)
// Holds the Pi 5 with the Active Cooler and the AI HAT+ 2 on top, a small
// MCP2515 CAN module on the wall, and the 5V 5A buck.
// Height, from the box floor (2026-11-18):
//   6 standoff + 1.6 Pi board + 16 AI HAT spacers (Raspberry Pi supply 16 mm,
//   made to clear the Active Cooler) + 1.6 HAT board = HAT top at about 25 mm.
//   The HAT's heatsink is about 14 mm tall including its push pins (Raspberry
//   Pi), so call its top about 37 mm. Jumper leads to the CAN module plug onto
//   the stacking header's pins on top of the HAT: about 45 mm.
//   56 leaves about 11 mm over the leads and 19 mm of air over the heatsink for
//   the lid fan. The old CAN HAT can't stack over the heatsink, hence the module.
//   CHECK on the real parts before printing.
// ---------------------------------------------------------------------------
pi_box_in   = [130, 105, 56];    // inside size: X, Y, height away from the back plate
pi_box_pos  = [0, -10];         // centre of the box on the back plate
pi_holes    = [58, 49];         // Pi 5 mounting hole spacing (Raspberry Pi spec)
pi_board    = [85, 56];
pi_standoff = 6;                // height of the Pi off the floor
pi_pos      = [-18, 20];         // Pi centre inside the box (leaves room for the buck)
pi_fan      = 30;               // lid fan size (30 or 40), 0 for no fan
pi_fan_hole = 24;               // fan screw spacing (30 mm fan = 24, 40 mm = 32)
// Glands go in the bottom wall so water runs off them
pi_glands   = [PG9, PG9, PG7, PG7];   // 12V in, CAN, camera, spare

// ---------------------------------------------------------------------------
// Pico 2 control box (Pico, MCP2515, MCP23017, ADS1115, opto board,
// MOSFET boards, 5V 2A buck). Boards screw to a printed grid plate.
// ---------------------------------------------------------------------------
cb_box_in = [170, 120, 45];     // GUESS lay the boards out on paper first
cb_glands = [PG9, PG9, PG16, PG16, PG7];   // 12V, CAN, inputs, outputs, USB to Pi

// ---------------------------------------------------------------------------
// Relay box (8-channel relay board and the three BTS7960 drivers)
// ---------------------------------------------------------------------------
rb_box_in    = [185, 125, 55];  // GUESS
rb_glands    = [PG9, PG16, PG16, PG16, M20];
relay_holes  = [132, 50];       // GUESS common 8-channel board hole spacing
relay_board  = [138, 56];

// Grid plate for the control and relay boxes: a hole every grid_pitch mm
// that an M3 self-tapping screw or M2.5 bolt can bite into.
grid_pitch  = 10;
grid_hole   = 2.6;
grid_t      = 3;
grid_post_h = 5;    // gap under the plate for wires and solder joints
