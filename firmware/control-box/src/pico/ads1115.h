// ADS1115 4-channel ADC, single-shot, read round robin without blocking.
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "hardware/i2c.h"

// Starts a conversion on channel ch (0-3, single ended, +/-4.096 V, 860 SPS).
bool ads1115_start(i2c_inst_t *i2c, uint8_t addr, int ch);
// true once the conversion is done; *raw is the signed result.
bool ads1115_ready(i2c_inst_t *i2c, uint8_t addr, bool *ready);
bool ads1115_read(i2c_inst_t *i2c, uint8_t addr, int16_t *raw);
#define ADS1115_UV_PER_COUNT 125   // 4.096 V / 32768
