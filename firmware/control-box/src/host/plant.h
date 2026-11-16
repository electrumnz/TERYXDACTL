// Host build: a simple model of the hardware behind the Pico (actuators, limit
// switches, pot, currents, 12V). Lets the firmware run with no Teryx attached.
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "../core/controller.h"

typedef struct {
    double pos[ACT_COUNT];        // 0..1 of stroke
    double rate[ACT_COUNT];       // stroke per second at full duty
    double run_a[ACT_COUNT];      // current while moving
    uint8_t din_model;            // inputs from the model (tray limits) + defaults
    uint8_t force_bits, force_mask;
    uint8_t faults;               // BENCH_* bits
    uint16_t aux_mv;
    uint16_t pot_min, pot_max;    // pot raw counts at 0 and 1 of stroke
    int8_t temp_c;
    uint8_t relays;               // what the firmware last set
    uint8_t light[L_COUNT];
} plant_t;

void plant_init(plant_t *p);
// Apply firmware outputs for dt seconds, then fill the inputs for the next tick.
void plant_step(plant_t *p, const cb_out_t *out, double dt);
void plant_inputs(const plant_t *p, cb_in_t *in, uint32_t now_ms);
// 0x7E0 bench frame from the simulator.
void plant_bench_frame(plant_t *p, const can_frame_t *f);
