// Pin-level model of the control box board, for the system sim (docs/system-sim.md).
//
// The unchanged src/pico/main_pico.c runs on its own thread against this file.
// Time is virtual: the firmware only moves on when Python calls rig_run_us(),
// and every pass of its main loop costs LOOP_US. So a run is the same every time
// and as fast as the PC allows.
//
// Models, each only as deep as the drivers use it (datasheet register maps):
//   RP2350   GPIO function / direction / level, PWM slices, ADC, watchdog, flash, UART0
//   MCP23017 IODIR, GPPU, GPIO, OLAT (IOCON.BANK = 0)
//   ADS1115  config + conversion registers, single shot, PGA, data rate timing
//   PCA9685  MODE1/2, PRESCALE, LEDn ON/OFF with the FULL bits, ALL_LED
//   MCP2515  SPI commands RESET, READ, WRITE, BIT MODIFY, READ RX BUFFER; modes,
//            CNF bit timing, 3 TX buffers, RXB0 -> RXB1 rollover, CANINTF, EFLG
#include "sdk/rig_sdk.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define RIG_API __attribute__((visibility("default")))
#define LOOP_US 250u          // cost of one pass of the firmware main loop
#define NPINS 48
#define NSLICES 12
#define CLK_SYS_HZ 150000000u // RP2350 default

int pico_main(void);          // main_pico.c's main(), renamed with -Dmain=pico_main

// ---------------------------------------------------------------- state
enum { RUN_IDLE, RUN_RUNNING, RUN_PARKED, RUN_EXITED };
enum { EXIT_NONE, EXIT_STOPPED, EXIT_WATCHDOG, EXIT_BOOTLOADER, EXIT_RETURNED };

// Two ways to run the firmware next to its caller, same behaviour:
//  * PC (Linux, macOS): its own thread, handed the CPU with a mutex + condition.
//  * Browser (Emscripten, the phone sim on GitHub Pages): a fiber on one thread,
//    swapped in and out with emscripten_fiber_swap (needs -sASYNCIFY).
#ifdef __EMSCRIPTEN__
#include <emscripten/fiber.h>
#define FW_STACK (64 * 1024)
static emscripten_fiber_t fib_main, fib_fw;
static char fib_main_astack[16 * 1024];
static char fib_fw_cstack[FW_STACK] __attribute__((aligned(16)));
static char fib_fw_astack[FW_STACK];
#define LOCK() ((void)0)
#define UNLOCK() ((void)0)
#else
#include <pthread.h>
#define LOCK() pthread_mutex_lock(&R.mu)
#define UNLOCK() pthread_mutex_unlock(&R.mu)
#endif

static struct {
#ifndef __EMSCRIPTEN__
    pthread_t thread;
    pthread_mutex_t mu;
    pthread_cond_t cv;
#endif
    bool started;
    int run;
    int exit_reason;
    bool quit;
    uint64_t now_us, target_us;
    // watchdog
    bool wd_on, wd_rebooted;
    uint32_t wd_ms;
    uint64_t wd_last_us;
    // errors seen (a short text log Python reads)
    char errors[2048];
} R;

static void note_error(const char *msg) {
    if (strstr(R.errors, msg)) return;  // once each
    size_t n = strlen(R.errors);
    snprintf(R.errors + n, sizeof R.errors - n, "%s\n", msg);
}

// ---- gpio + pwm
static struct { uint8_t fn; bool out_dir, out, pull_up; int8_t ext; } G[NPINS];  // ext: -1 float, 0, 1
static struct { uint32_t div, top; bool on; uint16_t level[2]; } S[NSLICES];
static uint spi_pins[3] = {2, 3, 4}, i2c_pins[2] = {26, 27}, uart_pins[2] = {0, 1};

// ---- adc
static uint adc_input;
static double adc_mv[5];
static double die_temp_c = 25.0;

// ---- uart
static char uart_tx[8192];
static size_t uart_tx_n;
static char uart_rx[256];
static size_t uart_rx_head, uart_rx_len;

// ---- flash
uint8_t rig_flash[PICO_FLASH_SIZE_BYTES];

// ---- i2c chips
enum { DEV_MCP23017 = 1, DEV_ADS1115 = 2, DEV_PCA9685 = 3 };
#define NI2C 8
static struct {
    int kind;
    uint8_t addr;
    bool powered;
    uint8_t reg[256];
    uint8_t ptr;
    // MCP23017: what the outside world does to each port B / A pin
    uint8_t ext_mask[2], ext_level[2];
    // ADS1115
    double in_mv[4];
    uint64_t conv_done_us;
    int16_t conv, pending;
} D[NI2C];
static int n_i2c;

// ---- mcp2515 chips
#define NCAN 4
#define QLEN 64
typedef struct { uint32_t id; uint8_t ext, dlc, data[8]; } rig_frame_t;
static struct {
    uint cs_pin;
    uint32_t osc_hz;
    bool powered, acked, selected;
    uint8_t reg[128];
    // the transaction in progress
    int phase;
    uint8_t cmd, addr, mask;
    int rxbuf;  // which RX buffer a READ RX command is streaming, -1 none
    rig_frame_t tx[QLEN];
    int tx_head, tx_len;
    rig_frame_t rx[QLEN];
    int rx_head, rx_len;
    uint32_t tx_dropped, rx_overflow;
} C[NCAN];
static int n_can;

