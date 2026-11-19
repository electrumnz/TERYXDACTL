// Toyota Aqua (NHP10) EPS column on its own 500 kbit/s CAN bus.
// docs/power-steering-aqua.md. Python twin: teryx/eps_toyota.py.
//
// The column's own Toyota ECU (89650-52B51) reads the torque sensor and drives
// the motor. The Pico only tells it "engine running" and "this is our speed",
// and listens to what it says back. Stop sending and it drops to limp mode
// (heavier), never to more assist. The Pico never drives the motor itself.
//
// EVERYTHING MARKED "ASSUMED" IS A GUESS UNTIL THE BENCH TEST. Each one is in
// this file (or a setting the dash can change), so a bench result is a one-line
// change. Python keeps the same numbers in teryx/eps_toyota.py and
// tests/test_eps_toyota.py checks they match.
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "protocol.h"

// ---- What we send ---------------------------------------------------------------
// ASSUMED: the Aqua ECU wants the same two frames as a 2004-09 Prius (gen 2), the
// only Toyota EPS with a proven standalone recipe (Carloop thread). Both are
// hybrids from the same era of Toyota CAN, and 0x0B4 is Toyota's usual ABS speed
// frame in opendbc. If the Aqua stays in limp mode, sniff a running Aqua's OBD
// port and change these.
#define EPS_BITRATE        500000u  // ASSUMED: Toyota powertrain CAN is 500 kbit/s
#define EPS_PERIOD_MS      20u      // Prius: 100 ms wasn't enough, 20 ms worked
#define EPS_RPM_ID         0x2C4u   // ASSUMED: engine RPM frame (Prius gen 2)
#define EPS_SPEED_ID       0x0B4u   // ASSUMED: vehicle speed frame (Prius gen 2, opendbc SPEED)
#define EPS_SPEED_BYTE     5        // big-endian u16 in bytes 5-6, 0.01 km/h per bit
#define EPS_SPEED_ENCODER  0x8Du    // byte 4, copied from the working Prius retrofit

// ---- What we listen for -----------------------------------------------------------
// ASSUMED: the Aqua ECU sends the same frames as the Toyota EPS ECUs in opendbc
// (MIT, commaai/opendbc toyota DBCs). If it doesn't, the dash shows "no reply"
// only when setting 37 (eps_listen) is on, and the steering still works.
#define EPS_TORQUE_ID      0x260u   // STEER_TORQUE_SENSOR: driver torque, angle, override
#define EPS_STATUS_ID      0x262u   // EPS_STATUS: LKA_STATE (probably missing on a non-LKA Aqua)
#define EPS_DIAG_REPLY_ID  0x7A9u   // reply to Toyota's EPS diagnostic address 0x7A1 (opendbc fingerprints)
#define EPS_STATUS_PERMANENT_FAULT 17u  // opendbc LKA_STATE "permanent_fault"
#define EPS_ANGLE_MILLIDEG_PER_BIT 57.3 // 0.0573 deg per bit (shown as an int below)

// ---- Modes (setting 33) -----------------------------------------------------------
enum {
    EPS_MODE_MANUAL = 0,  // relay 9 off: plain manual steering (bench, or if the column misbehaves)
    EPS_MODE_LIMP = 1,    // relay on, no frames: the ECU's own fail-safe assist
    EPS_MODE_NORMAL = 2,  // relay on + speed frames (default)
};

// ---- What the dash sees (0x718 byte 0, low nibble) ---------------------------------
enum {
    STEER_OFF = 0,        // key off or locked: column unpowered
    STEER_WAKING = 1,     // just powered, ECU booting (setting 40)
    STEER_OK = 2,         // powered, frames going, and the ECU is talking (or we don't listen)
    STEER_LIMP = 3,       // mode 1 on purpose: assist on, no speed frames
    STEER_MANUAL = 4,     // mode 0 on purpose: no assist
    STEER_NO_REPLY = 5,   // listening, but the ECU has gone quiet
    STEER_ECU_FAULT = 6,  // the ECU says it has a fault
    STEER_BUS_ERROR = 7,  // the Pico's steering CAN board isn't working
};
// 0x718 byte 1 flags
#define STEER_F_FRAMES     0x01u  // speed frames going out
#define STEER_F_HEARD      0x02u  // something heard from the ECU lately
#define STEER_F_TORQUE     0x04u  // 0x260 fresh: torque and angle are real
#define STEER_F_ANGLE_INIT 0x08u  // ECU says the angle is still initialising
#define STEER_F_OVERRIDE   0x10u  // ECU says the driver is turning the wheel hard
#define STEER_F_LISTEN     0x20u  // setting 37 on
#define STEER_F_PENDING    0x40u  // a mode change is waiting for the Teryx to stop
#define STEER_F_BUS_OK     0x80u

typedef struct {
    uint16_t floor_x10;   // setting 34: below this, report this (full assist when crawling)
    uint16_t gain_pct;    // setting 35: above the floor, report real speed x gain
    uint16_t max_kmh;     // setting 36: never report more than this
    bool listen;          // setting 37
    uint16_t silent_ms;   // setting 38
    uint16_t wake_ms;     // setting 40
} eps_cfg_t;

typedef struct {
    uint8_t mode;         // mode in use (setting 33 applies when stopped or key off)
    bool mode_pending;
    bool powered;
    uint32_t powered_ms;
    bool heard;
    uint32_t last_rx_ms;
    bool torque_seen;
    uint32_t last_torque_ms;
    int16_t torque_raw;   // STEER_TORQUE_DRIVER, raw (units unknown, sign = direction)
    int16_t angle_x10;    // STEER_ANGLE in 0.1 deg
    bool angle_init;
    bool override;
    uint8_t status_raw;   // EPS_STATUS LKA_STATE, 0xFF = never seen
    uint32_t last_status_ms;
    uint32_t rx_count;
    uint32_t bad_checksum;
    uint16_t told_x10;    // speed we're telling the ECU, 0.1 km/h
    uint8_t state;        // STEER_*
    uint8_t flags;        // STEER_F_*
} eps_t;

uint8_t eps_checksum(uint16_t id, const uint8_t *data, uint8_t len);

// Speed to tell the ECU, 0.1 km/h. Unknown speed reports the floor.
uint16_t eps_told_speed_x10(const eps_cfg_t *cfg, uint16_t real_x10, bool known);

// Fills the RPM and speed frames and returns 2.
int eps_frames(uint16_t told_x10, uint16_t rpm, can_frame_t out[2]);

void eps_init(eps_t *e, uint8_t mode);
// A frame heard on the steering bus.
void eps_on_frame(eps_t *e, const can_frame_t *f, uint32_t now);
// Once a tick: works out state + flags. powered = relay 9 on, sending = frames going.
void eps_update(eps_t *e, const eps_cfg_t *cfg, bool powered, bool sending, bool bus_ok, uint32_t now);
// 0x718 payload.
void eps_status_frame(const eps_t *e, uint8_t counter, can_frame_t *f);
