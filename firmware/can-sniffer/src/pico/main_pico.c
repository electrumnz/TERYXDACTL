// Teryx CAN sniffer: Pico 2 + MCP2515 as a USB CAN adaptor (slcan + GVRET).
//
// Core 1 owns the MCP2515 and does nothing but move frames into a queue, so a
// busy USB link never makes the chip's two receive buffers overflow. Core 0
// runs the USB protocol (src/core/sniffer.c) and the LED.
//
// Wiring is the same as the control box, so the same MCP2515 module works:
//   GP2 SCK, GP3 MOSI (SI), GP4 MISO (SO), GP5 CS, GP6 INT, 3V3 / GND.
//   GP15: TX jumper. Leave it open = listen only, can never send.
//         Bridge GP15 to GND only when you really want to send frames.
//   LED: slow blink = waiting, steady = bus open, flicker = frames,
//        fast blink = bus open but the MCP2515 isn't answering.
#include <string.h>

#include "hardware/gpio.h"
#include "hardware/spi.h"
#include "hardware/watchdog.h"
#include "pico/multicore.h"
#include "pico/stdio/driver.h"
#include "pico/stdio_usb.h"
#include "pico/stdlib.h"
#include "pico/util/queue.h"

#include "../core/sniffer.h"
#include "mcp2515.h"

#ifndef SNIFFER_OSC_HZ
#define SNIFFER_OSC_HZ 8000000u   // most blue MCP2515 modules; 16 MHz build also in CI
#endif

#define PIN_SCK  2
#define PIN_MOSI 3
#define PIN_MISO 4
#define PIN_CS   5
#define PIN_INT  6
#define PIN_TXEN 15
#ifdef PICO_DEFAULT_LED_PIN
#define PIN_LED PICO_DEFAULT_LED_PIN
#endif

typedef enum { CMD_OPEN, CMD_CLOSE, CMD_SEND } cmd_type_t;
typedef struct {
    cmd_type_t type;
    uint32_t bitrate;
    bool listen;
    sn_frame_t frame;
} cmd_t;
typedef struct {
    sn_frame_t frame;
    uint32_t t_us;
} rx_t;

static queue_t cmd_q, res_q, rx_q;
static volatile uint32_t overflows;
static volatile bool chip_ok = true;

// ------------------------------------------------------------------ core 1: CAN

static void core1_main(void) {
    mcp2515_t can = {.spi = spi0, .cs_pin = PIN_CS, .int_pin = PIN_INT, .osc_hz = SNIFFER_OSC_HZ};
    bool up = false;
    uint32_t last_check = 0;
    for (;;) {
        cmd_t c;
        if (queue_try_remove(&cmd_q, &c)) {
            bool r = true;
            if (c.type == CMD_OPEN) {
                up = mcp2515_begin(&can, c.bitrate, c.listen);
                chip_ok = up;
                r = up;
            } else if (c.type == CMD_CLOSE) {
                if (up) mcp2515_sleep(&can);
                up = false;
            } else {
                r = up && mcp2515_send(&can, &c.frame);
            }
            queue_add_blocking(&res_q, &r);
        }
        if (!up) continue;
        for (int n = 0; n < 8 && !gpio_get(PIN_INT); n++) {
            rx_t rx;
            if (!mcp2515_recv(&can, &rx.frame)) break;
            rx.t_us = time_us_32();
            if (!queue_try_add(&rx_q, &rx)) overflows++;
        }
        uint32_t now = time_us_32();
        if (now - last_check > 20000) {
            last_check = now;
            if (mcp2515_overflowed(&can)) overflows++;
        }
    }
}

static bool core1_call(const cmd_t *c) {
    bool r = false;
    queue_add_blocking(&cmd_q, c);
    queue_remove_blocking(&res_q, &r);
    return r;
}

// ------------------------------------------------------------------ core 0: USB

static uint8_t usb_out[1024];
static size_t usb_len;

