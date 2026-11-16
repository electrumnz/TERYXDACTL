#include "sniffer.h"

#include <string.h>

const uint32_t sn_slcan_rates[9] = {10000, 20000, 50000, 100000, 125000, 250000, 500000, 800000, 1000000};

// GVRET command bytes (after 0xF1), from SavvyCAN's GVRET protocol.
enum {
    G_BUILD_CAN_FRAME = 0, G_TIME_SYNC = 1, G_DIG_INPUTS = 2, G_ANA_INPUTS = 3, G_SET_DIG_OUT = 4,
    G_SETUP_CANBUS = 5, G_GET_CANBUS_PARAMS = 6, G_GET_DEV_INFO = 7, G_SET_SW_MODE = 8,
    G_KEEPALIVE = 9, G_SET_SYSTYPE = 10, G_ECHO_CAN_FRAME = 11, G_GET_NUMBUSES = 12,
    G_GET_EXT_BUSES = 13, G_SET_EXT_BUSES = 14, G_GET_FD = 22,
};
enum { GS_IDLE = 0, GS_COMMAND, GS_FRAME, GS_SKIP, GS_SETUP };

static const char HEX[] = "0123456789ABCDEF";

static void out(sniffer_t *s, const void *buf, size_t n) { s->hw.write(s->hw.ctx, (const uint8_t *)buf, n); }
static void ok(sniffer_t *s) { out(s, "\r", 1); }
static void bel(sniffer_t *s) { out(s, "\a", 1); }

void sn_init(sniffer_t *s, const sn_hw_t *hw) {
    memset(s, 0, sizeof *s);
    s->hw = *hw;
    s->bitrate = SN_DEFAULT_BITRATE;
    s->mode = SN_MODE_LISTEN;
}

static bool tx_ok(sniffer_t *s) { return s->hw.tx_allowed && s->hw.tx_allowed(s->hw.ctx); }

static bool bus_open(sniffer_t *s, sn_mode_t want) {
    if (s->open) {
        s->hw.can_close(s->hw.ctx);
        s->open = false;
    }
    // No TX jumper: always listen only, whatever was asked for.
    sn_mode_t mode = (want == SN_MODE_NORMAL && tx_ok(s)) ? SN_MODE_NORMAL : SN_MODE_LISTEN;
    if (!s->hw.can_open(s->hw.ctx, s->bitrate, mode)) return false;
    s->open = true;
    s->mode = mode;
    return true;
}

static void bus_close(sniffer_t *s) {
    if (s->open) s->hw.can_close(s->hw.ctx);
    s->open = false;
}

static bool send_frame(sniffer_t *s, const sn_frame_t *f) {
    if (!s->open || s->mode != SN_MODE_NORMAL || !tx_ok(s)) {
        s->tx_refused++;
        return false;
    }
    if (!s->hw.can_send(s->hw.ctx, f)) return false;
    s->tx_frames++;
    return true;
}

// ------------------------------------------------------------------ slcan

