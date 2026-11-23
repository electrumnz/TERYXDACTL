// Pin-level stand-in for the parts of the Pico SDK the control box uses.
//
// The real src/pico/ code (main_pico.c and the MCP2515, MCP23017, ADS1115 and
// PCA9685 drivers) compiles against these headers on a PC. Every SDK call lands
// in rig_board.c, which holds a model of the RP2350 pins and of each chip on the
// I2C and SPI buses. Python (teryx/rig) drives the other side: switches,
// sensors, CAN frames, and reads back every pin. See docs/system-sim.md.
//
// Only what main_pico.c and the drivers call is here. Add to it when they grow.
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef unsigned int uint;
typedef uint64_t absolute_time_t;

// ---- time ---------------------------------------------------------------------
absolute_time_t get_absolute_time(void);
uint32_t to_ms_since_boot(absolute_time_t t);
int64_t absolute_time_diff_us(absolute_time_t from, absolute_time_t to);
absolute_time_t delayed_by_ms(absolute_time_t t, uint32_t ms);
void sleep_ms(uint32_t ms);
void tight_loop_contents(void);
bool stdio_init_all(void);

// ---- gpio ---------------------------------------------------------------------
enum gpio_function {
    GPIO_FUNC_SPI = 1, GPIO_FUNC_UART = 2, GPIO_FUNC_I2C = 3, GPIO_FUNC_PWM = 4,
    GPIO_FUNC_SIO = 5, GPIO_FUNC_NULL = 0x1f,
};
#define GPIO_OUT 1
#define GPIO_IN 0
void gpio_init(uint pin);
void gpio_put(uint pin, bool value);
bool gpio_get(uint pin);
void gpio_set_dir(uint pin, bool out);
void gpio_set_function(uint pin, enum gpio_function fn);
void gpio_pull_up(uint pin);

// ---- pwm ----------------------------------------------------------------------
typedef struct { uint32_t div; uint32_t top; } pwm_config;
uint pwm_gpio_to_slice_num(uint pin);
pwm_config pwm_get_default_config(void);
void pwm_config_set_clkdiv_int(pwm_config *c, uint32_t div);
void pwm_config_set_wrap(pwm_config *c, uint16_t wrap);
void pwm_init(uint slice, pwm_config *c, bool start);
void pwm_set_gpio_level(uint pin, uint16_t level);

// ---- clocks -------------------------------------------------------------------
enum clock_index { clk_sys = 5 };
uint32_t clock_get_hz(enum clock_index clk);

// ---- spi / i2c / uart ---------------------------------------------------------
typedef struct rig_spi spi_inst_t;
typedef struct rig_i2c i2c_inst_t;
typedef struct rig_uart uart_inst_t;
extern spi_inst_t rig_spi0_obj;
extern i2c_inst_t rig_i2c0_obj, rig_i2c1_obj;
extern uart_inst_t rig_uart0_obj;
#define spi0 (&rig_spi0_obj)
#define i2c0 (&rig_i2c0_obj)
#define i2c1 (&rig_i2c1_obj)
#define uart0 (&rig_uart0_obj)
#define PICO_ERROR_GENERIC (-1)
#define PICO_OK 0

uint spi_init(spi_inst_t *spi, uint baud);
int spi_write_blocking(spi_inst_t *spi, const uint8_t *src, size_t len);
int spi_read_blocking(spi_inst_t *spi, uint8_t repeated_tx, uint8_t *dst, size_t len);

uint i2c_init(i2c_inst_t *i2c, uint baud);
int i2c_write_timeout_us(i2c_inst_t *i2c, uint8_t addr, const uint8_t *src, size_t len, bool nostop, uint timeout_us);
int i2c_read_timeout_us(i2c_inst_t *i2c, uint8_t addr, uint8_t *dst, size_t len, bool nostop, uint timeout_us);

uint uart_init(uart_inst_t *uart, uint baud);
void uart_puts(uart_inst_t *uart, const char *s);
bool uart_is_readable(uart_inst_t *uart);
char uart_getc(uart_inst_t *uart);

// ---- adc ----------------------------------------------------------------------
void adc_init(void);
void adc_gpio_init(uint pin);
void adc_set_temp_sensor_enabled(bool on);
void adc_select_input(uint input);
uint16_t adc_read(void);

// ---- watchdog, flash, boot, rand -------------------------------------------------
void watchdog_enable(uint32_t ms, bool pause_on_debug);
void watchdog_update(void);
void watchdog_disable(void);
bool watchdog_caused_reboot(void);

#define PICO_FLASH_SIZE_BYTES (4u * 1024u * 1024u)
#define FLASH_SECTOR_SIZE 4096u
#define FLASH_PAGE_SIZE 256u
extern uint8_t rig_flash[PICO_FLASH_SIZE_BYTES];
#define XIP_BASE ((uintptr_t)rig_flash)
void flash_range_erase(uint32_t offset, size_t count);
void flash_range_program(uint32_t offset, const uint8_t *data, size_t count);
int flash_safe_execute(void (*fn)(void *), void *param, uint32_t timeout_ms);

void reset_usb_boot(uint32_t gpio_mask, uint32_t disable_mask);
uint32_t get_rand_32(void);
