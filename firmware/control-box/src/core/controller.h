// Teryx control box: the control logic and safety rules.
//
// This is plain C with no hardware calls, so the same code runs on the Pico 2
// and in the host build / unit tests. The hardware layer reads the inputs,
// calls ctl_tick() every TICK_MS and writes the outputs it gets back. CAN
// frames are passed in with ctl_on_frame() and sent out through a callback.
#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "protocol.h"
#include "settings.h"
#include "lock.h"

// Digital inputs (MCP23017 port B), as logical bits: 1 = active.
// The two tray limits are normally closed, so 1 = "at limit or wire broken".
enum {
    IN_IGNITION = 0, IN_BRAKE = 1, IN_REVERSE = 2, IN_TRAY_DOWN = 3,
    IN_TRAY_UP = 4, IN_WINCH_REMOTE = 5, IN_PARK = 6, IN_TRAILER = 7,
};
#define BIT(n) (1u << (n))

// Relays (MCP23017 port A). Bit 0 = relay 1.
enum {
    R_REAR = 0, R_TRAILER_TAIL = 1, R_TRAILER_BRAKE = 2, R_WINCH_IN = 3,
    R_WINCH_OUT = 4, R_WINCH_ISOLATOR = 5, R_ACCESSORY = 6, R_POWER_HOLD = 7,
};

enum { ACT_DIFF = 0, ACT_4WD = 1, ACT_TRAY = 2, ACT_COUNT = 3 };
enum { L_FRONT_1 = 0, L_FRONT_2, L_FRONT_3, L_FRONT_4, L_INTERIOR, L_COUNT };

typedef struct {
    uint32_t now_ms;
    uint8_t din;            // IN_* bits, logical
    bool io_ok;             // MCP23017 and ADS1115 answering
    bool pot_ok;            // diff pot reading is fresh
    uint16_t diff_pot_raw;  // ADS1115 counts
    uint16_t aux_mv;        // 12V aux battery, mV
    uint16_t i_da[ACT_COUNT]; // actuator currents, 0.1 A
    int8_t temp_c;          // Pico die temperature
} cb_in_t;

typedef struct {
    uint8_t relays;            // R_* bits, logical (1 = relay on)
    uint8_t light[L_COUNT];    // PWM duty 0-255
    int8_t act_dir[ACT_COUNT]; // +1 extend (RPWM), -1 retract (LPWM), 0 off
    uint8_t act_duty[ACT_COUNT];
    bool enter_bootloader;     // hardware layer: make outputs safe, reboot to USB boot
    bool save_settings;        // hardware layer: write settings to flash, then clear
    bool throttle_hold;        // ask the Shinegle to hold throttle (how is TBC until it's decoded)
    bool drive_inhibit;        // vehicle locked: no drive at all (how is TBC, docs/vehicle-lock.md)
    bool save_lock;            // hardware layer: write c->lock.saved to its flash sector, then clear
} cb_out_t;

typedef void (*cb_send_fn)(const can_frame_t *f, void *user);

typedef struct {
    uint8_t state;          // FWD_*
    uint8_t target;         // REQ_2WD / REQ_4WD / DRIVE_NO_CHANGE
    bool from_unknown;
    bool moving;
    bool saw_current;
    uint32_t start_ms;
    uint32_t low_since_ms;
    bool waiting;           // asked for, waiting for the right speed (or timing out)
    uint32_t wait_start_ms;
} fourwd_t;

typedef struct {
    uint8_t target_pct;     // PCT_UNKNOWN until the dash asks
    bool moving;
    uint32_t start_ms;
    uint16_t ref_raw;       // pot reading when it last moved
    uint32_t last_move_ms;
    uint8_t pct;            // PCT_UNKNOWN if the pot can't be trusted
    bool waiting;           // adding lock asked for, waiting to slow down
    uint8_t wait_pct;       // what it's waiting to move to
    uint32_t wait_start_ms;
} diff_t;

typedef struct {
    int8_t dir;             // +1 up, -1 down, 0 stopped
    int8_t prev_req;
    uint32_t start_ms;
    int32_t pos_ms;         // estimated travel from the bottom, in ms of run time
} tray_t;

