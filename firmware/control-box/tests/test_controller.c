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
    can_frame_t sent[64];
    int nsent;
    uint8_t max_relays_both_winch;  // set if in and out were ever on together
} rig_t;

static rig_t R;

static void on_send(const can_frame_t *f, void *u) {
    (void)u;
    if (R.nsent < 64) R.sent[R.nsent++] = *f;
    else { memmove(R.sent, R.sent + 1, sizeof(R.sent[0]) * 63); R.sent[63] = *f; }
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
            if (R.dash) { uint8_t d[2] = {(uint8_t)(R.t / 100), DASH_RUNNING}; frame(CAN_ID_PI_HEARTBEAT, 2, d); }
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
    CHECK((R.out.relays & (BIT(R_WINCH_IN) | BIT(R_WINCH_OUT) | BIT(R_WINCH_ISOLATOR) | BIT(R_REAR))) == 0);
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
    R.speed_x10 = 100;  // 10 km/h, under the 15 km/h limit
    run(300);
    CHECK(R.c.diff.pct == 0);
    drive(DRIVE_NO_CHANGE, 50);
    run(3000);
    CHECK(R.c.diff.pct >= 47 && R.c.diff.pct <= 53);
    CHECK(!R.c.diff.moving);
    const can_frame_t *a = last_sent(CAN_ID_PICO_ACT);
    CHECK(a && a->data[7] == 50);
    // Too fast for diff changes
    R.speed_x10 = 200;
    run(200);
    drive(DRIVE_NO_CHANGE, 100);
    run(100);
    CHECK(reject_reason() == REJ_TOO_FAST);
    CHECK(!R.c.diff.moving);
    CHECK(R.c.diff.target_pct == 50 || R.c.diff.target_pct == R.c.diff.pct);
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
    CHECK((R.out.relays & BIT(R_WINCH_ISOLATOR)) == 0);
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
    CHECK(R.out.relays & BIT(R_WINCH_ISOLATOR));
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
    CHECK((R.out.relays & (BIT(R_WINCH_IN) | BIT(R_WINCH_OUT) | BIT(R_WINCH_ISOLATOR))) == 0);
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
    CHECK((R.out.relays & (BIT(R_WINCH_IN) | BIT(R_WINCH_OUT) | BIT(R_WINCH_ISOLATOR))) == 0);
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

int main(void) {
    struct { const char *name; void (*fn)(void); } tests[] = {
        {"boot: all outputs off", test_boot_all_off},
        {"4WD: speed rule, change-only requests", test_4wd_speed_rule_and_change_only},
        {"4WD: unknown position homes on resend", test_4wd_homes_when_unknown},
        {"4WD: stall gives overcurrent fault", test_4wd_stall},
        {"diff: closed loop and speed rule", test_diff_closed_loop},
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
        {"settings and flash blob", test_settings},
        {"key-off shutdown", test_key_off_shutdown},
        {"firmware update request", test_fw_update},
        {"IO bus dead", test_io_bus_dead},
        {"status frames", test_status_frames},
    };
    for (size_t i = 0; i < sizeof(tests) / sizeof(tests[0]); i++) {
        int before = failures;
        tests[i].fn();
        printf("%s %s\n", failures == before ? "ok  " : "FAIL", tests[i].name);
    }
    printf("\n%d checks, %d failed\n", checks, failures);
    return failures ? 1 : 0;
}
