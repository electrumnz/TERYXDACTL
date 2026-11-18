#include "plant.h"

#include <string.h>

#include "../core/config.h"

void plant_init(plant_t *p) {
    memset(p, 0, sizeof(*p));
    p->rate[ACT_DIFF] = 1.0 / 2.5;   // 50 mm at 20 mm/s
    p->rate[ACT_4WD] = 1.0 / 1.5;
    p->rate[ACT_TRAY] = 1.0 / 15.0;  // 400 mm at ~27 mm/s
    p->run_a[ACT_DIFF] = 2.5;
    p->run_a[ACT_4WD] = 3.0;
    p->run_a[ACT_TRAY] = 5.0;
    p->din_model = BIT(IN_IGNITION);  // bench default: key on
    p->aux_mv = 12800;
    p->pot_min = 1000;
    p->pot_max = 25000;
    p->temp_c = 35;
}

static double current_now[ACT_COUNT];

void plant_step(plant_t *p, const cb_out_t *out, double dt) {
    p->relays = out->relays;
    memcpy(p->light, out->light, sizeof(p->light));
    for (int i = 0; i < ACT_COUNT; i++) {
        int8_t d = out->act_dir[i];
        int dir = d;
        if (i == ACT_DIFF) dir *= DIFF_LOCK_DIR;
        if (i == ACT_4WD) dir *= FOURWD_ENGAGE_DIR;
        if (i == ACT_TRAY) dir *= TRAY_UP_DIR;
        current_now[i] = 0;
        if (!d) continue;
        bool jam = (i == ACT_DIFF && (p->faults & BENCH_JAM_DIFF)) ||
                   (i == ACT_TRAY && (p->faults & BENCH_JAM_TRAY)) ||
                   (i == ACT_4WD && (p->faults & BENCH_STALL_4WD));
        if (jam) { current_now[i] = 12.0; continue; }
        double duty = out->act_duty[i] / 255.0;
        double np = p->pos[i] + dir * p->rate[i] * duty * dt;
        // Built-in end stops: the actuator stops and draws nothing at the ends.
        if ((dir > 0 && p->pos[i] >= 1.0) || (dir < 0 && p->pos[i] <= 0.0)) continue;
        if (np > 1.0) np = 1.0;
        if (np < 0.0) np = 0.0;
        p->pos[i] = np;
        current_now[i] = p->run_a[i] * (0.4 + 0.6 * duty);
    }
}

void plant_inputs(const plant_t *p, cb_in_t *in, uint32_t now_ms) {
    memset(in, 0, sizeof(*in));
    in->now_ms = now_ms;
    uint8_t din = p->din_model & (uint8_t)~(BIT(IN_TRAY_DOWN) | BIT(IN_TRAY_UP));
    if (p->pos[ACT_TRAY] <= 0.002) din |= BIT(IN_TRAY_DOWN);
    if (p->pos[ACT_TRAY] >= 0.998) din |= BIT(IN_TRAY_UP);
    din = (uint8_t)((din & ~p->force_mask) | (p->force_bits & p->force_mask));
    in->din = din;
    in->io_ok = !(p->faults & BENCH_IO_BUS_DEAD);
    in->pot_ok = in->io_ok;
    in->pwm_ok = in->io_ok;
    in->diff_pot_raw = (p->faults & BENCH_POT_DISCONNECT)
        ? 0 : (uint16_t)(p->pot_min + p->pos[ACT_DIFF] * (p->pot_max - p->pot_min));
    in->aux_mv = p->aux_mv;
    for (int i = 0; i < ACT_COUNT; i++) in->i_da[i] = (uint16_t)(current_now[i] * 10.0 + 0.5);
    in->temp_c = p->temp_c;
}

void plant_bench_frame(plant_t *p, const can_frame_t *f) {
    if (f->dlc < 3) return;
    p->force_bits = f->data[0];
    p->force_mask = f->data[1];
    p->faults = f->data[2];
    if (f->dlc >= 5) {
        uint16_t mv = get_u16(&f->data[3]);
        if (mv) p->aux_mv = mv;
    }
}