static int hexval(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

static bool parse_hex(const char *p, int n, uint32_t *v) {
    uint32_t x = 0;
    for (int i = 0; i < n; i++) {
        int h = hexval(p[i]);
        if (h < 0) return false;
        x = (x << 4) | (uint32_t)h;
    }
    *v = x;
    return true;
}

static void put_hex(char *dst, uint32_t v, int digits) {
    for (int i = digits - 1; i >= 0; i--) {
        dst[i] = HEX[v & 0xF];
        v >>= 4;
    }
}

static void slcan_transmit(sniffer_t *s, const char *l, int n) {
    sn_frame_t f = {0};
    f.ext = (l[0] == 'T' || l[0] == 'R');
    f.rtr = (l[0] == 'r' || l[0] == 'R');
    int idlen = f.ext ? 8 : 3;
    uint32_t v;
    if (n < 1 + idlen + 1 || !parse_hex(l + 1, idlen, &f.id)) { bel(s); return; }
    if (!parse_hex(l + 1 + idlen, 1, &v) || v > 8) { bel(s); return; }
    f.dlc = (uint8_t)v;
    if (f.ext ? f.id > 0x1FFFFFFFu : f.id > 0x7FFu) { bel(s); return; }
    if (!f.rtr) {
        if (n < 2 + idlen + 2 * f.dlc) { bel(s); return; }
        for (int i = 0; i < f.dlc; i++) {
            if (!parse_hex(l + 2 + idlen + 2 * i, 2, &v)) { bel(s); return; }
            f.data[i] = (uint8_t)v;
        }
    }
    if (!send_frame(s, &f)) { bel(s); return; }
    out(s, f.ext ? "Z\r" : "z\r", 2);
}

static void slcan_line(sniffer_t *s, const char *l, int n) {
    if (n == 0) { ok(s); return; }
    switch (l[0]) {
    case 'S': {
        int k = n >= 2 ? l[1] - '0' : -1;
        if (s->open || k < 0 || k > 8) { bel(s); return; }
        s->bitrate = sn_slcan_rates[k];
        ok(s);
        return;
    }
    case 'O':
        if (s->open || !bus_open(s, SN_MODE_NORMAL)) { bel(s); return; }
        ok(s);
        return;
    case 'L':
        if (s->open || !bus_open(s, SN_MODE_LISTEN)) { bel(s); return; }
        ok(s);
        return;
    case 'C':
        bus_close(s);
        ok(s);
        return;
    case 't': case 'T': case 'r': case 'R':
        slcan_transmit(s, l, n);
        return;
    case 'V': out(s, "V1013\r", 6); return;
    case 'v': out(s, "v0113\r", 6); return;
    case 'N': out(s, "NTRX1\r", 6); return;
    case 'F': {
        // LAWICEL status flags: bit 3 = data overrun, bit 0 = receive queue full
        uint8_t flags = s->overflow_flag ? 0x09 : 0x00;
        s->overflow_flag = false;
        char r[4] = {'F', HEX[flags >> 4], HEX[flags & 0xF], '\r'};
        out(s, r, 4);
        return;
    }
    case 'Z':
        s->timestamps = n >= 2 && l[1] == '1';
        ok(s);
        return;
    case 'M': case 'm': case 'X': case 'Q': case 'W':
        ok(s);   // acceptance filters, auto-poll, etc.: accepted and ignored (we pass everything)
        return;
    default:
        bel(s);  // includes 's' (custom bit timing), not supported
        return;
    }
}

static void slcan_frame(sniffer_t *s, const sn_frame_t *f, uint32_t now_us) {
    char b[1 + 8 + 1 + 16 + 4 + 1];
    int n = 0;
    b[n++] = f->ext ? (f->rtr ? 'R' : 'T') : (f->rtr ? 'r' : 't');
    if (f->ext) { put_hex(b + n, f->id, 8); n += 8; }
    else { put_hex(b + n, f->id & 0x7FF, 3); n += 3; }
    uint8_t dlc = f->dlc > 8 ? 8 : f->dlc;
    b[n++] = HEX[dlc];
    if (!f->rtr) {
        for (int i = 0; i < dlc; i++) { put_hex(b + n, f->data[i], 2); n += 2; }
    }
    if (s->timestamps) { put_hex(b + n, (now_us / 1000u) % 60000u, 4); n += 4; }
    b[n++] = '\r';
    out(s, b, (size_t)n);
}

// ------------------------------------------------------------------ GVRET

static void put32(uint8_t *p, uint32_t v) {
    p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); p[2] = (uint8_t)(v >> 16); p[3] = (uint8_t)(v >> 24);
}

