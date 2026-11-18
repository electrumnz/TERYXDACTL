// Teryx control box: control logic and the safety rules from docs/io-list.md
// section 7. Rule numbers in the comments match that list.
#include "controller.h"

#include <string.h>

#include "config.h"

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

static uint32_t since(uint32_t now, uint32_t then) { return now - then; }

static void reject(controller_t *c, uint8_t reason) {
    c->reject_reason = reason;
    c->reject_count = (uint8_t)((c->reject_count + 1) & 0x0F);
}

bool ctl_dash_ok(const controller_t *c, uint32_t now) {
    return c->hb_seen && since(now, c->last_hb_ms) <= S(c, SET_HEARTBEAT_TIMEOUT_MS);
}

bool ctl_speed_valid(const controller_t *c, uint32_t now) {
    return c->speed_seen && since(now, c->last_speed_ms) <= S(c, SET_SPEED_TIMEOUT_MS);
}

static bool stopped(const controller_t *c, uint32_t now) {
    return ctl_speed_valid(c, now) && c->speed_x10 <= 5;  // under 0.5 km/h
}

static bool ignition(const controller_t *c) { return (c->in.din & BIT(IN_IGNITION)) != 0; }

static bool anything_moving(const controller_t *c) {
    return c->fwd.moving || c->diff.moving || c->tray.dir != 0 || c->winch.active != 0;
}

bool ctl_parked(const controller_t *c, uint32_t now) {
    if (anything_moving(c)) return false;
    // Stopped by the Shinegle's speed, or key off, or the park switch is on.
    return stopped(c, now) || !ignition(c) || (c->in.din & BIT(IN_PARK));
}

bool ctl_locked(const controller_t *c) { return vlock_is_locked(&c->lock); }

bool ctl_can_lock(const controller_t *c, uint32_t now) {
    if (anything_moving(c)) return false;
    if (!(c->in.din & BIT(IN_PARK))) return false;   // park brake on
    return stopped(c, now) || !ignition(c);
}

static bool reverse_active(const controller_t *c, uint32_t now) {
    if (c->in.din & BIT(IN_REVERSE)) return true;
    return ctl_speed_valid(c, now) && c->mc_dir == 2;
}