static void flush_usb(void) {
    if (usb_len) {
        stdio_usb.out_chars((const char *)usb_out, (int)usb_len);
        usb_len = 0;
    }
}

static void hw_write(void *ctx, const uint8_t *buf, size_t len) {
    if (usb_len + len > sizeof usb_out) flush_usb();
    memcpy(usb_out + usb_len, buf, len);
    usb_len += len;
}

static bool hw_open(void *ctx, uint32_t bitrate, sn_mode_t mode) {
    cmd_t c = {.type = CMD_OPEN, .bitrate = bitrate, .listen = mode == SN_MODE_LISTEN};
    return core1_call(&c);
}

static void hw_close(void *ctx) {
    cmd_t c = {.type = CMD_CLOSE};
    core1_call(&c);
}

static bool hw_send(void *ctx, const sn_frame_t *f) {
    cmd_t c = {.type = CMD_SEND, .frame = *f};
    return core1_call(&c);
}

static bool hw_tx_allowed(void *ctx) { return !gpio_get(PIN_TXEN); }

int main(void) {
    stdio_usb_init();

    spi_init(spi0, 10 * 1000 * 1000);
    gpio_set_function(PIN_SCK, GPIO_FUNC_SPI);
    gpio_set_function(PIN_MOSI, GPIO_FUNC_SPI);
    gpio_set_function(PIN_MISO, GPIO_FUNC_SPI);
    gpio_init(PIN_CS);
    gpio_put(PIN_CS, 1);
    gpio_set_dir(PIN_CS, GPIO_OUT);
    gpio_init(PIN_INT);
    gpio_set_dir(PIN_INT, GPIO_IN);
    gpio_pull_up(PIN_INT);
    gpio_init(PIN_TXEN);
    gpio_set_dir(PIN_TXEN, GPIO_IN);
    gpio_pull_up(PIN_TXEN);
#ifdef PIN_LED
    gpio_init(PIN_LED);
    gpio_set_dir(PIN_LED, GPIO_OUT);
#endif

    queue_init(&cmd_q, sizeof(cmd_t), 2);
    queue_init(&res_q, sizeof(bool), 2);
    queue_init(&rx_q, sizeof(rx_t), 512);
    multicore_launch_core1(core1_main);

    sniffer_t sn;
    sn_hw_t hw = {hw_open, hw_close, hw_send, hw_write, hw_tx_allowed, NULL};
    sn_init(&sn, &hw);

    bool was_connected = false;
    uint32_t seen_overflows = 0, last_frame = 0;
    for (;;) {
        bool connected = stdio_usb_connected();
        if (was_connected && !connected) {
            // Computer went away: get off the bus and forget the protocol.
            if (sn.open) hw_close(NULL);
            sn_init(&sn, &hw);
            usb_len = 0;
        }
        was_connected = connected;

        char in[64];
        int n = stdio_usb.in_chars(in, sizeof in);
        if (n > 0) sn_rx_bytes(&sn, (const uint8_t *)in, (size_t)n, time_us_32());

        rx_t rx;
        for (int k = 0; k < 64 && queue_try_remove(&rx_q, &rx); k++) {
            sn_on_frame(&sn, &rx.frame, rx.t_us);
            last_frame = time_us_32();
        }
        uint32_t ov = overflows;
        if (ov != seen_overflows) {
            seen_overflows = ov;
            sn_note_overflow(&sn);
        }
        flush_usb();

#ifdef PIN_LED
        uint32_t ms = to_ms_since_boot(get_absolute_time());
        bool led;
        if (!sn.open) led = (ms / 500) % 2;                       // waiting
        else if (!chip_ok) led = (ms / 80) % 2;                   // MCP2515 not answering
        else if (time_us_32() - last_frame < 50000) led = (ms / 25) % 2;   // frames flowing
        else led = true;                                          // open, quiet bus
        gpio_put(PIN_LED, led);
#endif
    }
}
