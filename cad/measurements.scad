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
M12V = 12.2;            // M12 breather vent plug (membrane vent)

// ---------------------------------------------------------------------------
// Pi 5 box (bolts on the back plate, behind the screen)
// Sealed for wash-downs (splash and hose spray, about IP65, not for dunking).
// No vents and no fan: the lid is a 3 mm aluminium plate (cut from the DXF with
// the back plate) with a finned heatsink bolted on the outside. Heat goes:
// Pi chip -> thermal pad -> aluminium pillar -> lid plate -> heatsink -> air.
// See docs/pi-box-cooling.md for the sums and the parts.
// Height, from the box floor (2026-11-18):
//   6 standoff + 1.6 Pi board + 16 AI HAT spacers (Raspberry Pi supply 16 mm,
//   made to clear the Active Cooler) + 1.6 HAT board = HAT top at about 25 mm.
//   The HAT's heatsink is about 14 mm tall including its push pins (Raspberry
//   Pi), so call its top about 37 mm. Jumper leads to the CAN module plug onto
//   the stacking header's pins on top of the HAT: about 45 mm.
//   56 inside, less the 2 mm printed liner under the lid plate, leaves about
//   9 mm over the leads. Kept so the AI HAT+ 2 still fits later (then the
//   pillar comes out, the Active Cooler goes on the Pi and a short pillar goes
//   from the HAT's chip to the lid). The old CAN HAT can't stack over the HAT,
//   hence the module.
//   CHECK on the real parts before printing.
// ---------------------------------------------------------------------------
pi_box_in   = [130, 105, 56];    // inside size: X, Y, height away from the back plate
pi_box_pos  = [0, -10];         // centre of the box on the back plate
pi_holes    = [58, 49];         // Pi 5 mounting hole spacing (Raspberry Pi spec)
pi_board    = [85, 56];
pi_standoff = 6;                // height of the Pi off the floor
pi_pos      = [-18, 20];         // Pi centre inside the box (leaves room for the buck)
// Glands go in the bottom wall so water runs off them. The last hole is for an
// M12 breather (a vent plug with a membrane): lets the air in the box breathe as
// it heats and cools, so it doesn't suck water past the seals.
pi_glands   = [PG9, PG9, PG7, PG7, M12V];   // 12V in, CAN, camera, spare, breather

// Lid and heatsink (2026-11-18, Sam: "heatsink on outside of box")
pi_lid_metal = true;            // aluminium lid plate + heatsink. false = old all-printed lid
lid_plate_t  = 3;               // aluminium lid plate, same 3 mm sheet as the back plate
liner_t      = 2;               // printed liner under the lid plate (holds the SSD and 4G board)
// Heatsink: Fischer Elektronik SK 92/100 SA, 100 x 100 x 40 mm, black anodised,
// 1.4 K/W (element14 listing). Any 100 x 100 x 40 finned block fits the same holes.
hs_size      = [100, 100, 40];  // X, Y, fin height. Fins run along Y: mount the box
                                // so the fin channels run up and down (hot air rises out)
hs_base      = 5;               // GUESS base thickness. CHECK: needs 5 mm for blind M3 threads
hs_pos       = [0, 0];          // heatsink centre on the lid, box coordinates
// M3 screws from inside the box, through the liner and the lid plate, into
// tapped blind holes in the heatsink base. Placed clear of the SSD and 4G board.
hs_screws    = [[-44, 44], [44, 44], [-44, -3], [8, -3]];
// Pi chip (BCM2712) centre, box coordinates. GUESS from photos: about 29 mm in
// from the USB-C end and 31 mm up from the HDMI edge. CHECK on the real Pi and
// mark it on the lid plate before drilling the pillar hole.
soc_pos      = [pi_pos[0] - pi_board[0] / 2 + 29, pi_pos[1] - pi_board[1] / 2 + 31];
soc_h        = 2.4;             // GUESS chip height above the board, with its metal lid
pillar_w     = 20;              // 20 x 20 mm solid aluminium bar
pad_t        = 1.0;             // thermal pad on the chip (T-Global PC94, 1 mm, 4 W/mK)
pad_squash   = 0.3;             // how much the pad gets squashed when the lid goes on
// Video SSD for sentry and dashcam clips (docs/sentry.md): Kingston XS1000, 69.54 x 32.58
// x 13.5 mm (Kingston datasheet). It sits in a cradle on the inside of the lid, over the
// free strip below the Pi, so it's clear of the AI HAT stack and the pillar.
// A short right-angle USB-C to USB-A lead goes to one of the Pi's USB 3 ports. Held in with a
// cable tie through the two slots. Another small USB SSD fits if it's within ssd_size.
// The 4G board (A7670SA) is on the liner too, right of the Pi, with its aerials outside
// on SMA bulkheads: see "Pi box extras" at the end of this file.
ssd_size    = [70.2, 33.2, 13.5];   // XS1000 plus 0.6 mm play in X and Y
ssd_pos     = [-18, -30];           // centre, box coordinates (same X and Y as the box)
ssd_on      = true;                 // false = plain lid

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