// Common checks before starting any motion. Returns REJ_NONE if OK.
static uint8_t motion_check(const controller_t *c, uint32_t now, bool need_stopped,
                            uint16_t max_kmh) {
    if (!c->in.io_ok) return REJ_FAULT;
    if (!ctl_dash_ok(c, now)) return REJ_DASH_LINK;
    if (!ignition(c)) return REJ_IGNITION_OFF;
    if (!ctl_speed_valid(c, now)) return REJ_SPEED_UNKNOWN;           // rule 2
    if (need_stopped) {
        if (c->speed_x10 > 5) return REJ_NOT_STOPPED;
    } else if (c->speed_x10 >= max_kmh * 10u) {
        return REJ_TOO_FAST;
    }
    return REJ_NONE;
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

void ctl_init(controller_t *c, const settings_t *saved, bool watchdog_reset,
              bool power_hold_on, uint32_t now) {
    memset(c, 0, sizeof(*c));
    if (saved) {
        c->settings = *saved;
        c->settings_from_flash_or_dash = true;
    } else {
        settings_defaults(&c->settings);
    }
    c->boot_ms = now;
    c->watchdog_reset = watchdog_reset;
    c->power_hold = power_hold_on;
    c->fwd.state = FWD_UNKNOWN;
    c->fwd.target = DRIVE_NO_CHANGE;
    c->diff.target_pct = PCT_UNKNOWN;
    c->diff.pct = PCT_UNKNOWN;
    c->tray.pos_ms = -1;  // unknown until a limit switch is seen
    c->last_tx_fast_ms = now;
    c->last_tx_slow_ms = now;
    c->winch.off_since_ms = now;
    c->in.io_ok = true;
    vlock_init(&c->lock, NULL, now);
}

void ctl_load_lock(controller_t *c, const lock_blob_t *saved, uint32_t now) {
    vlock_init(&c->lock, saved, now);
}

// ---------------------------------------------------------------------------
// Requests from the dash
// ---------------------------------------------------------------------------
//
// Safe drive changes (docs/drive-changes.md): when a 4WD or diff lock request
// only fails on speed (too fast / not stopped), it waits up to
// SET_SHIFT_WAIT_MS for the speed to come right, then runs. The dash shows a
// spinner and can cancel by asking for what's already there. Any other reason
// (no speed signal, key off, fault ...) is still refused at once, and a wait
// that times out is dropped, so nothing happens later by surprise.
// While one drive change waits or runs, the other is refused (REJ_BUSY),
// except taking diff lock off, which always works.

static void stop_all_motion(controller_t *c);
static void send_lock(controller_t *c, uint32_t now, cb_send_fn send, void *u);

static bool speed_reason(uint8_t r) { return r == REJ_TOO_FAST || r == REJ_NOT_STOPPED; }
static bool fwd_busy(const controller_t *c) { return c->fwd.moving || c->fwd.waiting; }
static bool diff_busy(const controller_t *c) { return c->diff.moving || c->diff.waiting; }

// Forget a 4WD request, so it isn't done later by surprise.
static void fwd_forget(controller_t *c) {
    fourwd_t *f = &c->fwd;
    f->waiting = false;
    f->target = f->state == FWD_4WD ? REQ_4WD : f->state == FWD_2WD ? REQ_2WD : DRIVE_NO_CHANGE;
}

static void try_start_4wd(controller_t *c, uint32_t now) {
    fourwd_t *f = &c->fwd;
    if (f->target == DRIVE_NO_CHANGE) { f->waiting = false; return; }
    uint8_t want = f->target == REQ_4WD ? FWD_4WD : FWD_2WD;
    uint8_t going = want == FWD_4WD ? FWD_TO_4WD : FWD_TO_2WD;
    // Already there (this is also how the dash cancels a wait).
    if (f->state == want || (f->moving && f->state == going)) { f->waiting = false; return; }
    // A change of mind mid-move just turns it round (same checks apply).
    uint8_t r = motion_check(c, now, false, S(c, SET_4WD_MAX_KMH));   // rule 3
    if (!r && !f->waiting && diff_busy(c)) r = REJ_BUSY;
    if (!r && c->diff.moving) r = REJ_BUSY;
    if (r) {
        if (f->waiting) return;  // wait_4wd() handles a request that's already waiting
        if (speed_reason(r) && S(c, SET_SHIFT_WAIT_MS) > 0) {
            f->waiting = true;
            f->wait_start_ms = now;
            return;
        }
        reject(c, r);
        fwd_forget(c);
        return;
    }
    f->waiting = false;
    f->from_unknown = f->moving || f->state == FWD_UNKNOWN || f->state == FWD_FAULT;
    f->moving = true;
    f->saw_current = false;
    f->start_ms = now;
    f->low_since_ms = 0;
    f->state = want == FWD_4WD ? FWD_TO_4WD : FWD_TO_2WD;
    c->latched &= (uint16_t)~(BIT(FAULT_4WD_TIMEOUT) | BIT(FAULT_4WD_OVERCURRENT));
}

// Returns REJ_NONE if started (or nothing to do), else why not. Doesn't reject.
static uint8_t try_start_diff(controller_t *c, uint32_t now) {
    diff_t *d = &c->diff;
    if (d->target_pct == PCT_UNKNOWN) return REJ_NONE;
    if (d->pct == PCT_UNKNOWN) return REJ_FAULT;
    int err = (int)d->target_pct - (int)d->pct;
    if (err <= DIFF_DEADBAND_PCT && err >= -DIFF_DEADBAND_PCT) return REJ_NONE;
    // Rule 4: the speed limit only applies to adding lock. Kawasaki's manual
    // has you stop to lock but unlock "after crossing the obstacle", and a
    // locked front diff makes steering heavy, so unlocking works at any speed.
    uint16_t lim = err > 0 ? S(c, SET_DIFF_MAX_KMH) : 0xFFFFu;
    uint8_t r = motion_check(c, now, false, lim);
    if (r) return r;
    if (err > 0 && fwd_busy(c)) return REJ_BUSY;  // taking lock off always works
    if (d->moving) return REJ_NONE;  // already moving, the loop follows the new target
    d->moving = true;
    d->start_ms = now;
    d->ref_raw = c->in.diff_pot_raw;
    d->last_move_ms = now;
    c->latched &= (uint16_t)~(BIT(FAULT_DIFF_TIMEOUT) | BIT(FAULT_DIFF_POT_STUCK) |
                              BIT(FAULT_DIFF_OVERCURRENT));
    return REJ_NONE;
}

// A new diff target from the dash. Replaces (or cancels) any wait.
static void diff_request(controller_t *c, uint8_t want, uint32_t now) {
    diff_t *d = &c->diff;
    d->waiting = false;
    uint8_t old = d->target_pct;
    d->target_pct = want;
    uint8_t r = try_start_diff(c, now);
    if (r == REJ_NONE) return;
    d->target_pct = d->moving ? old : d->pct;
    if (speed_reason(r) && S(c, SET_SHIFT_WAIT_MS) > 0) {
        d->waiting = true;
        d->wait_pct = want;
        d->wait_start_ms = now;
        return;
    }
    reject(c, r);
}

// Each tick: start a waiting request once it's safe, drop it on a hard
// reason or when the wait runs out.
static bool wait_over(const controller_t *c, uint32_t start, uint32_t now) {
    return since(now, start) >= S(c, SET_SHIFT_WAIT_MS);
}

static void wait_4wd(controller_t *c, uint32_t now) {
    fourwd_t *f = &c->fwd;
    if (!f->waiting) return;
    uint8_t r = motion_check(c, now, false, S(c, SET_4WD_MAX_KMH));
    if (r == REJ_NONE && c->diff.moving) r = REJ_BUSY;  // a diff unlock finishing
    if (r == REJ_NONE) { try_start_4wd(c, now); return; }
    if (!speed_reason(r) && r != REJ_BUSY) { reject(c, r); fwd_forget(c); return; }
    if (wait_over(c, f->wait_start_ms, now)) { reject(c, REJ_WAIT_TIMEOUT); fwd_forget(c); }
}

static void wait_diff(controller_t *c, uint32_t now) {
    diff_t *d = &c->diff;
    if (!d->waiting) return;
    uint8_t r = motion_check(c, now, false, S(c, SET_DIFF_MAX_KMH));
    if (r == REJ_NONE) {
        d->waiting = false;
        uint8_t old = d->target_pct;
        d->target_pct = d->wait_pct;
        r = try_start_diff(c, now);
        if (r) { d->target_pct = d->moving ? old : d->pct; reject(c, r); }
        return;
    }
    if (!speed_reason(r)) { d->waiting = false; reject(c, r); return; }
    if (wait_over(c, d->wait_start_ms, now)) { d->waiting = false; reject(c, REJ_WAIT_TIMEOUT); }
}

// Throttle hold: only while a shift runs AND the Teryx was stopped when it
// started. If it starts rolling the hold drops and stays off for that shift,
// so throttle is never cut while moving.
static void update_throttle_hold(controller_t *c, uint32_t now) {
    bool shifting = c->fwd.moving || c->diff.moving;
    if (!shifting || !S(c, SET_SHIFT_THROTTLE_HOLD)) {
        c->throttle_hold = false;
        c->throttle_hold_blocked = false;
        return;
    }
    if (!stopped(c, now)) {
        c->throttle_hold = false;
        c->throttle_hold_blocked = true;
        return;
    }
    if (!c->throttle_hold_blocked) c->throttle_hold = true;
}

static void winch_disarm(controller_t *c) {
    c->winch.armed = false;
}

static void try_arm_winch(controller_t *c, uint32_t now) {
    uint8_t r = motion_check(c, now, true, 0);                       // rule 6
    if (r) { reject(c, r); c->winch.interlock_ms = now ? now : 1; return; }
    c->winch.armed = true;
    c->winch.last_activity_ms = now;
}

static void send_set_ack(controller_t *c, uint8_t key, uint8_t result, cb_send_fn send, void *u) {
    can_frame_t f = {.id = CAN_ID_PICO_SET_ACK, .dlc = 4};
    f.data[0] = key;
    f.data[1] = result;
    put_u16(&f.data[2], settings_get(&c->settings, key));
    send(&f, u);
}

void ctl_on_frame(controller_t *c, const can_frame_t *f, uint32_t now,
                  cb_send_fn send, void *user) {
    if (f->ext) return;
    switch (f->id) {
    case CAN_ID_PI_HEARTBEAT:
        if (f->dlc < 2) { reject(c, REJ_BAD_FRAME); return; }
        c->hb_seen = true;
        c->last_hb_ms = now;
        c->dash_state = f->data[1];
        break;

    case CAN_ID_MC_SPEED:
        if (f->dlc < 3) return;
        c->speed_seen = true;
        c->last_speed_ms = now;
        c->speed_x10 = get_u16(&f->data[0]);
        c->mc_dir = f->data[2];
        break;

    case CAN_ID_PI_LIGHTS:
        if (f->dlc < 7) { reject(c, REJ_BAD_FRAME); return; }
        memcpy(c->light_req, f->data, L_COUNT);
        if (f->data[5] != c->effect) c->effect_start_ms = now;
        c->effect = f->data[5] < FX_COUNT ? f->data[5] : FX_NONE;
        c->light_flags = f->data[6];
        break;

    case CAN_ID_PI_DRIVE: {
        // Act on a CHANGE of value only (the first frame after boot counts).
        // The dash resends every second so a rebooted Pico catches up, but a
        // refused 4WD request must not quietly happen later when we slow down.
        if (f->dlc < 2) { reject(c, REJ_BAD_FRAME); return; }
        if (ctl_locked(c)) {
            // Locked: no 4WD / diff changes. Remember the values so nothing
            // happens by surprise on unlock (change-only rule).
            if (c->drive_seen && (f->data[0] != c->last_drive[0] || f->data[1] != c->last_drive[1]))
                reject(c, REJ_INTERLOCK);
            c->drive_seen = true;
            c->last_drive[0] = f->data[0];
            c->last_drive[1] = f->data[1];
            break;
        }
        bool first = !c->drive_seen;
        c->drive_seen = true;
        bool fwd_valid = f->data[0] == REQ_2WD || f->data[0] == REQ_4WD;
        if ((first || f->data[0] != c->last_drive[0]) && fwd_valid) {
            c->fwd.target = f->data[0];
            try_start_4wd(c, now);
        } else if (fwd_valid && c->fwd.state == FWD_UNKNOWN && !c->fwd.moving &&
                   motion_check(c, now, false, S(c, SET_4WD_MAX_KMH)) == REJ_NONE) {
            // Position unknown (after boot, or the first request was refused
            // before the Shinegle was heard): a resend quietly homes it to the
            // end the dash wants, once it's safe. No reject if it isn't.
            c->fwd.target = f->data[0];
            try_start_4wd(c, now);
        }
        if ((first || f->data[1] != c->last_drive[1]) && f->data[1] <= 100)
            diff_request(c, f->data[1], now);
        c->last_drive[0] = f->data[0];
        c->last_drive[1] = f->data[1];
        break;
    }

    case CAN_ID_PI_HOLD: {
        if (f->dlc < 3) { reject(c, REJ_BAD_FRAME); return; }
        c->last_hold_ms = now;
        int8_t tray = (int8_t)f->data[0];
        int8_t winch = (int8_t)f->data[1];
        c->hold_tray = tray > 0 ? 1 : tray < 0 ? -1 : 0;
        c->hold_winch = winch > 0 ? 1 : winch < 0 ? -1 : 0;
        c->hold_winch_timed_s = f->dlc >= 4 ? f->data[3] : 0;
        bool arm = (f->data[2] & HOLD_FLAG_WINCH_ARMED) != 0;
        if (ctl_locked(c)) {
            // Locked: no tray, no winch. Refuse a new press once, not every frame.
            if ((c->hold_tray && c->hold_tray != c->tray.prev_req) ||
                (c->hold_winch && c->hold_winch != c->winch.prev_req) || (arm && !c->winch.armed))
                reject(c, REJ_INTERLOCK);
            c->tray.prev_req = c->hold_tray;
            c->winch.prev_req = c->hold_winch;
            c->hold_tray = 0;
            c->hold_winch = 0;
            c->hold_winch_timed_s = 0;
            break;
        }
        if (arm && !c->winch.armed) try_arm_winch(c, now);
        else if (!arm && c->winch.armed) winch_disarm(c);
        break;
    }

    case CAN_ID_PI_SETTING: {
        if (f->dlc < 4) { reject(c, REJ_BAD_FRAME); return; }
        uint8_t key = f->data[0];
        uint8_t res = SET_ACK_OK;
        if (ctl_locked(c)) {
            res = SET_ACK_LOCKED;  // no setting changes while locked
        } else if (key == SET_CMD_SAVE) {
            c->out.save_settings = true;
        } else if (key == SET_CMD_DEFAULTS) {
            settings_defaults(&c->settings);
        } else if (key == SET_CMD_CLEAR_FAULTS) {
            c->latched = 0;
            if (c->fwd.state == FWD_FAULT) c->fwd.state = FWD_UNKNOWN;
        } else {
            res = (uint8_t)settings_set(&c->settings, key, get_u16(&f->data[2]));
        }
        if (res == SET_ACK_OK) c->settings_from_flash_or_dash = true;
        send_set_ack(c, key, res, send, user);
        break;
    }

    case CAN_ID_PI_FW_UPDATE:
        if (f->dlc < 2 || get_u16(f->data) != FW_UPDATE_MAGIC) {
            reject(c, REJ_BAD_FRAME);
            return;
        }
        if (!ctl_parked(c, now)) { reject(c, REJ_NOT_PARKED); return; }
        if (ctl_locked(c)) { reject(c, REJ_INTERLOCK); return; }  // no updates while locked
        c->bootloader_pending = true;
        break;

    case CAN_ID_PI_LOCK: {
        bool was = ctl_locked(c);
        vlock_on_frame(&c->lock, f->data, f->dlc, ctl_can_lock(c, now), now);
        if (!was && ctl_locked(c)) stop_all_motion(c);
        send_lock(c, now, send, user);  // answer straight away, not on the next 100 ms
        break;
    }

    default:
        break;
    }
}

// ---------------------------------------------------------------------------
// Tick: actuators
// ---------------------------------------------------------------------------

static void stop_all_motion(controller_t *c) {
    if (c->fwd.waiting) fwd_forget(c);
    c->diff.waiting = false;
    if (c->fwd.moving) { c->fwd.moving = false; c->fwd.state = FWD_UNKNOWN; }
    if (c->diff.moving) {
        c->diff.moving = false;
        c->diff.target_pct = c->diff.pct;  // don't carry on later by surprise
    }
    c->tray.dir = 0;
    c->hold_tray = 0;
    c->hold_winch = 0;
    c->hold_winch_timed_s = 0;
    winch_disarm(c);
}

static void run_4wd(controller_t *c, uint32_t now, cb_out_t *o) {
    fourwd_t *f = &c->fwd;
    if (!f->moving) return;
    uint32_t run = since(now, f->start_ms);
    uint16_t amps = c->in.i_da[ACT_4WD];
    bool engage = f->state == FWD_TO_4WD;
    uint8_t done_state = engage ? FWD_4WD : FWD_2WD;

    if (run > INRUSH_IGNORE_MS) {
        if (amps > S(c, SET_4WD_OVERCURRENT_DA)) {                   // rule 3
            f->moving = false;
            f->state = FWD_FAULT;
            c->latched |= BIT(FAULT_4WD_OVERCURRENT);
            return;
        }
        if (amps > END_STOP_CURRENT_DA) f->saw_current = true;
        // Actuators with built-in limit switches stop drawing current at the end.
        if (f->saw_current && amps <= END_STOP_CURRENT_DA) {
            if (!f->low_since_ms) f->low_since_ms = now ? now : 1;
            if (since(now, f->low_since_ms) >= END_STOP_HOLD_MS) {
                f->moving = false;
                f->state = done_state;
                return;
            }
        } else {
            f->low_since_ms = 0;
        }
    }
    if (run >= S(c, SET_4WD_MAX_RUN_MS)) {
        f->moving = false;
        f->state = done_state;  // probably there; flag it so it gets looked at
        // From an unknown position with no current seen, it was most likely
        // already at the end stop, so don't raise a fault for that.
        if (f->saw_current || !f->from_unknown) c->latched |= BIT(FAULT_4WD_TIMEOUT);
        return;
    }
    o->act_dir[ACT_4WD] = (int8_t)((engage ? 1 : -1) * FOURWD_ENGAGE_DIR);
    o->act_duty[ACT_4WD] = 255;
}

static uint8_t pot_to_pct(const controller_t *c, uint16_t raw, bool *ok) {
    int32_t lo = S(c, SET_DIFF_POT_MIN), hi = S(c, SET_DIFF_POT_MAX);
    int32_t span = hi - lo;
    *ok = false;
    if (span == 0) return PCT_UNKNOWN;
    int32_t a = lo < hi ? lo : hi, b = lo < hi ? hi : lo;
    if ((int32_t)raw < a - POT_MARGIN || (int32_t)raw > b + POT_MARGIN) return PCT_UNKNOWN;
    int32_t pct = ((int32_t)raw - lo) * 100 / span;
    if (pct < 0) pct = 0;
    if (pct > 100) pct = 100;
    *ok = true;
    return (uint8_t)pct;
}

static void run_diff(controller_t *c, uint32_t now, cb_out_t *o) {
    diff_t *d = &c->diff;
    bool ok = false;
    d->pct = c->in.pot_ok ? pot_to_pct(c, c->in.diff_pot_raw, &ok) : PCT_UNKNOWN;
    if (!ok) d->pct = PCT_UNKNOWN;
    if (!d->moving) return;

    if (!ok) {  // pot unplugged or wire broken
        d->moving = false;
        c->latched |= BIT(FAULT_DIFF_POT_STUCK);
        return;
    }
    int err = (int)d->target_pct - (int)d->pct;
    // Rule 4: the speed limit applies to starting AND carrying on while adding
    // lock. If we speed up past it mid-move, stop where we are. Unlocking
    // carries on at any speed (but still needs a known speed, rule 2).
    if (!ctl_speed_valid(c, now) ||
        (err > 0 && c->speed_x10 >= S(c, SET_DIFF_MAX_KMH) * 10u)) {
        d->moving = false;
        d->target_pct = d->pct;
        return;
    }
    if (err <= DIFF_DEADBAND_PCT && err >= -DIFF_DEADBAND_PCT) { d->moving = false; return; }

    uint32_t run = since(now, d->start_ms);
    if (run >= S(c, SET_DIFF_MAX_RUN_MS)) {
        d->moving = false;
        c->latched |= BIT(FAULT_DIFF_TIMEOUT);
        return;
    }
    if (run > INRUSH_IGNORE_MS && c->in.i_da[ACT_DIFF] > S(c, SET_DIFF_OVERCURRENT_DA)) {
        d->moving = false;
        c->latched |= BIT(FAULT_DIFF_OVERCURRENT);
        return;
    }
    // Pot must keep moving while we drive the motor.
    int32_t span = (int32_t)S(c, SET_DIFF_POT_MAX) - (int32_t)S(c, SET_DIFF_POT_MIN);
    if (span < 0) span = -span;
    int32_t moved = (int32_t)c->in.diff_pot_raw - (int32_t)d->ref_raw;
    if (moved < 0) moved = -moved;
    if (moved * 100 >= span) {  // 1 % of travel
        d->ref_raw = c->in.diff_pot_raw;
        d->last_move_ms = now;
    } else if (since(now, d->last_move_ms) >= DIFF_STUCK_MS) {
        d->moving = false;
        c->latched |= BIT(FAULT_DIFF_POT_STUCK);
        return;
    }
    int mag = err < 0 ? -err : err;
    int duty = DIFF_MIN_DUTY + mag * 8;
    if (duty > 255) duty = 255;
    o->act_dir[ACT_DIFF] = (int8_t)((err > 0 ? 1 : -1) * DIFF_LOCK_DIR);
    o->act_duty[ACT_DIFF] = (uint8_t)duty;
}

static void run_tray(controller_t *c, uint32_t now, cb_out_t *o, bool dash_ok) {
    tray_t *t = &c->tray;
    bool at_down = (c->in.din & BIT(IN_TRAY_DOWN)) != 0;
    bool at_up = (c->in.din & BIT(IN_TRAY_UP)) != 0;
    int32_t full = S(c, SET_TRAY_FULL_TRAVEL_MS);

    if (at_down) t->pos_ms = 0;
    if (at_up) t->pos_ms = full;
    if (at_down && at_up) {  // both "at limit": a wire is off. Don't move.
        t->dir = 0;
        t->prev_req = c->hold_tray;
        return;
    }

    int8_t req = dash_ok ? c->hold_tray : 0;
    bool new_press = req != 0 && req != t->prev_req;
    t->prev_req = req;

    if (t->dir != 0) {
        // Rule 5: stop on release, limit, overcurrent, timeout, or not stopped.
        uint32_t run = since(now, t->start_ms);
        bool stop = req != t->dir;
        if ((t->dir > 0 && at_up) || (t->dir < 0 && at_down)) stop = true;
        if (motion_check(c, now, true, 0) != REJ_NONE) stop = true;
        if (run > INRUSH_IGNORE_MS && c->in.i_da[ACT_TRAY] > S(c, SET_TRAY_OVERCURRENT_DA)) {
            c->latched |= BIT(FAULT_TRAY_OVERCURRENT);
            stop = true;
        }
        if (run >= S(c, SET_TRAY_MAX_RUN_MS)) {
            c->latched |= BIT(FAULT_TRAY_TIMEOUT);
            stop = true;
        }
        if (stop) {
            t->dir = 0;
            t->prev_req = req;  // must let go and press again
            // Fall through to also catch a direction swap press next tick.
        }
    } else if (new_press) {
        uint8_t r = motion_check(c, now, true, 0);
        if (!r && c->winch.active != 0) r = REJ_INTERLOCK;  // not while winching
        if (!r && ((req > 0 && at_up) || (req < 0 && at_down))) r = REJ_AT_LIMIT;
        if (r) {
            reject(c, r);
        } else {
            t->dir = req;
            t->start_ms = now;
            c->latched &= (uint16_t)~(BIT(FAULT_TRAY_TIMEOUT) | BIT(FAULT_TRAY_OVERCURRENT));
        }
    }

    if (t->dir != 0) {
        if (t->pos_ms >= 0) {
            t->pos_ms += t->dir * (int32_t)TICK_MS;
            if (t->pos_ms < 0) t->pos_ms = 0;
            if (t->pos_ms > full) t->pos_ms = full;
        }
        o->act_dir[ACT_TRAY] = (int8_t)(t->dir * TRAY_UP_DIR);
        o->act_duty[ACT_TRAY] = 255;
    }
}

static void run_winch(controller_t *c, uint32_t now, cb_out_t *o, bool dash_ok) {
    winch_t *w = &c->winch;
    // Rule 6: disarm on lost dash, key off, moving or unknown speed, idle timeout.
    if (w->armed) {
        uint8_t r = motion_check(c, now, true, 0);
        if (r) {
            winch_disarm(c);
            reject(c, r);
            w->interlock_ms = now ? now : 1;
        } else if (since(now, w->last_activity_ms) >= S(c, SET_WINCH_AUTO_DISARM_S) * 1000u) {
            winch_disarm(c);
        }
    }

    int8_t req = (w->armed && dash_ok) ? c->hold_winch : 0;
    if (c->hold_winch != 0 && !w->armed && c->hold_winch != w->prev_req) {
        reject(c, REJ_NOT_ARMED);
        w->interlock_ms = now ? now : 1;
    }
    // Not while the tray is moving.
    if (req != 0 && c->tray.dir != 0) {
        if (req != w->prev_req) reject(c, REJ_INTERLOCK);
        req = 0;
    }
    // Handheld remote has the winch: the dash keeps its hands off.
    if (req != 0 && (c->in.din & BIT(IN_WINCH_REMOTE))) {
        if (req != w->prev_req) reject(c, REJ_REMOTE_IN_USE);
        req = 0;
    }
    // Timed pull. A new press (or a release) starts the timer over.
    bool timed = c->hold_winch_timed_s != 0;
    if (c->hold_winch != w->prev_req || !timed) {
        w->timed_running = false;
        w->timed_done = false;
    }
    if (timed && w->timed_done) req = 0;
    w->prev_req = c->hold_winch;

    if (req != w->active) {
        if (w->active != 0) {
            w->active = 0;  // always pass through off first
            w->off_since_ms = now;
        }
        if (req != 0 && since(now, w->off_since_ms) >= S(c, SET_WINCH_DEAD_TIME_MS)) {
            w->active = req;
        }
    }
    if (timed && !w->timed_done) {
        if (w->active != 0 && !w->timed_running) {
            w->timed_running = true;
            w->timed_start_ms = now;
        } else if (w->active == 0 && w->timed_running) {
            w->timed_done = true;   // cut short (remote, interlock...): don't restart by itself
        }
        uint32_t secs = c->hold_winch_timed_s;
        if (secs > S(c, SET_WINCH_TIMED_MAX_S)) secs = S(c, SET_WINCH_TIMED_MAX_S);
        if (w->timed_running && since(now, w->timed_start_ms) >= secs * 1000u) {
            w->timed_done = true;
            w->active = 0;
            w->off_since_ms = now;
        }
    }
    if (w->active != 0) w->last_activity_ms = now;

    // In and out can never be on together. Belt and braces.
    if (w->active > 0) o->relays |= BIT(R_WINCH_IN);
    else if (w->active < 0) o->relays |= BIT(R_WINCH_OUT);
    if (w->armed) o->relays |= BIT(R_WINCH_ISOLATOR);
}

// ---------------------------------------------------------------------------
// Tick: lights
// ---------------------------------------------------------------------------

// Returns 0-255: how much of the requested level bar i shows right now.
static uint8_t effect_gain(const controller_t *c, int bar, uint32_t now, bool dimmable) {
    uint32_t t = since(now, c->effect_start_ms);
    switch (c->effect) {
    case FX_STROBE: {  // three quick flashes, then a pause
        uint32_t p = t % 700u;
        return (p < 300u && (p / 50u) % 2u == 0u) ? 255 : 0;
    }
    case FX_CHASE:
        return (uint8_t)(((t / 150u) % 4u) == (uint32_t)bar ? 255 : 0);
    case FX_OUTSIDE_ONLY:
        return (bar == L_FRONT_1 || bar == L_FRONT_4) ? 255 : 0;
    case FX_INSIDE_ONLY:
        return (bar == L_FRONT_2 || bar == L_FRONT_3) ? 255 : 0;
    case FX_BREATHE: {
        uint32_t p = t % 2000u;
        if (!dimmable) return p < 1000u ? 255 : 0;
        uint32_t ramp = p < 1000u ? p : 2000u - p;
        return (uint8_t)(ramp * 255u / 1000u);
    }
    case FX_SOS: {
        // dot = 1 unit (150 ms). S = dot dot dot, O = dash dash dash.
        static const uint8_t pattern[] = {
            1,0,1,0,1,0,0,0,  1,1,1,0,1,1,1,0,1,1,1,0,0,0,  1,0,1,0,1,0,0,0,0,0,0,0,
        };
        uint32_t i = (t / 150u) % sizeof(pattern);
        return pattern[i] ? 255 : 0;
    }
    default:
        return 255;
    }
}

static void run_lights(controller_t *c, uint32_t now, cb_out_t *o) {
    uint16_t mask = S(c, SET_LIGHT_DIMMABLE_MASK);
    for (int i = 0; i < L_COUNT; i++) {
        bool dimmable = (mask & (1u << i)) != 0;
        uint8_t req = c->light_req[i];
        if (!dimmable && req) req = 255;  // on/off bars: any level means full on
        bool fx = i <= L_FRONT_4 && c->effect != FX_NONE && req;
        bool zone = c->effect == FX_OUTSIDE_ONLY || c->effect == FX_INSIDE_ONLY;
        uint8_t target = req;
        if (fx) target = (uint8_t)((uint32_t)req * effect_gain(c, i, now, dimmable) / 255u);

        uint8_t lvl = c->light_level[i];
        if ((fx && !zone) || !dimmable) {
            lvl = target;  // flashing effects and on/off bars switch straight away
        } else if (lvl < target) {
            lvl = (uint8_t)(target - lvl > FADE_STEP ? lvl + FADE_STEP : target);
        } else if (lvl > target) {
            lvl = (uint8_t)(lvl - target > FADE_STEP ? lvl - FADE_STEP : target);
        }
        c->light_level[i] = lvl;
        o->light[i] = lvl;
    }
}

// ---------------------------------------------------------------------------
// Tick: status frames
// ---------------------------------------------------------------------------

static uint8_t pico_state(const controller_t *c, uint32_t now) {
    if (!c->hb_seen && since(now, c->boot_ms) < DASH_BOOT_GRACE_MS) return CB_STATE_BOOT;
    if (!ctl_dash_ok(c, now) || !c->in.io_ok) return CB_STATE_FAILSAFE;
    if (c->faults) return CB_STATE_DEGRADED;
    return CB_STATE_OK;
}

static uint8_t tray_state(const controller_t *c) {
    bool at_down = (c->in.din & BIT(IN_TRAY_DOWN)) != 0;
    bool at_up = (c->in.din & BIT(IN_TRAY_UP)) != 0;
    if (at_down && at_up) return TRAY_FAULT;
    if (c->tray.dir > 0) return TRAY_RAISING;
    if (c->tray.dir < 0) return TRAY_LOWERING;
    if (at_down) return TRAY_DOWN;
    if (at_up) return TRAY_UP;
    return TRAY_MID;
}

static uint8_t clamp_u8(uint32_t v) { return v > 255u ? 255u : (uint8_t)v; }

static void send_status(controller_t *c, uint32_t now, cb_send_fn send, void *u) {
    can_frame_t f = {.id = CAN_ID_PICO_STATUS, .dlc = 8};
    f.data[0] = c->tx_counter++;
    put_u16(&f.data[1], c->faults);
    f.data[3] = c->in.din;
    f.data[4] = pico_state(c, now) | (c->settings_from_flash_or_dash ? 0 : STATE_BIT_ON_DEFAULTS);
    if (c->fwd.waiting) f.data[4] |= STATE_BIT_4WD_WAIT;
    if (c->diff.waiting) f.data[4] |= STATE_BIT_DIFF_WAIT;
    if (c->throttle_hold) f.data[4] |= STATE_BIT_THROTTLE_HOLD;
    f.data[5] = (uint8_t)((c->reject_count << 4) | (c->reject_reason & 0x0F));
    uint8_t flags = 0;
    if (c->winch.armed) flags |= FLAG_WINCH_ARMED;
    if (ctl_speed_valid(c, now)) flags |= FLAG_SPEED_VALID;
    if (reverse_active(c, now)) flags |= FLAG_REVERSE;
    if (c->shutting_down) flags |= FLAG_SHUTDOWN_REQUEST;
    if (ctl_parked(c, now)) flags |= FLAG_PARKED;
    f.data[6] = flags;
    f.data[7] = ctl_speed_valid(c, now) ? clamp_u8((c->speed_x10 + 5u) / 10u) : 0xFF;
    send(&f, u);

    can_frame_t o = {.id = CAN_ID_PICO_OUTPUTS, .dlc = 8};
    o.data[0] = c->out.relays;
    memcpy(&o.data[1], c->out.light, L_COUNT);
    o.data[6] = c->effect;
    send(&o, u);

    can_frame_t a = {.id = CAN_ID_PICO_ACT, .dlc = 8};
    a.data[0] = c->diff.pct;
    a.data[1] = c->fwd.state;
    a.data[2] = tray_state(c);
    for (int i = 0; i < ACT_COUNT; i++) a.data[3 + i] = clamp_u8(c->in.i_da[i]);
    int32_t full = S(c, SET_TRAY_FULL_TRAVEL_MS);
    a.data[6] = c->tray.pos_ms < 0 ? PCT_UNKNOWN : (uint8_t)(c->tray.pos_ms * 100 / full);
    a.data[7] = c->diff.waiting ? c->diff.wait_pct : c->diff.target_pct;
    send(&a, u);
}

static void send_lock(controller_t *c, uint32_t now, cb_send_fn send, void *u) {
    can_frame_t f = {.id = CAN_ID_PICO_LOCK, .dlc = 8};
    vlock_status(&c->lock, now, ctl_locked(c), f.data);
    send(&f, u);
}

static void send_power(controller_t *c, uint32_t now, cb_send_fn send, void *u) {
    can_frame_t f = {.id = CAN_ID_PICO_POWER, .dlc = 8};
    put_u16(&f.data[0], c->in.aux_mv);
    f.data[2] = (uint8_t)c->in.temp_c;
    put_u16(&f.data[3], c->in.diff_pot_raw);  // raw, so the dash can calibrate keys 14/15
    f.data[5] = FW_VERSION_MAJOR;
    f.data[6] = FW_VERSION_MINOR;
    f.data[7] = c->winch.armed ? clamp_u8(since(now, c->winch.last_activity_ms) / 1000u) : 0;
    send(&f, u);
}

// ---------------------------------------------------------------------------
// Tick
// ---------------------------------------------------------------------------

void ctl_tick(controller_t *c, const cb_in_t *in, cb_out_t *out, cb_send_fn send, void *user) {
    uint32_t now = in->now_ms;
    bool save = c->out.save_settings;
    c->in = *in;
    memset(out, 0, sizeof(*out));
    out->save_settings = save;

    bool dash_ok = ctl_dash_ok(c, now);
    bool ign = ignition(c);

    // Rule 1: lost dash stops everything that moves. Lights stay as they were.
    // Same if the I2C parts stop answering, since we can't trust the inputs.
    if (!dash_ok || !in->io_ok) stop_all_motion(c);

    // Hold-to-run frames stopped coming: let go.
    if (since(now, c->last_hold_ms) > S(c, SET_HOLD_TIMEOUT_MS)) {
        c->hold_tray = 0;
        c->hold_winch = 0;
    c->hold_winch_timed_s = 0;
    }

    // Vehicle lock: nothing moves, lights off, drive inhibited. The lock
    // sits in flash, so this holds from the first tick after a power cut.
    vlock_tick(&c->lock, now);
    bool locked = ctl_locked(c);
    if (locked && (anything_moving(c) || c->fwd.waiting || c->diff.waiting || c->winch.armed))
        stop_all_motion(c);

    // Rule 8: key-off. Keep power on until the Pi has shut down, or time's up.
    if (ign) {
        c->power_hold = true;
        c->shutting_down = false;
    } else {
        if (c->tray.dir != 0 || fwd_busy(c) || diff_busy(c)) stop_all_motion(c);
        winch_disarm(c);
        if (c->power_hold && !c->shutting_down) {
            c->shutting_down = true;
            c->keyoff_ms = now;
        }
        if (c->shutting_down && c->power_hold) {
            uint32_t last = c->keyoff_ms;
            if (c->hb_seen && (int32_t)(c->last_hb_ms - last) > 0) last = c->last_hb_ms;
            bool pi_gone = !dash_ok && since(now, last) >= SHUTDOWN_GRACE_MS;
            if (pi_gone || since(now, c->keyoff_ms) >= S(c, SET_SHUTDOWN_WAIT_S) * 1000u) {
                c->power_hold = false;
            }
        }
        if (!c->power_hold) c->shutting_down = false;
    }

    wait_diff(c, now);
    wait_4wd(c, now);
    run_diff(c, now, out);
    run_4wd(c, now, out);
    update_throttle_hold(c, now);
    out->throttle_hold = c->throttle_hold;
    run_tray(c, now, out, dash_ok);
    run_winch(c, now, out, dash_ok);
    if (locked) memset(c->light_req, 0, sizeof(c->light_req));
    run_lights(c, now, out);

    // Rule 7 and the simple relays.
    bool rev = reverse_active(c, now);
    if (!locked && ((c->light_flags & LIGHTS_FLAG_REAR_ON) || ((c->light_flags & LIGHTS_FLAG_AUTO_REAR) && rev)))
        out->relays |= BIT(R_REAR);
    bool any_front = false;
    for (int i = L_FRONT_1; i <= L_FRONT_4; i++) any_front |= c->light_req[i] != 0;
    if (any_front) out->relays |= BIT(R_TRAILER_TAIL);
    if (in->din & BIT(IN_BRAKE)) out->relays |= BIT(R_TRAILER_BRAKE);
    if (ign) out->relays |= BIT(R_ACCESSORY);
    if (c->power_hold) out->relays |= BIT(R_POWER_HOLD);
    out->drive_inhibit = locked;
    if (c->lock.dirty) {
        out->save_lock = true;
        c->lock.dirty = false;
    }

    // Faults
    uint16_t live = 0;
    if (!dash_ok && (c->hb_seen || since(now, c->boot_ms) >= DASH_BOOT_GRACE_MS))
        live |= BIT(FAULT_DASH_LINK);
    if (ign && !ctl_speed_valid(c, now)) live |= BIT(FAULT_SPEED_UNKNOWN);
    if (c->fwd.state == FWD_FAULT) live |= BIT(FAULT_4WD_OVERCURRENT);
    if ((in->din & BIT(IN_TRAY_DOWN)) && (in->din & BIT(IN_TRAY_UP))) live |= BIT(FAULT_TRAY_LIMIT_SWITCH);
    if (c->winch.interlock_ms && since(now, c->winch.interlock_ms) < 2000u) live |= BIT(FAULT_WINCH_INTERLOCK);
    if (in->aux_mv && in->aux_mv < S(c, SET_LOW_12V_MV)) {
        if (!c->low12_since_ms) c->low12_since_ms = now ? now : 1;
        if (since(now, c->low12_since_ms) >= LOW_12V_HOLD_MS) live |= BIT(FAULT_LOW_12V);
    } else {
        c->low12_since_ms = 0;
    }
    if (in->temp_c >= PICO_HOT_C) live |= BIT(FAULT_PICO_HOT);
    if (c->watchdog_reset && since(now, c->boot_ms) < WATCHDOG_FLAG_MS) live |= BIT(FAULT_WATCHDOG_RESET);
    if (!in->io_ok) live |= BIT(FAULT_IO_BUS);
    c->faults = live | c->latched;

    // Firmware update: outputs go safe first, the hardware layer reboots.
    if (c->bootloader_pending) {
        if (ctl_parked(c, now)) {
            uint8_t keep = out->relays & (BIT(R_POWER_HOLD) | BIT(R_ACCESSORY));
            memset(out->act_dir, 0, sizeof(out->act_dir));
            memset(out->act_duty, 0, sizeof(out->act_duty));
            out->relays = keep;
            out->enter_bootloader = true;
        }
        c->bootloader_pending = false;
    }

    c->out = *out;

    if (since(now, c->last_tx_fast_ms) >= 100u) {
        c->last_tx_fast_ms = now;
        send_status(c, now, send, user);
        send_lock(c, now, send, user);
    }
    if (since(now, c->last_tx_slow_ms) >= 1000u) {
        c->last_tx_slow_ms = now;
        send_power(c, now, send, user);
    }
}
