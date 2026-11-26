#include "settings.h"

#include <stddef.h>
#include <string.h>

typedef struct { uint16_t def, min, max; } range_t;

// Defaults follow config/io-map.yaml "safety".
static const range_t k_ranges[SET_COUNT] = {
    [SET_HEARTBEAT_TIMEOUT_MS] = {500, 100, 5000},
    [SET_SPEED_TIMEOUT_MS]     = {500, 100, 5000},
    [SET_4WD_MAX_KMH]          = {1, 0, 40},   // Kawasaki: stop before 2WD/4WD
    [SET_4WD_MAX_RUN_MS]       = {3000, 500, 10000},
    [SET_4WD_OVERCURRENT_DA]   = {60, 5, 300},
    [SET_DIFF_MAX_KMH]         = {15, 0, 40},  // adding lock only; unlocking any speed
    [SET_DIFF_MAX_RUN_MS]      = {4000, 500, 10000},
    [SET_DIFF_OVERCURRENT_DA]  = {80, 5, 300},
    [SET_TRAY_MAX_RUN_MS]      = {20000, 1000, 60000},
    [SET_TRAY_OVERCURRENT_DA]  = {100, 5, 300},
    [SET_WINCH_DEAD_TIME_MS]   = {100, 50, 1000},
    [SET_WINCH_AUTO_DISARM_S]  = {120, 10, 3600},
    [SET_SHUTDOWN_WAIT_S]      = {30, 5, 300},
    [SET_DIFF_POT_MIN]         = {1000, 0, 32767},
    [SET_DIFF_POT_MAX]         = {25000, 0, 32767},
    [SET_LIGHT_DIMMABLE_MASK]  = {0x1F, 0, 0x1F},
    [SET_HOLD_TIMEOUT_MS]      = {300, 100, 2000},
    [SET_RELAY_ACTIVE_LOW]     = {1, 0, 1},
    [SET_TRAY_FULL_TRAVEL_MS]  = {18000, 1000, 60000},
    [SET_LOW_12V_MV]           = {11500, 9000, 13500},
    [SET_WINCH_TIMED_MAX_S]    = {30, 1, 120},
    [SET_SHIFT_WAIT_MS]        = {10000, 0, 30000},
    [SET_SHIFT_THROTTLE_HOLD]  = {1, 0, 1},
    [SET_SENTRY_MIN_12V_MV]    = {12200, 11000, 13500},
    [SET_EPS_MODE]             = {2, 0, 2},
    [SET_EPS_FLOOR_KMH_X10]    = {163, 0, 600},   // 16.3 km/h: the Prius retrofit's "max assist" speed
    [SET_EPS_SPEED_GAIN_PCT]   = {100, 50, 300},
    [SET_EPS_MAX_KMH]          = {120, 20, 200},
    [SET_EPS_LISTEN]           = {0, 0, 1},       // off until the bench shows what the Aqua sends
    [SET_EPS_SILENT_MS]        = {1000, 200, 5000},
    [SET_EPS_RPM]              = {1674, 0, 8000},
    [SET_EPS_WAKE_MS]          = {3000, 500, 15000},
    [SET_PARK_INTERLOCK]       = {1, 0, 1},       // on: no drive with the park brake on
};

void settings_defaults(settings_t *s) {
    memset(s, 0, sizeof(*s));
    for (int k = 1; k < SET_COUNT; k++) s->v[k] = k_ranges[k].def;
}

int settings_set(settings_t *s, uint8_t key, uint16_t value) {
    if (key == 0 || key >= SET_COUNT) return SET_ACK_UNKNOWN;
    if (k_ranges[key].max == 0) return SET_ACK_UNKNOWN;   // reserved slot (22-29)
    if (value < k_ranges[key].min || value > k_ranges[key].max) return SET_ACK_RANGE;
    s->v[key] = value;
    return SET_ACK_OK;
}

uint16_t settings_get(const settings_t *s, uint8_t key) {
    if (key == 0 || key >= SET_COUNT) return 0;
    return s->v[key];
}

bool settings_is_defaults(const settings_t *s) {
    for (int k = 1; k < SET_COUNT; k++)
        if (s->v[k] != k_ranges[k].def) return false;
    return true;
}

uint32_t settings_crc32(const void *data, uint32_t len) {
    const uint8_t *p = data;
    uint32_t crc = 0xFFFFFFFFu;
    while (len--) {
        crc ^= *p++;
        for (int i = 0; i < 8; i++) crc = (crc >> 1) ^ (0xEDB88320u & (0u - (crc & 1u)));
    }
    return ~crc;
}

void settings_to_blob(const settings_t *s, settings_blob_t *b) {
    memset(b, 0, sizeof(*b));
    b->magic = SETTINGS_MAGIC;
    b->version = 1;
    b->count = SET_COUNT;
    memcpy(b->v, s->v, sizeof(s->v));
    b->crc = settings_crc32(b, offsetof(settings_blob_t, crc));
}

bool settings_from_blob(settings_t *s, const settings_blob_t *b) {
    if (b->magic != SETTINGS_MAGIC || b->version != 1) return false;
    if (b->crc != settings_crc32(b, offsetof(settings_blob_t, crc))) return false;
    settings_defaults(s);
    // Older firmware may have stored fewer keys; newer keys keep their defaults.
    uint16_t n = b->count < SET_COUNT ? b->count : SET_COUNT;
    for (uint16_t k = 1; k < n; k++)
        if (settings_set(s, (uint8_t)k, b->v[k]) != SET_ACK_OK) s->v[k] = k_ranges[k].def;
    return true;
}
