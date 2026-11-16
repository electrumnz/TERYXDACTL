#include "mcp_timing.h"

// MCP2515 rules (datasheet section 5): bit = Sync(1) + Prop(1-8) + PS1(1-8) + PS2(2-8) TQ,
// Prop + PS1 >= PS2, PS2 > SJW. TQ = 2 * (BRP + 1) / Fosc. We aim for an 87.5 % sample
// point (the CANopen / most-vehicles choice) and as many TQ per bit as fit.
static bool split(uint8_t n, mcp_timing_t *t) {
    if (n < 5 || n > 25) return false;
    uint8_t ps2 = (uint8_t)((n + 4) / 8);           // about 12.5 % of the bit, rounded
    if (ps2 < 2) ps2 = 2;
    if (ps2 > 8) ps2 = 8;
    int rest = n - 1 - ps2;                          // prop + ps1
    if (rest < 2 || rest > 16) return false;
    uint8_t ps1 = (uint8_t)(rest / 2);
    uint8_t prop = (uint8_t)(rest - ps1);
    if (prop > 8) { ps1 = (uint8_t)(ps1 + prop - 8); prop = 8; }
    if (ps1 > 8 || ps1 < 1 || prop < 1 || prop + ps1 < ps2) return false;
    t->tq = n; t->prop = prop; t->ps1 = ps1; t->ps2 = ps2;
    t->sample_permille = (uint16_t)((1 + prop + ps1) * 1000 / n);
    return true;
}

bool mcp_timing(uint32_t osc_hz, uint32_t bitrate, mcp_timing_t *t) {
    if (!bitrate || !osc_hz) return false;
    // Two passes: first look for at least 8 TQ per bit (better sync), then accept 5-7.
    for (int pass = 0; pass < 2; pass++) {
        for (uint32_t brp = 0; brp < 64; brp++) {
            uint32_t div = 2u * (brp + 1u) * bitrate;
            if (osc_hz % div) continue;
            uint32_t n = osc_hz / div;
            if (n > 25) continue;
            if (pass == 0 && n < 8) continue;
            if (!split((uint8_t)n, t)) continue;
            t->brp = (uint8_t)brp;
            t->cnf1 = (uint8_t)(0x00 | brp);                       // SJW = 1 TQ
            t->cnf2 = (uint8_t)(0x80 | ((t->ps1 - 1) << 3) | (t->prop - 1));  // BTLMODE: PS2 from CNF3
            t->cnf3 = (uint8_t)(t->ps2 - 1);
            return true;
        }
    }
    return false;
}