struct rig_spi { int n; };
struct rig_i2c { int n; };
struct rig_uart { int n; };
spi_inst_t rig_spi0_obj = {0};
i2c_inst_t rig_i2c0_obj = {0}, rig_i2c1_obj = {1};
uart_inst_t rig_uart0_obj = {0};

// ---------------------------------------------------------------- scheduling
// The firmware thread gives the CPU back here. It parks once virtual time
// reaches the target Python asked for, and waits for the next rig_run_us().
#ifdef __EMSCRIPTEN__
static void yield_us(uint64_t us) {
    R.now_us += us;
    if (R.wd_on && R.now_us - R.wd_last_us > (uint64_t)R.wd_ms * 1000u) {
        R.exit_reason = EXIT_WATCHDOG;
        R.quit = true;
    }
    while (!R.quit && R.now_us >= R.target_us) {
        R.run = RUN_PARKED;
        emscripten_fiber_swap(&fib_fw, &fib_main);
    }
    if (R.quit) {
        if (R.exit_reason == EXIT_NONE) R.exit_reason = EXIT_STOPPED;
        R.run = RUN_EXITED;
        for (;;) emscripten_fiber_swap(&fib_fw, &fib_main);  // never comes back
    }
    R.run = RUN_RUNNING;
}

static void fw_fiber(void *arg) {
    (void)arg;
    yield_us(0);
    pico_main();
    R.exit_reason = EXIT_RETURNED;
    R.run = RUN_EXITED;
    for (;;) emscripten_fiber_swap(&fib_fw, &fib_main);
}
#else
static void yield_us(uint64_t us) {
    pthread_mutex_lock(&R.mu);
    R.now_us += us;
    if (R.wd_on && R.now_us - R.wd_last_us > (uint64_t)R.wd_ms * 1000u) {
        R.exit_reason = EXIT_WATCHDOG;
        R.quit = true;
    }
    while (!R.quit && R.now_us >= R.target_us) {
        R.run = RUN_PARKED;
        pthread_cond_broadcast(&R.cv);
        pthread_cond_wait(&R.cv, &R.mu);
    }
    if (R.quit) {
        if (R.exit_reason == EXIT_NONE) R.exit_reason = EXIT_STOPPED;
        R.run = RUN_EXITED;
        pthread_cond_broadcast(&R.cv);
        pthread_mutex_unlock(&R.mu);
        pthread_exit(NULL);
    }
    R.run = RUN_RUNNING;
    pthread_mutex_unlock(&R.mu);
}

static void *fw_thread(void *arg) {
    (void)arg;
    yield_us(0);  // wait for the first run
    pico_main();
    pthread_mutex_lock(&R.mu);
    R.exit_reason = EXIT_RETURNED;
    R.run = RUN_EXITED;
    pthread_cond_broadcast(&R.cv);
    pthread_mutex_unlock(&R.mu);
    return NULL;
}
#endif

// ---------------------------------------------------------------- SDK: time
absolute_time_t get_absolute_time(void) { return R.now_us; }
uint32_t to_ms_since_boot(absolute_time_t t) { return (uint32_t)(t / 1000u); }
int64_t absolute_time_diff_us(absolute_time_t from, absolute_time_t to) { return (int64_t)(to - from); }
absolute_time_t delayed_by_ms(absolute_time_t t, uint32_t ms) { return t + (uint64_t)ms * 1000u; }
void sleep_ms(uint32_t ms) {
    uint64_t end = R.now_us + (uint64_t)ms * 1000u;
    while (R.now_us < end) yield_us(LOOP_US);
}
void tight_loop_contents(void) { yield_us(LOOP_US); }
bool stdio_init_all(void) { return true; }

// ---------------------------------------------------------------- SDK: gpio
static int can_by_cs(uint pin) {
    for (int i = 0; i < n_can; i++) if (C[i].cs_pin == pin) return i;
    return -1;
}
static void can_cs(int i, bool low);

void gpio_init(uint pin) {
    if (pin >= NPINS) return;
    G[pin].fn = GPIO_FUNC_SIO;
    G[pin].out_dir = false;
    G[pin].out = false;
}
void gpio_put(uint pin, bool value) {
    if (pin >= NPINS) return;
    bool was = G[pin].out;
    G[pin].out = value;
    int c = can_by_cs(pin);
    if (c >= 0 && G[pin].fn == GPIO_FUNC_SIO && G[pin].out_dir && was != value) can_cs(c, !value);
}
bool gpio_get(uint pin) {
    if (pin >= NPINS) return false;
    if (G[pin].fn == GPIO_FUNC_SIO && G[pin].out_dir) return G[pin].out;
    if (G[pin].ext >= 0) return G[pin].ext;
    return G[pin].pull_up;
}
void gpio_set_dir(uint pin, bool out) { if (pin < NPINS) G[pin].out_dir = out; }
void gpio_set_function(uint pin, enum gpio_function fn) { if (pin < NPINS) G[pin].fn = (uint8_t)fn; }
void gpio_pull_up(uint pin) { if (pin < NPINS) G[pin].pull_up = true; }

