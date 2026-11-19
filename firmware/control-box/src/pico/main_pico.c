// Teryx control box: Pico 2 main loop and hardware layer.
#include <stdio.h>
#include <string.h>

#include "hardware/adc.h"
#include "hardware/clocks.h"
#include "hardware/flash.h"
#include "hardware/gpio.h"
#include "hardware/i2c.h"
#include "hardware/pwm.h"
#include "hardware/spi.h"
#include "hardware/uart.h"
#include "hardware/watchdog.h"
#include "pico/bootrom.h"
#include "pico/flash.h"
#include "pico/rand.h"
#include "pico/stdlib.h"

#include "../core/config.h"
#include "../core/controller.h"
#include "ads1115.h"
#include "mcp23017.h"
#include "mcp2515.h"
#include "../core/eps.h"
#include "pca9685.h"

#define I2C_PORT i2c1
#define NC_INPUTS (BIT(IN_TRAY_DOWN) | BIT(IN_TRAY_UP))

static controller_t ctl;
static mcp2515_t can = {.spi = spi0, .cs_pin = PIN_CAN_CS, .int_pin = PIN_CAN_INT};
// Steering bus: second MCP2515 on the same SPI, own chip select. Its INT pin isn't
// wired: we poll its receive flags over SPI (mcp2515_recv reads CANINTF), so the
// int_pin below is never used for it.
static mcp2515_t eps_can = {.spi = spi0, .cs_pin = PIN_EPS_CAN_CS, .int_pin = PIN_CAN_INT};
static bool eps_up;
static uint32_t eps_last_ms;
static bool can_up;

// ---- CAN transmit queue (the MCP2515 only has 3 TX buffers) -----------------
#define TXQ 16
static can_frame_t txq[TXQ];
static uint8_t txq_head, txq_len;

static void can_send_cb(const can_frame_t *f, void *user) {
    (void)user;
    if (txq_len == TXQ) { txq_head = (uint8_t)((txq_head + 1) % TXQ); txq_len--; }  // drop oldest
    txq[(txq_head + txq_len) % TXQ] = *f;
    txq_len++;
}

static void can_flush(void) {
    while (can_up && txq_len && mcp2515_send(&can, &txq[txq_head])) {
        txq_head = (uint8_t)((txq_head + 1) % TXQ);
        txq_len--;
    }
}

// ---- Settings in the last flash sector --------------------------------------
#define SETTINGS_OFFSET (PICO_FLASH_SIZE_BYTES - FLASH_SECTOR_SIZE)

static bool settings_load(settings_t *s) {
    const settings_blob_t *b = (const settings_blob_t *)(XIP_BASE + SETTINGS_OFFSET);
    return settings_from_blob(s, b);
}

static void flash_write_cb(void *param) {
    static uint8_t page[FLASH_PAGE_SIZE * 2];
    _Static_assert(sizeof(settings_blob_t) <= sizeof(page), "settings blob too big");
    memset(page, 0xFF, sizeof(page));
    memcpy(page, param, sizeof(settings_blob_t));
    flash_range_erase(SETTINGS_OFFSET, FLASH_SECTOR_SIZE);
    flash_range_program(SETTINGS_OFFSET, page, sizeof(page));
}

static void settings_save(const settings_t *s) {
    static settings_blob_t blob;
    settings_to_blob(s, &blob);
    flash_safe_execute(flash_write_cb, &blob, 100);
}

// ---- Vehicle lock in the sector before it (docs/vehicle-lock.md) ---------------
#define LOCK_OFFSET (SETTINGS_OFFSET - FLASH_SECTOR_SIZE)

static void lock_write_cb(void *param) {
    static uint8_t page[FLASH_PAGE_SIZE];
    _Static_assert(sizeof(lock_blob_t) <= sizeof(page), "lock blob too big");
    memset(page, 0xFF, sizeof(page));
    memcpy(page, param, sizeof(lock_blob_t));
    flash_range_erase(LOCK_OFFSET, FLASH_SECTOR_SIZE);
    flash_range_program(LOCK_OFFSET, page, sizeof(page));
}

