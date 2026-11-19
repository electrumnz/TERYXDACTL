#include "eps.h"
#include <string.h>

static uint32_t since(uint32_t now, uint32_t then) { return now - then; }

uint8_t eps_checksum(uint16_t id, const uint8_t *data, uint8_t len) {
    uint32_t t = (id >> 8) + (id & 0xFF) + len;
    for (uint8_t i = 0; i + 1 < len; i++) t += data[i];
    return (uint8_t)t;
}

uint16_t eps_told_speed_x10(const eps_cfg_t *cfg, uint16_t real_x10, bool known) {
    uint32_t v = known ? (uint32_t)real_x10 * cfg->gain_pct / 100u : 0;
    if (v < cfg->floor_x10) v = cfg->floor_x10;
    uint32_t cap = (uint32_t)cfg->max_kmh * 10u;
    if (v > cap) v = cap;
    return (uint16_t)v;
}

int eps_frames(uint16_t told_x10, uint16_t rpm, can_frame_t out[2]) {
    memset(out, 0, 2 * sizeof(can_frame_t));
    out[0].id = EPS_RPM_ID;
    out[0].dlc = 8;
    // Bytes 2-6 copied from the Prius retrofit, meaning unknown.
    const uint8_t body[8] = {(uint8_t)(rpm >> 8), (uint8_t)rpm, 0x00, 0x19, 0x00, 0x00, 0x92, 0x00};
    memcpy(out[0].data, body, 8);
    out[0].data[7] = eps_checksum(EPS_RPM_ID, out[0].data, 8);

    uint32_t raw = (uint32_t)told_x10 * 10u;  // 0.01 km/h per bit
    if (raw > 0xFFFF) raw = 0xFFFF;
    out[1].id = EPS_SPEED_ID;
    out[1].dlc = 8;
    out[1].data[4] = EPS_SPEED_ENCODER;
    out[1].data[EPS_SPEED_BYTE] = (uint8_t)(raw >> 8);
    out[1].data[EPS_SPEED_BYTE + 1] = (uint8_t)raw;
    out[1].data[7] = eps_checksum(EPS_SPEED_ID, out[1].data, 8);
    return 2;
}

void eps_init(eps_t *e, uint8_t mode) {
    memset(e, 0, sizeof(*e));
    e->mode = mode;
    e->status_raw = 0xFF;
}

static int16_t be16(const uint8_t *p) { return (int16_t)(((uint16_t)p[0] << 8) | p[1]); }

void eps_on_frame(eps_t *e, const can_frame_t *f, uint32_t now) {
    if (f->ext) return;
    // Anything on this bus that isn't one of ours came from the ECU.
    if (f->id == EPS_RPM_ID || f->id == EPS_SPEED_ID) return;
    e->heard = true;
    e->last_rx_ms = now;
    e->rx_count++;
    if ((f->id == EPS_TORQUE_ID || f->id == EPS_STATUS_ID) && f->dlc >= 5) {
        if (f->data[f->dlc - 1] != eps_checksum((uint16_t)f->id, f->data, f->dlc)) {
            e->bad_checksum++;
            return;
        }
    }
    if (f->id == EPS_TORQUE_ID && f->dlc == 8) {
        // opendbc STEER_TORQUE_SENSOR (big-endian): override b0.0, angle init b0.3,
        // driver torque bytes 1-2, angle bytes 3-4 (0.0573 deg), EPS torque bytes 5-6.
        e->override = (f->data[0] & 0x01) != 0;
        e->angle_init = (f->data[0] & 0x08) != 0;
        e->torque_raw = be16(&f->data[1]);
        int32_t a = (int32_t)be16(&f->data[3]) * 573 / 1000;  // 0.1 deg
        if (a > 32767) a = 32767;
        if (a < -32768) a = -32768;
        e->angle_x10 = (int16_t)a;
        e->torque_seen = true;
        e->last_torque_ms = now;
    } else if (f->id == EPS_STATUS_ID && f->dlc >= 4) {
        e->status_raw = (uint8_t)((f->data[3] >> 1) & 0x7F);  // LKA_STATE, bits 31..25
        e->last_status_ms = now;
    }
}

void eps_update(eps_t *e, const eps_cfg_t *cfg, bool powered, bool sending, bool bus_ok, uint32_t now) {
    if (powered && !e->powered) e->powered_ms = now;
    e->powered = powered;
    bool heard = e->heard && since(now, e->last_rx_ms) <= cfg->silent_ms;
    bool torque = e->torque_seen && since(now, e->last_torque_ms) <= cfg->silent_ms;
    bool status_fresh = e->status_raw != 0xFF && since(now, e->last_status_ms) <= cfg->silent_ms;
    bool waking = powered && since(now, e->powered_ms) < cfg->wake_ms;

    uint8_t s;
    if (!powered) s = (e->mode == EPS_MODE_MANUAL) ? STEER_MANUAL : STEER_OFF;
    else if (!bus_ok && e->mode == EPS_MODE_NORMAL) s = STEER_BUS_ERROR;
    else if (cfg->listen && status_fresh && e->status_raw == EPS_STATUS_PERMANENT_FAULT) s = STEER_ECU_FAULT;
    else if (waking) s = STEER_WAKING;
    else if (e->mode == EPS_MODE_LIMP) s = STEER_LIMP;
    else if (cfg->listen && !heard) s = STEER_NO_REPLY;
    else s = STEER_OK;
    e->state = s;

    uint8_t fl = 0;
    if (sending) fl |= STEER_F_FRAMES;
    if (heard) fl |= STEER_F_HEARD;
    if (torque) {
        fl |= STEER_F_TORQUE;
        if (e->angle_init) fl |= STEER_F_ANGLE_INIT;
        if (e->override) fl |= STEER_F_OVERRIDE;
    }
    if (cfg->listen) fl |= STEER_F_LISTEN;
    if (e->mode_pending) fl |= STEER_F_PENDING;
    if (bus_ok) fl |= STEER_F_BUS_OK;
    e->flags = fl;
}

void eps_status_frame(const eps_t *e, uint8_t counter, can_frame_t *f) {
    memset(f, 0, sizeof(*f));
    f->id = CAN_ID_PICO_STEER;
    f->dlc = 8;
    f->data[0] = (uint8_t)((e->state & 0x0F) | (counter << 4));
    f->data[1] = e->flags;
    bool torque = (e->flags & STEER_F_TORQUE) != 0;
    int16_t t = torque ? e->torque_raw : 0;
    int16_t a = torque ? e->angle_x10 : 0;
    f->data[2] = (uint8_t)t;          // little-endian like the rest of our frames
    f->data[3] = (uint8_t)((uint16_t)t >> 8);
    f->data[4] = (uint8_t)a;
    f->data[5] = (uint8_t)((uint16_t)a >> 8);
    uint32_t kmh = (e->told_x10 + 5u) / 10u;
    f->data[6] = (e->flags & STEER_F_FRAMES) ? (uint8_t)(kmh > 254u ? 254u : kmh) : 0xFF;
    f->data[7] = e->status_raw;
}