// ---------------------------------------------------------------- SDK: pwm
uint pwm_gpio_to_slice_num(uint pin) { return pin < 32 ? (pin >> 1) & 7u : 8u + ((pin >> 1) & 3u); }
pwm_config pwm_get_default_config(void) { return (pwm_config){.div = 1, .top = 0xFFFF}; }
void pwm_config_set_clkdiv_int(pwm_config *c, uint32_t div) { c->div = div ? div : 1; }
void pwm_config_set_wrap(pwm_config *c, uint16_t wrap) { c->top = wrap; }
void pwm_init(uint slice, pwm_config *c, bool start) {
    if (slice >= NSLICES) return;
    if (S[slice].on && (S[slice].div != c->div || S[slice].top != c->top))
        note_error("pwm: a slice was set up twice with different speeds (two outputs share it)");
    S[slice].div = c->div;
    S[slice].top = c->top;
    S[slice].on = start;
}
void pwm_set_gpio_level(uint pin, uint16_t level) {
    uint s = pwm_gpio_to_slice_num(pin);
    if (s < NSLICES) S[s].level[pin & 1u] = level;
}
uint32_t clock_get_hz(enum clock_index clk) { (void)clk; return CLK_SYS_HZ; }

// ---------------------------------------------------------------- SDK: adc
void adc_init(void) {}
void adc_gpio_init(uint pin) { if (pin < NPINS) G[pin].fn = GPIO_FUNC_NULL; }
void adc_set_temp_sensor_enabled(bool on) { (void)on; }
void adc_select_input(uint input) { adc_input = input; }
uint16_t adc_read(void) {
    double mv;
    if (adc_input == 4) mv = (0.706 - (die_temp_c - 27.0) * 0.001721) * 1000.0;
    else if (adc_input < 4) mv = adc_mv[adc_input];
    else return 0;
    double c = mv * 4096.0 / 3300.0;
    if (c < 0) c = 0;
    if (c > 4095) c = 4095;
    return (uint16_t)c;
}

// ---------------------------------------------------------------- SDK: uart
uint uart_init(uart_inst_t *u, uint baud) { (void)u; return baud; }
void uart_puts(uart_inst_t *u, const char *s) {
    (void)u;
    if (G[uart_pins[0]].fn != GPIO_FUNC_UART) return;  // TX pin not set up: nothing comes out
    size_t n = strlen(s);
    if (uart_tx_n + n >= sizeof uart_tx) uart_tx_n = 0;
    memcpy(uart_tx + uart_tx_n, s, n);
    uart_tx_n += n;
    uart_tx[uart_tx_n] = 0;
}
bool uart_is_readable(uart_inst_t *u) { (void)u; return uart_rx_len > 0 && G[uart_pins[1]].fn == GPIO_FUNC_UART; }
char uart_getc(uart_inst_t *u) {
    (void)u;
    if (!uart_rx_len) return 0;
    char c = uart_rx[uart_rx_head];
    uart_rx_head = (uart_rx_head + 1) % sizeof uart_rx;
    uart_rx_len--;
    return c;
}

// ---------------------------------------------------------------- SDK: watchdog, flash, boot
void watchdog_enable(uint32_t ms, bool p) { (void)p; R.wd_on = true; R.wd_ms = ms; R.wd_last_us = R.now_us; }
void watchdog_update(void) { R.wd_last_us = R.now_us; }
void watchdog_disable(void) { R.wd_on = false; }
bool watchdog_caused_reboot(void) { return R.wd_rebooted; }
void flash_range_erase(uint32_t off, size_t n) {
    if (off % FLASH_SECTOR_SIZE || n % FLASH_SECTOR_SIZE || off + n > PICO_FLASH_SIZE_BYTES) { note_error("flash: bad erase"); return; }
    memset(rig_flash + off, 0xFF, n);
}
void flash_range_program(uint32_t off, const uint8_t *data, size_t n) {
    if (off % FLASH_PAGE_SIZE || n % FLASH_PAGE_SIZE || off + n > PICO_FLASH_SIZE_BYTES) { note_error("flash: bad program"); return; }
    for (size_t i = 0; i < n; i++) rig_flash[off + i] &= data[i];  // flash can only clear bits
}
int flash_safe_execute(void (*fn)(void *), void *param, uint32_t t) { (void)t; fn(param); return PICO_OK; }
void reset_usb_boot(uint32_t a, uint32_t b) {
    (void)a; (void)b;
    LOCK();
    R.exit_reason = EXIT_BOOTLOADER;
    R.quit = true;
    UNLOCK();
    yield_us(0);  // never returns
    for (;;) {}
}
static uint64_t rand_state = 0x9E3779B97F4A7C15ull;
uint32_t get_rand_32(void) {
    rand_state ^= rand_state << 13; rand_state ^= rand_state >> 7; rand_state ^= rand_state << 17;
    return (uint32_t)rand_state;
}

