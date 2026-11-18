// Toyota EPS column (Aqua / Prius ECU) on its own 500 kbit/s CAN bus.
// docs/power-steering-wrecker.md, same frames as teryx/eps_toyota.py.
// The ECU wants engine RPM (0x2C4) and vehicle speed (0x0B4) every 20 ms, or it
// sits in limp mode (heavy). Stop sending and it drops back to limp, never to
// more assist.
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "protocol.h"

#define EPS_BITRATE        500000u
#define EPS_PERIOD_MS      20u
#define EPS_RPM_ID         0x2C4u
#define EPS_SPEED_ID       0x0B4u
#define EPS_RPM_RUNNING    1674u   // 0x068A, the value the working retrofit sends
#define EPS_FLOOR_KMH_X100 1630u   // below 16.3 km/h report 16.3: full assist when crawling

uint8_t eps_checksum(uint16_t id, const uint8_t *data, uint8_t len);
// speed_x10 in 0.1 km/h; speed_known false = report the floor.
// Fills two frames (RPM, speed) and returns 2.
int eps_frames(uint16_t speed_x10, bool speed_known, can_frame_t out[2]);
