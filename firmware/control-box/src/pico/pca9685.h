// PCA9685 16-channel 12-bit PWM board (0x40): stock lamps, floods, beacon, trailer bar.
// docs/lights.md has the channel map (also LAMP_PCA_CH in config.h).
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "hardware/i2c.h"

// Sets the PWM frequency and turns every channel off.
bool pca9685_init(i2c_inst_t *i2c, uint8_t addr, uint32_t hz);
// duty 0 = fully off, 255 = fully on (no PWM at either end).
bool pca9685_set(i2c_inst_t *i2c, uint8_t addr, uint8_t ch, uint8_t duty);