static void lock_save(const lock_blob_t *b) {
    static lock_blob_t copy;
    copy = *b;
    flash_safe_execute(lock_write_cb, &copy, 100);
}

uint32_t vlock_random32(void) { return get_rand_32(); }

// Workshop recovery: on the debug UART (GP0/GP1, inside the control box, not
// the Pi's USB) type "LOCK RESET" then Enter, with the key on and the park
// brake on. Wipes the PIN and recovery code and unlocks.
// Bench helper: every ID heard on the steering bus, so "EPS" on the console shows
// what the Aqua ECU actually sends (docs/power-steering-aqua.md, bench test step 4).
#define EPS_SEEN_MAX 24
static struct { uint16_t id; uint32_t count; uint8_t last[8]; uint8_t dlc; } eps_seen[EPS_SEEN_MAX];
static uint8_t eps_seen_n;

static void eps_note(const can_frame_t *f) {
    for (uint8_t i = 0; i < eps_seen_n; i++) {
        if (eps_seen[i].id == f->id) {
            eps_seen[i].count++;
            memcpy(eps_seen[i].last, f->data, 8);
            eps_seen[i].dlc = f->dlc;
            return;
        }
    }
    if (eps_seen_n < EPS_SEEN_MAX) {
        eps_seen[eps_seen_n].id = (uint16_t)f->id;
        eps_seen[eps_seen_n].count = 1;
        memcpy(eps_seen[eps_seen_n].last, f->data, 8);
        eps_seen[eps_seen_n].dlc = f->dlc;
        eps_seen_n++;
    }
}

static void eps_report(const controller_t *c) {
    char b[96];
    const eps_t *e = &c->eps;
    snprintf(b, sizeof b, "eps: mode %u state %u flags %02X told %u.%u km/h rx %lu badsum %lu\r\n",
             e->mode, e->state, e->flags, e->told_x10 / 10u, e->told_x10 % 10u,
             (unsigned long)e->rx_count, (unsigned long)e->bad_checksum);
    uart_puts(uart0, b);
    snprintf(b, sizeof b, "eps: torque %d angle %d.%d deg status %u\r\n", e->torque_raw,
             e->angle_x10 / 10, (e->angle_x10 < 0 ? -e->angle_x10 : e->angle_x10) % 10, e->status_raw);
    uart_puts(uart0, b);
    for (uint8_t i = 0; i < eps_seen_n; i++) {
        int k = snprintf(b, sizeof b, "  %03X x%lu:", eps_seen[i].id, (unsigned long)eps_seen[i].count);
        for (uint8_t j = 0; j < eps_seen[i].dlc && k < (int)sizeof b - 4; j++)
            k += snprintf(b + k, sizeof b - k, " %02X", eps_seen[i].last[j]);
        snprintf(b + k, sizeof b - k, "\r\n");
        uart_puts(uart0, b);
    }
}

static void uart_console(controller_t *c) {
    static char line[24];
    static uint8_t n;
    while (uart_is_readable(uart0)) {
        char ch = (char)uart_getc(uart0);
        if (ch == '\r' || ch == '\n') {
            line[n] = 0;
            if (!strcmp(line, "LOCK RESET")) {
                bool ok = (c->in.din & BIT(IN_IGNITION)) && (c->in.din & BIT(IN_PARK));
                if (ok) vlock_workshop_reset(&c->lock);
                uart_puts(uart0, ok ? "lock: wiped and unlocked\r\n" : "lock: key on and park brake on first\r\n");
            } else if (!strcmp(line, "EPS")) {
                eps_report(c);
            } else if (n) {
                uart_puts(uart0, "?\r\n");
            }
            n = 0;
        } else if (n < sizeof(line) - 1) {
            line[n++] = ch;
        }
    }
}

