// Small SHA-256 (FIPS 180-4), written for this project. Used to keep the
// vehicle lock PIN out of flash in plain form.
#pragma once

#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint32_t h[8];
    uint64_t len;       // bytes so far
    uint8_t buf[64];
    uint32_t used;      // bytes in buf
} sha256_t;

void sha256_init(sha256_t *s);
void sha256_update(sha256_t *s, const void *data, size_t n);
void sha256_final(sha256_t *s, uint8_t out[32]);