// ---------------------------------------------------------------- I2C chips
static bool i2c_pins_ok(void) {
    return G[i2c_pins[0]].fn == GPIO_FUNC_I2C && G[i2c_pins[1]].fn == GPIO_FUNC_I2C;
}
static int i2c_dev(i2c_inst_t *bus, uint8_t addr) {
    if (bus != i2c1 || !i2c_pins_ok()) return -1;
    for (int i = 0; i < n_i2c; i++) if (D[i].addr == addr && D[i].powered) return i;
    return -1;
}

static void mcp_reset(int i) {
    memset(D[i].reg, 0, sizeof D[i].reg);
    D[i].reg[0x00] = D[i].reg[0x01] = 0xFF;  // IODIRA/B: all inputs at power up
}
static uint8_t mcp_port_in(int i, int port) {
    uint8_t iodir = D[i].reg[port], gppu = D[i].reg[0x0C + port], olat = D[i].reg[0x14 + port];
    uint8_t v = 0;
    for (int b = 0; b < 8; b++) {
        bool level;
        if (!(iodir & (1u << b))) level = olat & (1u << b);
        else if (D[i].ext_mask[port] & (1u << b)) level = D[i].ext_level[port] & (1u << b);
        else level = (gppu >> b) & 1u;  // floating: pull-up or reads low
        if (level) v |= (uint8_t)(1u << b);
    }
    return v ^ D[i].reg[0x02 + port];  // IPOL
}
static uint8_t mcp_read(int i, uint8_t r) {
    if (r == 0x12 || r == 0x13) return mcp_port_in(i, r - 0x12);
    return D[i].reg[r];
}
static void mcp_write(int i, uint8_t r, uint8_t v) {
    if (r > 0x15) return;
    if (r == 0x12 || r == 0x13) r = (uint8_t)(r + 2);  // writing GPIO writes OLAT
    D[i].reg[r] = v;
}

static void ads_reset(int i) {
    memset(D[i].reg, 0, sizeof D[i].reg);
    D[i].reg[2] = 0x85; D[i].reg[3] = 0x83;  // config default 0x8583
    D[i].conv_done_us = 0;
}
static const double ads_fs_mv[8] = {6144, 4096, 2048, 1024, 512, 256, 256, 256};
static const uint32_t ads_sps[8] = {8, 16, 32, 64, 128, 250, 475, 860};
static void ads_start(int i) {
    uint16_t cfg = (uint16_t)((D[i].reg[2] << 8) | D[i].reg[3]);
    int mux = (cfg >> 12) & 7, pga = (cfg >> 9) & 7, dr = (cfg >> 5) & 7;
    double mv = mux >= 4 ? D[i].in_mv[mux - 4] : 0.0;  // single ended only
    double c = mv / ads_fs_mv[pga] * 32768.0;
    if (c > 32767) c = 32767;
    if (c < -32768) c = -32768;
    D[i].pending = (int16_t)c;
    D[i].conv_done_us = R.now_us + 1000000u / ads_sps[dr] + 1u;
    D[i].reg[2] &= 0x7F;  // OS = 0: converting
}
static uint8_t ads_read(int i, uint8_t r, int byte) {
    if (D[i].conv_done_us && R.now_us >= D[i].conv_done_us) D[i].conv = D[i].pending;
    if ((r & 3) == 0) {  // conversion: the last finished result
        int16_t v = D[i].conv;
        return byte == 0 ? (uint8_t)((uint16_t)v >> 8) : (uint8_t)v;
    }
    if ((r & 3) == 1) {
        if (R.now_us >= D[i].conv_done_us) D[i].reg[2] |= 0x80;
        return D[i].reg[2 + byte];
    }
    return 0;
}

static void pca_reset(int i) {
    memset(D[i].reg, 0, sizeof D[i].reg);
    D[i].reg[0x00] = 0x11;  // MODE1: SLEEP + ALLCALL
    D[i].reg[0x01] = 0x04;  // MODE2: OUTDRV
    for (int ch = 0; ch < 16; ch++) D[i].reg[0x06 + 4 * ch + 3] = 0x10;  // LEDn_OFF_H full off
    D[i].reg[0xFE] = 0x1E;
}
static void pca_write(int i, uint8_t r, uint8_t v) {
    if (r == 0xFE && !(D[i].reg[0] & 0x10)) return;  // PRESCALE only takes while asleep
    D[i].reg[r] = v;
    if (r >= 0xFA && r <= 0xFD)  // ALL_LED_* writes every channel
        for (int ch = 0; ch < 16; ch++) D[i].reg[0x06 + 4 * ch + (r - 0xFA)] = v;
}

int i2c_write_timeout_us(i2c_inst_t *bus, uint8_t addr, const uint8_t *src, size_t len, bool nostop, uint t) {
    (void)nostop; (void)t;
    int i = i2c_dev(bus, addr);
    if (i < 0 || !len) return PICO_ERROR_GENERIC;
    uint8_t r = src[0];
    D[i].ptr = r;
    for (size_t k = 1; k < len; k++) {
        if (D[i].kind == DEV_MCP23017) mcp_write(i, r, src[k]);
        else if (D[i].kind == DEV_PCA9685) pca_write(i, r, src[k]);
        else if (D[i].kind == DEV_ADS1115) {
            if ((r & 3) >= 1) D[i].reg[2 * (r & 3) + (int)(k - 1) % 2] = src[k];
            if ((r & 3) == 1 && k == 2 && (src[1] & 0x80)) ads_start(i);
            continue;
        }
        if (D[i].kind == DEV_PCA9685 && !(D[i].reg[0] & 0x20)) continue;  // no auto-increment
        r++;
    }
    return (int)len;
}

