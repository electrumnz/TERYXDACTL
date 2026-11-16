# CAN sniffer firmware (Pico 2 + MCP2515)

Turns a spare Pico 2 and an MCP2515 module into a USB CAN adaptor, for decoding
the Shinegle controller. **How to use it: [docs/shinegle-decode.md](../../docs/shinegle-decode.md).**

- Shows up as a USB serial port (no drivers on Windows 10+, Mac or Linux).
- Speaks **slcan / LAWICEL** (python-can, Linux `slcand`, SavvyCAN's LAWICEL
  connection, the `teryx decode` tools) and **GVRET** (SavvyCAN's own serial
  connection). It works out which from the first bytes the computer sends.
- **Listen-only unless GP15 is bridged to GND.** Without that jumper it never
  sends a frame, never ACKs, never sends an error frame, whatever it's asked.
- Any bit rate from 10k to 1M (1M needs a 16 MHz crystal). Bit timing is
  worked out for the crystal, aiming for an 87.5% sample point.
- Core 1 does nothing but empty the MCP2515 into a 512-frame queue, so a slow
  USB moment doesn't lose frames. Lost frames are counted and reported by the
  slcan `F` command (bit 3).

## Pins

Same as the control box, so the same module and wiring work.

| Pico 2 | Use |
|---|---|
| GP2 / GP3 / GP4 / GP5 | MCP2515 SCK / SI / SO / CS |
| GP6 | MCP2515 INT |
| GP15 | Transmit jumper: leave open (listen-only), bridge to GND to allow sending |
| LED | slow blink = waiting, steady = bus open, flicker = frames, fast blink = MCP2515 not answering |

## slcan commands supported

`S0`-`S8` (10k, 20k, 50k, 100k, 125k, 250k, 500k, 800k, 1M), `O` open (listen-only
without the jumper), `L` open listen-only, `C` close, `t` `T` `r` `R` send,
`V` `v` `N` version and serial, `F` status, `Z0`/`Z1` timestamps. `M`, `m`, `X`,
`Q`, `W` are accepted and ignored. `s` (custom timing) is refused.

## Build

GitHub Actions builds both crystal versions on every push
(`teryx_can_sniffer_8mhz.uf2` and `teryx_can_sniffer_16mhz.uf2`).

```sh
# Pico 2 (Pico SDK 2.x and arm-none-eabi-gcc)
cmake -S . -B build -DPICO_BOARD=pico2 -DPICO_SDK_PATH=/path/to/pico-sdk -DSNIFFER_OSC_HZ=8000000
cmake --build build -j4

# PC build: unit tests, plus a pseudo-terminal "adaptor" on the test bus
cmake -S . -B build-host -DSNIFFER_HOST=ON && cmake --build build-host
ctest --test-dir build-host --output-on-failure
./build-host/can-sniffer-host --bus udp --link /tmp/ttySNIFF
python -m teryx decode capture --bus slcan:/tmp/ttySNIFF@250000   # with `python -m teryx sim --bus udp` running
```

`tests/test_sniffer_host.py` (in the main Python tests) builds the PC version and
drives it with python-can's slcan driver and a SavvyCAN-style GVRET handshake.

## Layout

| Folder | What |
|---|---|
| `src/core/` | USB protocols (`sniffer.c`) and MCP2515 bit timing (`mcp_timing.c`). Plain C, no hardware calls |
| `src/pico/` | Pico 2: MCP2515 driver, two-core main loop, USB |
| `src/host/` | PC version: pseudo terminal + the control box's UDP/SocketCAN bus code |
| `tests/` | Unit tests |

The GVRET protocol is implemented from SavvyCAN's published protocol (as used by
the MIT-licensed ESP32RET); no code was copied.
