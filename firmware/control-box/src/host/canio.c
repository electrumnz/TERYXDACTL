#define _DEFAULT_SOURCE
#include "canio.h"

#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#ifdef __linux__
#include <linux/can.h>
#include <linux/can/raw.h>
#include <net/if.h>
#include <sys/ioctl.h>
#endif

enum { MODE_NONE, MODE_UDP, MODE_SOCKETCAN };
static int mode, rx_fd = -1, tx_fd = -1;
static struct sockaddr_in group_addr, own_addr;

static bool open_udp(const char *group, int port) {
    rx_fd = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    tx_fd = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (rx_fd < 0 || tx_fd < 0) return false;
    int one = 1;
    setsockopt(rx_fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
#ifdef SO_REUSEPORT
    setsockopt(rx_fd, SOL_SOCKET, SO_REUSEPORT, &one, sizeof(one));
#endif
    memset(&group_addr, 0, sizeof(group_addr));
    group_addr.sin_family = AF_INET;
    group_addr.sin_port = htons((uint16_t)port);
    inet_pton(AF_INET, group, &group_addr.sin_addr);
    if (bind(rx_fd, (struct sockaddr *)&group_addr, sizeof(group_addr)) < 0) {
        struct sockaddr_in any = group_addr;
        any.sin_addr.s_addr = htonl(INADDR_ANY);
        if (bind(rx_fd, (struct sockaddr *)&any, sizeof(any)) < 0) { perror("bind"); return false; }
    }
    struct ip_mreq mreq;
    mreq.imr_multiaddr = group_addr.sin_addr;
    inet_pton(AF_INET, "127.0.0.1", &mreq.imr_interface);
    if (setsockopt(rx_fd, IPPROTO_IP, IP_ADD_MEMBERSHIP, &mreq, sizeof(mreq)) < 0) {
        perror("IP_ADD_MEMBERSHIP");
        return false;
    }
    unsigned char ttl = 0, loop = 1;
    setsockopt(tx_fd, IPPROTO_IP, IP_MULTICAST_TTL, &ttl, sizeof(ttl));
    setsockopt(tx_fd, IPPROTO_IP, IP_MULTICAST_LOOP, &loop, sizeof(loop));
    struct in_addr lo;
    inet_pton(AF_INET, "127.0.0.1", &lo);
    setsockopt(tx_fd, IPPROTO_IP, IP_MULTICAST_IF, &lo, sizeof(lo));
    struct sockaddr_in b = {.sin_family = AF_INET};
    b.sin_addr = lo;
    if (bind(tx_fd, (struct sockaddr *)&b, sizeof(b)) < 0) { perror("bind tx"); return false; }
    socklen_t len = sizeof(own_addr);
    getsockname(tx_fd, (struct sockaddr *)&own_addr, &len);
    mode = MODE_UDP;
    return true;
}

#ifdef __linux__
static bool open_socketcan(const char *ifname) {
    rx_fd = socket(PF_CAN, SOCK_RAW, CAN_RAW);
    if (rx_fd < 0) { perror("socket(PF_CAN)"); return false; }
    struct ifreq ifr;
    memset(&ifr, 0, sizeof(ifr));
    snprintf(ifr.ifr_name, sizeof(ifr.ifr_name), "%s", ifname);
    if (ioctl(rx_fd, SIOCGIFINDEX, &ifr) < 0) { perror(ifname); return false; }
    struct sockaddr_can addr = {.can_family = AF_CAN, .can_ifindex = ifr.ifr_ifindex};
    if (bind(rx_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) { perror("bind can"); return false; }
    tx_fd = rx_fd;
    mode = MODE_SOCKETCAN;
    return true;
}
#endif

bool canio_open(const char *spec) {
    if (strncmp(spec, "udp", 3) == 0) {
        char group[64] = "239.0.7.0";
        int port = 47000;
        if (spec[3] == ':') sscanf(spec + 4, "%63[^:]:%d", group, &port);
        return open_udp(group, port);
    }
#ifdef __linux__
    if (strncmp(spec, "socketcan:", 10) == 0) return open_socketcan(spec + 10);
#endif
    fprintf(stderr, "unknown bus '%s' (use udp, udp:<group>:<port> or socketcan:<if>)\n", spec);
    return false;
}

bool canio_send(const can_frame_t *f) {
    if (mode == MODE_UDP) {
        uint8_t b[16] = {0};
        b[0] = (uint8_t)f->id; b[1] = (uint8_t)(f->id >> 8);
        b[2] = (uint8_t)(f->id >> 16); b[3] = (uint8_t)(f->id >> 24);
        b[4] = f->dlc;
        b[5] = f->ext ? 1 : 0;
        memcpy(&b[8], f->data, 8);
        return sendto(tx_fd, b, sizeof(b), 0, (struct sockaddr *)&group_addr, sizeof(group_addr)) == 16;
    }
#ifdef __linux__
    if (mode == MODE_SOCKETCAN) {
        struct can_frame cf = {0};
        cf.can_id = f->ext ? (f->id | CAN_EFF_FLAG) : f->id;
        cf.can_dlc = f->dlc;
        memcpy(cf.data, f->data, 8);
        return write(tx_fd, &cf, sizeof(cf)) == (ssize_t)sizeof(cf);
    }
#endif
    return false;
}

bool canio_recv(can_frame_t *f, int timeout_ms) {
    struct pollfd p = {.fd = rx_fd, .events = POLLIN};
    for (;;) {
        int r = poll(&p, 1, timeout_ms);
        if (r <= 0) return false;
        if (mode == MODE_UDP) {
            uint8_t b[64];
            struct sockaddr_in from;
            socklen_t fl = sizeof(from);
            ssize_t n = recvfrom(rx_fd, b, sizeof(b), 0, (struct sockaddr *)&from, &fl);
            if (n != 16) { timeout_ms = 0; continue; }
            if (from.sin_addr.s_addr == own_addr.sin_addr.s_addr && from.sin_port == own_addr.sin_port) {
                timeout_ms = 0;  // our own frame looped back
                continue;
            }
            f->id = (uint32_t)b[0] | ((uint32_t)b[1] << 8) | ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24);
            f->dlc = b[4] > 8 ? 8 : b[4];
            f->ext = (b[5] & 1) != 0;
            memcpy(f->data, &b[8], 8);
            return true;
        }
#ifdef __linux__
        struct can_frame cf;
        if (read(rx_fd, &cf, sizeof(cf)) != (ssize_t)sizeof(cf)) return false;
        f->ext = (cf.can_id & CAN_EFF_FLAG) != 0;
        f->id = cf.can_id & (f->ext ? CAN_EFF_MASK : CAN_SFF_MASK);
        f->dlc = cf.can_dlc > 8 ? 8 : cf.can_dlc;
        memcpy(f->data, cf.data, 8);
        return true;
#else
        return false;
#endif
    }
}

void canio_close(void) {
    if (rx_fd >= 0) close(rx_fd);
    if (tx_fd >= 0 && tx_fd != rx_fd) close(tx_fd);
    rx_fd = tx_fd = -1;
    mode = MODE_NONE;
}
