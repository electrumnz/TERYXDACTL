// Teryx control box: stock lamps, floods, beacon, trailer bar, light show.
// Copy of teryx/lights.py, rule for rule. Integer maths only so both match.
#include "lights.h"

#include <string.h>

// Every lamp the show knows: the 15 PCA9685 lamps, then the 5 0x701 lights.
enum { U_FRONT0 = LP_COUNT, U_COUNT = LP_COUNT + LF_COUNT };
#define K_RED   0x01u
#define K_HIGH  0x02u
#define K_LEFT  0x04u
#define K_RIGHT 0x08u
#define K_BAR   0x10u   // front bar 1-4

typedef struct { int8_t x; uint8_t kind; } lamp_info_t;   // x: left -10 .. right +10

static const lamp_info_t INFO[U_COUNT] = {
    [LP_HEAD_L_LOW] = {-10, K_LEFT},
    [LP_HEAD_L_HIGH] = {-10, K_HIGH},
    [LP_HEAD_R_LOW] = {10, K_RIGHT},
    [LP_HEAD_R_HIGH] = {10, K_HIGH},
    [LP_TAIL_L] = {-10, K_RED | K_LEFT},
    [LP_BRAKE_L] = {-10, K_RED | K_LEFT},
    [LP_TAIL_R] = {10, K_RED | K_RIGHT},
    [LP_BRAKE_R] = {10, K_RED | K_RIGHT},
    [LP_TRAILER_TAIL] = {0, K_RED},
    [LP_TRAILER_STOP] = {0, K_RED},
    [LP_FLOOD_L] = {-6, K_LEFT},
    [LP_FLOOD_R] = {6, K_RIGHT},
    [LP_BEACON] = {0, 0},
    [LP_TRAILER_BAR] = {0, 0},
    [LP_BEACON_WHITE] = {0, 0},
    [U_FRONT0 + LF_FRONT_1] = {-6, K_LEFT | K_BAR},
    [U_FRONT0 + LF_FRONT_2] = {-2, K_LEFT | K_BAR},
    [U_FRONT0 + LF_FRONT_3] = {2, K_RIGHT | K_BAR},
    [U_FRONT0 + LF_FRONT_4] = {6, K_RIGHT | K_BAR},
    [U_FRONT0 + LF_INTERIOR] = {0, 0},
};

static uint32_t tri(uint32_t t, uint32_t period) {   // 0 -> 255 -> 0
    uint32_t p = t % period, half = period / 2u;
    return p < half ? p * 255u / half : (period - p) * 255u / half;
}

static uint8_t show_level(uint8_t show, int u, uint32_t t) {
    uint8_t k = INFO[u].kind;
    bool head_low = u == LP_HEAD_L_LOW || u == LP_HEAD_R_LOW;
    bool brake = u == LP_BRAKE_L || u == LP_BRAKE_R || u == LP_TRAILER_STOP;
    bool interior = u == U_FRONT0 + LF_INTERIOR;
    switch (show) {
    case SHOW_WAVE: {
        int32_t pos = (int32_t)(tri(t, 2000u) * 24u / 255u) - 12;
        if ((k & K_HIGH) || brake) return 0;
        if (u == LP_BEACON || u == LP_BEACON_WHITE) return (pos >= -2 && pos <= 2) ? 255 : 0;
        if (interior) return 60;
        int32_t d = INFO[u].x - pos;
        if (d < 0) d = -d;
        int32_t v = 255 - d * 255 / 5;
        return v > 0 ? (uint8_t)v : 0;
    }
    case SHOW_BREATHE: {
        uint32_t lvl = tri(t, 3000u);
        if (k & K_HIGH) return 0;
        return (uint8_t)((k & K_RED) ? 255u - lvl : lvl);
    }
    case SHOW_ROAR:
        t %= 8000u;
        if (t < 2000u) return (k & K_RED) ? (uint8_t)(t * 255u / 2000u) : 0;
        if (t < 3000u) {
            if (k & K_RED) return 255;
            if (head_low) return (uint8_t)((t - 2000u) * 255u / 1000u);
            return 0;
        }
        if (t < 3800u) {
            if (head_low) return 0;
            if (interior) return 255;
            return ((t - 3000u) / 50u) % 2u == 0u ? 255 : 0;   // 10 Hz strobe
        }
        if (t < 6000u) {
            if (k & K_HIGH) return 0;
            uint32_t beat = (t - 3800u) % 900u;
            return (beat < 100u || (beat >= 250u && beat < 350u)) ? 255 : 40;
        }
        if (k & K_HIGH) return 0;
        return (uint8_t)((8000u - t) * 255u / 2000u / ((k & K_RED) ? 1u : 4u));
    case SHOW_PARTY: {
        uint32_t step = t / 125u;
        if ((k & K_HIGH) || interior) return 0;
        if (u == LP_BEACON) return step % 4u == 0u ? 255 : 0;
        if (u == LP_BEACON_WHITE) return step % 4u == 2u ? 255 : 0;
        if (k & K_BAR) return (uint32_t)(u - U_FRONT0) == step % 4u ? 255 : 0;
        if (k & K_LEFT) return step % 2u == 0u ? 255 : 0;
        if (k & K_RIGHT) return step % 2u == 1u ? 255 : 0;
        return step % 2u == 0u ? 255 : 0;
    }
    default:
        return 0;
    }
}

