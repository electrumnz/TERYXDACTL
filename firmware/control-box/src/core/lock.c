#include "lock.h"

#include <stddef.h>
#include <string.h>

#include "settings.h"  // settings_crc32
#include "sha256.h"

static uint32_t since(uint32_t now, uint32_t then) { return now - then; }

void vlock_hash(const uint8_t salt[16], const char *digits, uint8_t n, uint8_t out[32]) {
    sha256_t s;
    sha256_init(&s);
    sha256_update(&s, salt, 16);
    sha256_update(&s, digits, n);
    sha256_final(&s, out);
    for (int i = 1; i < LOCK_HASH_ROUNDS; i++) {
        sha256_init(&s);
        sha256_update(&s, out, 32);
        sha256_update(&s, salt, 16);
        sha256_final(&s, out);
    }
}

uint32_t vlock_blob_crc(const lock_blob_t *b) {
    return settings_crc32(b, offsetof(lock_blob_t, crc));
}

static void save(vlock_t *l) {
    l->saved.magic = LOCK_MAGIC;
    l->saved.version = 1;
    l->saved.crc = vlock_blob_crc(&l->saved);
    l->dirty = true;
}

static void forget(vlock_t *l) {
    uint8_t fails = l->saved.fails;
    memset(&l->saved, 0, sizeof(l->saved));
    l->saved.fails = fails;
}

static uint32_t wait_ms(uint8_t fails) {
    uint32_t s = LOCK_FIRST_WAIT_S;
    for (int i = LOCK_FREE_TRIES; i < fails && s < LOCK_MAX_WAIT_S; i++) s *= 2u;
    if (s > LOCK_MAX_WAIT_S) s = LOCK_MAX_WAIT_S;
    return s * 1000u;
}

static void start_lockout(vlock_t *l, uint32_t now) {
    l->lockout = true;
    l->lockout_from_ms = now;
    l->lockout_ms = wait_ms(l->saved.fails);
}

void vlock_init(vlock_t *l, const lock_blob_t *saved, uint32_t now) {
    memset(l, 0, sizeof(*l));
    if (saved && saved->magic == LOCK_MAGIC && saved->version == 1 && saved->crc == vlock_blob_crc(saved))
        l->saved = *saved;
    // A power cut doesn't reset the count: a lockout starts over after boot.
    if (l->saved.fails >= LOCK_FREE_TRIES) start_lockout(l, now);
}

bool vlock_pin_set(const vlock_t *l) { return (l->saved.flags & LOCKF_PIN_SET) != 0; }
bool vlock_is_locked(const vlock_t *l) { return (l->saved.flags & LOCKF_LOCKED) != 0; }
bool vlock_pending(const vlock_t *l) { return (l->saved.flags & LOCKF_PENDING) != 0; }

bool vlock_remote_check(vlock_t *l, bool safe) {
    if (!vlock_pending(l) || !safe) return false;
    l->saved.flags = (uint8_t)((l->saved.flags & ~LOCKF_PENDING) | LOCKF_LOCKED);
    l->window = false;
    save(l);
    return true;
}

// BCD digits to ASCII. Returns false if a nibble isn't 0-9 or the length is off.
static bool digits(const uint8_t *d, uint8_t dlc, char out[8], uint8_t *n) {
    if (dlc < 6) return false;
    *n = d[1];
    if (*n < LOCK_PIN_MIN || *n > 8) return false;
    for (uint8_t i = 0; i < *n; i++) {
        uint8_t b = d[2 + i / 2];
        uint8_t v = (i % 2 == 0) ? (b >> 4) : (b & 0x0F);
        if (v > 9) return false;
        out[i] = (char)('0' + v);
    }
    return true;
}

static bool same(const uint8_t *a, const uint8_t *b) {
    uint8_t diff = 0;  // no early exit, so timing doesn't hint at the PIN
    for (int i = 0; i < 32; i++) diff |= (uint8_t)(a[i] ^ b[i]);
    return diff == 0;
}

static bool check(const vlock_t *l, const char *p, uint8_t n, bool puk) {
    uint8_t h[32];
    vlock_hash(l->saved.salt, p, n, h);
    return same(h, puk ? l->saved.puk_hash : l->saved.pin_hash);
}

static uint8_t wrong(vlock_t *l, uint32_t now) {
    if (l->saved.fails < 255) l->saved.fails++;
    save(l);
    if (l->saved.fails >= LOCK_FREE_TRIES) start_lockout(l, now);
    return LOCK_RES_WRONG;
}

static void right(vlock_t *l) {
    if (l->saved.fails) { l->saved.fails = 0; save(l); }
}