// ---- PWM ----------------------------------------------------------------------
static uint16_t light_wrap, act_wrap;

static uint16_t pwm_setup(uint pin, uint32_t hz) {
    gpio_set_function(pin, GPIO_FUNC_PWM);
    uint slice = pwm_gpio_to_slice_num(pin);
    uint32_t sys = clock_get_hz(clk_sys);
    uint32_t div = sys / (hz * 65536u) + 1u;
    uint32_t wrap = sys / (div * hz) - 1u;
    pwm_config cfg = pwm_get_default_config();
    pwm_config_set_clkdiv_int(&cfg, div);
    pwm_config_set_wrap(&cfg, (uint16_t)wrap);
    pwm_init(slice, &cfg, true);
    pwm_set_gpio_level(pin, 0);
    return (uint16_t)wrap;
}

static void pwm_duty(uint pin, uint16_t wrap, uint8_t duty) {
    // duty 255 = fully on (level above wrap keeps the pin high)
    uint32_t lvl = duty >= 255 ? (uint32_t)wrap + 1u : (uint32_t)duty * (wrap + 1u) / 255u;
    pwm_set_gpio_level(pin, (uint16_t)lvl);
}

static const uint light_pins[L_COUNT] = {
    PIN_LIGHT_FRONT_1, PIN_LIGHT_FRONT_2, PIN_LIGHT_FRONT_3, PIN_LIGHT_FRONT_4, PIN_LIGHT_INTERIOR,
};
static const uint act_pins[ACT_COUNT][3] = {
    {PIN_DIFF_RPWM, PIN_DIFF_LPWM, PIN_DIFF_EN},
    {PIN_4WD_RPWM, PIN_4WD_LPWM, PIN_4WD_EN},
    {PIN_TRAY_RPWM, PIN_TRAY_LPWM, PIN_TRAY_EN},
};

static void outputs_init(void) {
    for (int i = 0; i < ACT_COUNT; i++) {
        gpio_init(act_pins[i][2]);
        gpio_put(act_pins[i][2], 0);
        gpio_set_dir(act_pins[i][2], GPIO_OUT);
        act_wrap = pwm_setup(act_pins[i][0], ACT_PWM_HZ);
        pwm_setup(act_pins[i][1], ACT_PWM_HZ);
    }
    for (int i = 0; i < L_COUNT; i++) light_wrap = pwm_setup(light_pins[i], LIGHT_PWM_HZ);
}

static void outputs_write_pins(const cb_out_t *o) {
    for (int i = 0; i < ACT_COUNT; i++) {
        int8_t d = o->act_dir[i];
        // Never drive both halves of the bridge at once.
        pwm_duty(act_pins[i][0], act_wrap, d > 0 ? o->act_duty[i] : 0);
        pwm_duty(act_pins[i][1], act_wrap, d < 0 ? o->act_duty[i] : 0);
        gpio_put(act_pins[i][2], d != 0);
    }
    for (int i = 0; i < L_COUNT; i++) pwm_duty(light_pins[i], light_wrap, o->light[i]);
}

static uint8_t relay_bits_to_pins(uint8_t logical) {
    return S(&ctl, SET_RELAY_ACTIVE_LOW) ? (uint8_t)~logical : logical;
}

// ---- PCA9685 lamps ---------------------------------------------------------------
static const uint8_t lamp_ch[LP_COUNT] = LAMP_PCA_CH;
static bool pca_ok;
static uint8_t pca_written[16];
static bool pca_valid[16];
static uint32_t last_pca_retry_ms, last_pca_refresh_ms;

static void pca_init(void) {
    pca_ok = pca9685_init(I2C_PORT, PCA9685_ADDR, LAMP_PWM_HZ);
    for (int i = 0; i < 16; i++) pca_valid[i] = false;
}