static uint32_t get32(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static void gvret_frame(sniffer_t *s, const sn_frame_t *f, uint32_t now_us) {
    uint8_t b[2 + 4 + 4 + 1 + 8 + 1];
    uint8_t dlc = f->dlc > 8 ? 8 : f->dlc;
    b[0] = 0xF1;
    b[1] = G_BUILD_CAN_FRAME;
    put32(b + 2, now_us);
    put32(b + 6, f->id | (f->ext ? 0x80000000u : 0));
    b[10] = dlc;   // bus 0 in the top nibble
    memcpy(b + 11, f->data, dlc);
    b[11 + dlc] = 0;
    out(s, b, (size_t)(12 + dlc));
}

static void gvret_command(sniffer_t *s, uint8_t cmd, uint32_t now_us) {
    uint8_t r[20] = {0xF1, cmd};
    s->g_state = GS_IDLE;
    s->g_step = 0;
    switch (cmd) {
    case G_BUILD_CAN_FRAME:
    case G_ECHO_CAN_FRAME:
        s->g_state = GS_FRAME;
        return;
    case G_TIME_SYNC:
        put32(r + 2, now_us);
        out(s, r, 6);
        return;
    case G_DIG_INPUTS:
        out(s, r, 4);                 // value 0, checksum 0
        return;
    case G_ANA_INPUTS:
        out(s, r, 17);                // seven zero readings + checksum
        return;
    case G_SETUP_CANBUS:
        s->g_state = GS_SETUP;
        return;
    case G_GET_CANBUS_PARAMS:
        r[2] = (uint8_t)((s->open ? 1 : 0) | (s->mode == SN_MODE_LISTEN ? 0x10 : 0));
        put32(r + 3, s->bitrate);
        r[7] = 0;
        put32(r + 8, 0);
        out(s, r, 12);
        return;
    case G_GET_DEV_INFO:
        r[2] = SN_VERSION_SW; r[3] = 0; r[4] = 0x20; r[5] = 0; r[6] = 0; r[7] = 0;
        out(s, r, 8);
        return;
    case G_KEEPALIVE:
        r[2] = 0xDE; r[3] = 0xAD;
        out(s, r, 4);
        return;
    case G_GET_NUMBUSES:
        r[2] = 1;
        out(s, r, 3);
        return;
    case G_GET_EXT_BUSES:
        out(s, r, 17);
        return;
    case G_GET_FD:
        r[2] = 1;                     // one bus, not FD capable
        out(s, r, 8);
        return;
    case G_SET_DIG_OUT: case G_SET_SW_MODE: case G_SET_SYSTYPE:
        s->g_state = GS_SKIP;
        s->g_buf[0] = 1;              // bytes to skip
        return;
    case G_SET_EXT_BUSES:
        s->g_state = GS_SKIP;
        s->g_buf[0] = 12;
        return;
    default:
        return;                       // unknown: ignore
    }
}

static void gvret_byte(sniffer_t *s, uint8_t c, uint32_t now_us) {
    switch (s->g_state) {
    case GS_IDLE:
        if (c == 0xF1) s->g_state = GS_COMMAND;
        else if (c == 0xE7) { /* "binary mode" request, already in it */ }
        return;
    case GS_COMMAND:
        s->g_cmd = c;
        gvret_command(s, c, now_us);
        return;
    case GS_SKIP:
        if (--s->g_buf[0] == 0) s->g_state = GS_IDLE;
        return;
    case GS_SETUP:
        s->g_buf[s->g_step++] = c;
        if (s->g_step == 8) {
            uint32_t v = get32(s->g_buf);
            s->g_state = GS_IDLE;
            if (v == 0) { bus_close(s); return; }
            uint32_t speed = v & 0xFFFFFu;
            bool enable = (v & 0x80000000u) ? (v & 0x40000000u) != 0 : true;
            bool listen = (v & 0x80000000u) && (v & 0x20000000u);
            if (speed) s->bitrate = speed > 1000000u ? 1000000u : speed;
            if (!enable) { bus_close(s); return; }
            if (!bus_open(s, listen ? SN_MODE_LISTEN : SN_MODE_NORMAL)) bus_close(s);
        }
        return;
    case GS_FRAME:
        // id[4] bus[1] len[1] data[len] checksum[1]
        s->g_buf[s->g_step++] = c;
        if (s->g_step >= 6) {
            uint8_t len = s->g_buf[5] & 0x0F;
            if (len > 8) len = 8;
            if (s->g_step == 6u + len + 1u) {
                sn_frame_t f = {0};
                uint32_t id = get32(s->g_buf);
                f.ext = (id & 0x80000000u) != 0;
                f.id = id & 0x1FFFFFFFu;
                f.dlc = len;
                memcpy(f.data, s->g_buf + 6, len);
                if (s->g_cmd == G_ECHO_CAN_FRAME) gvret_frame(s, &f, now_us);
                else send_frame(s, &f);
                s->g_state = GS_IDLE;
            }
        }
        return;
    }
}

// ------------------------------------------------------------------ entry points

void sn_rx_bytes(sniffer_t *s, const uint8_t *buf, size_t len, uint32_t now_us) {
    for (size_t i = 0; i < len; i++) {
        uint8_t c = buf[i];
        if (c == 0xE7 && s->proto != SN_PROTO_GVRET) {
            // SavvyCAN GVRET handshake. Open the bus listen-only straight away so
            // frames flow even before SavvyCAN sends its bus setup.
            s->proto = SN_PROTO_GVRET;
            s->g_state = GS_IDLE;
            if (!s->open) bus_open(s, SN_MODE_LISTEN);
            continue;
        }
        if (s->proto == SN_PROTO_GVRET) {
            gvret_byte(s, c, now_us);
            continue;
        }
        if (c == '\r' || c == '\n') {
            if (c == '\n' && s->line_len == 0) continue;   // \r\n from a terminal
            s->proto = SN_PROTO_SLCAN;
            s->line[s->line_len] = 0;
            slcan_line(s, s->line, s->line_len);
            s->line_len = 0;
        } else if (s->line_len < sizeof s->line - 1) {
            s->line[s->line_len++] = (char)c;
        } else {
            s->line_len = 0;   // line too long: drop it
            bel(s);
        }
    }
}

void sn_on_frame(sniffer_t *s, const sn_frame_t *f, uint32_t now_us) {
    if (!s->open) return;
    s->rx_frames++;
    if (s->proto == SN_PROTO_GVRET) gvret_frame(s, f, now_us);
    else slcan_frame(s, f, now_us);
}

void sn_note_overflow(sniffer_t *s) {
    s->overflows++;
    s->overflow_flag = true;
}