int i2c_read_timeout_us(i2c_inst_t *bus, uint8_t addr, uint8_t *dst, size_t len, bool nostop, uint t) {
    (void)nostop; (void)t;
    int i = i2c_dev(bus, addr);
    if (i < 0) return PICO_ERROR_GENERIC;
    uint8_t r = D[i].ptr;
    for (size_t k = 0; k < len; k++) {
        if (D[i].kind == DEV_MCP23017) dst[k] = mcp_read(i, r++);
        else if (D[i].kind == DEV_PCA9685) dst[k] = D[i].reg[r++];
        else dst[k] = ads_read(i, r, (int)(k % 2));
    }
    return (int)len;
}
uint i2c_init(i2c_inst_t *i2c, uint baud) { (void)i2c; return baud; }

// ---------------------------------------------------------------- MCP2515
#define CANSTAT 0x0E
#define CANCTRL 0x0F
#define CANINTF 0x2C
#define EFLG 0x2D

static void can_reset(int i) {
    memset(C[i].reg, 0, sizeof C[i].reg);
    C[i].reg[CANSTAT] = 0x80;
    C[i].reg[CANCTRL] = 0x87;
}
static int can_mode(int i) { return C[i].reg[CANSTAT] >> 5; }  // 0 normal, 4 config

static void can_fill_rx(int i) {
    if (can_mode(i) != 0) return;
    while (C[i].rx_len) {
        int b;
        if (!(C[i].reg[CANINTF] & 0x01)) b = 0;
        else if (!(C[i].reg[CANINTF] & 0x02) && (C[i].reg[0x60] & 0x04)) b = 1;  // BUKT rollover
        else return;
        rig_frame_t *f = &C[i].rx[C[i].rx_head];
        uint8_t *p = &C[i].reg[0x61 + 0x10 * b];
        if (f->ext) {
            p[0] = (uint8_t)(f->id >> 21);
            p[1] = (uint8_t)(((f->id >> 13) & 0xE0) | 0x08 | ((f->id >> 16) & 0x03));
            p[2] = (uint8_t)(f->id >> 8);
            p[3] = (uint8_t)f->id;
        } else {
            p[0] = (uint8_t)(f->id >> 3);
            p[1] = (uint8_t)((f->id & 7u) << 5);
            p[2] = p[3] = 0;
        }
        p[4] = f->dlc;
        memcpy(&p[5], f->data, 8);
        C[i].reg[CANINTF] |= (uint8_t)(1u << b);
        C[i].rx_head = (C[i].rx_head + 1) % QLEN;
        C[i].rx_len--;
    }
}

// A TX buffer with TXREQ set goes out on the bus if another node is there to ACK it.
static void can_try_tx(int i) {
    if (can_mode(i) != 0 || !C[i].acked) return;
    for (int b = 0; b < 3; b++) {
        uint8_t ctrl = (uint8_t)(0x30 + 0x10 * b);
        if (!(C[i].reg[ctrl] & 0x08)) continue;
        uint8_t *p = &C[i].reg[ctrl + 1];
        rig_frame_t f = {0};
        f.ext = (p[1] & 0x08) != 0;
        if (f.ext) f.id = ((uint32_t)p[0] << 21) | ((uint32_t)(p[1] & 0xE0) << 13) | ((uint32_t)(p[1] & 3) << 16) | ((uint32_t)p[2] << 8) | p[3];
        else f.id = ((uint32_t)p[0] << 3) | (p[1] >> 5);
        f.dlc = p[4] & 0x0F;
        if (f.dlc > 8) f.dlc = 8;
        memcpy(f.data, &p[5], f.dlc);
        if (C[i].tx_len == QLEN) { C[i].tx_head = (C[i].tx_head + 1) % QLEN; C[i].tx_len--; C[i].tx_dropped++; }
        C[i].tx[(C[i].tx_head + C[i].tx_len) % QLEN] = f;
        C[i].tx_len++;
        C[i].reg[ctrl] &= (uint8_t)~0x08;
        C[i].reg[CANINTF] |= (uint8_t)(0x04 << b);
    }
}

static void can_reg_write(int i, uint8_t a, uint8_t v) {
    if (a >= 128) return;
    if (a == CANSTAT) return;  // read only
    if ((a & 0x0F) == 0x0E) return;  // CANSTAT mirrors
    C[i].reg[a] = v;
    if (a == CANCTRL) C[i].reg[CANSTAT] = (uint8_t)((C[i].reg[CANSTAT] & 0x1F) | (v & 0xE0));
    if (a >= 0x28 && a <= 0x2A && can_mode(i) != 4) note_error("mcp2515: CNF written outside config mode");
}