static void pca_put(uint8_t ch, uint8_t duty, bool force) {
    if (!pca_ok || (!force && pca_valid[ch] && pca_written[ch] == duty)) return;
    if (pca9685_set(I2C_PORT, PCA9685_ADDR, ch, duty)) {
        pca_written[ch] = duty;
        pca_valid[ch] = true;
    } else {
        pca_ok = false;
    }
}

// Write on change, and every channel once a second anyway in case of a glitch.
static void lamps_write(const cb_out_t *o, uint32_t now) {
    if (!pca_ok) {
        if (now - last_pca_retry_ms > 500u) { last_pca_retry_ms = now; pca_init(); }
        if (!pca_ok) return;
    }
    bool force = now - last_pca_refresh_ms >= 1000u;
    if (force) last_pca_refresh_ms = now;
    for (int i = 0; i < LP_COUNT; i++) pca_put(lamp_ch[i], o->lamp[i], force);
    pca_put(PCA_CH_LAMP_ENABLE, o->lamp_enable ? 255 : 0, force);
}

// ---- I2C parts -------------------------------------------------------------------
static bool exp_ok, exp2_ok, ads_ok;
static int io_fail;
static uint8_t din_last;
static int ads_ch;
static int16_t ads_raw[4];
static bool pot_fresh;
static uint32_t pot_time_ms;
static uint32_t last_io_retry_ms;

static void ads_kick(void) {
    ads_ok = ads1115_start(I2C_PORT, ADS1115_ADDR, ads_ch);
}

static void io_init(void) {
    uint8_t off = relay_bits_to_pins(0);
    exp_ok = mcp23017_init(I2C_PORT, MCP23017_ADDR, off);
    // Second expander is optional (relays 9-10). Missing = no steering relay, no drive lock relay.
    exp2_ok = mcp23017_init(I2C_PORT, MCP23017_2_ADDR, off);
    ads_ch = 0;
    ads_kick();
}

static void io_poll(cb_in_t *in, uint32_t now) {
    uint8_t raw;
    if (exp_ok && mcp23017_read_b(I2C_PORT, MCP23017_ADDR, &raw)) {
        // Opto pulls the pin low when 12V is there. Normally-closed limits read
        // high when the switch opens (at limit) or the wire breaks.
        din_last = (uint8_t)((~raw & ~NC_INPUTS) | (raw & NC_INPUTS));
        io_fail = 0;
    } else {
        io_fail++;
    }
    bool ready = false;
    if (ads_ok && ads1115_ready(I2C_PORT, ADS1115_ADDR, &ready)) {
        if (ready) {
            int16_t v;
            if (ads1115_read(I2C_PORT, ADS1115_ADDR, &v)) {
                ads_raw[ads_ch] = v < 0 ? 0 : v;
                if (ads_ch == 0) { pot_fresh = true; pot_time_ms = now; }
            }
            ads_ch = (ads_ch + 1) & 3;
            ads_kick();
        }
    } else {
        io_fail++;
        ads_ok = false;
    }
    if ((!exp_ok || !ads_ok) && now - last_io_retry_ms > 500u) {
        last_io_retry_ms = now;
        io_init();
    }

    in->din = din_last;
    in->io_ok = exp_ok && ads_ok && io_fail < 3;
    in->pwm_ok = pca_ok;
    in->pot_ok = pot_fresh && now - pot_time_ms < 100u;
    in->diff_pot_raw = (uint16_t)ads_raw[0];
    uint32_t aux_adc_mv = (uint32_t)ads_raw[1] * ADS1115_UV_PER_COUNT / 1000u;
    in->aux_mv = (uint16_t)(aux_adc_mv * AUX_DIV_NUM / AUX_DIV_DEN);
    // current: mV * 10 / (117.6 mV/A) -> 0.1 A units
    in->i_da[ACT_4WD] = (uint16_t)((uint32_t)ads_raw[2] * ADS1115_UV_PER_COUNT / 1000u * 100u / BTS_IS_MV_PER_A_X10);
    in->i_da[ACT_TRAY] = (uint16_t)((uint32_t)ads_raw[3] * ADS1115_UV_PER_COUNT / 1000u * 100u / BTS_IS_MV_PER_A_X10);
}

