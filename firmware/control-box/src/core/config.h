// Teryx control box: fixed hardware config. Pin numbers follow docs/io-list.md
// section 3. Things that might change on the bench without rewiring are in
// settings.h instead, so they can be changed from the dash.
#pragma once

#define FW_VERSION_MAJOR 0
#define FW_VERSION_MINOR 1
#define FW_VERSION_PATCH 0

// ---- Pico 2 pins --------------------------------------------------------------
#define PIN_UART_TX        0
#define PIN_UART_RX        1
#define PIN_CAN_SCK        2
#define PIN_CAN_MOSI       3
#define PIN_CAN_MISO       4
#define PIN_CAN_CS         5
#define PIN_CAN_INT        6
#define PIN_DIFF_RPWM      7
#define PIN_DIFF_LPWM      8
#define PIN_DIFF_EN        9
#define PIN_4WD_RPWM       10
#define PIN_4WD_LPWM       11
#define PIN_4WD_EN         12
#define PIN_TRAY_RPWM      13
#define PIN_TRAY_LPWM      14
#define PIN_TRAY_EN        15
#define PIN_LIGHT_FRONT_1  16
#define PIN_LIGHT_FRONT_2  17
#define PIN_LIGHT_FRONT_3  18
#define PIN_LIGHT_FRONT_4  19
#define PIN_LIGHT_INTERIOR 20
#define PIN_EXP_INT        21
#define PIN_ADC_RDY        22
#define PIN_I2C_SDA        26
#define PIN_I2C_SCL        27
#define PIN_DIFF_IS        28   // ADC2

// ---- Buses ------------------------------------------------------------------------
#define CAN_BITRATE        250000u   // TBC: must match the Shinegle
#define MCP2515_OSC_HZ     8000000u  // most cheap modules have an 8 MHz crystal. Check yours.
#define I2C_BAUD           400000u
#define MCP23017_ADDR      0x20
#define ADS1115_ADDR       0x48

// ---- Loads --------------------------------------------------------------------------
#define LIGHT_PWM_HZ       500u      // light bar MOSFETs
#define ACT_PWM_HZ         20000u    // BTS7960, above hearing

// BTS7960 current sense: IS pins diode-OR'd into 1k to ground.
// I_IS = I_load / 8500, so V = I_load * 1000 / 8500. 1 A gives ~118 mV.
#define BTS_IS_MV_PER_A_X10  1176    // 117.6 mV per amp

// 12V aux sense divider 10k over 2.2k.
#define AUX_DIV_NUM        122       // (10k + 2.2k) / 2.2k = 5.545, as 122/22
#define AUX_DIV_DEN        22

// ---- Actuator wiring sense ---------------------------------------------------------------
// +1 = RPWM (extend). Flip these if an actuator is wired the other way round.
#define DIFF_LOCK_DIR      (+1)      // extend = more lock (pot reading goes up)
#define FOURWD_ENGAGE_DIR  (+1)      // extend = 4WD
#define TRAY_UP_DIR        (+1)      // extend = tray up

// ---- Fixed timings ------------------------------------------------------------------------
#define TICK_MS            5u        // control loop period
#define WATCHDOG_MS        250u
#define INRUSH_IGNORE_MS   300u      // ignore current spikes when a motor starts
#define END_STOP_CURRENT_DA 3        // under 0.3 A after inrush = actuator hit its own limit
#define END_STOP_HOLD_MS   100u
#define DIFF_DEADBAND_PCT  2
#define DIFF_STUCK_MS      1000u     // pot must move within this while driving
#define DIFF_MIN_DUTY      110       // of 255, so a small move still overcomes friction
#define POT_MARGIN         400       // raw counts outside cal range = pot wire fault
#define DASH_BOOT_GRACE_MS 3000u     // after Pico boot, before "lost dash" is a fault
#define SHUTDOWN_GRACE_MS  10000u     // after Pi stops heartbeating while shutting down
#define LOW_12V_HOLD_MS    5000u
#define PICO_HOT_C         70
#define WATCHDOG_FLAG_MS   30000u    // how long the watchdog-reset fault shows after boot
#define FADE_STEP          16        // light level change per tick when dimming
