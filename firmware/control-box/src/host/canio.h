// Host build CAN transport: SocketCAN (Linux) or UDP multicast (anywhere).
// UDP format matches teryx/canbus/udpbus.py: 16 bytes per frame,
// u32 id LE | u8 dlc | u8 flags (bit0 ext) | 2 pad | 8 data.
#pragma once
#include <stdbool.h>
#include "../core/protocol.h"

// spec: "udp", "udp:<group>:<port>", "socketcan:<ifname>"
bool canio_open(const char *spec);
bool canio_send(const can_frame_t *f);
// Waits up to timeout_ms for a frame. Returns false on timeout.
bool canio_recv(can_frame_t *f, int timeout_ms);
void canio_close(void);