static uint8_t handle(vlock_t *l, const uint8_t *d, uint8_t dlc, bool can_lock, uint32_t now) {
    uint8_t cmd = d[0];
    char p[8];
    uint8_t n = 0;
    bool locked = vlock_is_locked(l);
    bool window = l->window;

    switch (cmd) {
    case LOCK_CMD_LOCK:
        if (!vlock_pin_set(l)) return LOCK_RES_NO_PIN;
        if (locked) return LOCK_RES_OK;
        if (!can_lock) return LOCK_RES_NOT_PARKED;
        l->saved.flags |= LOCKF_LOCKED;
        l->window = false;
        save(l);
        return LOCK_RES_OK;

    case LOCK_CMD_UNLOCK:
    case LOCK_CMD_VERIFY: {
        if (!vlock_pin_set(l)) return LOCK_RES_NO_PIN;
        if (l->lockout) return LOCK_RES_LOCKOUT;
        if (!digits(d, dlc, p, &n)) return LOCK_RES_BAD_DIGITS;
        if (n == LOCK_PUK_LEN && cmd == LOCK_CMD_UNLOCK && (l->saved.flags & LOCKF_PUK_SET)) {
            if (!check(l, p, n, true)) return wrong(l, now);
            // Recovery code: unlock and wipe both, so a new PIN must be set.
            forget(l);
            l->saved.fails = 0;
            save(l);
            l->window = true;
            l->window_from_ms = now;
            return LOCK_RES_RECOVERED;
        }
        if (n > LOCK_PIN_MAX) return LOCK_RES_BAD_DIGITS;
        if (!check(l, p, n, false)) return wrong(l, now);
        right(l);
        if (cmd == LOCK_CMD_UNLOCK) {
            // The right PIN also cancels a remote lock that hasn't happened yet.
            if (locked || vlock_pending(l)) {
                l->saved.flags &= (uint8_t)~(LOCKF_LOCKED | LOCKF_PENDING);
                save(l);
            }
        } else {
            if (locked) return LOCK_RES_NOT_ALLOWED;  // unlock first
            l->window = true;
            l->window_from_ms = now;
        }
        return LOCK_RES_OK;
    }

    case LOCK_CMD_REMOTE:
        // From the owner's phone, checked by the Pi (number + code). Locking is the
        // safe direction, so no PIN here, but it never cuts drive on the move: it
        // waits until vlock_remote_check() says it's stopped.
        if (!vlock_pin_set(l)) return LOCK_RES_NO_PIN;   // nobody could unlock it
        if (locked) return LOCK_RES_OK;
        if (!vlock_pending(l)) { l->saved.flags |= LOCKF_PENDING; save(l); }
        return LOCK_RES_PENDING;

    case LOCK_CMD_SET_PIN:
        if (locked) return LOCK_RES_NOT_ALLOWED;
        if (vlock_pin_set(l) && !window) return LOCK_RES_NOT_ALLOWED;
        if (!digits(d, dlc, p, &n) || n > LOCK_PIN_MAX) return LOCK_RES_BAD_DIGITS;
        // New salt each time a PIN is set. The old recovery code goes with it.
        for (int i = 0; i < 16; i += 4) {
            uint32_t r = vlock_random32();
            memcpy(&l->saved.salt[i], &r, 4);
        }
        vlock_hash(l->saved.salt, p, n, l->saved.pin_hash);
        memset(l->saved.puk_hash, 0, sizeof(l->saved.puk_hash));
        l->saved.flags = LOCKF_PIN_SET;
        l->saved.fails = 0;
        save(l);
        l->window = true;   // so the dash can send the recovery code next
        l->window_from_ms = now;
        return LOCK_RES_OK;

    case LOCK_CMD_SET_PUK:
        if (locked || !vlock_pin_set(l) || !window) return LOCK_RES_NOT_ALLOWED;
        if (!digits(d, dlc, p, &n) || n != LOCK_PUK_LEN) return LOCK_RES_BAD_DIGITS;
        vlock_hash(l->saved.salt, p, n, l->saved.puk_hash);
        l->saved.flags |= LOCKF_PUK_SET;
        save(l);
        return LOCK_RES_OK;

    case LOCK_CMD_REMOVE:
        if (locked || !window) return LOCK_RES_NOT_ALLOWED;
        forget(l);
        save(l);
        l->window = false;
        return LOCK_RES_OK;

    default:
        return LOCK_RES_NOT_ALLOWED;
    }
}

uint8_t vlock_on_frame(vlock_t *l, const uint8_t *d, uint8_t dlc, bool can_lock, uint32_t now) {
    vlock_tick(l, now);
    uint8_t r = dlc < 1 ? LOCK_RES_BAD_DIGITS : handle(l, d, dlc, can_lock, now);
    l->result = r;
    l->result_count++;
    return r;
}

void vlock_tick(vlock_t *l, uint32_t now) {
    if (l->lockout && since(now, l->lockout_from_ms) >= l->lockout_ms) l->lockout = false;
    if (l->window && since(now, l->window_from_ms) >= LOCK_WINDOW_MS) l->window = false;
}

void vlock_status(const vlock_t *l, uint32_t now, bool inhibit, uint8_t out[8]) {
    memset(out, 0, 8);
    out[0] = vlock_is_locked(l) ? LOCK_LOCKED : vlock_pin_set(l) ? LOCK_UNLOCKED : LOCK_OFF;
    uint8_t f = l->saved.fails;
    out[1] = l->lockout ? 0 : f < LOCK_FREE_TRIES ? (uint8_t)(LOCK_FREE_TRIES - f) : 1;
    uint32_t left = 0;
    if (l->lockout) left = (l->lockout_ms - since(now, l->lockout_from_ms) + 999u) / 1000u;
    out[2] = (uint8_t)left;
    out[3] = (uint8_t)(left >> 8);
    uint8_t flags = 0;
    if (l->window) flags |= LOCK_FLAG_WINDOW;
    if (l->saved.flags & LOCKF_PUK_SET) flags |= LOCK_FLAG_PUK_SET;
    if (inhibit) flags |= LOCK_FLAG_INHIBIT;
    if (l->lockout) flags |= LOCK_FLAG_LOCKOUT;
    if (vlock_pending(l)) flags |= LOCK_FLAG_PENDING;
    out[4] = flags;
    out[5] = l->result;
    out[6] = l->result_count;
    out[7] = f;
}

void vlock_workshop_reset(vlock_t *l) {
    memset(&l->saved, 0, sizeof(l->saved));
    save(l);
    l->lockout = false;
    l->window = false;
}
