#include "pca9685.h"

#define MODE1      0x00
#define MODE2      0x01
#define LED0_ON_L  0x06
#define ALL_OFF_H  0xFD
#define PRESCALE   0xFE
#define MODE1_SLEEP 0x10
#define MODE1_AI    0x20   // register auto-increment
#define MODE2_OUTDRV 0x04  // totem pole outputs (drive the MOSFET / BTS7960 inputs directly)
#define FULL_BIT    0x10
#define OSC_HZ      25000000u

static bool wr(i2c_inst_t *i2c, uint8_t addr, uint8_t reg, uint8_t v) {
    uint8_t b[2] = {reg, v};
    return i2c_write_timeout_us(i2c, addr, b, 2, false, 2000) == 2;
}

bool pca9685_init(i2c_inst_t *i2c, uint8_t addr, uint32_t hz) {
    uint32_t pre = (OSC_HZ + 2048u * hz) / (4096u * hz) - 1u;   // rounded
    if (pre < 3) pre = 3;
    if (pre > 255) pre = 255;
    return wr(i2c, addr, ALL_OFF_H, FULL_BIT) &&     // everything off first
           wr(i2c, addr, MODE1, MODE1_SLEEP | MODE1_AI) &&
           wr(i2c, addr, PRESCALE, (uint8_t)pre) &&   // only takes while asleep
           wr(i2c, addr, MODE2, MODE2_OUTDRV) &&
           wr(i2c, addr, MODE1, MODE1_AI);            // wake (oscillator needs 500 us)
}

bool pca9685_set(i2c_inst_t *i2c, uint8_t addr, uint8_t ch, uint8_t duty) {
    uint16_t on = 0, off = 0;
    if (duty == 0) off = FULL_BIT << 8;
    else if (duty == 255) on = FULL_BIT << 8;
    else off = (uint16_t)((uint32_t)duty * 4095u / 255u);
    uint8_t b[5] = {(uint8_t)(LED0_ON_L + 4u * ch), (uint8_t)on, (uint8_t)(on >> 8), (uint8_t)off, (uint8_t)(off >> 8)};
    return i2c_write_timeout_us(i2c, addr, b, 5, false, 2000) == 5;
}
