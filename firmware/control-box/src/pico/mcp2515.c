#include "mcp2515.h"

#include "hardware/gpio.h"
#include "pico/stdlib.h"

#define CMD_RESET     0xC0
#define CMD_READ      0x03
#define CMD_WRITE     0x02
#define CMD_BITMOD    0x05
#define CMD_READ_RX0  0x90
#define CMD_READ_RX1  0x94
#define CMD_STATUS    0xA0

#define REG_CANSTAT   0x0E
#define REG_CANCTRL   0x0F
#define REG_CNF3      0x28
#define REG_CNF2      0x29
#define REG_CNF1      0x2A
#define REG_CANINTE   0x2B
#define REG_CANINTF   0x2C
#define REG_EFLG      0x2D
#define REG_TXB0CTRL  0x30
#define REG_RXB0CTRL  0x60
#define REG_RXB1CTRL  0x70

static inline void cs(mcp2515_t *m, bool on) {
    asm volatile("nop \n nop \n nop");
    gpio_put(m->cs_pin, !on);
    asm volatile("nop \n nop \n nop");
}

static void write_reg(mcp2515_t *m, uint8_t reg, uint8_t val) {
    uint8_t b[3] = {CMD_WRITE, reg, val};
    cs(m, true); spi_write_blocking(m->spi, b, 3); cs(m, false);
}

static uint8_t read_reg(mcp2515_t *m, uint8_t reg) {
    uint8_t b[2] = {CMD_READ, reg}, v = 0;
    cs(m, true); spi_write_blocking(m->spi, b, 2); spi_read_blocking(m->spi, 0, &v, 1); cs(m, false);
    return v;
}

static void bitmod(mcp2515_t *m, uint8_t reg, uint8_t mask, uint8_t val) {
    uint8_t b[4] = {CMD_BITMOD, reg, mask, val};
    cs(m, true); spi_write_blocking(m->spi, b, 4); cs(m, false);
}

// Bit timing tables (same values as the common Arduino mcp_can library).
static bool timing(uint32_t osc, uint32_t rate, uint8_t *c1, uint8_t *c2, uint8_t *c3) {
    if (osc == 8000000u && rate == 250000u)  { *c1 = 0x00; *c2 = 0xB1; *c3 = 0x85; return true; }
    if (osc == 8000000u && rate == 500000u)  { *c1 = 0x00; *c2 = 0x90; *c3 = 0x82; return true; }
    if (osc == 16000000u && rate == 250000u) { *c1 = 0x41; *c2 = 0xF1; *c3 = 0x85; return true; }
    if (osc == 16000000u && rate == 500000u) { *c1 = 0x00; *c2 = 0xF0; *c3 = 0x86; return true; }
    return false;
}

bool mcp2515_init(mcp2515_t *m, uint32_t osc_hz, uint32_t bitrate) {
    uint8_t c1, c2, c3;
    if (!timing(osc_hz, bitrate, &c1, &c2, &c3)) return false;
    uint8_t r = CMD_RESET;
    cs(m, true); spi_write_blocking(m->spi, &r, 1); cs(m, false);
    sleep_ms(5);
    if ((read_reg(m, REG_CANSTAT) & 0xE0) != 0x80) return false;  // not in config mode
    write_reg(m, REG_CNF1, c1);
    write_reg(m, REG_CNF2, c2);
    write_reg(m, REG_CNF3, c3);
    write_reg(m, REG_RXB0CTRL, 0x64);  // accept all, roll over into RXB1
    write_reg(m, REG_RXB1CTRL, 0x60);
    write_reg(m, REG_CANINTE, 0x03);   // RX0, RX1 interrupts (INT pin)
    write_reg(m, REG_CANINTF, 0x00);
    write_reg(m, REG_CANCTRL, 0x00);   // normal mode
    for (int i = 0; i < 10; i++) {
        if ((read_reg(m, REG_CANSTAT) & 0xE0) == 0x00) return true;
        sleep_ms(1);
    }
    return false;
}

bool mcp2515_send(mcp2515_t *m, const can_frame_t *f) {
    for (int b = 0; b < 3; b++) {
        uint8_t ctrl = (uint8_t)(REG_TXB0CTRL + b * 0x10);
        if (read_reg(m, ctrl) & 0x08) continue;  // TXREQ still set, buffer busy
        uint8_t buf[2 + 5 + 8];
        buf[0] = CMD_WRITE;
        buf[1] = (uint8_t)(ctrl + 1);  // TXBnSIDH
        if (f->ext) {
            buf[2] = (uint8_t)(f->id >> 21);
            buf[3] = (uint8_t)(((f->id >> 13) & 0xE0) | 0x08 | ((f->id >> 16) & 0x03));
            buf[4] = (uint8_t)(f->id >> 8);
            buf[5] = (uint8_t)f->id;
        } else {
            buf[2] = (uint8_t)(f->id >> 3);
            buf[3] = (uint8_t)((f->id & 0x07) << 5);
            buf[4] = 0;
            buf[5] = 0;
        }
        uint8_t dlc = f->dlc > 8 ? 8 : f->dlc;
        buf[6] = dlc;
        for (int i = 0; i < dlc; i++) buf[7 + i] = f->data[i];
        cs(m, true); spi_write_blocking(m->spi, buf, (size_t)(7 + dlc)); cs(m, false);
        bitmod(m, ctrl, 0x08, 0x08);  // request to send
        return true;
    }
    return false;  // all three buffers busy
}

bool mcp2515_recv(mcp2515_t *m, can_frame_t *f) {
    uint8_t intf = read_reg(m, REG_CANINTF);
    uint8_t cmd;
    if (intf & 0x01) cmd = CMD_READ_RX0;
    else if (intf & 0x02) cmd = CMD_READ_RX1;
    else return false;
    uint8_t h[5];
    cs(m, true);
    spi_write_blocking(m->spi, &cmd, 1);
    spi_read_blocking(m->spi, 0, h, 5);
    f->ext = (h[1] & 0x08) != 0;
    if (f->ext) {
        f->id = ((uint32_t)h[0] << 21) | ((uint32_t)(h[1] & 0xE0) << 13) |
                ((uint32_t)(h[1] & 0x03) << 16) | ((uint32_t)h[2] << 8) | h[3];
    } else {
        f->id = ((uint32_t)h[0] << 3) | (h[1] >> 5);
    }
    f->dlc = h[4] & 0x0F;
    if (f->dlc > 8) f->dlc = 8;
    spi_read_blocking(m->spi, 0, f->data, f->dlc);
    cs(m, false);  // raising CS after READ RX clears the RXnIF flag
    return true;
}

bool mcp2515_bus_off(mcp2515_t *m) {
    uint8_t e = read_reg(m, REG_EFLG);
    if (e & 0xC0) bitmod(m, REG_EFLG, 0xC0, 0x00);  // clear RX overflow
    return (e & 0x20) != 0;  // TXBO
}
