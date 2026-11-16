# Teryx CAN sniffer firmware (Raspberry Pi Pico 2 + MCP2515 = USB CAN adaptor).
#
# Pico 2 build:  cmake -B build -DPICO_BOARD=pico2 [-DSNIFFER_OSC_HZ=16000000] && cmake --build build
#                (needs PICO_SDK_PATH and arm-none-eabi-gcc). Default crystal 8 MHz.
# Host build:    cmake -B build-host -DSNIFFER_HOST=ON && cmake --build build-host
#                ctest --test-dir build-host
cmake_minimum_required(VERSION 3.13)

option(SNIFFER_HOST "Build for the PC (pty bridge + unit tests) instead of the Pico" OFF)
set(SNIFFER_OSC_HZ 8000000 CACHE STRING "MCP2515 crystal in Hz (8000000 or 16000000, printed on the can)")

if(NOT SNIFFER_HOST)
    if(NOT DEFINED PICO_BOARD)
        set(PICO_BOARD pico2)
    endif()
    include(${CMAKE_CURRENT_LIST_DIR}/../control-box/pico_sdk_import.cmake)
endif()

project(teryx_can_sniffer C CXX ASM)
set(CMAKE_C_STANDARD 11)

set(CORE_SRC src/core/sniffer.c src/core/mcp_timing.c)

if(SNIFFER_HOST)
    add_compile_options(-Wall -Wextra -Werror -Wno-unused-parameter)
    add_library(sniffer_core STATIC ${CORE_SRC})
    target_include_directories(sniffer_core PUBLIC src/core)

    # The UDP / SocketCAN bus code is shared with the control box host build.
    add_executable(can-sniffer-host src/host/main_host.c ../control-box/src/host/canio.c)
    target_include_directories(can-sniffer-host PRIVATE ../control-box/src/host)
    target_link_libraries(can-sniffer-host sniffer_core)

    enable_testing()
    add_executable(test_sniffer tests/test_sniffer.c)
    target_link_libraries(test_sniffer sniffer_core)
    add_test(NAME sniffer COMMAND test_sniffer)
else()
    pico_sdk_init()
    add_executable(teryx_can_sniffer ${CORE_SRC} src/pico/main_pico.c src/pico/mcp2515.c)
    target_compile_options(teryx_can_sniffer PRIVATE -Wall -Wextra -Wno-unused-parameter)
    target_compile_definitions(teryx_can_sniffer PRIVATE
        SNIFFER_OSC_HZ=${SNIFFER_OSC_HZ}u
        USBD_PRODUCT="Teryx CAN sniffer"
        USBD_MANUFACTURER="Teryx OS"
        PICO_STDIO_USB_CONNECT_WAIT_TIMEOUT_MS=0)
    target_link_libraries(teryx_can_sniffer pico_stdlib pico_multicore pico_util hardware_spi hardware_watchdog)
    pico_enable_stdio_usb(teryx_can_sniffer 1)
    pico_enable_stdio_uart(teryx_can_sniffer 0)
    pico_set_program_name(teryx_can_sniffer "teryx-can-sniffer")
    pico_add_extra_outputs(teryx_can_sniffer)
endif()
