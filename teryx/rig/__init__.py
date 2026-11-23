"""System sim: the real control box firmware, pin for pin, inside the whole-vehicle wiring.

    firmware.py  builds src/pico/main_pico.c + drivers for the PC and loads it (ctypes)
    netlist.py   turns config/wiring.yaml into nets and solves them (switch-level)
    models.py    what each device in wiring.yaml does electrically
    system.py    ties it together with the fake Shinegle and the dash gateway on one CAN bus

docs/system-sim.md explains it in plain words.
"""

from .system import System  # noqa: F401
