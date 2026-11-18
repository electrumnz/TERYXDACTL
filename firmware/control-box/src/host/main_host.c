// Teryx control box: host build. Runs the real control logic against a model
// of the hardware, on a UDP or SocketCAN bus shared with the simulator / dash.
//
//   ./control-box-host --bus udp
//   ./control-box-host --bus socketcan:vcan0 --settings /tmp/cb.bin
#define _POSIX_C_SOURCE 200809L
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "../core/config.h"
#include "../core/controller.h"
#include "canio.h"
#include "plant.h"

static volatile sig_atomic_t stop;
static void on_sig(int s) { (void)s; stop = 1; }

static uint32_t now_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint32_t)(ts.tv_sec * 1000u + ts.tv_nsec / 1000000u);
}

static void send_cb(const can_frame_t *f, void *user) { (void)user; canio_send(f); }

static bool load_settings(const char *path, settings_t *s) {
    FILE *fp = fopen(path, "rb");
    if (!fp) return false;
    settings_blob_t b;
    bool ok = fread(&b, sizeof(b), 1, fp) == 1 && settings_from_blob(s, &b);
    fclose(fp);
    return ok;
}

static void save_settings(const char *path, const settings_t *s) {
    settings_blob_t b;
    settings_to_blob(s, &b);
    FILE *fp = fopen(path, "wb");
    if (!fp) { perror(path); return; }
    fwrite(&b, sizeof(b), 1, fp);
    fclose(fp);
}

// Vehicle lock sector (docs/vehicle-lock.md), a file here.
static bool load_lock(const char *path, lock_blob_t *b) {
    FILE *fp = fopen(path, "rb");
    if (!fp) return false;
    bool ok = fread(b, sizeof(*b), 1, fp) == 1;
    fclose(fp);
    return ok;
}

static void save_lock(const char *path, const lock_blob_t *b) {
    FILE *fp = fopen(path, "wb");
    if (!fp) { perror(path); return; }
    fwrite(b, sizeof(*b), 1, fp);
    fclose(fp);
}

static void usage(void) {
    puts("control-box-host [--bus udp|udp:<group>:<port>|socketcan:<if>] [--settings FILE]\n"
         "                 [--lock FILE] [--lock-reset] [--key-off] [--quiet]\n"
         "Plays the Pico 2 control box on a shared bus. The simulator drives the\n"
         "wired inputs with 0x7E0 bench frames.");
}

int main(int argc, char **argv) {
    const char *bus = "udp";
    const char *settings_path = "control-box-settings.bin";
    const char *lock_path = "control-box-lock.bin";
    bool quiet = false, key_off = false, lock_reset = false;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--bus") && i + 1 < argc) bus = argv[++i];
        else if (!strcmp(argv[i], "--settings") && i + 1 < argc) settings_path = argv[++i];
        else if (!strcmp(argv[i], "--lock") && i + 1 < argc) lock_path = argv[++i];
        else if (!strcmp(argv[i], "--lock-reset")) lock_reset = true;  // workshop recovery
        else if (!strcmp(argv[i], "--quiet")) quiet = true;
        else if (!strcmp(argv[i], "--key-off")) key_off = true;
        else { usage(); return 2; }
    }
    if (!canio_open(bus)) return 1;
    signal(SIGINT, on_sig);
    signal(SIGTERM, on_sig);

    static controller_t ctl;
    plant_t plant;
    plant_init(&plant);
    if (key_off) plant.din_model &= (uint8_t)~BIT(IN_IGNITION);

    settings_t saved;
    bool have = load_settings(settings_path, &saved);
    uint32_t t = now_ms();
    ctl_init(&ctl, have ? &saved : NULL, false, false, t);
    lock_blob_t lock_saved;
    bool have_lock = load_lock(lock_path, &lock_saved);
    ctl_load_lock(&ctl, have_lock ? &lock_saved : NULL, t);
    if (lock_reset) {
        lock_workshop_reset(&ctl.lock);
        printf("vehicle lock: workshop reset, PIN and recovery code wiped\n");
    }
    printf("Teryx control box host build v%d.%d.%d on %s (%s settings)\n",
           FW_VERSION_MAJOR, FW_VERSION_MINOR, FW_VERSION_PATCH, bus, have ? "saved" : "default");
    fflush(stdout);

    cb_out_t out = {0};
    uint32_t next = t, last_print = t;
    uint16_t last_faults = 0;
    while (!stop) {
        t = now_ms();
        int wait = (int32_t)(next - t) > 0 ? (int)(next - t) : 0;
        can_frame_t f;
        if (canio_recv(&f, wait)) {
            if (f.id == CAN_ID_BENCH && !f.ext) plant_bench_frame(&plant, &f);
            else ctl_on_frame(&ctl, &f, now_ms(), send_cb, NULL);
            continue;
        }
        t = now_ms();
        if ((int32_t)(t - next) < 0) continue;
        next += TICK_MS;
        if ((int32_t)(t - next) > 100) next = t;  // fell behind (debugger, sleep)

        plant_step(&plant, &out, TICK_MS / 1000.0);
        cb_in_t in;
        plant_inputs(&plant, &in, t);
        ctl_tick(&ctl, &in, &out, send_cb, NULL);

        if (out.save_settings) {
            save_settings(settings_path, &ctl.settings);
            ctl.out.save_settings = false;
            printf("settings saved to %s\n", settings_path);
        }
        if (out.save_lock) save_lock(lock_path, &ctl.lock.saved);
        if (out.enter_bootloader) {
            // On the Pico this reboots into the USB bootloader. Here we act out
            // the reboot: the flash tool on the Pi would now copy new firmware.
            printf("firmware update requested: rebooting to bootloader (host: restarting)\n");
            fflush(stdout);
            have = load_settings(settings_path, &saved);
            ctl_init(&ctl, have ? &saved : NULL, false, (out.relays & BIT(R_POWER_HOLD)) != 0, now_ms());
            have_lock = load_lock(lock_path, &lock_saved);
            ctl_load_lock(&ctl, have_lock ? &lock_saved : NULL, now_ms());
            memset(&out, 0, sizeof(out));
            continue;
        }
        if (!quiet && (t - last_print >= 1000u || ctl.faults != last_faults)) {
            last_print = t;
            last_faults = ctl.faults;
            printf("din=%02x relays=%02x lights=%3d %3d %3d %3d %3d diff=%3d%% 4wd=%d tray=%3d%% "
                   "armed=%d faults=%04x speed=%s%u\n",
                   in.din, out.relays, out.light[0], out.light[1], out.light[2], out.light[3],
                   out.light[4], ctl.diff.pct == PCT_UNKNOWN ? -1 : ctl.diff.pct, ctl.fwd.state,
                   (int)(plant.pos[ACT_TRAY] * 100), ctl.winch.armed, ctl.faults,
                   ctl_speed_valid(&ctl, t) ? "" : "?", ctl.speed_x10 / 10);
            fflush(stdout);
        }
    }
    canio_close();
    return 0;
}