// ---------------------------------------------------------------------------
// Pi box extras: micro HDMI clamp and the 4G board
// ---------------------------------------------------------------------------
// Screen's micro HDMI lead. Micro HDMI plugs work loose with vibration, so the
// plug sits on a cradle printed into the box floor and two cable ties hold it:
// one round the plug's moulding (stops it rocking) and one round the cable a bit
// further on (takes any pull off the plug). Leave a small loop of slack between
// the second tie and the floor hole.
// The Pi sits with its HDMI edge facing the bottom wall (-Y), USB-C on the left.
// Port spots from the Raspberry Pi 5 mechanical drawing (datasheets.raspberrypi.com):
// HDMI0 centre 25.8 mm from the board's left edge, ports flush with the edge,
// about 3.4 mm tall. Use HDMI0 (the one next to USB-C).
hdmi_clamp   = true;              // false = no cradle
pi_hdmi0_x   = 25.8;              // Raspberry Pi drawing
pi_pcb_t     = 1.6;               // Pi board thickness
hdmi_port_h  = 3.4;               // Raspberry Pi drawing, height of the socket
// Official Raspberry Pi micro HDMI to HDMI cable, Pi end. Raspberry Pi don't
// publish the moulding size: GUESS from a similar official adaptor's micro end
// (11.26 x 8.16 mm). CHECK with calipers when the cable turns up.
hdmi_plug    = [11.3, 8.2, 22];   // GUESS moulding width, thickness, length out from the board edge
hdmi_cable_d = 5;                 // cable OD (reseller listing: 5 mm)
hdmi_pad     = 1.0;               // gap left under the plug for foam tape, so the
                                  // cradle never pushes the plug up

// 4G board inside the Pi box, under the lid, over the strip right of the Pi
// (clear of the pillar, the SSD cradle and the AI HAT's leads).
// Board: SIMCom A7670SA core board (AliExpress, must list B28, see the shopping
// list). SIMCom's manual gives 44.45 x 31.75 x 12.44 mm including the header
// pins, micro SIM holder and one IPEX (u.FL) aerial socket. It hangs parts-down
// on four standoffs, so with the lid off and flipped the SIM slot is right there.
// The header pins point up at the lid: solder the wires on (or use right-angle
// plugs) so they fit in the modem_gap. Its UART goes to the Pi or a spare Pico.
// Beside it on the lid: a pad for the small buck that feeds it (MP1584, 22 x 17
// mm, set to about 3.8-4.0 V) and a saddle for the 1000 uF capacitor, each held
// with a cable tie through a tunnel. One u.FL to SMA lead goes to an SMA
// bulkhead in the right-hand wall, so the aerial sits outside the box.
modem_on       = true;              // false = no 4G board
modem_board    = [31.75, 44.45];    // X, Y as it sits in the box (long side along Y)
modem_holes    = [25.75, 38.45];    // GUESS holes 3 mm in from each edge. CHECK on the board
modem_hole_d   = 3.2;               // hole for an M2 heat-set insert (or 2.2 for an M2 self-tapper)
modem_pos      = [39, 10];          // board centre, box coordinates
modem_gap      = 12;                // lid to the back of the board (room for the header pins)
modem_buck     = [17, 22];          // MP1584 module, X and Y
modem_buck_pos = [39, -37.5];
modem_cap      = [10.5, 21];        // 1000 uF capacitor, diameter and length (16 V is usually 10 x 20)
modem_cap_pos  = [39, -20];         // lies along X
// SMA bulkheads in the right-hand wall: [y, z, ring] each. y along the wall,
// z up from the box floor's underside. ring = 1 engraves a ring round the hole on
// the outside, so you can tell them apart: plain hole = 4G, ringed and higher = GPS
// (for the A7670SA FASE/GNSS board's active GPS aerial). Delete the GPS row if the
// board has no GPS.
sma_holes      = [[4, 38, 0],       // 4G (LTE) aerial
                  [22, 48, 1]];     // GPS aerial, ringed
sma_hole       = 6.6;               // 1/4"-36 SMA bulkhead thread is 6.35 mm
