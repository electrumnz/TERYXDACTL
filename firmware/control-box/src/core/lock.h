// Vehicle lock: PIN lock that the control box enforces (docs/vehicle-lock.md).
//
// The dash only asks. The Pico keeps the lock state, a salted hash of the PIN
// and of the recovery code, and the wrong-try count in its own flash sector,
// so rebooting the Pi, unplugging the screen or cutting power does not unlock.
#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "protocol.h"

#define LOCK_PIN_MIN        4
#define LOCK_PIN_MAX        6
#define LOCK_PUK_LEN        8
#define LOCK_FREE_TRIES     5        // wrong tries before the first lockout
#define LOCK_FIRST_WAIT_S   30u      // then 30 s, doubling each wrong try...
#define LOCK_MAX_WAIT_S     900u     // ...up to 15 min
#define LOCK_WINDOW_MS      60000u   // change window after a correct VERIFY
#define LOCK_HASH_ROUNDS    512

#define LOCK_MAGIC 0x4C4F434Bu       // "LOCK"
#define LOCKF_PIN_SET 0x01u
#define LOCKF_PUK_SET 0x02u
#define LOCKF_LOCKED  0x04u

// Stored in its own flash sector (or a file on the host build).
typedef struct {
    uint32_t magic;
    uint16_t version;
    uint8_t flags;           // LOCKF_*
    uint8_t fails;           // wrong tries in a row, kept over power cuts
    uint8_t salt[16];
    uint8_t pin_hash[32];
    uint8_t puk_hash[32];
    uint32_t crc;
} lock_blob_t;

typedef struct {
    lock_blob_t saved;       // what is (or should be) in flash
    bool dirty;              // hardware layer: write `saved` to flash, then clear
    bool lockout;
    uint32_t lockout_from_ms;
    uint32_t lockout_ms;
    bool window;
    uint32_t window_from_ms;
    uint8_t result;          // LOCK_RES_* of the last command
    uint8_t result_count;
} vlock_t;

// Every platform gives the core a random number (salt). Pico: get_rand_32().
uint32_t vlock_random32(void);

// saved = the blob read from flash, or NULL / garbage for "never set".
void vlock_init(vlock_t *l, const lock_blob_t *saved, uint32_t now_ms);
bool vlock_is_locked(const vlock_t *l);
bool vlock_pin_set(const vlock_t *l);
// One 0x705 frame. can_lock = stopped (or key off), park brake on, nothing moving.
uint8_t vlock_on_frame(vlock_t *l, const uint8_t *d, uint8_t dlc, bool can_lock, uint32_t now_ms);
void vlock_tick(vlock_t *l, uint32_t now_ms);
void vlock_status(const vlock_t *l, uint32_t now_ms, bool inhibit, uint8_t out[8]);
// Workshop recovery from the debug UART inside the control box: unlock and
// forget the PIN and code. Needs the box opened, so it can't be done from the dash.
void vlock_workshop_reset(vlock_t *l);

// The hash: h = SHA256(salt | digits as ASCII), then 511 more rounds of
// h = SHA256(h | salt). teryx/vehicle_lock.py does the same so tests can compare.
void vlock_hash(const uint8_t salt[16], const char *digits, uint8_t n, uint8_t out[32]);
uint32_t vlock_blob_crc(const lock_blob_t *b);
