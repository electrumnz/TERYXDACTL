#include "mcp23017.h"

// IOCON.BANK = 0 register map
#define IODIRA 0x00
#define IODIRB 0x01
#define GPPUB  0x0D
#define GPIOB  0x13
#define OLATA  0x14

static bool wr(i2c_inst_t *i2c, uint8_t addr, uint8_t reg, uint8_t v) {
    uint8_t b[2] = {reg, v};
    return i2c_write_timeout_us(i2c, addr, b, 2, false, 2000) == 2;
}

static bool rd(i2c_inst_t *i2c, uint8_t addr, uint8_t reg, uint8_t *v) {
    if (i2c_write_timeout_us(i2c, addr, &reg, 1, true, 2000) != 1) return false;
    return i2c_read_timeout_us(i2c, addr, v, 1, false, 2000) == 1;
}

bool mcp23017_read_olat_a(i2c_inst_t *i2c, uint8_t addr, uint8_t *v) { return rd(i2c, addr, OLATA, v); }

bool mcp23017_init(i2c_inst_t *i2c, uint8_t addr, uint8_t olat_a) {
    // Latch the "all off" pattern BEFORE turning port A into outputs, so no
    // relay clicks on at power-up.
    return wr(i2c, addr, OLATA, olat_a) &&
           wr(i2c, addr, IODIRA, 0x00) &&
           wr(i2c, addr, IODIRB, 0xFF) &&
           wr(i2c, addr, GPPUB, 0xFF);   // opto outputs pull low when 12V is present
}

bool mcp23017_write_a(i2c_inst_t *i2c, uint8_t addr, uint8_t v) { return wr(i2c, addr, OLATA, v); }
bool mcp23017_read_b(i2c_inst_t *i2c, uint8_t addr, uint8_t *v) { return rd(i2c, addr, GPIOB, v); }

bool mcp23017_port_a_is_output(i2c_inst_t *i2c, uint8_t addr, bool *yes) {
    uint8_t v;
    if (!rd(i2c, addr, IODIRA, &v)) return false;
    *yes = v == 0x00;
    return true;
}
