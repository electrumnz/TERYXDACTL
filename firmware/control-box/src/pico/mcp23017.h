// MCP23017: port A = 8 relay outputs, port B = 8 opto inputs.
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "hardware/i2c.h"

bool mcp23017_init(i2c_inst_t *i2c, uint8_t addr, uint8_t olat_a);
bool mcp23017_read_olat_a(i2c_inst_t *i2c, uint8_t addr, uint8_t *v);
// true if port A is already set up as outputs (the Pico reset, the expander did not)
bool mcp23017_port_a_is_output(i2c_inst_t *i2c, uint8_t addr, bool *yes);
bool mcp23017_write_a(i2c_inst_t *i2c, uint8_t addr, uint8_t v);
bool mcp23017_read_b(i2c_inst_t *i2c, uint8_t addr, uint8_t *v);
