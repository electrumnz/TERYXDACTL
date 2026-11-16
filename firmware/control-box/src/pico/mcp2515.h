// Minimal MCP2515 CAN driver for the Pico SDK (polled, 11-bit and 29-bit IDs).
#pragma once
#include <stdbool.h>
#include "hardware/spi.h"
#include "../core/protocol.h"

typedef struct {
    spi_inst_t *spi;
    uint cs_pin;
    uint int_pin;
} mcp2515_t;

bool mcp2515_init(mcp2515_t *m, uint32_t osc_hz, uint32_t bitrate);
bool mcp2515_send(mcp2515_t *m, const can_frame_t *f);
bool mcp2515_recv(mcp2515_t *m, can_frame_t *f);
// Returns true if the chip has gone bus-off or has errors that need a re-init.
bool mcp2515_bus_off(mcp2515_t *m);