static uint8_t can_xfer(int i, uint8_t mosi) {
    uint8_t miso = 0xFF;
    switch (C[i].phase) {
    case 0:
        C[i].cmd = mosi;
        C[i].phase = 1;
        if (mosi == 0xC0) can_reset(i);
        else if ((mosi & 0xF9) == 0x90) {  // READ RX BUFFER
            C[i].rxbuf = (mosi >> 2) & 1;
            C[i].addr = (uint8_t)(0x61 + 0x10 * C[i].rxbuf + ((mosi & 2) ? 5 : 0));
            C[i].phase = 3;
        }
        break;
    case 1:  // address
        C[i].addr = mosi;
        C[i].phase = C[i].cmd == 0x05 ? 4 : 2;
        break;
    case 2:  // data, auto increment
        if (C[i].cmd == 0x03) miso = C[i].reg[C[i].addr & 0x7F];
        else if (C[i].cmd == 0x02) can_reg_write(i, C[i].addr & 0x7F, mosi);
        C[i].addr++;
        break;
    case 3:  // READ RX BUFFER stream
        miso = C[i].reg[C[i].addr & 0x7F];
        C[i].addr++;
        break;
    case 4:  // BIT MODIFY mask
        C[i].mask = mosi;
        C[i].phase = 5;
        break;
    case 5: {
        uint8_t a = C[i].addr & 0x7F;
        can_reg_write(i, a, (uint8_t)((C[i].reg[a] & ~C[i].mask) | (mosi & C[i].mask)));
        C[i].phase = 6;
        break;
    }
    default:
        break;
    }
    return miso;
}

static void can_cs(int i, bool low) {
    if (low) {
        for (int k = 0; k < n_can; k++)
            if (k != i && C[k].selected) note_error("spi: two chip selects low at once");
        C[i].selected = true;
        C[i].phase = 0;
        C[i].rxbuf = -1;
        return;
    }
    C[i].selected = false;
    if (!C[i].powered) return;
    if (C[i].phase == 3 && C[i].rxbuf >= 0) C[i].reg[CANINTF] &= (uint8_t)~(1u << C[i].rxbuf);
    can_try_tx(i);
    can_fill_rx(i);
}

static bool spi_pins_ok(void) {
    return G[spi_pins[0]].fn == GPIO_FUNC_SPI && G[spi_pins[1]].fn == GPIO_FUNC_SPI && G[spi_pins[2]].fn == GPIO_FUNC_SPI;
}
static int spi_selected(void) {
    for (int i = 0; i < n_can; i++) if (C[i].selected) return i;
    return -1;
}
uint spi_init(spi_inst_t *spi, uint baud) { (void)spi; return baud; }
int spi_write_blocking(spi_inst_t *spi, const uint8_t *src, size_t len) {
    (void)spi;
    int i = spi_selected();
    if (i >= 0 && C[i].powered && spi_pins_ok())
        for (size_t k = 0; k < len; k++) can_xfer(i, src[k]);
    return (int)len;
}
int spi_read_blocking(spi_inst_t *spi, uint8_t tx, uint8_t *dst, size_t len) {
    (void)spi;
    int i = spi_selected();
    for (size_t k = 0; k < len; k++)
        dst[k] = (i >= 0 && C[i].powered && spi_pins_ok()) ? can_xfer(i, tx) : 0xFF;
    return (int)len;
}

// ================================================================ API for Python
RIG_API void rig_init(void) {
    memset(&R, 0, sizeof R);
#ifndef __EMSCRIPTEN__
    pthread_mutex_init(&R.mu, NULL);
    pthread_cond_init(&R.cv, NULL);
#endif
    for (int p = 0; p < NPINS; p++) { G[p].fn = GPIO_FUNC_NULL; G[p].ext = -1; G[p].out = G[p].out_dir = G[p].pull_up = false; }
    memset(S, 0, sizeof S);
    memset(rig_flash, 0xFF, sizeof rig_flash);
    n_i2c = n_can = 0;
    uart_tx_n = uart_rx_len = uart_rx_head = 0;
}

RIG_API void rig_set_watchdog_reboot(int yes) { R.wd_rebooted = yes != 0; }
RIG_API void rig_set_pins(int sck, int mosi, int miso, int sda, int scl, int tx, int rx) {
    spi_pins[0] = (uint)sck; spi_pins[1] = (uint)mosi; spi_pins[2] = (uint)miso;
    i2c_pins[0] = (uint)sda; i2c_pins[1] = (uint)scl;
    uart_pins[0] = (uint)tx; uart_pins[1] = (uint)rx;
}

#ifdef __EMSCRIPTEN__
RIG_API int rig_start(void) {
    R.run = RUN_IDLE;
    R.target_us = 0;
    emscripten_fiber_init_from_current_context(&fib_main, fib_main_astack, sizeof fib_main_astack);
    emscripten_fiber_init(&fib_fw, fw_fiber, NULL, fib_fw_cstack, sizeof fib_fw_cstack,
                          fib_fw_astack, sizeof fib_fw_astack);
    R.started = true;
    return 0;
}

RIG_API int rig_run_us(uint32_t us) {  // 32-bit: a 64-bit argument breaks the browser build's fiber rewind
    if (!R.started || R.run == RUN_EXITED) return RUN_EXITED;
    R.target_us = R.now_us + us;
    R.run = RUN_RUNNING;
    emscripten_fiber_swap(&fib_main, &fib_fw);
    return R.run;
}

