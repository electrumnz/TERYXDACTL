// Teryx CAN sniffer: the USB protocol side, in plain C with no hardware calls,
// so the same code runs on the Pico 2, on a PC (host build) and in the tests.
//
// Speaks two protocols on one USB serial port and works out which one the
// computer wants from the first bytes it sends:
//   * slcan / LAWICEL (text lines ending in \r). python-can, Linux slcand
//     (gives you can0), SavvyCAN "LAWICEL" connection, CANable tools.
//   * GVRET (binary, starts with 0xE7 0xE7). SavvyCAN's own "GVRET" serial
//     connection, works on Windows and Mac with no drivers.
//
// Safety: the adaptor never transmits unless the TX jumper is fitted
// (hw.tx_allowed returns true). Without it, "open" (O) still opens, but in
// listen-only mode, and every send is refused. Listen-only means the MCP2515
// never ACKs or sends error frames, so it can't upset the Shinegle.
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define SN_VERSION_HW  0x10   // reported by the slcan V command as "V1013"
#define SN_VERSION_SW  0x13
#define SN_DEFAULT_BITRATE 250000u

typedef struct {
    uint32_t id;
    uint8_t dlc;
    bool ext;
    bool rtr;
    uint8_t data[8];
} sn_frame_t;

typedef enum { SN_MODE_NORMAL = 0, SN_MODE_LISTEN = 1 } sn_mode_t;
typedef enum { SN_PROTO_NONE = 0, SN_PROTO_SLCAN, SN_PROTO_GVRET } sn_proto_t;

typedef struct {
    bool (*can_open)(void *ctx, uint32_t bitrate, sn_mode_t mode);  // false = bitrate not possible
    void (*can_close)(void *ctx);
    bool (*can_send)(void *ctx, const sn_frame_t *f);
    void (*write)(void *ctx, const uint8_t *buf, size_t len);
    bool (*tx_allowed)(void *ctx);
    void *ctx;
} sn_hw_t;

typedef struct {
    sn_hw_t hw;
    sn_proto_t proto;
    // bus
    bool open;
    sn_mode_t mode;
    uint32_t bitrate;
    // slcan
    char line[40];
    uint8_t line_len;
    bool timestamps;
    // gvret parser
    uint8_t g_state;
    uint8_t g_cmd;
    uint8_t g_step;
    uint8_t g_buf[24];
    // counters (also shown by the slcan F command)
    uint32_t rx_frames, tx_frames, overflows, tx_refused;
    bool overflow_flag;
} sniffer_t;

void sn_init(sniffer_t *s, const sn_hw_t *hw);
// Bytes from the computer.
void sn_rx_bytes(sniffer_t *s, const uint8_t *buf, size_t len, uint32_t now_us);
// A frame heard on the CAN bus. Sent to the computer if the bus is open.
void sn_on_frame(sniffer_t *s, const sn_frame_t *f, uint32_t now_us);
// The CAN side lost frames (MCP2515 or queue overflow).
void sn_note_overflow(sniffer_t *s);

// Bit rates for slcan S0..S8. Exposed for the tests.
extern const uint32_t sn_slcan_rates[9];
