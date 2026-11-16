#include "ads1115.h"

#define REG_CONV 0x00
#define REG_CFG  0x01

bool ads1115_start(i2c_inst_t *i2c, uint8_t addr, int ch) {
    // OS=1 start, MUX=100+ch (AINx vs GND), PGA=001 (+/-4.096), MODE=1 single
    // DR=111 (860 SPS), comparator off (COMP_QUE=11).
    uint16_t cfg = (uint16_t)(0x8000 | ((4 + (ch & 3)) << 12) | (1 << 9) | (1 << 8) | (7 << 5) | 0x03);
    uint8_t b[3] = {REG_CFG, (uint8_t)(cfg >> 8), (uint8_t)cfg};
    return i2c_write_timeout_us(i2c, addr, b, 3, false, 2000) == 3;
}

static bool rd16(i2c_inst_t *i2c, uint8_t addr, uint8_t reg, uint16_t *v) {
    uint8_t b[2];
    if (i2c_write_timeout_us(i2c, addr, &reg, 1, true, 2000) != 1) return false;
    if (i2c_read_timeout_us(i2c, addr, b, 2, false, 2000) != 2) return false;
    *v = (uint16_t)((b[0] << 8) | b[1]);
    return true;
}

bool ads1115_ready(i2c_inst_t *i2c, uint8_t addr, bool *ready) {
    uint16_t cfg;
    if (!rd16(i2c, addr, REG_CFG, &cfg)) return false;
    *ready = (cfg & 0x8000) != 0;
    return true;
}

bool ads1115_read(i2c_inst_t *i2c, uint8_t addr, int16_t *raw) {
    uint16_t v;
    if (!rd16(i2c, addr, REG_CONV, &v)) return false;
    *raw = (int16_t)v;
    return true;
}
