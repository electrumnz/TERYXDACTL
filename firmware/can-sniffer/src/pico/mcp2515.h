// MCP2515 driver for the sniffer: any bit rate (via mcp_timing), normal or
// listen-only mode, polled receive with overflow detection.
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "hardware/spi.h"
#include "../core/sniffer.h"

typedef struct {
    spi_inst_t *spi;
    uint cs_pin;
    uint int_pin;
    uint32_t osc_hz;
} mcp2515_t;

bool mcp2515_begin(mcp2515_t *m, uint32_t bitrate, bool listen_only);
void mcp2515_sleep(mcp2515_t *m);   // back to config mode: off the bus
bool mcp2515_send(mcp2515_t *m, const sn_frame_t *f);
bool mcp2515_recv(mcp2515_t *m, sn_frame_t *f);
// Returns true (and clears it) if the chip dropped a frame since last asked.
bool mcp2515_overflowed(mcp2515_t *m);
