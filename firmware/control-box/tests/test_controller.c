#define _GNU_SOURCE
// Unit tests for the control box logic, run against the host plant model with
// a fake clock. Each test drives the dash and Shinegle frames by hand.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "config.h"
#include "controller.h"
#include "../src/host/plant.h"

static int failures, checks;
#define CHECK(cond) do { checks++; if (!(cond)) { failures++; \
    printf("  FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); } } while (0)

// ---- Test rig ------------------------------------------------------------------
typedef struct {
    controller_t c;
    plant_t p;
    cb_out_t out;
    cb_in_t in;
    uint32_t t;
    bool dash;              // send heartbeats
    bool shinegle;          // send speed
    uint16_t speed_x10;
    uint8_t dir;
    int8_t hold_tray, hold_winch;
    uint8_t timed_s;        // 0x703 byte 3, 0 = plain hold
    bool armed;
    bool holding;           // send 0x703
    bool sentry;            // heartbeat says DASH_SENTRY instead of DASH_RUNNING
    can_frame_t sent[96];
    int nsent;
    uint8_t max_relays_both_winch;  // set if in and out were ever on together
} rig_t;

static rig_t R;

static void on_send(const can_frame_t *f, void *u) {
    (void)u;
    if (R.nsent < 96) R.sent[R.nsent++] = *f;
    else { memmove(R.sent, R.sent + 1, sizeof(R.sent[0]) * 95); R.sent[95] = *f; }
}

static void frame(uint32_t id, uint8_t dlc, const uint8_t *d) {
    can_frame_t f = {.id = id, .dlc = dlc};
    memcpy(f.data, d, dlc);
    ctl_on_frame(&R.c, &f, R.t, on_send, NULL);
}

static void rig_init(void) {
    memset(&R, 0, sizeof(R));
    plant_init(&R.p);
    ctl_init(&R.c, NULL, false, false, 0);
    R.dash = true;
    R.shinegle = true;
}

// Run for ms milliseconds of fake time.
static void run(uint32_t ms) {
    for (uint32_t e = 0; e < ms; e += TICK_MS) {
        R.t += TICK_MS;
        if (R.t % 100 == 0) {
            if (R.dash) { uint8_t d[2] = {(uint8_t)(R.t / 100), R.sentry ? DASH_SENTRY : DASH_RUNNING}; frame(CAN_ID_PI_HEARTBEAT, 2, d); }
            if (R.shinegle) { uint8_t d[4] = {(uint8_t)R.speed_x10, (uint8_t)(R.speed_x10 >> 8), R.dir, 0}; frame(CAN_ID_MC_SPEED, 4, d); }
            if (R.holding) {
                uint8_t d[4] = {(uint8_t)R.hold_tray, (uint8_t)R.hold_winch, R.armed ? HOLD_FLAG_WINCH_ARMED : 0, R.timed_s};
                frame(CAN_ID_PI_HOLD, R.timed_s ? 4 : 3, d);
            }
        }
        plant_step(&R.p, &R.out, TICK_MS / 1000.0);
        plant_inputs(&R.p, &R.in, R.t);
        ctl_tick(&R.c, &R.in, &R.out, on_send, NULL);
        if ((R.out.relays & BIT(R_WINCH_IN)) && (R.out.relays & BIT(R_WINCH_OUT))) R.max_relays_both_winch = 1;
        for (int i = 0; i < ACT_COUNT; i++)
            if (R.out.act_dir[i] != 0 && R.out.act_duty[i] == 0) R.max_relays_both_winch = 2;
    }
}

static void drive(uint8_t fwd, uint8_t diff) {
    uint8_t d[8] = {fwd, diff};
    frame(CAN_ID_PI_DRIVE, 8, d);
}

static void lights(uint8_t f1, uint8_t f2, uint8_t f3, uint8_t f4, uint8_t in, uint8_t fx, uint8_t flags) {
    uint8_t d[8] = {f1, f2, f3, f4, in, fx, flags, 0};
    frame(CAN_ID_PI_LIGHTS, 8, d);
}

static void setting(uint8_t key, uint16_t v) {
    uint8_t d[4] = {key, 0, (uint8_t)v, (uint8_t)(v >> 8)};
    frame(CAN_ID_PI_SETTING, 4, d);
}

static const can_frame_t *last_sent(uint32_t id) {
    for (int i = R.nsent - 1; i >= 0; i--) if (R.sent[i].id == id) return &R.sent[i];
    return NULL;
}

static uint8_t reject_reason(void) { return R.c.reject_reason; }
static bool fault(int bit) { return (R.c.faults & BIT(bit)) != 0; }

// ---- Tests -----------------------------------------------------------------------

static void test_boot_all_off(void) {
    rig_init();
    R.dash = false;
    run(50);
    CHECK(R.out.light[0] == 0 && R.out.light[4] == 0);
    for (int i = 0; i < ACT_COUNT; i++) CHECK(R.out.act_dir[i] == 0);
    CHECK((R.out.relays & (BIT(R_WINCH_IN) | BIT(R_WINCH_OUT) | BIT(R_REAR))) == 0);
    CHECK(R.out.relays & BIT(R_ACCESSORY));  // key is on in the bench model
    CHECK(R.out.relays & BIT(R_POWER_HOLD));
    run(200);
    const can_frame_t *s = last_sent(CAN_ID_PICO_STATUS);
    CHECK(s && (s->data[4] & 0x03) == CB_STATE_BOOT);
    CHECK(s && (s->data[4] & STATE_BIT_ON_DEFAULTS));
    run(3000);  // past the boot grace with no dash: failsafe
    s = last_sent(CAN_ID_PICO_STATUS);
    CHECK(s && (s->data[4] & 0x03) == CB_STATE_FAILSAFE);
    CHECK(fault(FAULT_DASH_LINK));
}

static void test_4wd_speed_rule_and_change_only(void) {
    rig_init();
    setting(SET_SHIFT_WAIT_MS, 0);  // waiting off: the old refuse-at-once rule
    run(300);
    drive(REQ_2WD, 0);  // known position first (unknown homes on resend, see below)
    run(3500);
    CHECK(R.c.fwd.state == FWD_2WD);
    R.speed_x10 = 200;  // 20 km/h
    run(300);
    drive(REQ_4WD, 0);
    run(50);
    CHECK(reject_reason() == REJ_TOO_FAST);
    CHECK(R.c.fwd.moving == false);
    // Dash resends the same request every second while we slow down.
    R.speed_x10 = 0;
    for (int i = 0; i < 3; i++) { drive(REQ_4WD, 0); run(1000); }
    CHECK(R.c.fwd.state != FWD_4WD);  // refused request is not done later
    // A fresh request (a change) now works.
    drive(REQ_2WD, 0);
    run(100);
    drive(REQ_4WD, 0);
    run(100);
    CHECK(R.c.fwd.moving);
    CHECK(R.c.fwd.state == FWD_TO_4WD);
    run(2500);
    CHECK(R.c.fwd.state == FWD_4WD);
    CHECK(!fault(FAULT_4WD_TIMEOUT));
    CHECK(R.p.pos[ACT_4WD] > 0.99);
}

static void test_4wd_homes_when_unknown(void) {
    rig_init();
    R.shinegle = false;  // dash asks before the Shinegle is heard
    run(300);
    drive(REQ_4WD, 0);
    run(50);
    CHECK(reject_reason() == REJ_SPEED_UNKNOWN);
    CHECK(R.c.fwd.state == FWD_UNKNOWN);
    uint8_t rc = R.c.reject_count;
    drive(REQ_4WD, 0);   // resend while still unsafe: no new reject
    run(50);
    CHECK(R.c.reject_count == rc);
    R.shinegle = true;
    run(300);
    drive(REQ_4WD, 0);   // resend once speed is known: homes to 4WD
    run(2500);
    CHECK(R.c.fwd.state == FWD_4WD);
    CHECK(R.c.reject_count == rc);
}

static void test_4wd_stall(void) {
    rig_init();
    run(300);
    R.p.faults = BENCH_STALL_4WD;
    drive(REQ_4WD, 0);
    run(1000);
    CHECK(R.c.fwd.state == FWD_FAULT);
    CHECK(fault(FAULT_4WD_OVERCURRENT));
    CHECK(R.out.act_dir[ACT_4WD] == 0);
}

static void test_diff_closed_loop(void) {
    rig_init();
    setting(SET_SHIFT_WAIT_MS, 0);
    R.speed_x10 = 100;  // 10 km/h, under the 15 km/h limit for adding lock
    run(300);
    CHECK(R.c.diff.pct == 0);
    drive(DRIVE_NO_CHANGE, 100);
    run(4000);
    CHECK(R.c.diff.pct >= 97);
    CHECK(!R.c.diff.moving);
    const can_frame_t *a = last_sent(CAN_ID_PICO_ACT);
    CHECK(a && a->data[7] == 100);
    // Unlocking works on the move (Kawasaki: unlock after crossing the obstacle)
    R.speed_x10 = 200;
    run(200);
    drive(DRIVE_NO_CHANGE, 0);
    run(4000);
    CHECK(R.c.diff.pct <= 3);
    CHECK(!R.c.diff.moving);
    // ...but locking again at 20 km/h is refused
    drive(DRIVE_NO_CHANGE, 100);
    run(100);
    CHECK(reject_reason() == REJ_TOO_FAST);
    CHECK(!R.c.diff.moving);
    CHECK(R.c.diff.target_pct == R.c.diff.pct);
}

static void test_diff_jam(void) {
    rig_init();
    run(300);
    R.p.faults = BENCH_JAM_DIFF;
    drive(DRIVE_NO_CHANGE, 80);
    run(2000);
    CHECK(!R.c.diff.moving);
    CHECK(fault(FAULT_DIFF_POT_STUCK) || fault(FAULT_DIFF_OVERCURRENT));
}

static void test_diff_pot_disconnected(void) {
    rig_init();
    run(300);
    R.p.faults = BENCH_POT_DISCONNECT;
    run(50);
    CHECK(R.c.diff.pct == PCT_UNKNOWN);
    drive(DRIVE_NO_CHANGE, 60);
    run(100);
    CHECK(!R.c.diff.moving);
    CHECK(reject_reason() == REJ_FAULT);
}

static void test_tray_hold_to_run(void) {
    rig_init();
    run(300);
    CHECK(R.in.din & BIT(IN_TRAY_DOWN));
    R.holding = true;
    R.hold_tray = 1;
    run(3000);
    CHECK(R.c.tray.dir == 1);
    double pos = R.p.pos[ACT_TRAY];
    CHECK(pos > 0.1);
    // Let go: stops within the hold timeout
    R.holding = false;
    run(400);
    CHECK(R.c.tray.dir == 0);
    CHECK(R.out.act_dir[ACT_TRAY] == 0);
    // Hold until it hits the top limit
    R.holding = true;
    run(20000);
    CHECK(R.in.din & BIT(IN_TRAY_UP));
    CHECK(R.c.tray.dir == 0);
    const can_frame_t *a = last_sent(CAN_ID_PICO_ACT);
    CHECK(a && a->data[2] == TRAY_UP && a->data[6] == 100);
    // Up again at the limit: refused
    R.holding = false;
    run(400);
    R.holding = true;
    run(200);
    CHECK(reject_reason() == REJ_AT_LIMIT);
}

static void test_tray_needs_stopped(void) {
    rig_init();
    R.speed_x10 = 30;
    run(300);
    R.holding = true;
    R.hold_tray = 1;
    run(500);
    CHECK(R.c.tray.dir == 0);
    CHECK(reject_reason() == REJ_NOT_STOPPED);
    // Shinegle goes quiet: speed unknown also blocks
    R.speed_x10 = 0;
    R.shinegle = false;
    R.holding = false;
    run(1000);
    R.holding = true;
    run(300);
    CHECK(R.c.tray.dir == 0);
    CHECK(reject_reason() == REJ_SPEED_UNKNOWN);
    CHECK(fault(FAULT_SPEED_UNKNOWN));
}

static void test_tray_moving_stops_when_speed_rises(void) {
    rig_init();
    run(300);
    R.holding = true;
    R.hold_tray = 1;
    run(1000);
    CHECK(R.c.tray.dir == 1);
    R.speed_x10 = 20;
    run(200);
    CHECK(R.c.tray.dir == 0);
}

static void test_tray_jam_and_broken_limit(void) {
    rig_init();
    run(300);
    R.p.faults = BENCH_JAM_TRAY;
    R.holding = true;
    R.hold_tray = 1;
    run(1000);
    CHECK(R.c.tray.dir == 0);
    CHECK(fault(FAULT_TRAY_OVERCURRENT));
    // Broken limit wire: both limits read "at limit"
    rig_init();
    run(300);
    R.p.force_mask = BIT(IN_TRAY_UP);
    R.p.force_bits = BIT(IN_TRAY_UP);
    R.holding = true;
    R.hold_tray = 1;
    run(500);
    CHECK(R.c.tray.dir == 0);
    CHECK(fault(FAULT_TRAY_LIMIT_SWITCH));
}

static void test_lost_dash_stops_motion_keeps_lights(void) {
    rig_init();
    run(300);
    lights(200, 200, 200, 200, 50, FX_NONE, 0);
    R.holding = true;
    R.hold_tray = 1;
    R.armed = true;
    run(1000);
    CHECK(R.c.tray.dir == 1);
    CHECK(R.c.winch.armed);
    R.dash = false;   // Pi crashes; hold frames keep coming from a stuck sender
    run(700);
    CHECK(R.c.tray.dir == 0);
    CHECK(!R.c.winch.armed);
    CHECK(R.out.light[0] == 200 && R.out.light[4] == 50);
    CHECK(fault(FAULT_DASH_LINK));
}

static void test_winch_rules(void) {
    rig_init();
    run(300);
    // Not armed: refused
    R.holding = true;
    R.hold_winch = 1;
    run(300);
    CHECK((R.out.relays & BIT(R_WINCH_IN)) == 0);
    CHECK(reject_reason() == REJ_NOT_ARMED);
    // Arm and winch in
    R.armed = true;
    R.hold_winch = 0;
    run(200);
    CHECK(R.c.winch.armed);
    R.hold_winch = 1;
    run(300);
    CHECK(R.out.relays & BIT(R_WINCH_IN));
    // Swap straight to out: must pass through a dead time with both off
    R.hold_winch = -1;
    bool gap = false;
    for (int i = 0; i < 60; i++) {
        run(TICK_MS);
        if (!(R.out.relays & (BIT(R_WINCH_IN) | BIT(R_WINCH_OUT)))) gap = true;
    }
    CHECK(gap);
    CHECK(R.out.relays & BIT(R_WINCH_OUT));
    CHECK(R.max_relays_both_winch == 0);
    // Tray is interlocked while winching
    R.hold_tray = 1;
    run(300);
    CHECK(R.c.tray.dir == 0);
    CHECK(reject_reason() == REJ_INTERLOCK);
    R.hold_tray = 0;
    // Speed rises: disarm
    R.speed_x10 = 50;
    run(200);
    CHECK(!R.c.winch.armed);
    CHECK((R.out.relays & (BIT(R_WINCH_IN) | BIT(R_WINCH_OUT))) == 0);
}

static void test_winch_auto_disarm(void) {
    rig_init();
    run(300);
    setting(SET_WINCH_AUTO_DISARM_S, 10);
    R.holding = true;
    R.armed = true;
    run(300);
    R.holding = false;  // arm, then nothing
    CHECK(R.c.winch.armed);
    run(9000);
    CHECK(R.c.winch.armed);
    run(1500);
    CHECK(!R.c.winch.armed);
}

static void test_winch_remote_has_priority(void) {
    rig_init();
    run(300);
    R.holding = true;
    R.armed = true;
    R.hold_winch = 1;
    R.p.force_mask = BIT(IN_WINCH_REMOTE);
    R.p.force_bits = BIT(IN_WINCH_REMOTE);
    run(500);
    CHECK((R.out.relays & BIT(R_WINCH_IN)) == 0);
    CHECK(reject_reason() == REJ_REMOTE_IN_USE);
}

static bool winch_in(void) { return (R.out.relays & BIT(R_WINCH_IN)) != 0; }

static void test_winch_timed_pull(void) {
    rig_init();
    run(300);
    R.holding = true;
    R.armed = true;
    run(200);
    CHECK(R.c.winch.armed);
    // "Pull for 5 s": the dash keeps sending, the Pico stops it on time by itself
    R.hold_winch = 1;
    R.timed_s = 5;
    run(4500);
    CHECK(winch_in());
    run(800);
    CHECK(!winch_in());
    run(3000);          // frames still coming: stays off, no restart
    CHECK(!winch_in());
    // Release and press again: a new pull
    R.hold_winch = 0;
    run(300);
    R.hold_winch = 1;
    run(1000);
    CHECK(winch_in());
    // STOP: the dash sends 0, it stops straight away
    R.hold_winch = 0;
    run(100);
    CHECK(!winch_in());
    // Too long a pull is capped at the Pico's own max (setting 21)
    setting(SET_WINCH_TIMED_MAX_S, 3);
    R.hold_winch = 1;
    R.timed_s = 60;
    run(2800);
    CHECK(winch_in());
    run(500);
    CHECK(!winch_in());
    // Dash dies mid pull: stops within the hold timeout, not at the end of the pull
    R.hold_winch = 0;
    run(300);
    R.timed_s = 3;
    R.hold_winch = 1;
    run(1000);
    CHECK(winch_in());
    R.holding = false;
    run(400);
    CHECK(!winch_in());
    // Handheld remote takes over mid pull: dash pull is over, needs a new press
    R.holding = true;
    R.hold_winch = 0;
    run(300);
    R.hold_winch = 1;
    run(1000);
    CHECK(winch_in());
    R.p.force_mask = BIT(IN_WINCH_REMOTE);
    R.p.force_bits = BIT(IN_WINCH_REMOTE);
    run(300);
    CHECK(!winch_in());
    R.p.force_mask = 0;
    R.p.force_bits = 0;
    run(1000);
    CHECK(!winch_in());
    CHECK(R.max_relays_both_winch == 0);
}

static void lights2(uint8_t lo, uint8_t hi, uint8_t tail, uint8_t beacon, uint8_t show) {
    uint8_t d[8] = {lo, hi, tail, 0, 0, beacon, show, 0};
    frame(CAN_ID_PI_LIGHTS2, 8, d);
}

static void test_lamps_and_show(void) {
    rig_init();
    run(300);
    // Moving: low beam asked at 40 % comes out full, tails follow
    R.speed_x10 = 200;
    lights2(100, 0, 0, 0, SHOW_NONE);
    run(100);
    CHECK(R.out.lamp[LP_HEAD_L_LOW] == 255 && R.out.lamp[LP_HEAD_R_LOW] == 255);
    CHECK(R.out.lamp[LP_TAIL_L] == 255 && R.out.lamp[LP_BRAKE_L] == 0);
    CHECK(R.out.lamp_enable);
    // A show asked for on the move is refused
    lights2(100, 0, 0, 0, SHOW_PARTY);
    run(500);
    CHECK(!R.c.lout.show_running && R.c.lout.show_blocked);
    // Stopped but no park brake: still refused
    R.speed_x10 = 0;
    run(200);
    CHECK(!R.c.lout.show_running);
    // Stopped, park brake on: dims, and the show runs
    R.p.force_mask = BIT(IN_PARK);
    R.p.force_bits = BIT(IN_PARK);
    lights2(100, 0, 0, 0, SHOW_NONE);
    run(100);
    CHECK(R.out.lamp[LP_HEAD_L_LOW] == 100);
    lights2(100, 100, 0, 0, SHOW_PARTY);
    run(100);
    CHECK(R.c.lout.show_running);
    // Low and high never together, brake always full, through a whole show
    bool both = false, brake_low = false;
    R.p.force_mask = BIT(IN_PARK) | BIT(IN_BRAKE);
    R.p.force_bits = BIT(IN_PARK) | BIT(IN_BRAKE);
    for (int i = 0; i < 400; i++) {
        run(TICK_MS);
        both |= R.out.lamp[LP_HEAD_L_LOW] && R.out.lamp[LP_HEAD_L_HIGH];
        brake_low |= R.out.lamp[LP_BRAKE_L] != 255 || R.out.lamp[LP_BRAKE_R] != 255 || R.out.lamp[LP_TRAILER_STOP] != 255;
    }
    CHECK(!both && !brake_low);
    // 0x717 reports it
    const can_frame_t *f = last_sent(CAN_ID_PICO_LIGHTS2);
    CHECK(f && (f->data[7] & LIGHTS2_FLAG_SHOW_RUNNING) && (f->data[2] >> 4) == 15);   // brake_l nibble
    // It rolls: the show stops on the next speed frame
    R.speed_x10 = 30;
    run(100);
    CHECK(!R.c.lout.show_running);
    // Beacon flashes at 3 Hz while driving
    R.p.force_mask = 0;
    lights2(0, 0, 0, 200, SHOW_NONE);
    int rises = 0; uint8_t prev = 0;
    for (int i = 0; i < (int)(3000 / TICK_MS); i++) {
        run(TICK_MS);
        if (!prev && R.out.lamp[LP_BEACON]) rises++;
        prev = R.out.lamp[LP_BEACON];
    }
    CHECK(rises >= 8 && rises <= 10);
    // Dash gone with the key on: low beams and tails on by themselves
    lights2(0, 0, 0, 0, SHOW_NONE);
    R.dash = false;
    run(1000);
    CHECK(R.out.lamp[LP_HEAD_L_LOW] == 255 && R.out.lamp[LP_TAIL_R] == 255);
}

static void test_lights_and_relays(void) {
    rig_init();
    run(300);
    // Bars 1-2 dim, 3-4 and interior on/off only
    setting(SET_LIGHT_DIMMABLE_MASK, 0x03);
    lights(100, 100, 100, 0, 10, FX_NONE, LIGHTS_FLAG_AUTO_REAR);
    run(500);
    CHECK(R.out.light[0] == 100 && R.out.light[1] == 100);
    CHECK(R.out.light[2] == 255 && R.out.light[3] == 0 && R.out.light[4] == 255);
    CHECK(R.out.relays & BIT(R_TRAILER_TAIL));
    CHECK((R.out.relays & BIT(R_REAR)) == 0);
    // Reverse from the Shinegle: rear pods on automatically
    R.dir = 2;
    run(200);
    CHECK(R.out.relays & BIT(R_REAR));
    R.dir = 1;
    run(200);
    CHECK((R.out.relays & BIT(R_REAR)) == 0);
    // Brake input drives the trailer brake relay
    R.p.force_mask = BIT(IN_BRAKE);
    R.p.force_bits = BIT(IN_BRAKE);
    run(20);
    CHECK(R.out.relays & BIT(R_TRAILER_BRAKE));
    // Lights off: trailer tail off
    lights(0, 0, 0, 0, 0, FX_NONE, 0);
    run(500);
    CHECK((R.out.relays & BIT(R_TRAILER_TAIL)) == 0);
    CHECK(R.out.light[0] == 0);
    // Effects: chase lights one bar at a time
    setting(SET_LIGHT_DIMMABLE_MASK, 0x1F);
    lights(255, 255, 255, 255, 0, FX_CHASE, 0);
    int seen_multi = 0, seen_one = 0;
    for (int i = 0; i < 100; i++) {
        run(10);
        int on = 0;
        for (int b = 0; b < 4; b++) on += R.out.light[b] > 0;
        if (on > 1) seen_multi++;
        if (on == 1) seen_one++;
    }
    CHECK(seen_one > 90 && seen_multi == 0);
    lights(255, 255, 255, 255, 0, FX_OUTSIDE_ONLY, 0);
    run(300);
    CHECK(R.out.light[0] == 255 && R.out.light[1] == 0 && R.out.light[2] == 0 && R.out.light[3] == 255);
}

static void test_settings(void) {
    rig_init();
    run(300);
    setting(SET_4WD_MAX_KMH, 10);
    const can_frame_t *a = last_sent(CAN_ID_PICO_SET_ACK);
    CHECK(a && a->data[0] == SET_4WD_MAX_KMH && a->data[1] == SET_ACK_OK && get_u16(&a->data[2]) == 10);
    setting(SET_4WD_MAX_KMH, 500);
    a = last_sent(CAN_ID_PICO_SET_ACK);
    CHECK(a && a->data[1] == SET_ACK_RANGE && get_u16(&a->data[2]) == 10);
    setting(99, 1);
    a = last_sent(CAN_ID_PICO_SET_ACK);
    CHECK(a && a->data[1] == SET_ACK_UNKNOWN);
    run(200);
    const can_frame_t *s = last_sent(CAN_ID_PICO_STATUS);
    CHECK(s && !(s->data[4] & STATE_BIT_ON_DEFAULTS));
    // 4WD now allowed at 8 km/h
    R.speed_x10 = 80;
    run(200);
    drive(REQ_4WD, 0);
    run(50);
    CHECK(R.c.fwd.moving);
    // Save asks the hardware layer to write flash
    setting(SET_CMD_SAVE, 0);
    run(10);
    CHECK(R.out.save_settings);
    // Blob round trip
    settings_blob_t b;
    settings_t back;
    settings_to_blob(&R.c.settings, &b);
    CHECK(settings_from_blob(&back, &b) && back.v[SET_4WD_MAX_KMH] == 10);
    b.v[3] ^= 1;
    CHECK(!settings_from_blob(&back, &b));
}

static void send_hb(uint8_t state) { uint8_t d[2] = {0, state}; frame(CAN_ID_PI_HEARTBEAT, 2, d); }

static void test_key_off_shutdown(void) {
    // Pi shuts down cleanly: power drops a grace period after its last heartbeat.
    rig_init();
    run(300);
    R.p.din_model &= (uint8_t)~BIT(IN_IGNITION);
    run(200);
    const can_frame_t *s = last_sent(CAN_ID_PICO_STATUS);
    CHECK(s && (s->data[6] & FLAG_SHUTDOWN_REQUEST));
    CHECK(R.out.relays & BIT(R_POWER_HOLD));
    CHECK((R.out.relays & BIT(R_ACCESSORY)) == 0);
    R.dash = false;
    send_hb(DASH_SHUTTING_DOWN);
    run(SHUTDOWN_GRACE_MS - 1000);
    CHECK(R.out.relays & BIT(R_POWER_HOLD));
    run(1500);
    CHECK((R.out.relays & BIT(R_POWER_HOLD)) == 0);

    // Pi never stops: hard limit at shutdown_wait_s.
    rig_init();
    run(300);
    R.p.din_model &= (uint8_t)~BIT(IN_IGNITION);
    run(29000);
    CHECK(R.out.relays & BIT(R_POWER_HOLD));
    run(1500);
    CHECK((R.out.relays & BIT(R_POWER_HOLD)) == 0);

    // Key back on during the countdown cancels it.
    rig_init();
    run(300);
    R.p.din_model &= (uint8_t)~BIT(IN_IGNITION);
    run(5000);
    R.p.din_model |= BIT(IN_IGNITION);
    run(30000);
    CHECK(R.out.relays & BIT(R_POWER_HOLD));
    CHECK(!R.c.shutting_down);
}

// Sentry (docs/sentry.md): key off, the Pi asks to stay on. Kept on while the 12V is OK.
static void test_sentry_hold(void) {
    rig_init();
    run(300);
    R.sentry = true;
    R.p.din_model &= (uint8_t)~BIT(IN_IGNITION);
    run(120000);   // well past shutdown_wait_s
    const can_frame_t *s = last_sent(CAN_ID_PICO_STATUS);
    CHECK(R.out.relays & BIT(R_POWER_HOLD));
    CHECK(s && !(s->data[6] & FLAG_SHUTDOWN_REQUEST) && (s->data[6] & FLAG_SENTRY_HOLD));
    CHECK((R.out.relays & BIT(R_ACCESSORY)) == 0);
    // Nothing moves in sentry: tray refused (ignition off).
    R.holding = true;
    R.hold_tray = 1;
    run(500);
    CHECK(R.c.tray.dir == 0);
    R.holding = false;
    R.hold_tray = 0;
    // A short dip (winch, a cold morning) doesn't end it...
    R.p.aux_mv = 12000;
    run(20000);
    CHECK(R.c.sentry_hold && !R.c.sentry_flat);
    R.p.aux_mv = 12600;
    run(5000);
    // ...30 s under 12.2 V does. Then the normal shutdown runs.
    R.p.aux_mv = 12100;
    run(31000);
    s = last_sent(CAN_ID_PICO_STATUS);
    CHECK(R.c.sentry_flat && !R.c.sentry_hold);
    CHECK(s && (s->data[6] & FLAG_SHUTDOWN_REQUEST) && (s->data[6] & FLAG_SENTRY_FLAT));
    run(31000);
    CHECK((R.out.relays & BIT(R_POWER_HOLD)) == 0);

    // The Pi stops asking: normal shutdown wait, then off.
    rig_init();
    run(300);
    R.sentry = true;
    R.p.din_model &= (uint8_t)~BIT(IN_IGNITION);
    run(60000);
    CHECK(R.out.relays & BIT(R_POWER_HOLD));
    R.sentry = false;
    run(29000);
    CHECK(R.out.relays & BIT(R_POWER_HOLD));
    run(1500);
    CHECK((R.out.relays & BIT(R_POWER_HOLD)) == 0);

    // The setting moves the cut-off. Key on clears a flat latch.
    rig_init();
    run(300);
    setting(SET_SENTRY_MIN_12V_MV, 12900);
    R.sentry = true;
    R.p.din_model &= (uint8_t)~BIT(IN_IGNITION);
    run(31000);
    CHECK(R.c.sentry_flat);
    R.p.din_model |= BIT(IN_IGNITION);
    run(200);
    CHECK(!R.c.sentry_flat);
}

static void test_fw_update(void) {
    rig_init();
    R.speed_x10 = 100;
    run(300);
    uint8_t magic[2] = {0x45, 0x54};
    frame(CAN_ID_PI_FW_UPDATE, 2, magic);
    run(10);
    CHECK(!R.out.enter_bootloader);
    CHECK(reject_reason() == REJ_NOT_PARKED);
    uint8_t bad[2] = {1, 2};
    R.speed_x10 = 0;
    run(200);
    frame(CAN_ID_PI_FW_UPDATE, 2, bad);
    run(10);
    CHECK(!R.out.enter_bootloader);
    frame(CAN_ID_PI_FW_UPDATE, 2, magic);
    R.t += TICK_MS;
    plant_inputs(&R.p, &R.in, R.t);
    ctl_tick(&R.c, &R.in, &R.out, on_send, NULL);
    CHECK(R.out.enter_bootloader);
    CHECK((R.out.relays & (BIT(R_WINCH_IN) | BIT(R_WINCH_OUT))) == 0);
    CHECK(R.out.relays & BIT(R_POWER_HOLD));
}

static void test_io_bus_dead(void) {
    rig_init();
    run(300);
    R.holding = true;
    R.hold_tray = 1;
    run(500);
    CHECK(R.c.tray.dir == 1);
    R.p.faults = BENCH_IO_BUS_DEAD;
    run(20);
    CHECK(R.c.tray.dir == 0);
    CHECK(fault(FAULT_IO_BUS));
}

static void test_status_frames(void) {
    rig_init();
    R.speed_x10 = 123;
    run(1200);
    const can_frame_t *s = last_sent(CAN_ID_PICO_STATUS);
    CHECK(s && s->dlc == 8 && s->data[7] == 12 && (s->data[6] & FLAG_SPEED_VALID));
    CHECK(s && (s->data[4] & 0x03) == CB_STATE_OK);
    const can_frame_t *p = last_sent(CAN_ID_PICO_POWER);
    CHECK(p && get_u16(&p->data[0]) == 12800 && p->data[5] == FW_VERSION_MAJOR && p->data[6] == FW_VERSION_MINOR && get_u16(&p->data[3]) == 1000);
    int n710 = 0;
    for (int i = 0; i < R.nsent; i++) n710 += R.sent[i].id == CAN_ID_PICO_STATUS;
    CHECK(n710 >= 11);  // 10 Hz
}


// ---- Safe drive changes: wait for the right speed, time out, cancel, busy, throttle hold

static uint8_t status_b4(void) { const can_frame_t *s = last_sent(CAN_ID_PICO_STATUS); return s ? s->data[4] : 0; }

static void test_4wd_waits_for_stop(void) {
    rig_init();
    run(300);
    drive(REQ_2WD, 0);
    run(3500);
    R.speed_x10 = 120;  // 12 km/h
    run(300);
    uint8_t rc = R.c.reject_count;
    drive(REQ_4WD, 0);
    run(500);
    CHECK(R.c.fwd.waiting);
    CHECK(!R.c.fwd.moving && R.c.fwd.state == FWD_2WD);
    CHECK(status_b4() & STATE_BIT_4WD_WAIT);
    CHECK(R.c.reject_count == rc);  // waiting is not a refusal
    // Dash resends every second while we slow: still just one wait
    for (int i = 0; i < 2; i++) { drive(REQ_4WD, 0); run(1000); }
    CHECK(R.c.fwd.waiting);
    R.speed_x10 = 0;
    run(200);
    CHECK(!R.c.fwd.waiting && R.c.fwd.moving && R.c.fwd.state == FWD_TO_4WD);
    run(2500);
    CHECK(R.c.fwd.state == FWD_4WD);
    CHECK(!(status_b4() & STATE_BIT_4WD_WAIT));
    CHECK(R.c.reject_count == rc);
}

static void test_4wd_wait_times_out(void) {
    rig_init();
    run(300);
    drive(REQ_2WD, 0);
    run(3500);
    R.speed_x10 = 200;
    run(300);
    drive(REQ_4WD, 0);
    run(9800);
    CHECK(R.c.fwd.waiting);
    run(400);
    CHECK(!R.c.fwd.waiting);
    CHECK(reject_reason() == REJ_WAIT_TIMEOUT);
    // Not done later by surprise, even with the dash still resending 4WD
    R.speed_x10 = 0;
    for (int i = 0; i < 3; i++) { drive(REQ_4WD, 0); run(1000); }
    CHECK(R.c.fwd.state == FWD_2WD && !R.c.fwd.moving);
}

static void test_4wd_wait_cancel(void) {
    rig_init();
    run(300);
    drive(REQ_2WD, 0);
    run(3500);
    R.speed_x10 = 200;
    run(300);
    uint8_t rc = R.c.reject_count;
    drive(REQ_4WD, 0);
    run(1000);
    CHECK(R.c.fwd.waiting);
    drive(REQ_2WD, 0);  // Cancel = ask for what's already there
    run(100);
    CHECK(!R.c.fwd.waiting);
    CHECK(R.c.reject_count == rc);
    R.speed_x10 = 0;
    run(2000);
    CHECK(R.c.fwd.state == FWD_2WD && !R.c.fwd.moving);
}

static void test_4wd_wait_hard_reason(void) {
    rig_init();
    run(300);
    drive(REQ_2WD, 0);
    run(3500);
    R.speed_x10 = 200;
    run(300);
    drive(REQ_4WD, 0);
    run(500);
    CHECK(R.c.fwd.waiting);
    R.shinegle = false;  // speed signal lost: drop the wait, say why
    run(1000);
    CHECK(!R.c.fwd.waiting);
    CHECK(reject_reason() == REJ_SPEED_UNKNOWN);
    // Lost dash also drops a wait
    rig_init();
    run(300);
    drive(REQ_2WD, 0);
    run(3500);
    R.speed_x10 = 200;
    run(300);
    drive(REQ_4WD, 0);
    run(300);
    R.dash = false;
    run(1000);
    CHECK(!R.c.fwd.waiting);
}

static void test_diff_waits_to_slow(void) {
    rig_init();
    drive(REQ_4WD, 0);
    run(3000);
    R.speed_x10 = 250;  // 25 km/h, over the 15 km/h lock limit
    run(300);
    drive(REQ_4WD, 60);
    run(500);
    CHECK(R.c.diff.waiting && !R.c.diff.moving);
    CHECK(status_b4() & STATE_BIT_DIFF_WAIT);
    const can_frame_t *a = last_sent(CAN_ID_PICO_ACT);
    CHECK(a && a->data[7] == 60);  // dash sees what it's waiting for
    R.speed_x10 = 100;
    run(4000);
    CHECK(!R.c.diff.waiting);
    CHECK(R.c.diff.pct >= 57 && R.c.diff.pct <= 63);
    // Unlocking never waits
    R.speed_x10 = 300;
    run(200);
    drive(REQ_4WD, 0);
    run(100);
    CHECK(!R.c.diff.waiting && R.c.diff.moving);
    run(3000);
    CHECK(R.c.diff.pct <= 3);
    // A wait cancelled by asking for the current %
    drive(REQ_4WD, 80);
    run(300);
    CHECK(R.c.diff.waiting);
    drive(REQ_4WD, R.c.diff.pct);
    run(100);
    CHECK(!R.c.diff.waiting && !R.c.diff.moving);
}

static void test_drive_busy(void) {
    rig_init();
    drive(REQ_2WD, 0);
    run(3000);
    // 4WD running: adding diff lock is refused as busy
    drive(REQ_4WD, 0);
    run(100);
    CHECK(R.c.fwd.moving);
    drive(REQ_4WD, 50);
    run(50);
    CHECK(reject_reason() == REJ_BUSY);
    CHECK(!R.c.diff.moving && !R.c.diff.waiting);
    run(3000);
    CHECK(R.c.fwd.state == FWD_4WD);
    // Diff running: a 4WD change is refused as busy
    drive(REQ_4WD, 100);
    run(100);
    CHECK(R.c.diff.moving);
    drive(REQ_2WD, 100);
    run(50);
    CHECK(reject_reason() == REJ_BUSY);
    CHECK(R.c.fwd.state == FWD_4WD && !R.c.fwd.waiting);
    drive(REQ_4WD, 100);  // the dash snaps its request back after a refusal
    run(4000);
    // 4WD waiting: adding lock is busy too, but taking it off still works
    R.speed_x10 = 100;
    run(300);
    drive(REQ_2WD, 100);
    run(100);
    CHECK(R.c.fwd.waiting);
    drive(REQ_2WD, 20);
    run(100);
    CHECK(R.c.diff.moving);
    CHECK(R.c.fwd.waiting);
}

static void test_throttle_hold(void) {
    rig_init();
    drive(REQ_2WD, 0);
    run(3000);
    CHECK(!R.out.throttle_hold);
    drive(REQ_4WD, 0);  // from a standstill: held while it shifts
    run(200);
    CHECK(R.c.fwd.moving && R.out.throttle_hold);
    CHECK(status_b4() & STATE_BIT_THROTTLE_HOLD);
    run(3000);
    CHECK(!R.c.fwd.moving && !R.out.throttle_hold);
    // Starts to roll mid-shift: hold drops and stays off for that shift
    drive(REQ_2WD, 0);
    run(200);
    CHECK(R.out.throttle_hold);
    R.speed_x10 = 20;
    run(200);
    CHECK(!R.out.throttle_hold);
    R.speed_x10 = 0;
    run(200);
    CHECK(R.c.fwd.moving ? !R.out.throttle_hold : true);
    run(3000);
    // Diff added on the move: never held, even after stopping
    R.speed_x10 = 80;
    drive(REQ_4WD, 0);
    run(3000);
    drive(REQ_4WD, 100);
    run(200);
    CHECK(R.c.diff.moving && !R.out.throttle_hold);
    R.speed_x10 = 0;
    run(300);
    CHECK(!R.out.throttle_hold);
    run(4000);
    // Setting off: never held
    setting(SET_SHIFT_THROTTLE_HOLD, 0);
    drive(REQ_4WD, 0);
    run(200);
    CHECK(R.c.diff.moving && !R.out.throttle_hold);
}

// ---- Vehicle lock (docs/vehicle-lock.md) ------------------------------------------
#include "sha256.h"

static void lock_cmd(uint8_t cmd, const char *digits) {
    uint8_t d[8] = {cmd, 0};
    uint8_t n = digits ? (uint8_t)strlen(digits) : 0;
    d[1] = n;
    for (uint8_t i = 0; i < n; i++) {
        uint8_t v = (uint8_t)(digits[i] - '0');
        d[2 + i / 2] |= (uint8_t)(i % 2 == 0 ? v << 4 : v);
    }
    frame(CAN_ID_PI_LOCK, 8, d);
}
static const uint8_t *lock_frame(void) { const can_frame_t *f = last_sent(CAN_ID_PICO_LOCK); return f ? f->data : NULL; }
static void park_brake(bool on) {
    if (on) R.p.din_model |= BIT(IN_PARK); else R.p.din_model &= (uint8_t)~BIT(IN_PARK);
}
static void hexcmp(const uint8_t *h, const char *hex) {
    char buf[65];
    for (int i = 0; i < 32; i++) sprintf(buf + 2 * i, "%02x", h[i]);
    CHECK(strcmp(buf, hex) == 0);
}

// Park brake interlock (docs/park-brake.md): park brake on = relay 6 opens the pedal
// switch line, so no drive. F-N-R is free; the pedal does nothing until it's let off.
static void test_park_interlock(void) {
    rig_init();
    run(300);
    CHECK(!(R.out.relays & BIT(R_PARK_BLOCK)) && !R.out.park_block);
    park_brake(true);
    run(50);
    CHECK(R.out.relays & BIT(R_PARK_BLOCK));
    CHECK(R.out.park_block);
    run(200);
    CHECK(status_b4() & STATE_BIT_PARK_BLOCK);
    // Forward selected: still blocked (F-N-R goes straight to the Shinegle)
    R.dir = 1;
    run(200);
    CHECK(R.out.relays & BIT(R_PARK_BLOCK));
    // Let it off: drive comes straight back
    park_brake(false);
    run(50);
    CHECK(!(R.out.relays & BIT(R_PARK_BLOCK)));
    run(200);
    CHECK(!(status_b4() & STATE_BIT_PARK_BLOCK));
    // Pulled on while rolling: not cut on the move...
    R.speed_x10 = 150;
    run(300);
    park_brake(true);
    run(200);
    CHECK(!(R.out.relays & BIT(R_PARK_BLOCK)));
    // ...but blocks once it's stopped, and stays on if it then creeps
    R.speed_x10 = 0;
    run(200);
    CHECK(R.out.relays & BIT(R_PARK_BLOCK));
    R.speed_x10 = 30;
    run(200);
    CHECK(R.out.relays & BIT(R_PARK_BLOCK));
    R.speed_x10 = 0;
    // Speed not known yet (Shinegle still waking at key-on): blocks
    park_brake(false);
    run(50);
    R.shinegle = false;
    run(1000);
    park_brake(true);
    run(50);
    CHECK(R.out.relays & BIT(R_PARK_BLOCK));
    R.shinegle = true;
    // Key off: relay drops (no coil power wasted, and nothing to block)
    R.p.din_model &= (uint8_t)~BIT(IN_IGNITION);
    run(50);
    CHECK(!(R.out.relays & BIT(R_PARK_BLOCK)));
    R.p.din_model |= BIT(IN_IGNITION);
    run(300);
    CHECK(R.out.relays & BIT(R_PARK_BLOCK));
    // Setting off: never blocks
    setting(SET_PARK_INTERLOCK, 0);
    run(50);
    CHECK(!(R.out.relays & BIT(R_PARK_BLOCK)));
    setting(SET_PARK_INTERLOCK, 1);
    run(50);
    CHECK(R.out.relays & BIT(R_PARK_BLOCK));
}

static void test_lock_hash(void) {
    sha256_t s;
    uint8_t h[32];
    sha256_init(&s);
    sha256_update(&s, "abc", 3);
    sha256_final(&s, h);
    hexcmp(h, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    uint8_t salt[16];
    for (int i = 0; i < 16; i++) salt[i] = (uint8_t)i;
    vlock_hash(salt, "1234", 4, h);   // same vector as tests/test_vehicle_lock.py
    hexcmp(h, "97ddbcf2cb504922480796891327ead84d3a26b65429411b513a9480e49a3e29");
}

static void test_lock_set_and_lock_rules(void) {
    rig_init();
    run(500);
    CHECK(lock_frame() && lock_frame()[0] == LOCK_OFF);
    lock_cmd(LOCK_CMD_LOCK, NULL);
    CHECK(R.c.lock.result == LOCK_RES_NO_PIN && !ctl_locked(&R.c));
    lock_cmd(LOCK_CMD_SET_PIN, "12");
    CHECK(R.c.lock.result == LOCK_RES_BAD_DIGITS);
    lock_cmd(LOCK_CMD_SET_PIN, "4821");
    CHECK(R.c.lock.result == LOCK_RES_OK && vlock_pin_set(&R.c.lock));
    run(10);
    CHECK(R.out.save_lock || R.c.lock.saved.crc != 0);
    // The PIN itself is never stored.
    CHECK(memmem(&R.c.lock.saved, sizeof(R.c.lock.saved), "4821", 4) == NULL);
    lock_cmd(LOCK_CMD_SET_PUK, "11223344");
    CHECK(R.c.lock.result == LOCK_RES_OK && (R.c.lock.saved.flags & LOCKF_PUK_SET));

    // Rolling: refused. No park brake: refused.
    R.speed_x10 = 50;
    park_brake(true);
    run(300);
    lock_cmd(LOCK_CMD_LOCK, NULL);
    CHECK(R.c.lock.result == LOCK_RES_NOT_PARKED && !ctl_locked(&R.c));
    R.speed_x10 = 0;
    park_brake(false);
    run(300);
    lock_cmd(LOCK_CMD_LOCK, NULL);
    CHECK(R.c.lock.result == LOCK_RES_NOT_PARKED && !ctl_locked(&R.c));
    // No speed signal and key on: can't prove it's stopped.
    park_brake(true);
    R.shinegle = false;
    run(800);
    lock_cmd(LOCK_CMD_LOCK, NULL);
    CHECK(R.c.lock.result == LOCK_RES_NOT_PARKED);
    R.shinegle = true;
    run(300);
    lock_cmd(LOCK_CMD_LOCK, NULL);
    CHECK(R.c.lock.result == LOCK_RES_OK && ctl_locked(&R.c));
    run(200);
    CHECK(lock_frame()[0] == LOCK_LOCKED && (lock_frame()[4] & LOCK_FLAG_INHIBIT));
    CHECK(R.out.drive_inhibit);
    // Relay 10 opens the key line, steering assist and its frames stop.
    CHECK(R.out.relays2 & BIT(R2_DRIVE_LOCK));
    CHECK(!(R.out.relays2 & BIT(R2_STEER_ENABLE)) && !R.out.eps_on);
}

// ---- Power steering (docs/power-steering-aqua.md) ------------------------------------
#include "eps.h"

static void eps_hear(int16_t torque, int16_t angle_raw, uint8_t b0) {
    can_frame_t f = {.id = EPS_TORQUE_ID, .dlc = 8};
    f.data[0] = b0;
    f.data[1] = (uint8_t)((uint16_t)torque >> 8); f.data[2] = (uint8_t)torque;
    f.data[3] = (uint8_t)((uint16_t)angle_raw >> 8); f.data[4] = (uint8_t)angle_raw;
    f.data[7] = eps_checksum(EPS_TORQUE_ID, f.data, 8);
    ctl_on_eps_frame(&R.c, &f, R.t);
}

static const uint8_t *steer_frame(void) {
    const can_frame_t *f = last_sent(CAN_ID_PICO_STEER);
    static const uint8_t none[8];
    return f ? f->data : none;
}

static void test_eps(void) {
    // Same bytes as teryx/eps_toyota.py (checked against the retrofit thread).
    can_frame_t f[2];
    CHECK(eps_frames(163, 1674, f) == 2);
    const uint8_t rpm[8] = {0x06, 0x8A, 0x00, 0x19, 0x00, 0x00, 0x92, 0x09};
    CHECK(f[0].id == 0x2C4 && memcmp(f[0].data, rpm, 8) == 0);
    CHECK(f[1].id == 0x0B4 && f[1].data[5] == 0x06 && f[1].data[6] == 0x5E);   // 16.3 km/h
    CHECK(f[1].data[4] == 0x8D && f[1].data[7] == 0xAD);
    eps_frames(300, 1674, f);                                                     // 30 km/h
    CHECK(((f[1].data[5] << 8) | f[1].data[6]) == 3000);

    // Assist curve: floor, gain, cap. Unknown speed = floor.
    eps_cfg_t cfg = {.floor_x10 = 163, .gain_pct = 100, .max_kmh = 120};
    CHECK(eps_told_speed_x10(&cfg, 50, true) == 163);
    CHECK(eps_told_speed_x10(&cfg, 300, true) == 300);
    CHECK(eps_told_speed_x10(&cfg, 300, false) == 163);
    cfg.gain_pct = 200;
    CHECK(eps_told_speed_x10(&cfg, 300, true) == 600);
    CHECK(eps_told_speed_x10(&cfg, 900, true) == 1200);   // capped at 120 km/h

    rig_init();
    run(300);   // key on, not locked
    CHECK(R.out.relays2 & BIT(R2_STEER_ENABLE));
    CHECK(R.out.eps_on && !(R.out.relays2 & BIT(R2_DRIVE_LOCK)));
    CHECK(R.out.eps_speed_x10 == 163 && R.out.eps_rpm == 1674);
    CHECK((steer_frame()[0] & 0x0F) == STEER_WAKING);   // ECU gets 3 s to boot
    run(3000);
    CHECK((steer_frame()[0] & 0x0F) == STEER_OK);        // not listening by default: OK
    CHECK(steer_frame()[1] & STEER_F_FRAMES);
    CHECK(steer_frame()[6] == 16 && steer_frame()[7] == 0xFF);
    R.speed_x10 = 300;
    run(200);
    CHECK(R.out.eps_speed_x10 == 300 && steer_frame()[6] == 30);
}

static void test_eps_listen(void) {
    rig_init();
    setting(SET_EPS_LISTEN, 1);
    run(3500);
    CHECK((steer_frame()[0] & 0x0F) == STEER_NO_REPLY);   // ECU silent
    CHECK(R.out.relays2 & BIT(R2_STEER_ENABLE));           // ...but assist stays on
    eps_hear(-120, 175, 0x01);   // 175 x 0.0573 = 10.0 deg, driver override bit
    run(200);
    const uint8_t *d = steer_frame();
    CHECK((d[0] & 0x0F) == STEER_OK);
    CHECK((d[1] & (STEER_F_HEARD | STEER_F_TORQUE | STEER_F_OVERRIDE | STEER_F_LISTEN)) ==
          (STEER_F_HEARD | STEER_F_TORQUE | STEER_F_OVERRIDE | STEER_F_LISTEN));
    CHECK((int16_t)(d[2] | (d[3] << 8)) == -120);
    CHECK((int16_t)(d[4] | (d[5] << 8)) == 100);
    // Bad checksum: counted as "heard" but the numbers aren't used.
    can_frame_t bad = {.id = EPS_TORQUE_ID, .dlc = 8, .data = {0, 0x7F, 0xFF, 0, 0, 0, 0, 0x00}};
    ctl_on_eps_frame(&R.c, &bad, R.t);
    CHECK(R.c.eps.bad_checksum == 1 && R.c.eps.torque_raw == -120);
    run(1200);
    CHECK((steer_frame()[0] & 0x0F) == STEER_NO_REPLY);   // quiet for more than 1 s
    // ECU says permanent fault (EPS_STATUS LKA_STATE 17)
    can_frame_t st = {.id = EPS_STATUS_ID, .dlc = 8};
    st.data[3] = (uint8_t)(17u << 1);
    st.data[7] = eps_checksum(EPS_STATUS_ID, st.data, 8);
    ctl_on_eps_frame(&R.c, &st, R.t);
    run(100);
    CHECK((steer_frame()[0] & 0x0F) == STEER_ECU_FAULT && steer_frame()[7] == 17);
    CHECK(R.out.relays2 & BIT(R2_STEER_ENABLE));   // the Toyota ECU runs its own fail-safe
    // Steering CAN board dies: says so, but only while it should be sending
    eps_t e;
    eps_init(&e, EPS_MODE_NORMAL);
    eps_cfg_t cfg = {.floor_x10 = 163, .gain_pct = 100, .max_kmh = 120, .silent_ms = 1000, .wake_ms = 3000};
    eps_update(&e, &cfg, true, true, false, 0);
    CHECK(e.state == STEER_BUS_ERROR && !(e.flags & STEER_F_BUS_OK));
    e.mode = EPS_MODE_LIMP;
    eps_update(&e, &cfg, true, false, false, 5000);
    CHECK(e.state == STEER_LIMP);
    eps_update(&e, &cfg, false, false, true, 6000);
    CHECK(e.state == STEER_OFF);
}

static void test_eps_modes(void) {
    rig_init();
    R.speed_x10 = 200;   // 20 km/h
    run(300);
    setting(SET_EPS_MODE, EPS_MODE_MANUAL);
    run(300);
    // Never on the move: still powered, change waiting
    CHECK((R.out.relays2 & BIT(R2_STEER_ENABLE)) && R.out.eps_on);
    CHECK(steer_frame()[1] & STEER_F_PENDING);
    R.speed_x10 = 0;
    run(300);
    CHECK(!(R.out.relays2 & BIT(R2_STEER_ENABLE)) && !R.out.eps_on);
    CHECK((steer_frame()[0] & 0x0F) == STEER_MANUAL && !(steer_frame()[1] & STEER_F_PENDING));
    setting(SET_EPS_MODE, EPS_MODE_LIMP);
    run(3500);
    CHECK((R.out.relays2 & BIT(R2_STEER_ENABLE)) && !R.out.eps_on);
    CHECK((steer_frame()[0] & 0x0F) == STEER_LIMP && steer_frame()[6] == 0xFF);
    setting(SET_EPS_MODE, EPS_MODE_NORMAL);
    run(3500);
    CHECK(R.out.eps_on && (steer_frame()[0] & 0x0F) == STEER_OK);
    setting(SET_EPS_MODE, 3);   // out of range
    CHECK(last_sent(CAN_ID_PICO_SET_ACK)->data[1] == SET_ACK_RANGE);
}

static void lock_up(void) {
    rig_init();
    park_brake(true);
    run(500);
    lock_cmd(LOCK_CMD_SET_PIN, "4821");
    lock_cmd(LOCK_CMD_SET_PUK, "11223344");
    lock_cmd(LOCK_CMD_LOCK, NULL);
    run(100);
}

static void test_lock_blocks_everything(void) {
    rig_init();
    park_brake(true);
    run(300);
    // Lights on, winch armed before locking.
    lights(255, 255, 0, 0, 200, FX_NONE, LIGHTS_FLAG_REAR_ON);
    R.holding = true;
    R.armed = true;
    run(300);
    CHECK(R.c.winch.armed && R.out.light[0] > 0);
    lock_cmd(LOCK_CMD_SET_PIN, "4821");
    lock_cmd(LOCK_CMD_LOCK, NULL);
    CHECK(ctl_locked(&R.c));
    run(400);
    CHECK(!R.c.winch.armed);
    for (int i = 0; i < L_COUNT; i++) CHECK(R.out.light[i] == 0);
    CHECK(!(R.out.relays & BIT(R_REAR)) && !(R.out.relays & BIT(R_TRAILER_TAIL)));
    // Tray and winch presses refused.
    R.armed = false;
    R.hold_tray = 1;
    run(500);
    CHECK(R.c.tray.dir == 0 && R.out.act_dir[ACT_TRAY] == 0 && reject_reason() == REJ_INTERLOCK);
    R.hold_tray = 0;
    R.holding = false;
    // 4WD / diff refused, and not done by surprise after unlock.
    drive(REQ_4WD, 50);
    run(500);
    CHECK(!R.c.fwd.moving && !R.c.diff.moving && R.out.act_dir[ACT_4WD] == 0);
    // Settings and firmware update refused.
    setting(SET_SHIFT_WAIT_MS, 5000);
    CHECK(last_sent(CAN_ID_PICO_SET_ACK)->data[1] == SET_ACK_LOCKED);
    CHECK(S(&R.c, SET_SHIFT_WAIT_MS) == 10000);
    uint8_t m[2] = {0x45, 0x54};
    frame(CAN_ID_PI_FW_UPDATE, 2, m);
    run(20);
    CHECK(!R.out.enter_bootloader);
    // Can't change or remove the PIN while locked.
    lock_cmd(LOCK_CMD_SET_PIN, "0000");
    CHECK(R.c.lock.result == LOCK_RES_NOT_ALLOWED);
    lock_cmd(LOCK_CMD_REMOVE, NULL);
    CHECK(R.c.lock.result == LOCK_RES_NOT_ALLOWED && ctl_locked(&R.c));
    // Unlock: drive is allowed again but the old 4WD ask doesn't fire by itself.
    lock_cmd(LOCK_CMD_UNLOCK, "4821");
    CHECK(R.c.lock.result == LOCK_RES_OK && !ctl_locked(&R.c));
    run(300);
    CHECK(!R.out.drive_inhibit && !R.c.fwd.moving);
    drive(REQ_2WD, 0);
    drive(REQ_4WD, 0);
    run(20);
    CHECK(R.c.fwd.moving);
}

static void test_lock_survives_power_cut(void) {
    lock_up();
    CHECK(ctl_locked(&R.c));
    lock_blob_t flash = R.c.lock.saved;   // what the Pico wrote
    // Power cut: new controller, same flash.
    ctl_init(&R.c, NULL, false, false, R.t);
    ctl_load_lock(&R.c, &flash, R.t);
    run(200);
    CHECK(ctl_locked(&R.c) && R.out.drive_inhibit);
    // A corrupt sector reads as "never set" (and doesn't lock).
    flash.crc ^= 1;
    ctl_init(&R.c, NULL, false, false, R.t);
    ctl_load_lock(&R.c, &flash, R.t);
    CHECK(!ctl_locked(&R.c) && !vlock_pin_set(&R.c.lock));
}

// Remote lock (text from the owner's phone): never on the move, waits until stopped.
static void test_lock_remote(void) {
    rig_init();
    run(300);
    lock_cmd(LOCK_CMD_REMOTE, NULL);
    CHECK(R.c.lock.result == LOCK_RES_NO_PIN && !vlock_pending(&R.c.lock));
    lock_cmd(LOCK_CMD_SET_PIN, "4821");
    // Driving at 40 km/h, no park brake (a thief won't put it on).
    park_brake(false);
    R.speed_x10 = 400;
    run(500);
    lock_cmd(LOCK_CMD_REMOTE, NULL);
    CHECK(R.c.lock.result == LOCK_RES_PENDING && vlock_pending(&R.c.lock) && !ctl_locked(&R.c));
    run(30000);
    CHECK(!ctl_locked(&R.c) && !R.out.drive_inhibit);
    CHECK(lock_frame()[0] == LOCK_UNLOCKED && (lock_frame()[4] & LOCK_FLAG_PENDING));
    // Pending survives a power cut.
    lock_blob_t flash = R.c.lock.saved;
    ctl_init(&R.c, NULL, false, false, R.t);
    ctl_load_lock(&R.c, &flash, R.t);
    CHECK(vlock_pending(&R.c.lock) && !ctl_locked(&R.c));
    // A short stop (lights, a gate) doesn't lock it...
    R.speed_x10 = 0;
    run(5000);
    CHECK(!ctl_locked(&R.c));
    R.speed_x10 = 150;
    run(2000);
    CHECK(!ctl_locked(&R.c));
    // ...10 s stopped does.
    R.speed_x10 = 0;
    run(9000);
    CHECK(!ctl_locked(&R.c));
    run(1200);
    CHECK(ctl_locked(&R.c) && !vlock_pending(&R.c.lock) && R.out.drive_inhibit);
    // The PIN on the dash unlocks as normal.
    lock_cmd(LOCK_CMD_UNLOCK, "4821");
    CHECK(R.c.lock.result == LOCK_RES_OK && !ctl_locked(&R.c));

    // Already stopped for 10 s when the text comes: locks straight away.
    lock_cmd(LOCK_CMD_REMOTE, NULL);
    CHECK(ctl_locked(&R.c));
    lock_cmd(LOCK_CMD_UNLOCK, "4821");
    // Speed unknown (Shinegle quiet) with the key on: not proven stopped, so it waits.
    R.speed_x10 = 300;
    run(300);
    lock_cmd(LOCK_CMD_REMOTE, NULL);
    R.speed_x10 = 0;
    R.shinegle = false;
    run(20000);
    CHECK(!ctl_locked(&R.c) && vlock_pending(&R.c.lock));
    // Key off: locks straight away.
    R.p.din_model &= (uint8_t)~BIT(IN_IGNITION);
    run(100);
    CHECK(ctl_locked(&R.c));
    R.p.din_model |= BIT(IN_IGNITION);
    R.shinegle = true;
    run(300);

    // The right PIN cancels a remote lock that hasn't happened yet.
    lock_cmd(LOCK_CMD_UNLOCK, "4821");
    R.speed_x10 = 300;
    run(300);
    lock_cmd(LOCK_CMD_REMOTE, NULL);
    CHECK(vlock_pending(&R.c.lock));
    lock_cmd(LOCK_CMD_UNLOCK, "4821");
    CHECK(R.c.lock.result == LOCK_RES_OK && !vlock_pending(&R.c.lock));
    R.speed_x10 = 0;
    run(15000);
    CHECK(!ctl_locked(&R.c));
}

static void test_lock_wrong_tries(void) {
    lock_up();
    for (int i = 0; i < LOCK_FREE_TRIES - 1; i++) {
        lock_cmd(LOCK_CMD_UNLOCK, "0000");
        CHECK(R.c.lock.result == LOCK_RES_WRONG);
    }
    run(100);
    CHECK(lock_frame()[1] == 1 && lock_frame()[7] == LOCK_FREE_TRIES - 1);
    lock_cmd(LOCK_CMD_UNLOCK, "0000");
    CHECK(R.c.lock.result == LOCK_RES_WRONG && R.c.lock.lockout);
    run(100);
    CHECK(lock_frame()[1] == 0 && (lock_frame()[4] & LOCK_FLAG_LOCKOUT));
    uint16_t left = (uint16_t)(lock_frame()[2] | lock_frame()[3] << 8);
    CHECK(left >= 29 && left <= 30);
    // Even the right PIN is refused during the lockout, and doesn't count.
    lock_cmd(LOCK_CMD_UNLOCK, "4821");
    CHECK(R.c.lock.result == LOCK_RES_LOCKOUT && ctl_locked(&R.c));
    // A power cut doesn't clear it.
    lock_blob_t flash = R.c.lock.saved;
    ctl_init(&R.c, NULL, false, false, R.t);
    ctl_load_lock(&R.c, &flash, R.t);
    CHECK(R.c.lock.lockout);
    run(30000);
    CHECK(!R.c.lock.lockout);
    // One more wrong try: twice as long.
    lock_cmd(LOCK_CMD_UNLOCK, "9999");
    CHECK(R.c.lock.lockout && R.c.lock.lockout_ms == 60000u);
    run(60000);
    lock_cmd(LOCK_CMD_UNLOCK, "4821");
    CHECK(R.c.lock.result == LOCK_RES_OK && !ctl_locked(&R.c) && R.c.lock.saved.fails == 0);
}

static void test_lock_change_pin_and_recovery(void) {
    lock_up();
    lock_cmd(LOCK_CMD_UNLOCK, "4821");
    // Change needs the old PIN first.
    lock_cmd(LOCK_CMD_SET_PIN, "5555");
    CHECK(R.c.lock.result == LOCK_RES_NOT_ALLOWED);
    lock_cmd(LOCK_CMD_VERIFY, "4821");
    CHECK(R.c.lock.result == LOCK_RES_OK && R.c.lock.window);
    lock_cmd(LOCK_CMD_SET_PIN, "555555");
    CHECK(R.c.lock.result == LOCK_RES_OK);
    // Setting a PIN drops the old recovery code until a new one is sent.
    CHECK(!(R.c.lock.saved.flags & LOCKF_PUK_SET));
    lock_cmd(LOCK_CMD_SET_PUK, "87654321");
    run(LOCK_WINDOW_MS + 100);
    CHECK(!R.c.lock.window);
    lock_cmd(LOCK_CMD_REMOVE, NULL);
    CHECK(R.c.lock.result == LOCK_RES_NOT_ALLOWED);
    // Lock, forget the PIN, use the recovery code: unlocked and wiped.
    lock_cmd(LOCK_CMD_LOCK, NULL);
    CHECK(ctl_locked(&R.c));
    lock_cmd(LOCK_CMD_UNLOCK, "4821");
    CHECK(R.c.lock.result == LOCK_RES_WRONG);
    lock_cmd(LOCK_CMD_UNLOCK, "87654321");
    CHECK(R.c.lock.result == LOCK_RES_RECOVERED && !ctl_locked(&R.c) && !vlock_pin_set(&R.c.lock));
    CHECK(R.c.lock.saved.fails == 0);
    // Remove: needs the window.
    lock_cmd(LOCK_CMD_SET_PIN, "2468");
    lock_cmd(LOCK_CMD_VERIFY, "2468");
    lock_cmd(LOCK_CMD_REMOVE, NULL);
    CHECK(R.c.lock.result == LOCK_RES_OK && !vlock_pin_set(&R.c.lock));
    // Workshop reset (debug UART in the box).
    lock_up();
    vlock_workshop_reset(&R.c.lock);
    run(20);
    CHECK(!ctl_locked(&R.c) && !vlock_pin_set(&R.c.lock) && !R.out.drive_inhibit);
}

int main(void) {
    struct { const char *name; void (*fn)(void); } tests[] = {
        {"boot: all outputs off", test_boot_all_off},
        {"4WD: speed rule, change-only requests", test_4wd_speed_rule_and_change_only},
        {"4WD: unknown position homes on resend", test_4wd_homes_when_unknown},
        {"4WD: stall gives overcurrent fault", test_4wd_stall},
        {"diff: closed loop and speed rule", test_diff_closed_loop},
        {"4WD: waits for a stop, then goes", test_4wd_waits_for_stop},
        {"4WD: wait times out, not done later", test_4wd_wait_times_out},
        {"4WD: wait cancelled by the dash", test_4wd_wait_cancel},
        {"4WD: wait dropped on a hard reason", test_4wd_wait_hard_reason},
        {"diff: waits to slow, unlock never waits", test_diff_waits_to_slow},
        {"drive: one change at a time", test_drive_busy},
        {"drive: throttle hold only from a standstill", test_throttle_hold},
        {"diff: jam detected", test_diff_jam},
        {"diff: pot disconnected", test_diff_pot_disconnected},
        {"tray: hold-to-run and limits", test_tray_hold_to_run},
        {"tray: needs stopped and known speed", test_tray_needs_stopped},
        {"tray: stops if the Teryx moves", test_tray_moving_stops_when_speed_rises},
        {"tray: jam and broken limit wire", test_tray_jam_and_broken_limit},
        {"lost dash: motion stops, lights stay", test_lost_dash_stops_motion_keeps_lights},
        {"winch: arm, dead time, interlocks", test_winch_rules},
        {"winch: auto disarm", test_winch_auto_disarm},
        {"winch: handheld remote has priority", test_winch_remote_has_priority},
        {"winch: timed pull stops by itself", test_winch_timed_pull},
        {"lights, reverse, trailer", test_lights_and_relays},
        {"lamps: brake full, show parked only, beacon", test_lamps_and_show},
        {"settings and flash blob", test_settings},
        {"key-off shutdown", test_key_off_shutdown},
        {"sentry: power kept on while the 12V is OK", test_sentry_hold},
        {"firmware update request", test_fw_update},
        {"IO bus dead", test_io_bus_dead},
        {"status frames", test_status_frames},
        {"park brake: blocks drive, never on the move", test_park_interlock},
        {"lock: SHA-256 and PIN hash vectors", test_lock_hash},
        {"lock: set PIN, lock only when parked", test_lock_set_and_lock_rules},
        {"lock: blocks motion, lights, settings, OTA", test_lock_blocks_everything},
        {"lock: survives a power cut", test_lock_survives_power_cut},
        {"lock: wrong tries and lockout", test_lock_wrong_tries},
        {"lock: remote lock waits until stopped", test_lock_remote},
        {"lock: change PIN, recovery code, workshop reset", test_lock_change_pin_and_recovery},
        {"power steering: relay 9 and Toyota frames", test_eps},
        {"power steering: listening to the ECU", test_eps_listen},
        {"power steering: modes wait until stopped", test_eps_modes},
    };
    for (size_t i = 0; i < sizeof(tests) / sizeof(tests[0]); i++) {
        int before = failures;
        tests[i].fn();
        printf("%s %s\n", failures == before ? "ok  " : "FAIL", tests[i].name);
    }
    printf("\n%d checks, %d failed\n", checks, failures);
    return failures ? 1 : 0;
}