typedef struct {
    bool armed;
    int8_t active;          // +1 in, -1 out, 0 off
    uint32_t off_since_ms;
    uint32_t last_activity_ms;
    int8_t prev_req;
    uint32_t interlock_ms;  // when an interlock last blocked a request
    // Timed pull ("pull for 5 s"): the Pico times it, not just the dash.
    bool timed_running;     // motor on as part of a timed pull
    bool timed_done;        // pull finished or was cut short: needs a release first
    uint32_t timed_start_ms;
} winch_t;

typedef struct {
    settings_t settings;
    bool settings_from_flash_or_dash;

    uint32_t boot_ms;
    bool watchdog_reset;

    // Dash link
    bool hb_seen;
    uint32_t last_hb_ms;
    uint8_t dash_state;

    // Shinegle
    bool speed_seen;
    uint32_t last_speed_ms;
    uint16_t speed_x10;     // 0.1 km/h
    uint8_t mc_dir;         // 0 N 1 F 2 R

    // Lights
    uint8_t light_req[L_COUNT];
    uint8_t effect;
    uint8_t light_flags;
    uint8_t light_level[L_COUNT];
    uint32_t effect_start_ms;

    // Drive requests act on change only
    bool drive_seen;
    uint8_t last_drive[2];

    // Hold-to-run
    int8_t hold_tray, hold_winch;
    uint8_t hold_winch_timed_s;   // 0 = plain hold-to-run
    uint32_t last_hold_ms;

    fourwd_t fwd;
    diff_t diff;
    // Throttle hold while a shift runs from a standstill. Never applied once
    // moving: if the Teryx rolls, it drops and stays off until the shift ends.
    bool throttle_hold;
    bool throttle_hold_blocked;
    tray_t tray;
    winch_t winch;

    // Power
    bool power_hold;
    bool shutting_down;
    bool sentry_hold;       // key off, power kept on because the Pi asked for sentry
    bool sentry_flat;       // 12V stayed under setting 32: no sentry until the key goes on
    bool sentry_low;        // 12V under setting 32 since sentry_low_ms
    uint32_t sentry_low_ms;
    uint32_t keyoff_ms;
    uint32_t low12_since_ms;

    // Faults and rejects
    uint16_t latched;       // actuator faults, cleared by the next accepted move
    uint16_t faults;        // everything, as last sent
    uint8_t reject_reason;
    uint8_t reject_count;

    bool bootloader_pending;

    // Vehicle lock (docs/vehicle-lock.md)
    vlock_t lock;
    bool still;             // remote lock: known stopped (under 0.5 km/h) since still_from_ms
    uint32_t still_from_ms;

    uint8_t tx_counter;
    uint32_t last_tx_fast_ms;
    uint32_t last_tx_slow_ms;

    cb_in_t in;             // last inputs seen
    cb_out_t out;           // last outputs given
} controller_t;

// saved: settings read from flash, or NULL for defaults.
// power_hold_on: relay 8 state read back from the expander at boot, so a Pico
// reset during key-off doesn't cut the Pi off mid shutdown.
void ctl_init(controller_t *c, const settings_t *saved, bool watchdog_reset,
              bool power_hold_on, uint32_t now_ms);
// lock_saved: the lock sector read from flash, or NULL. Call right after ctl_init.
void ctl_load_lock(controller_t *c, const lock_blob_t *lock_saved, uint32_t now_ms);
void ctl_on_frame(controller_t *c, const can_frame_t *f, uint32_t now_ms,
                  cb_send_fn send, void *user);
void ctl_tick(controller_t *c, const cb_in_t *in, cb_out_t *out,
              cb_send_fn send, void *user);

// Handy for tests and the host console.
bool ctl_dash_ok(const controller_t *c, uint32_t now_ms);
bool ctl_speed_valid(const controller_t *c, uint32_t now_ms);
bool ctl_parked(const controller_t *c, uint32_t now_ms);
bool ctl_locked(const controller_t *c);
// Can the lock be put on now: stopped (or key off), park brake on, nothing moving.
bool ctl_can_lock(const controller_t *c, uint32_t now_ms);
