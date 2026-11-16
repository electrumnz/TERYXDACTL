// Unit tests for the sniffer's USB protocols and MCP2515 timing maths.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "mcp_timing.h"
#include "sniffer.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL %s:%d  %s\n", __FILE__, __LINE__, #c); fails++; } } while (0)

// ---- fake hardware
static uint8_t outbuf[4096];
static size_t outlen;
static bool tx_jumper, opened, open_listen;
static uint32_t opened_rate;
static sn_frame_t sent[8];
static int nsent;

static bool f_open(void *c, uint32_t rate, sn_mode_t m) {
    if (rate == 1000000u) return false;
    opened = true; opened_rate = rate; open_listen = m == SN_MODE_LISTEN;
    return true;
}
static void f_close(void *c) { opened = false; }
static bool f_send(void *c, const sn_frame_t *f) { sent[nsent++ % 8] = *f; return true; }
static void f_write(void *c, const uint8_t *b, size_t n) { memcpy(outbuf + outlen, b, n); outlen += n; }
static bool f_tx(void *c) { return tx_jumper; }

static sniffer_t sn;
static void reset(bool jumper) {
    sn_hw_t hw = {f_open, f_close, f_send, f_write, f_tx, NULL};
    sn_init(&sn, &hw);
    outlen = 0; nsent = 0; opened = false; tx_jumper = jumper;
}
static void say(const char *s) { outlen = 0; sn_rx_bytes(&sn, (const uint8_t *)s, strlen(s), 1234000); }
static bool got(const char *s) { return outlen == strlen(s) && memcmp(outbuf, s, outlen) == 0; }
static void bytes(const uint8_t *b, size_t n) { outlen = 0; sn_rx_bytes(&sn, b, n, 0x01020304); }

static void test_slcan_basics(void) {
    reset(false);
    say("V\r");            CHECK(got("V1013\r"));
    say("S5\r");           CHECK(got("\r"));
    say("S9\r");           CHECK(got("\a"));
    say("O\r");            CHECK(got("\r")); CHECK(opened && opened_rate == 250000);
    CHECK(open_listen);    // no jumper: O still opens listen-only
    say("S6\r");           CHECK(got("\a"));   // can't change rate while open
    say("t1232AABB\r");    CHECK(got("\a")); CHECK(nsent == 0);   // and can't send
    CHECK(sn.tx_refused == 1);
    say("C\r");            CHECK(got("\r")); CHECK(!opened);
    say("S8\rO\r");        CHECK(got("\r\a"));   // 1M refused by this "8 MHz" adaptor
    say("s031C\r");        CHECK(got("\a"));     // custom BTR not supported
    say("S5\rL\r");        CHECK(got("\r\r")); CHECK(opened && open_listen && opened_rate == 250000);
}

static void test_slcan_frames_out(void) {
    reset(false);
    say("S6\rL\r");
    sn_frame_t f = {.id = 0x180, .dlc = 3, .data = {0x01, 0xAB, 0xFF}};
    outlen = 0;
    sn_on_frame(&sn, &f, 0);
    CHECK(got("t180301ABFF\r"));
    sn_frame_t e = {.id = 0x0CF11E05, .dlc = 0, .ext = true};
    outlen = 0;
    sn_on_frame(&sn, &e, 0);
    CHECK(got("T0CF11E050\r"));
    sn_frame_t r = {.id = 0x7FF, .dlc = 2, .rtr = true};
    outlen = 0;
    sn_on_frame(&sn, &r, 0);
    CHECK(got("r7FF2\r"));
    say("Z1\r");
    outlen = 0;
    sn_on_frame(&sn, &f, 61234000u);   // 61234 ms -> 1234 ms after wrap at 60000
    CHECK(got("t180301ABFF04D2\r"));
    say("C\r");
    outlen = 0;
    sn_on_frame(&sn, &f, 0);
    CHECK(outlen == 0);    // closed: nothing goes out
}

static void test_slcan_send_with_jumper(void) {
    reset(true);
    say("S5\rO\r");        CHECK(got("\r\r")); CHECK(!open_listen);
    say("t1232AABB\r");    CHECK(got("z\r"));
    CHECK(nsent == 1 && sent[0].id == 0x123 && sent[0].dlc == 2 && sent[0].data[1] == 0xBB && !sent[0].ext);
    say("T0CF11E0580102030405060708\r");   // 8 bytes
    CHECK(got("Z\r") && sent[1].ext && sent[1].id == 0x0CF11E05 && sent[1].data[7] == 8);
    say("t12321\r");       CHECK(got("\a"));   // too short
    say("t8001\r");        CHECK(got("\a"));   // id > 0x7FF
    say("C\rL\r");         CHECK(open_listen);
    say("t1230\r");        CHECK(got("\a"));   // listen-only even with the jumper
    tx_jumper = false;
    say("C\rO\r");         CHECK(open_listen);   // jumper removed: back to listen-only
}

static void test_overflow_flag(void) {
    reset(false);
    say("F\r");            CHECK(got("F00\r"));
    sn_note_overflow(&sn);
    say("F\r");            CHECK(got("F09\r"));
    say("F\r");            CHECK(got("F00\r"));
}

