#include "eps.h"
#include <string.h>

uint8_t eps_checksum(uint16_t id, const uint8_t *data, uint8_t len) {
    uint32_t t = (id >> 8) + (id & 0xFF) + len;
    for (uint8_t i = 0; i + 1 < len; i++) t += data[i];
    return (uint8_t)t;
}

int eps_frames(uint16_t speed_x10, bool speed_known, can_frame_t out[2]) {
    memset(out, 0, 2 * sizeof(can_frame_t));
    out[0].id = EPS_RPM_ID;
    out[0].dlc = 8;
    const uint8_t rpm[8] = {EPS_RPM_RUNNING >> 8, EPS_RPM_RUNNING & 0xFF, 0x00, 0x19, 0x00, 0x00, 0x92, 0x00};
    memcpy(out[0].data, rpm, 8);
    out[0].data[7] = eps_checksum(EPS_RPM_ID, out[0].data, 8);

    uint32_t raw = speed_known ? (uint32_t)speed_x10 * 10u : 0;  // 0.01 km/h per bit
    if (raw < EPS_FLOOR_KMH_X100) raw = EPS_FLOOR_KMH_X100;
    if (raw > 0xFFFF) raw = 0xFFFF;
    out[1].id = EPS_SPEED_ID;
    out[1].dlc = 8;
    out[1].data[4] = 0x8D;
    out[1].data[5] = (uint8_t)(raw >> 8);
    out[1].data[6] = (uint8_t)raw;
    out[1].data[7] = eps_checksum(EPS_SPEED_ID, out[1].data, 8);
    return 2;
}