uint8_t show_level_lamp(uint8_t show, int lamp, uint32_t t) { return show_level(show, lamp, t); }
uint8_t show_level_front(uint8_t show, int front, uint32_t t) { return show_level(show, U_FRONT0 + front, t); }

bool lights_show_ok(const lights_req_t *r, const lights_state_t *s) {
    return r->show > SHOW_NONE && r->show < SHOW_COUNT && s->ignition && s->park && s->stopped &&
           s->dash_ok && !s->locked;
}

void lights_step(lights_t *L, const lights_req_t *r, const lights_state_t *s, lights_out_t *o) {
    memset(o, 0, sizeof(*o));
    uint8_t *lv = o->level;
    bool moving = !s->stopped;

    // Normal running
    if (r->head_high) {
        lv[LP_HEAD_L_HIGH] = lv[LP_HEAD_R_HIGH] = r->head_high;
    } else if (r->head_low) {
        lv[LP_HEAD_L_LOW] = lv[LP_HEAD_R_LOW] = r->head_low;
    }
    bool heads_on = r->head_high || r->head_low;
    uint8_t tail = r->tail ? r->tail : ((heads_on || s->front_on) ? 255 : 0);
    lv[LP_TAIL_L] = lv[LP_TAIL_R] = lv[LP_TRAILER_TAIL] = tail;
    if (moving) {   // rule 3: headlights and tails don't dim on the move
        static const uint8_t road[] = {LP_HEAD_L_LOW, LP_HEAD_L_HIGH, LP_HEAD_R_LOW, LP_HEAD_R_HIGH,
                                       LP_TAIL_L, LP_TAIL_R, LP_TRAILER_TAIL};
        for (unsigned i = 0; i < sizeof(road); i++)
            if (lv[road[i]]) lv[road[i]] = 255;
    }
    if (r->rear_auto && s->reverse) {
        lv[LP_FLOOD_L] = lv[LP_FLOOD_R] = 255;
    } else if (r->rear_on) {
        lv[LP_FLOOD_L] = lv[LP_FLOOD_R] = r->rear ? r->rear : 255;
    }
    if (r->beacon && s->now_ms % BEACON_PERIOD_MS < BEACON_ON_MS) lv[LP_BEACON] = r->beacon;   // rule 5
    if (r->beacon_white && s->stopped && s->now_ms % BEACON_PERIOD_MS >= BEACON_ON_MS)
        lv[LP_BEACON_WHITE] = r->beacon_white;   // white: other half of the flash, stopped only
    if (s->trailer) lv[LP_TRAILER_BAR] = r->trailer_bar;
    if (s->ignition && !s->dash_ok) {   // rule 9: no dash, key on: low beams + tails
        if (!lv[LP_HEAD_L_HIGH]) lv[LP_HEAD_L_LOW] = lv[LP_HEAD_R_LOW] = 255;
        lv[LP_TAIL_L] = lv[LP_TAIL_R] = lv[LP_TRAILER_TAIL] = 255;
    }
    if (s->locked) memset(lv, 0, LP_COUNT);   // rule 8

    // Light show, parked only (rule 10)
    bool ok = lights_show_ok(r, s);
    if (ok) {
        if (L->running != r->show) {
            L->running = r->show;
            L->start_ms = s->now_ms;
        }
        uint32_t t = s->now_ms - L->start_ms;
        for (int i = 0; i < LP_COUNT; i++) lv[i] = show_level(r->show, i, t);
        if (!s->trailer) lv[LP_TRAILER_BAR] = 0;
        for (int i = 0; i < LF_COUNT; i++) o->front[i] = show_level(r->show, U_FRONT0 + i, t);
        o->front_valid = true;
        o->show_running = true;
    } else {
        L->running = SHOW_NONE;
        o->show_blocked = r->show != SHOW_NONE;
    }

    // Rule 2, then rule 1 last so nothing can undo it
    if (lv[LP_HEAD_L_HIGH]) lv[LP_HEAD_L_LOW] = 0;
    if (lv[LP_HEAD_R_HIGH]) lv[LP_HEAD_R_LOW] = 0;
    if (s->brake) {
        lv[LP_BRAKE_L] = lv[LP_BRAKE_R] = lv[LP_TRAILER_STOP] = 255;
    } else if (!ok) {
        lv[LP_BRAKE_L] = lv[LP_BRAKE_R] = lv[LP_TRAILER_STOP] = 0;
    }
}
