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
// Touch screen (10.1" waterproof HDMI + USB)
// Measure the screen's own housing, not the glass.
// ---------------------------------------------------------------------------
scr_w      = 257;   // GUESS outer width of the screen housing
scr_h      = 167;   // GUESS outer height of the screen housing
scr_d      = 28;    // GUESS thickness, front glass to the deepest point at the back
                    //       (not counting cables or plugs)
scr_r      = 5;     // GUESS corner radius of the housing (0 for square corners)

// The part of the front you need to see. The frame lip covers everything
// outside this, so measure the black border round the picture and stay
// a few mm outside the lit area.
scr_view_w     = 226;   // GUESS (1024x600 panels light up about 223 x 126)
scr_view_h     = 132;   // GUESS
scr_view_off_x = 0;     // GUESS picture centre offset from housing centre, + = right
scr_view_off_y = 0;     // GUESS picture centre offset from housing centre, + = up

// Where the cables leave the back of the screen, measured from the centre
// of the back. A hole this size goes through the back plate.
scr_cable_x = 0;        // GUESS + = right when looking at the screen from the front
scr_cable_y = -35;      // GUESS + = up
scr_cable_d = 32;       // big enough to pass the HDMI plug (about 21 x 11)

// VESA holes on the back of the screen, if it has them
scr_has_vesa   = false; // GUESS
scr_vesa       = 75;    // 75 or 100 square
scr_vesa_clear = 4.5;   // M4

gasket_t = 2;           // foam tape between the screen face and the frame lip

// ---------------------------------------------------------------------------
// Front frame (holds the screen)
// ---------------------------------------------------------------------------
frame_wall     = 3.2;   // side wall thickness
frame_front_t  = 3.0;   // thickness of the lip in front of the screen
frame_flange_w = 10;    // flange round the back, where the bolts go
frame_flange_t = 9;     // flange thickness (must be more than hood_t + m3_insert_deep)
frame_r_extra  = 3;     // extra outer corner rounding
frame_split_x  = 0;     // where the frame is cut if it is too big for the bed

// ---------------------------------------------------------------------------
// Back plate (bolts to the frame, the Pi box and the dash)
// ---------------------------------------------------------------------------
bp_t       = 5;         // thickness
bp_split_x = 60;        // cut line if too big; kept away from the frame cut so
                        // the two seams overlap and hold each other

// How the back plate fixes to the Teryx. Measure the stock gauge cluster's
// bolt holes (or wherever you will bolt it) relative to where you want the
// centre of the new screen. List as many as you like.
dash_holes   = [[-95, -60], [95, -60], [-95, 55], [95, 55]];  // GUESS
dash_hole_d  = 6.5;     // GUESS M6 clearance
// Also add a standard AMPS pattern (30 x 38 mm, M5), handy for a RAM ball
// mount or an off-the-shelf bracket while the real mount is worked out.
dash_amps     = true;
dash_amps_pos = [0, 25];

// ---------------------------------------------------------------------------
// Sun hood
// ---------------------------------------------------------------------------
hood_reach  = 70;       // how far the top sticks out past the screen face
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
// Holds the Pi 5, the CAN HAT and the 5V 5A buck.
// ---------------------------------------------------------------------------
pi_box_in   = [130, 105, 46];    // inside size: X, Y, height away from the back plate
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
