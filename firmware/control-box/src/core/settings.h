// Teryx control box: settings the dash can change over CAN (0x704).
#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "protocol.h"

typedef struct {
    uint16_t v[SET_COUNT];   // indexed by SET_* key, slot 0 unused
} settings_t;

#define SETTINGS_BLOB_SLOTS 32
_Static_assert(SET_COUNT <= SETTINGS_BLOB_SLOTS, "too many settings for the flash blob");
#define SETTINGS_MAGIC 0x54455259u  // "TERY"

// Blob stored in flash (or a file on the host build).
typedef struct {
    uint32_t magic;
    uint16_t version;
    uint16_t count;
    uint16_t v[SETTINGS_BLOB_SLOTS];   // fixed size so new keys don't move the CRC
    uint32_t crc;
} settings_blob_t;


void settings_defaults(settings_t *s);
// Returns SET_ACK_*. On OK the value is stored.
int settings_set(settings_t *s, uint8_t key, uint16_t value);
uint16_t settings_get(const settings_t *s, uint8_t key);
bool settings_is_defaults(const settings_t *s);

void settings_to_blob(const settings_t *s, settings_blob_t *b);
bool settings_from_blob(settings_t *s, const settings_blob_t *b);
uint32_t settings_crc32(const void *data, uint32_t len);

#define S(ctl, key) ((ctl)->settings.v[(key)])
