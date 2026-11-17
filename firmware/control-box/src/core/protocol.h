// Teryx control box: CAN message layouts.
//
// This file is the firmware side of docs/can-protocol.md. The dash / simulator
// side lives in teryx/canbus/messages.py. If you change one, change the other.
// All multi-byte values are little-endian. All IDs are standard 11-bit.
#pragma once

#include <stdbool.h>
#include <stdint.h>

// ---- IDs -------------------------------------------------------------------
#define CAN_ID_PI_HEARTBEAT   0x700u  // Pi -> Pico, 10 Hz
#define CAN_ID_PI_LIGHTS      0x701u  // Pi -> Pico, on change + every 1 s
#define CAN_ID_PI_DRIVE       0x702u  // Pi -> Pico, on change + every 1 s
#define CAN_ID_PI_HOLD        0x703u  // Pi -> Pico, 10 Hz while held / armed
#define CAN_ID_PI_SETTING     0x704u  // Pi -> Pico, on change
#define CAN_ID_PICO_STATUS    0x710u  // Pico -> Pi, 10 Hz
#define CAN_ID_PICO_OUTPUTS   0x711u  // Pico -> Pi, 10 Hz
#define CAN_ID_PICO_ACT       0x712u  // Pico -> Pi, 10 Hz
#define CAN_ID_PICO_POWER     0x713u  // Pico -> Pi, 1 Hz
#define CAN_ID_PICO_SET_ACK   0x714u  // Pico -> Pi, reply to every 0x704
#define CAN_ID_PICO_REGEN     0x715u  // Pico -> Pi, 10 Hz, brake pedal regen (not sent yet)
#define CAN_ID_PI_FW_UPDATE   0x71Fu  // Pi -> Pico, on demand (magic 0x5445)
#define CAN_ID_BENCH          0x7E0u  // Simulator -> host build only

// Shinegle motor controller. These are the MOCK layouts used until the real
// bus has been recorded. Only the speed/direction frame matters to the Pico.
#define CAN_ID_MC_SPEED       0x180u  // [0-1] u16 speed 0.1 km/h, [2] dir 0 N 1 F 2 R

// ---- Frame -----------------------------------------------------------------
typedef struct {
    uint32_t id;
    uint8_t dlc;
    bool ext;
    uint8_t data[8];
} can_frame_t;

// ---- 0x700 dash state --------------------------------------------------------
enum { DASH_BOOTING = 0, DASH_RUNNING = 1, DASH_SHUTTING_DOWN = 2 };

// ---- 0x701 light effects -------------------------------------------------------
enum {
    FX_NONE = 0,
    FX_STROBE = 1,        // all front bars flash together
    FX_CHASE = 2,         // one front bar at a time, left to right
    FX_OUTSIDE_ONLY = 3,  // bars 1 and 4 only
    FX_INSIDE_ONLY = 4,   // bars 2 and 3 only
    FX_BREATHE = 5,       // slow fade up and down (on/off bars blink slowly)
    FX_SOS = 6,           // ... --- ... on all front bars
    FX_COUNT
};
#define LIGHTS_FLAG_REAR_ON    0x01u
#define LIGHTS_FLAG_AUTO_REAR  0x02u

// ---- 0x702 drive --------------------------------------------------------------
#define DRIVE_NO_CHANGE 0xFFu
enum { REQ_2WD = 0, REQ_4WD = 1 };

// ---- 0x703 hold-to-run ----------------------------------------------------------
#define HOLD_FLAG_WINCH_ARMED 0x01u
// Byte 3 (optional): timed pull length in whole seconds. 0 = plain hold-to-run.
// The dash still sends 0x703 every 100 ms for the whole pull, so the 300 ms
// hold timeout still stops it if the dash dies. The Pico stops it on time by
// itself (capped at SET_WINCH_TIMED_MAX_S) even if the frames keep coming.

// ---- 0x704 settings keys ---------------------------------------------------------
// Frame: [0] key, [1] 0, [2-3] u16 value. Pico echoes the stored value on 0x714:
// [0] key, [1] result (0 ok, 1 unknown key, 2 out of range), [2-3] value now in use.
enum {
    SET_HEARTBEAT_TIMEOUT_MS = 1,
    SET_SPEED_TIMEOUT_MS = 2,
    SET_4WD_MAX_KMH = 3,
    SET_4WD_MAX_RUN_MS = 4,
    SET_4WD_OVERCURRENT_DA = 5,   // 0.1 A
    SET_DIFF_MAX_KMH = 6,
    SET_DIFF_MAX_RUN_MS = 7,
    SET_DIFF_OVERCURRENT_DA = 8,
    SET_TRAY_MAX_RUN_MS = 9,
    SET_TRAY_OVERCURRENT_DA = 10,
    SET_WINCH_DEAD_TIME_MS = 11,
    SET_WINCH_AUTO_DISARM_S = 12,
    SET_SHUTDOWN_WAIT_S = 13,
    SET_DIFF_POT_MIN = 14,        // raw ADS1115 counts at 0 %
    SET_DIFF_POT_MAX = 15,        // raw ADS1115 counts at 100 %
    SET_LIGHT_DIMMABLE_MASK = 16, // bit 0-3 front 1-4, bit 4 interior. 1 = dims
    SET_HOLD_TIMEOUT_MS = 17,
    SET_RELAY_ACTIVE_LOW = 18,    // 1 = relay board switches on a low input
    SET_TRAY_FULL_TRAVEL_MS = 19, // used for the tray % estimate
    SET_LOW_12V_MV = 20,
    SET_WINCH_TIMED_MAX_S = 21,   // longest timed pull the Pico will run
    // Brake pedal regen (docs/brake-regen.md). Stored and acked only for now:
    // the rules live in teryx/regen.py and get ported once the Shinegle is checked.
    SET_BRAKE_REGEN_ON = 22,      // feature flag, 0 = off (default)
    SET_BRAKE_REGEN_PCT = 23,     // strength, % of the Shinegle's max regen
    SET_BRAKE_REGEN_START = 24,   // pedal travel % where regen starts
    SET_BRAKE_REGEN_FULL = 25,    // pedal travel % where regen is full
    SET_BRAKE_REGEN_FADE_KMH = 26,// fades to 0 below this speed
    SET_BRAKE_REGEN_2WD_PCT = 27, // share allowed when not in 4WD
    SET_BRAKE_PEDAL_MIN = 28,     // raw ADS1115 counts, pedal up
    SET_BRAKE_PEDAL_MAX = 29,     // raw ADS1115 counts, pedal on the floor
    SET_COUNT,
    SET_CMD_SAVE = 0xF0,          // write current settings to flash
    SET_CMD_DEFAULTS = 0xF1,      // go back to defaults (not saved until 0xF0)
    SET_CMD_CLEAR_FAULTS = 0xF2,  // clear latched actuator faults
};
enum { SET_ACK_OK = 0, SET_ACK_UNKNOWN = 1, SET_ACK_RANGE = 2 };

