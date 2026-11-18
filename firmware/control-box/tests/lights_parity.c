// Prints the C light rules for tests/test_lights_parity.py to compare with teryx/lights.py.
// stdin, one case per line:
//   L show unified_lamp t                       -> show level
//   S hl hh tail rear tbar beacon show rear_on rear_auto brake rev trailer stopped park ign locked dash front now white
//                                               -> 15 levels, show_running, show_blocked
#include <stdio.h>
#include "lights.h"

int main(void) {
    char kind;
    lights_t L = {0};
    while (scanf(" %c", &kind) == 1) {
        if (kind == 'L') {
            unsigned show, u, t;
            if (scanf("%u %u %u", &show, &u, &t) != 3) return 1;
            printf("%u\n", u < LP_COUNT ? show_level_lamp((uint8_t)show, (int)u, t)
                                        : show_level_front((uint8_t)show, (int)(u - LP_COUNT), t));
        } else if (kind == 'S') {
            unsigned v[20];
            for (int i = 0; i < 20; i++) if (scanf("%u", &v[i]) != 1) return 1;
            lights_req_t r = {(uint8_t)v[0], (uint8_t)v[1], (uint8_t)v[2], (uint8_t)v[3], (uint8_t)v[4],
                              (uint8_t)v[5], (uint8_t)v[6], (uint8_t)v[19], v[7], v[8]};
            lights_state_t s = {v[9], v[10], v[11], v[12], v[13], v[14], v[15], v[16], v[17], v[18]};
            lights_out_t o;
            lights_step(&L, &r, &s, &o);
            for (int i = 0; i < LP_COUNT; i++) printf("%u ", o.level[i]);
            printf("%d %d\n", o.show_running, o.show_blocked);
        }
    }
    return 0;
}
