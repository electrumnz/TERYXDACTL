// Works out MCP2515 bit timing registers (CNF1-3) for any crystal and bit rate,
// instead of a fixed table, so 8 MHz and 16 MHz modules both do 10k to 1M.
#pragma once
#include <stdbool.h>
#include <stdint.h>

typedef struct {
    uint8_t cnf1, cnf2, cnf3;
    uint8_t brp;       // baud rate prescaler (0-63)
    uint8_t tq;        // time quanta per bit (5-25)
    uint8_t prop, ps1, ps2;
    uint16_t sample_permille;   // sample point, e.g. 875 = 87.5%
} mcp_timing_t;

// Returns false if the bit rate can't be made exactly from this crystal
// (e.g. 1 Mbit/s from an 8 MHz crystal).
bool mcp_timing(uint32_t osc_hz, uint32_t bitrate, mcp_timing_t *t);