static void pico_adc(cb_in_t *in) {
    adc_select_input(2);  // GP28, diff current
    uint32_t mv = (uint32_t)adc_read() * 3300u / 4096u;
    in->i_da[ACT_DIFF] = (uint16_t)(mv * 100u / BTS_IS_MV_PER_A_X10);
    adc_select_input(4);  // die temperature
    float v = adc_read() * 3.3f / 4096.0f;
    in->temp_c = (int8_t)(27.0f - (v - 0.706f) / 0.001721f);
}

// ---- Main ----------------------------------------------------------------------------
int main(void) {
    // USB serial for debugging. Also lets "picotool reboot -f -u" reach the
    // bootloader over USB as a fallback to the CAN request.
    stdio_init_all();
    bool wd_reset = watchdog_caused_reboot();

    outputs_init();  // every PWM output off, every bridge disabled

    gpio_init(PIN_CAN_INT);
    gpio_set_dir(PIN_CAN_INT, GPIO_IN);
    gpio_pull_up(PIN_CAN_INT);
    spi_init(spi0, 10 * 1000 * 1000);
    gpio_set_function(PIN_CAN_SCK, GPIO_FUNC_SPI);
    gpio_set_function(PIN_CAN_MOSI, GPIO_FUNC_SPI);
    gpio_set_function(PIN_CAN_MISO, GPIO_FUNC_SPI);
    gpio_init(PIN_CAN_CS);
    gpio_put(PIN_CAN_CS, 1);
    gpio_set_dir(PIN_CAN_CS, GPIO_OUT);
    gpio_init(PIN_EPS_CAN_CS);
    gpio_put(PIN_EPS_CAN_CS, 1);
    gpio_set_dir(PIN_EPS_CAN_CS, GPIO_OUT);
    can_up = mcp2515_init(&can, MCP2515_OSC_HZ, CAN_BITRATE);
    eps_up = mcp2515_init(&eps_can, MCP2515_OSC_HZ, EPS_BITRATE);

    i2c_init(I2C_PORT, I2C_BAUD);
    gpio_set_function(PIN_I2C_SDA, GPIO_FUNC_I2C);
    gpio_set_function(PIN_I2C_SCL, GPIO_FUNC_I2C);
    gpio_pull_up(PIN_I2C_SDA);
    gpio_pull_up(PIN_I2C_SCL);

    adc_init();
    adc_gpio_init(PIN_DIFF_IS);
    adc_set_temp_sensor_enabled(true);

    settings_t saved;
    bool have_saved = settings_load(&saved);
    ctl.settings = have_saved ? saved : (settings_t){0};
    if (!have_saved) settings_defaults(&ctl.settings);  // needed for relay polarity below

    // If only the Pico reset (watchdog, OTA) the expander still holds its
    // outputs. Keep power-hold as it was so the Pi isn't cut off mid shutdown.
    bool hold_on = false, a_out = false;
    uint8_t olat;
    if (mcp23017_port_a_is_output(I2C_PORT, MCP23017_ADDR, &a_out) && a_out &&
        mcp23017_read_olat_a(I2C_PORT, MCP23017_ADDR, &olat)) {
        hold_on = (relay_bits_to_pins(olat) & BIT(R_POWER_HOLD)) != 0;
    }
    io_init();
    pca_init();   // every lamp off, BTS7960 4-8 disabled
    if (hold_on) mcp23017_write_a(I2C_PORT, MCP23017_ADDR, relay_bits_to_pins(BIT(R_POWER_HOLD)));

    uint32_t now = to_ms_since_boot(get_absolute_time());
    ctl_init(&ctl, have_saved ? &saved : NULL, wd_reset, hold_on, now);
    ctl_load_lock(&ctl, (const lock_blob_t *)(XIP_BASE + LOCK_OFFSET), now);  // checks magic + CRC

    uart_init(uart0, 115200);
    gpio_set_function(PIN_UART_TX, GPIO_FUNC_UART);
    gpio_set_function(PIN_UART_RX, GPIO_FUNC_UART);

    watchdog_enable(WATCHDOG_MS, true);  // rule 9

    absolute_time_t next = get_absolute_time();
    uint8_t relays_written = 0xFF, relays2_written = 0xFF;
    uint32_t last_can_check = now;
    while (true) {
        watchdog_update();
        now = to_ms_since_boot(get_absolute_time());

        can_frame_t f;
        int n = 0;
        while (can_up && n++ < 16 && mcp2515_recv(&can, &f)) ctl_on_frame(&ctl, &f, now, can_send_cb, NULL);
        n = 0;
        while (eps_up && n++ < 8 && mcp2515_recv(&eps_can, &f)) {
            eps_note(&f);
            ctl_on_eps_frame(&ctl, &f, now);
        }

        if (absolute_time_diff_us(next, get_absolute_time()) >= 0) {
            next = delayed_by_ms(next, TICK_MS);
            cb_in_t in = {.now_ms = now, .eps_bus_down = !eps_up};
            io_poll(&in, now);
            pico_adc(&in);
            cb_out_t out;
            ctl_tick(&ctl, &in, &out, can_send_cb, NULL);

            outputs_write_pins(&out);
            lamps_write(&out, now);
            uint8_t pins = relay_bits_to_pins(out.relays);
            if (exp_ok && (pins != relays_written || (now & 0x3FF) < TICK_MS)) {
                // Write on change, and about once a second anyway in case of a glitch.
                if (mcp23017_write_a(I2C_PORT, MCP23017_ADDR, pins)) relays_written = pins;
            }
            uint8_t pins2 = relay_bits_to_pins(out.relays2);
            if (exp2_ok && (pins2 != relays2_written || (now & 0x3FF) < TICK_MS)) {
                if (mcp23017_write_a(I2C_PORT, MCP23017_2_ADDR, pins2)) relays2_written = pins2;
                else exp2_ok = false;
            }
            if (out.eps_on && eps_up && now - eps_last_ms >= EPS_PERIOD_MS) {
                eps_last_ms = now;
                can_frame_t ef[2];
                int nf = eps_frames(out.eps_speed_x10, out.eps_rpm, ef);
                for (int i = 0; i < nf; i++) mcp2515_send(&eps_can, &ef[i]);
            }

            if (out.save_lock) lock_save(&ctl.lock.saved);
            uart_console(&ctl);
            if (out.save_settings) {
                settings_save(&ctl.settings);
                ctl.out.save_settings = false;
            }
            if (out.enter_bootloader) {
                // The PCA9685 keeps its outputs while the Pico is in the bootloader, so
                // turn every lamp off first (the brake switch still lights the brakes).
                for (uint8_t ch = 0; ch < 16; ch++) pca_put(ch, 0, true);
                can_flush();
                sleep_ms(20);
                watchdog_disable();
                reset_usb_boot(0, 0);  // comes back as a USB drive / picotool device
            }
        }

        can_flush();
        if (now - last_can_check > 1000u) {
            last_can_check = now;
            if (!can_up || mcp2515_bus_off(&can)) can_up = mcp2515_init(&can, MCP2515_OSC_HZ, CAN_BITRATE);
            if (!eps_up || mcp2515_bus_off(&eps_can)) eps_up = mcp2515_init(&eps_can, MCP2515_OSC_HZ, EPS_BITRATE);
            if (!exp2_ok && (exp2_ok = mcp23017_init(I2C_PORT, MCP23017_2_ADDR, relay_bits_to_pins(0)))) relays2_written = 0xFF;
        }
        tight_loop_contents();
    }
}
