// Teryx control box: stock lamps, rear floods, beacon, trailer bar and the
// parked-only light show. Rule for rule copy of teryx/lights.py (the spec);
// docs/lights.md explains it. Plain C, no hardware calls.
#pragma once

#include <stdbool.h>
#include <stdint.h>

// Lamp order = PCA9685 map (config.h) = 0x717 nibble order = LAMPS in teryx/lights.py.
enum {
    LP_HEAD_L_LOW = 0, LP_HEAD_L_HIGH, LP_HEAD_R_LOW, LP_HEAD_R_HIGH,
    LP_TAIL_L, LP_BRAKE_L, LP_TAIL_R, LP_BRAKE_R,
    LP_TRAILER_TAIL, LP_TRAILER_STOP, LP_FLOOD_L, LP_FLOOD_R, LP_BEACON, LP_TRAILER_BAR, LP_BEACON_WHITE,
    LP_COUNT
};
// The 0x701 lights, as the show sees them.
enum { LF_FRONT_1 = 0, LF_FRONT_2, LF_FRONT_3, LF_FRONT_4, LF_INTERIOR, LF_COUNT };

enum { SHOW_NONE = 0, SHOW_WAVE = 1, SHOW_BREATHE = 2, SHOW_ROAR = 3, SHOW_PARTY = 4, SHOW_COUNT };

#define BEACON_PERIOD_MS 333u   // 3 Hz (NZ Vehicle Lighting Rule 11.1(2): 2 to 4 Hz)
#define BEACON_ON_MS     167u

// Flash modes (0x706 byte 6 bits 4-5, rule 11 in teryx/lights.py).
enum { FLASH_OFF = 0, FLASH_WARNING = 1, FLASH_EMERGENCY = 2, FLASH_COUNT };
#define STROBE_PERIOD_MS 500u   // stopped: double strobe, 2 groups a second
#define STROBE_PULSE_MS  60u

typedef struct {          // 0x706 + the rear bits of 0x701
    uint8_t head_low, head_high, tail, rear, trailer_bar, beacon, show, beacon_white;
    bool rear_on, rear_auto;
    uint8_t flash;        // FLASH_*
} lights_req_t;

typedef struct {
    bool brake, reverse, trailer, stopped, park, ignition, locked, dash_ok, front_on;
    uint32_t now_ms;
    uint8_t interior;     // what the cabin bar is doing now (emergency leaves it alone)
} lights_state_t;

typedef struct {
    uint8_t level[LP_COUNT];
    bool front_valid;           // the show is driving the 0x701 lights
    uint8_t front[LF_COUNT];
    bool show_running, show_blocked;
    bool flash_running;         // a flash mode is running (moving = beacon only)
} lights_out_t;

typedef struct {
    uint8_t running;
    uint32_t start_ms;
    uint8_t flash;
    uint32_t flash_start_ms;
} lights_t;

uint8_t show_level_lamp(uint8_t show, int lamp, uint32_t t);
uint8_t show_level_front(uint8_t show, int front, uint32_t t);
bool lights_flash_ok(const lights_req_t *r, const lights_state_t *s);
bool lights_show_ok(const lights_req_t *r, const lights_state_t *s);
void lights_step(lights_t *L, const lights_req_t *r, const lights_state_t *s, lights_out_t *o);
