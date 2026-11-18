# Teryx control box firmware (Raspberry Pi Pico 2).
#
# Pico 2 build:  cmake -B build -DPICO_BOARD=pico2 && cmake --build build
#                (needs PICO_SDK_PATH and arm-none-eabi-gcc)
# Host build:    cmake -B build-host -DTERYX_HOST=ON && cmake --build build-host
#                ctest --test-dir build-host
cmake_minimum_required(VERSION 3.13)

option(TERYX_HOST "Build for the PC (simulator + unit tests) instead of the Pico" OFF)

if(NOT TERYX_HOST)
    if(NOT DEFINED PICO_BOARD)
        set(PICO_BOARD pico2)
    endif()
    include(pico_sdk_import.cmake)
endif()

project(teryx_control_box C CXX ASM)
set(CMAKE_C_STANDARD 11)

# Firmware version lives in firmware/VERSION as "major.minor".
file(STRINGS ${CMAKE_CURRENT_SOURCE_DIR}/../VERSION FW_VERSION LIMIT_COUNT 1)
string(REGEX MATCH "^([0-9]+)\\.([0-9]+)" _ ${FW_VERSION})
add_compile_definitions(FW_VERSION_MAJOR=${CMAKE_MATCH_1} FW_VERSION_MINOR=${CMAKE_MATCH_2})

set(CORE_SRC
    src/core/controller.c
    src/core/settings.c
    src/core/lock.c
    src/core/sha256.c
    src/core/lights.c
)

if(TERYX_HOST)
    add_compile_options(-Wall -Wextra -Werror -Wno-unused-parameter)
    add_library(cb_core STATIC ${CORE_SRC} src/host/plant.c src/host/rand_host.c)
    target_include_directories(cb_core PUBLIC src/core)

    add_executable(control-box-host src/host/main_host.c src/host/canio.c)
    target_link_libraries(control-box-host cb_core)

    enable_testing()
    add_executable(test_controller tests/test_controller.c)
    target_link_libraries(test_controller cb_core m)
    add_test(NAME controller COMMAND test_controller)
    find_package(Python3 COMPONENTS Interpreter)
    if(Python3_FOUND)
        add_test(NAME bus COMMAND Python3::Interpreter ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_bus.py
                 $<TARGET_FILE:control-box-host>)
    endif()
else()
    pico_sdk_init()
    add_executable(teryx_control_box
        ${CORE_SRC}
        src/pico/main_pico.c
        src/pico/mcp2515.c
        src/pico/mcp23017.c
        src/pico/ads1115.c
        src/pico/pca9685.c
    )
    target_compile_options(teryx_control_box PRIVATE -Wall -Wextra -Wno-unused-parameter)
    target_link_libraries(teryx_control_box
        pico_stdlib pico_flash pico_rand hardware_spi hardware_i2c hardware_pwm hardware_adc
        hardware_watchdog hardware_flash
    )
    # USB serial for logs, and so "picotool reboot -f -u" works from the Pi.
    pico_enable_stdio_usb(teryx_control_box 1)
    pico_enable_stdio_uart(teryx_control_box 0)
    pico_set_program_name(teryx_control_box "teryx-control-box")
    pico_add_extra_outputs(teryx_control_box)   # .uf2 for drag and drop / picotool
endif()