static void test_gvret(void) {
    reset(false);
    const uint8_t hello[] = {0xE7, 0xE7};
    bytes(hello, 2);
    CHECK(sn.proto == SN_PROTO_GVRET && opened && open_listen);   // opens straight away
    const uint8_t info[] = {0xF1, 0x07};
    bytes(info, 2);
    CHECK(outlen == 8 && outbuf[0] == 0xF1 && outbuf[1] == 0x07);
    const uint8_t keep[] = {0xF1, 0x09};
    bytes(keep, 2);
    CHECK(outlen == 4 && outbuf[2] == 0xDE && outbuf[3] == 0xAD);
    const uint8_t nb[] = {0xF1, 0x0C};
    bytes(nb, 2);
    CHECK(outlen == 3 && outbuf[2] == 1);
    const uint8_t ts[] = {0xF1, 0x01};
    bytes(ts, 2);
    CHECK(outlen == 6 && outbuf[2] == 0x04 && outbuf[5] == 0x01);
    // SETUP_CANBUS: 500k, flags: settings present, enabled, listen-only
    uint32_t v = 500000u | 0x80000000u | 0x40000000u | 0x20000000u;
    uint8_t setup[] = {0xF1, 0x05, (uint8_t)v, (uint8_t)(v >> 8), (uint8_t)(v >> 16), (uint8_t)(v >> 24), 0, 0, 0, 0};
    bytes(setup, sizeof setup);
    CHECK(outlen == 0 && opened && opened_rate == 500000u && open_listen);
    const uint8_t params[] = {0xF1, 0x06};
    bytes(params, 2);
    CHECK(outlen == 12 && outbuf[2] == 0x11 && outbuf[3] == 0x20 && outbuf[4] == 0xA1 && outbuf[5] == 0x07);
    // frame out
    sn_frame_t e = {.id = 0x0CF11E05, .ext = true, .dlc = 2, .data = {0xAA, 0xBB}};
    outlen = 0;
    sn_on_frame(&sn, &e, 0x11223344u);
    const uint8_t want[] = {0xF1, 0x00, 0x44, 0x33, 0x22, 0x11, 0x05, 0x1E, 0xF1, 0x8C, 0x02, 0xAA, 0xBB, 0x00};
    CHECK(outlen == sizeof want && memcmp(outbuf, want, sizeof want) == 0);
    // a send from SavvyCAN is refused without the jumper, and the parser stays in step
    const uint8_t tx[] = {0xF1, 0x00, 0x23, 0x01, 0, 0, 0, 2, 0xF1, 0xF1, 0, 0xF1, 0x09};
    bytes(tx, sizeof tx);
    CHECK(nsent == 0 && sn.tx_refused == 1);
    CHECK(outlen == 4 && outbuf[1] == 0x09);   // the keepalive after it was understood
    // echo frame comes back as if received
    const uint8_t echo[] = {0xF1, 0x0B, 0x80, 0, 0, 0, 0, 1, 0x5A, 0};
    bytes(echo, sizeof echo);
    CHECK(outlen == 13 && outbuf[1] == 0x00 && outbuf[6] == 0x80 && outbuf[11] == 0x5A);
    // disable bus
    const uint8_t off[] = {0xF1, 0x05, 0, 0, 0, 0, 0, 0, 0, 0};
    bytes(off, sizeof off);
    CHECK(!opened);
}

static void test_gvret_send_with_jumper(void) {
    reset(true);
    const uint8_t hello[] = {0xE7, 0xE7};
    bytes(hello, 2);
    uint32_t v = 250000u | 0x80000000u | 0x40000000u;   // enabled, not listen-only
    uint8_t setup[] = {0xF1, 0x05, (uint8_t)v, (uint8_t)(v >> 8), (uint8_t)(v >> 16), (uint8_t)(v >> 24), 0, 0, 0, 0};
    bytes(setup, sizeof setup);
    CHECK(opened && !open_listen);
    const uint8_t tx[] = {0xF1, 0x00, 0x23, 0x01, 0, 0, 0, 2, 0xF1, 0xF2, 0};
    bytes(tx, sizeof tx);
    CHECK(nsent == 1 && sent[0].id == 0x123 && sent[0].dlc == 2 && sent[0].data[0] == 0xF1);
}

static void test_timing(void) {
    struct { uint32_t osc, rate; } ok[] = {
        {8000000, 10000}, {8000000, 20000}, {8000000, 50000}, {8000000, 100000}, {8000000, 125000},
        {8000000, 250000}, {8000000, 500000}, {8000000, 800000},
        {16000000, 10000}, {16000000, 125000}, {16000000, 250000}, {16000000, 500000},
        {16000000, 800000}, {16000000, 1000000}, {20000000, 500000},
    };
    for (size_t i = 0; i < sizeof ok / sizeof ok[0]; i++) {
        mcp_timing_t t;
        bool r = mcp_timing(ok[i].osc, ok[i].rate, &t);
        CHECK(r);
        if (!r) { printf("  no timing for %u at %u\n", ok[i].rate, ok[i].osc); continue; }
        // registers say what the struct says
        uint32_t brp = t.cnf1 & 0x3F, prop = (t.cnf2 & 7) + 1, ps1 = ((t.cnf2 >> 3) & 7) + 1, ps2 = (t.cnf3 & 7) + 1;
        uint32_t n = 1 + prop + ps1 + ps2;
        CHECK(ok[i].osc == 2 * (brp + 1) * n * ok[i].rate);       // exact bit rate
        CHECK(t.cnf2 & 0x80);
        CHECK(ps2 >= 2 && prop + ps1 >= ps2 && ps1 <= 8 && prop <= 8 && ps2 <= 8);
        CHECK(t.sample_permille >= 600 && t.sample_permille <= 900);
    }
    mcp_timing_t t;
    CHECK(!mcp_timing(8000000, 1000000, &t));   // impossible from 8 MHz
    CHECK(mcp_timing(16000000, 250000, &t) && t.tq == 16 && t.sample_permille == 875);
}

int main(void) {
    test_slcan_basics();
    test_slcan_frames_out();
    test_slcan_send_with_jumper();
    test_overflow_flag();
    test_gvret();
    test_gvret_send_with_jumper();
    test_timing();
    if (fails) { printf("%d check(s) failed\n", fails); return 1; }
    printf("all sniffer tests passed\n");
    return 0;
}