RIG_API void rig_stop(void) {
    if (R.started && R.run != RUN_EXITED) {
        R.quit = true;
        emscripten_fiber_swap(&fib_main, &fib_fw);
    }
    R.started = false;
}
#else
RIG_API int rig_start(void) {
    R.run = RUN_IDLE;
    R.target_us = 0;
    int e = pthread_create(&R.thread, NULL, fw_thread, NULL);
    R.started = e == 0;
    return e;
}

// Let the firmware run until virtual time has moved on by `us`. Returns the run state.
RIG_API int rig_run_us(uint32_t us) {  // 32-bit: a 64-bit argument breaks the browser build's fiber rewind
    pthread_mutex_lock(&R.mu);
    if (R.run == RUN_EXITED) { pthread_mutex_unlock(&R.mu); return RUN_EXITED; }
    R.target_us = R.now_us + us;
    R.run = RUN_RUNNING;
    pthread_cond_broadcast(&R.cv);
    while (R.run == RUN_RUNNING) pthread_cond_wait(&R.cv, &R.mu);
    int st = R.run;
    pthread_mutex_unlock(&R.mu);
    return st;
}

RIG_API void rig_stop(void) {
    pthread_mutex_lock(&R.mu);
    bool started = R.started;
    R.quit = true;
    pthread_cond_broadcast(&R.cv);
    while (started && R.run != RUN_EXITED) pthread_cond_wait(&R.cv, &R.mu);
    pthread_mutex_unlock(&R.mu);
    if (started) pthread_join(R.thread, NULL);
    R.started = false;
}
#endif

RIG_API int rig_exit_reason(void) { return R.exit_reason; }
// The run state after rig_run_us(). The browser build reads it here: a call that swapped
// fibers loses its own return value on the way back out to JavaScript.
RIG_API int rig_run_state(void) { return R.run; }
RIG_API uint64_t rig_now_us(void) { return R.now_us; }
RIG_API const char *rig_errors(void) { return R.errors; }

// mode: 0 input / high-Z, 1 driven (value 0/1), 2 PWM (duty), 3 peripheral (SPI, I2C, UART), 4 ADC
RIG_API int rig_pin(int pin, double *value, double *hz, int *pull_up) {
    if (pin < 0 || pin >= NPINS) return -1;
    *pull_up = G[pin].pull_up;
    *hz = 0;
    *value = 0;
    switch (G[pin].fn) {
    case GPIO_FUNC_SIO:
        if (!G[pin].out_dir) return 0;
        *value = G[pin].out;
        return 1;
    case GPIO_FUNC_PWM: {
        uint s = pwm_gpio_to_slice_num((uint)pin);
        if (!S[s].on) return 2;
        double d = (double)S[s].level[pin & 1] / ((double)S[s].top + 1.0);
        *value = d > 1.0 ? 1.0 : d;
        *hz = (double)CLK_SYS_HZ / ((double)S[s].div * ((double)S[s].top + 1.0));
        return 2;
    }
    case GPIO_FUNC_SPI: case GPIO_FUNC_I2C: case GPIO_FUNC_UART: return 3;
    case GPIO_FUNC_NULL: return G[pin].pull_up ? 0 : 4;
    default: return 0;
    }
}
RIG_API void rig_pin_in(int pin, int level) { if (pin >= 0 && pin < NPINS) G[pin].ext = (int8_t)level; }
RIG_API void rig_adc_mv(int input, double mv) { if (input >= 0 && input < 4) adc_mv[input] = mv; }
RIG_API void rig_die_temp(double c) { die_temp_c = c; }

RIG_API int rig_i2c_add(int kind, int addr) {
    if (n_i2c == NI2C) return -1;
    int i = n_i2c++;
    memset(&D[i], 0, sizeof D[i]);
    D[i].kind = kind;
    D[i].addr = (uint8_t)addr;
    if (kind == DEV_MCP23017) mcp_reset(i);
    else if (kind == DEV_ADS1115) ads_reset(i);
    else pca_reset(i);
    return i;
}
// A chip losing power forgets everything; it comes back in its power-up state.
RIG_API void rig_i2c_power(int i, int on) {
    if (i < 0 || i >= n_i2c) return;
    if (on && !D[i].powered) {
        if (D[i].kind == DEV_MCP23017) mcp_reset(i);
        else if (D[i].kind == DEV_ADS1115) ads_reset(i);
        else pca_reset(i);
    }
    D[i].powered = on != 0;
}
RIG_API int rig_i2c_reg(int i, int r) { return (i >= 0 && i < n_i2c && r >= 0 && r < 256) ? D[i].reg[r] : -1; }
RIG_API void rig_i2c_set_reg(int i, int r, int v) { if (i >= 0 && i < n_i2c && r >= 0 && r < 256) D[i].reg[r] = (uint8_t)v; }
RIG_API void rig_mcp_in(int i, int port, int mask, int level) {
    if (i < 0 || i >= n_i2c || port < 0 || port > 1) return;
    D[i].ext_mask[port] = (uint8_t)mask;
    D[i].ext_level[port] = (uint8_t)level;
}
RIG_API void rig_ads_mv(int i, int ch, double mv) { if (i >= 0 && i < n_i2c && ch >= 0 && ch < 4) D[i].in_mv[ch] = mv; }
// PCA9685 channel output: duty 0..1, or -1 when the chip is asleep / unpowered (outputs off)
RIG_API double rig_pca_duty(int i, int ch, double *hz) {
    *hz = 0;
    if (i < 0 || i >= n_i2c || !D[i].powered || ch < 0 || ch > 15) return 0.0;
    const uint8_t *r = D[i].reg;
    if (r[0] & 0x10) return 0.0;  // asleep: no PWM
    *hz = 25e6 / (4096.0 * (r[0xFE] + 1));
    const uint8_t *l = &r[0x06 + 4 * ch];
    if (l[3] & 0x10) return 0.0;  // full off wins
    if (l[1] & 0x10) return 1.0;  // full on
    int on = ((l[1] & 0x0F) << 8) | l[0], off = ((l[3] & 0x0F) << 8) | l[2];
    int span = (off - on + 4096) % 4096;
    return span / 4096.0;
}
RIG_API int rig_pca_totem(int i) { return (i >= 0 && i < n_i2c) ? (D[i].reg[1] & 0x04) != 0 : 0; }