// ---- 0x710 status --------------------------------------------------------------
// b0 counter, b1-2 faults, b3 inputs (B0-B7), b4 state, b5 reject, b6 flags,
// b7 speed km/h as seen by the Pico (0xFF unknown).
enum { CB_STATE_BOOT = 0, CB_STATE_OK = 1, CB_STATE_DEGRADED = 2, CB_STATE_FAILSAFE = 3 };
#define STATE_BIT_ON_DEFAULTS   0x08u   // b4 bit 3: settings are defaults, please resend

#define FLAG_WINCH_ARMED        0x01u   // b6
#define FLAG_SPEED_VALID        0x02u
#define FLAG_REVERSE            0x04u
#define FLAG_SHUTDOWN_REQUEST   0x08u   // key is off, Pi should shut down now
#define FLAG_PARKED             0x10u   // stopped and nothing moving (OTA allowed)

enum {
    FAULT_DASH_LINK = 0,
    FAULT_SPEED_UNKNOWN = 1,
    FAULT_4WD_TIMEOUT = 2,
    FAULT_4WD_OVERCURRENT = 3,
    FAULT_DIFF_TIMEOUT = 4,
    FAULT_DIFF_POT_STUCK = 5,
    FAULT_TRAY_TIMEOUT = 6,
    FAULT_TRAY_OVERCURRENT = 7,
    FAULT_TRAY_LIMIT_SWITCH = 8,
    FAULT_WINCH_INTERLOCK = 9,
    FAULT_LOW_12V = 10,
    FAULT_PICO_HOT = 11,
    FAULT_WATCHDOG_RESET = 12,
    FAULT_DIFF_OVERCURRENT = 13,
    FAULT_IO_BUS = 14,            // I2C expander or ADC not answering
};

// Reject reasons, b5 low nibble. High nibble counts rejects (wraps at 16).
// 0-7 match teryx/canbus/messages.py REJECT_REASON, 8+ added by the firmware.
enum {
    REJ_NONE = 0,
    REJ_TOO_FAST = 1,        // above the speed limit for that action
    REJ_NOT_STOPPED = 2,     // needs speed 0
    REJ_SPEED_UNKNOWN = 3,   // no Shinegle speed, so "stopped" can't be proven
    REJ_NOT_ARMED = 4,       // winch not armed
    REJ_INTERLOCK = 5,       // e.g. tray while winching
    REJ_FAULT = 6,           // actuator or IO fault
    REJ_LOW_12V = 7,
    REJ_DASH_LINK = 8,
    REJ_IGNITION_OFF = 9,
    REJ_AT_LIMIT = 10,
    REJ_NOT_PARKED = 11,     // firmware update refused
    REJ_REMOTE_IN_USE = 12,  // handheld winch remote has it
    REJ_BAD_FRAME = 13,
};

// ---- 0x712 actuator states ---------------------------------------------------------
enum { FWD_2WD = 0, FWD_4WD = 1, FWD_TO_4WD = 2, FWD_TO_2WD = 3, FWD_FAULT = 4, FWD_UNKNOWN = 5 };
enum { TRAY_DOWN = 0, TRAY_UP = 1, TRAY_MID = 2, TRAY_RAISING = 3, TRAY_LOWERING = 4, TRAY_FAULT = 5 };
#define PCT_UNKNOWN 0xFFu

// ---- 0x71F firmware update ------------------------------------------------------------
#define FW_UPDATE_MAGIC 0x5445u   // u16 LE in bytes 0-1 ("ET" on the wire)

// ---- 0x7E0 bench (host build only) -------------------------------------------------------
// [0] input bits, [1] mask of input bits to force (others follow the model),
// [2] fault inject bits, [3-4] u16 12V aux mV (0 = leave alone).
#define BENCH_JAM_DIFF      0x01u
#define BENCH_JAM_TRAY      0x02u
#define BENCH_STALL_4WD     0x04u
#define BENCH_POT_DISCONNECT 0x08u
#define BENCH_IO_BUS_DEAD   0x10u

// ---- Little helpers ------------------------------------------------------------------
static inline uint16_t get_u16(const uint8_t *p) { return (uint16_t)(p[0] | (p[1] << 8)); }
static inline void put_u16(uint8_t *p, uint16_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); }
static inline void put_u32(uint8_t *p, uint32_t v) {
    p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); p[2] = (uint8_t)(v >> 16); p[3] = (uint8_t)(v >> 24);
}
