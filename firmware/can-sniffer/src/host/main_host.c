// PC build of the sniffer: the same protocol code, with a pseudo terminal
// standing in for USB and the test environment's bus standing in for CAN.
//
//   ./build-host/can-sniffer-host --bus udp --link /tmp/ttySNIFF [--tx]
//
// Then anything that talks to a USB CAN adaptor can open /tmp/ttySNIFF:
//   python -m teryx decode capture --bus slcan:/tmp/ttySNIFF@250000
// while `python -m teryx sim --bus udp` plays the Shinegle. Used by the tests.
#define _XOPEN_SOURCE 600
#define _DEFAULT_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

#include "../core/sniffer.h"
#include "canio.h"

static int master = -1;
static bool tx_enabled = false;
static bool bus_up = false;
static sn_mode_t bus_mode;
static volatile sig_atomic_t stop;

static uint32_t now_us(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint32_t)((uint64_t)ts.tv_sec * 1000000u + (uint64_t)ts.tv_nsec / 1000u);
}

static bool h_open(void *ctx, uint32_t bitrate, sn_mode_t mode) {
    // The fake bus has no bit rate. Refuse rates the real MCP2515 can't do from 8 MHz,
    // so the tests see the same answers as the hardware.
    if (bitrate == 1000000u) return false;
    bus_up = true;
    bus_mode = mode;
    fprintf(stderr, "sniffer: bus open %u bit/s %s\n", bitrate, mode == SN_MODE_LISTEN ? "listen-only" : "normal");
    return true;
}

static void h_close(void *ctx) {
    bus_up = false;
    fprintf(stderr, "sniffer: bus closed\n");
}

static bool h_send(void *ctx, const sn_frame_t *f) {
    if (!bus_up || bus_mode != SN_MODE_NORMAL) return false;
    can_frame_t c = {0};
    c.id = f->id;
    c.ext = f->ext;
    c.dlc = f->dlc;
    memcpy(c.data, f->data, f->dlc);
    return canio_send(&c);
}

static void h_write(void *ctx, const uint8_t *buf, size_t len) {
    while (len) {
        ssize_t n = write(master, buf, len);
        if (n < 0) {
            if (errno == EAGAIN || errno == EINTR) { usleep(200); continue; }
            return;
        }
        buf += n;
        len -= (size_t)n;
    }
}

static bool h_tx_allowed(void *ctx) { return tx_enabled; }

static void on_signal(int sig) { stop = 1; }

int main(int argc, char **argv) {
    const char *bus = "udp", *link_path = NULL;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--bus") && i + 1 < argc) bus = argv[++i];
        else if (!strcmp(argv[i], "--link") && i + 1 < argc) link_path = argv[++i];
        else if (!strcmp(argv[i], "--tx")) tx_enabled = true;
        else {
            fprintf(stderr, "usage: %s [--bus udp|socketcan:vcan0] [--link /tmp/ttySNIFF] [--tx]\n", argv[0]);
            return 2;
        }
    }
    signal(SIGINT, on_signal);
    signal(SIGTERM, on_signal);

    if (!canio_open(bus)) {
        fprintf(stderr, "can't open bus %s\n", bus);
        return 1;
    }
    master = posix_openpt(O_RDWR | O_NOCTTY);
    if (master < 0 || grantpt(master) || unlockpt(master)) {
        perror("pty");
        return 1;
    }
    const char *slave = ptsname(master);
    // Raw mode on the slave so bytes pass through untouched (GVRET is binary).
    int sfd = open(slave, O_RDWR | O_NOCTTY);
    struct termios tio;
    if (sfd >= 0 && tcgetattr(sfd, &tio) == 0) {
        cfmakeraw(&tio);
        tcsetattr(sfd, TCSANOW, &tio);
    }
    fcntl(master, F_SETFL, fcntl(master, F_GETFL) | O_NONBLOCK);
    if (link_path) {
        unlink(link_path);
        if (symlink(slave, link_path)) perror("symlink");
    }
    printf("%s\n", link_path ? link_path : slave);
    fflush(stdout);

    sniffer_t sn;
    sn_hw_t hw = {h_open, h_close, h_send, h_write, h_tx_allowed, NULL};
    sn_init(&sn, &hw);

    while (!stop) {
        uint8_t buf[256];
        ssize_t n = read(master, buf, sizeof buf);
        if (n > 0) sn_rx_bytes(&sn, buf, (size_t)n, now_us());
        can_frame_t f;
        while (canio_recv(&f, 1)) {
            if (!bus_up) continue;
            sn_frame_t s = {0};
            s.id = f.id;
            s.ext = f.ext;
            s.dlc = f.dlc > 8 ? 8 : f.dlc;
            memcpy(s.data, f.data, s.dlc);
            sn_on_frame(&sn, &s, now_us());
        }
    }
    if (link_path) unlink(link_path);
    if (sfd >= 0) close(sfd);
    canio_close();
    return 0;
}