RIG_API int rig_can_add(int cs_pin, int osc_hz) {
    if (n_can == NCAN) return -1;
    int i = n_can++;
    memset(&C[i], 0, sizeof C[i]);
    C[i].cs_pin = (uint)cs_pin;
    C[i].osc_hz = (uint32_t)osc_hz;
    can_reset(i);
    return i;
}
RIG_API void rig_can_power(int i, int on) {
    if (i < 0 || i >= n_can) return;
    if (on && !C[i].powered) can_reset(i);
    C[i].powered = on != 0;
}
RIG_API void rig_can_acked(int i, int yes) { if (i >= 0 && i < n_can) C[i].acked = yes != 0; }
RIG_API int rig_can_mode(int i) { return (i >= 0 && i < n_can && C[i].powered) ? can_mode(i) : -1; }
// Bit rate from CNF1-3 and the crystal (MCP2515 datasheet section 5).
RIG_API uint32_t rig_can_bitrate(int i) {
    if (i < 0 || i >= n_can) return 0;
    uint8_t c1 = C[i].reg[0x2A], c2 = C[i].reg[0x29], c3 = C[i].reg[0x28];
    uint32_t brp = (c1 & 0x3F) + 1u, prop = (c2 & 7) + 1u, ps1 = ((c2 >> 3) & 7) + 1u, ps2 = (c3 & 7) + 1u;
    uint32_t tq_per_bit = 1u + prop + ps1 + ps2;
    return C[i].osc_hz / (2u * brp * tq_per_bit);
}
RIG_API int rig_can_push(int i, uint32_t id, int ext, int dlc, const uint8_t *data) {
    if (i < 0 || i >= n_can || !C[i].powered || can_mode(i) != 0) return 0;
    if (C[i].rx_len == QLEN) { C[i].rx_overflow++; C[i].reg[EFLG] |= 0x40; return 0; }
    rig_frame_t *f = &C[i].rx[(C[i].rx_head + C[i].rx_len) % QLEN];
    memset(f, 0, sizeof *f);
    f->id = id; f->ext = (uint8_t)ext; f->dlc = (uint8_t)(dlc > 8 ? 8 : dlc);
    memcpy(f->data, data, f->dlc);
    C[i].rx_len++;
    if (!C[i].selected) can_fill_rx(i);
    return 1;
}
RIG_API int rig_can_pop(int i, uint32_t *id, int *ext, int *dlc, uint8_t *data) {
    if (i < 0 || i >= n_can) return 0;
    if (!C[i].selected) can_try_tx(i);
    if (!C[i].tx_len) return 0;
    rig_frame_t *f = &C[i].tx[C[i].tx_head];
    *id = f->id; *ext = f->ext; *dlc = f->dlc;
    memcpy(data, f->data, 8);
    C[i].tx_head = (C[i].tx_head + 1) % QLEN;
    C[i].tx_len--;
    return 1;
}
RIG_API int rig_can_tx_pending(int i) {
    int n = 0;
    for (int b = 0; b < 3; b++) if (C[i].reg[0x30 + 0x10 * b] & 0x08) n++;
    return n;
}

RIG_API size_t rig_uart_take(char *buf, size_t n) {
    size_t k = uart_tx_n < n - 1 ? uart_tx_n : n - 1;
    memcpy(buf, uart_tx, k);
    buf[k] = 0;
    memmove(uart_tx, uart_tx + k, uart_tx_n - k);
    uart_tx_n -= k;
    return k;
}
RIG_API void rig_uart_send(const char *s) {
    for (; *s && uart_rx_len < sizeof uart_rx; s++) {
        uart_rx[(uart_rx_head + uart_rx_len) % sizeof uart_rx] = *s;
        uart_rx_len++;
    }
}
RIG_API uint8_t *rig_flash_base(void) { return rig_flash; }
RIG_API size_t rig_flash_size(void) { return sizeof rig_flash; }
