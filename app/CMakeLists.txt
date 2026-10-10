cmake_minimum_required(VERSION 3.25)
project(mercenaries2 VERSION 0.0.1 LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(REXSDK_DIR "" CACHE PATH "ReXGlue SDK source (Switch requires the Horizon fork)")
if(REXSDK_DIR)
    add_subdirectory("${REXSDK_DIR}" rexglue-sdk)
else()
    find_package(rexglue 0.10.0 REQUIRED CONFIG)
endif()
if(NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/generated/default/sources.cmake")
    message(FATAL_ERROR "Run tools/codegen.ps1 first")
endif()
include(generated/default/sources.cmake)
# Generation is a separate host step: a cross-built rexglue cannot run here.
add_library(mercenaries2_recomp OBJECT ${GENERATED_SOURCES})
target_include_directories(mercenaries2_recomp PRIVATE generated/default)
target_link_libraries(mercenaries2_recomp PRIVATE rex::runtime)
rexglue_apply_target_settings(mercenaries2_recomp)
target_precompile_headers(mercenaries2_recomp PRIVATE generated/default/mercenaries2_pch.h)
if(WIN32)
    add_executable(mercenaries2 WIN32 src/main.cpp src/bootstrap_callbacks.cpp src/math_compat_windows.cpp src/debug_guest_windows.cpp src/xam_enumerate_compat.cpp src/resolution_override.cpp src/guest_perf_switches.cpp)
    if(MSVC)
        target_compile_options(mercenaries2_recomp PRIVATE /EHa)
    endif()
else()
    add_executable(mercenaries2 src/main.cpp src/bootstrap_callbacks.cpp src/xam_enumerate_compat.cpp src/switch_memory_test.cpp src/switch_screenshot.cpp src/resolution_override.cpp src/guest_perf_switches.cpp
        # Native renderer (GPL-3.0, from project8-sw / nfsmw-nx, see src/native/README.md).
        # Selected at run time with mercs2_renderer = "native"; FSI emulation stays the default.
        src/native/mercs2_native_system.cpp src/native/native_renderer.cpp
        src/native/native_textures.cpp src/native/native_geometry_shaders.cpp
        src/native/native_tessellation.cpp)
endif()
target_include_directories(mercenaries2 PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
target_link_libraries(mercenaries2 PRIVATE mercenaries2_recomp rex::runtime)
rexglue_configure_target(mercenaries2 GPU_PLUGINS xenos)
if(REXGLUE_PLATFORM_SWITCH)
    target_include_directories(mercenaries2 PRIVATE "${REXSDK_DIR}/src/core"
        # Native renderer: the SDK's prebuilt SPIR-V and glslang's SPIR-V builder.
        "${REXSDK_DIR}/src/graphics" "${REXSDK_DIR}/thirdparty/glslang")
    # -lvulkan alone gives Ninja no archive dependency for driver patches.
    set_property(TARGET mercenaries2 APPEND PROPERTY LINK_DEPENDS
        "${REXGLUE_SWITCH_NVK_SDK}/lib/libvulkan.a")
    # NVK's non-sparse 512 MB Xenos shared buffer and Xbox guest allocations
    # share newlib's heap. Keep a cap for Horizon page tables and aliases.
    set(MERCENARIES2_SWITCH_HEAP_MB 2048 CACHE STRING "Capped Switch heap size in MiB")
    set_source_files_properties("${REXSDK_DIR}/src/ui/runtime_switch.cpp"
        DIRECTORY "${REXSDK_DIR}"
        PROPERTIES COMPILE_DEFINITIONS "REX_SWITCH_HEAP_MB=${MERCENARIES2_SWITCH_HEAP_MB}")
    set(MERCENARIES2_SWITCH_HOST_STACK_MB 8 CACHE STRING "Host stack budget per Xbox thread in MiB")
    set_source_files_properties("${REXSDK_DIR}/src/system/xthread.cpp"
        DIRECTORY "${REXSDK_DIR}/src/system"
        PROPERTIES COMPILE_DEFINITIONS "REX_SWITCH_HOST_STACK_MB=${MERCENARIES2_SWITCH_HOST_STACK_MB}")
    # This initializer contains tens of thousands of virtual registration calls.
    # GCC -O3 spends many minutes optimizing it; it runs only once at startup.
    set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/generated/default/mercenaries2_register.cpp"
        PROPERTIES COMPILE_OPTIONS "-O0" SKIP_PRECOMPILE_HEADERS ON)
    option(MERCENARIES2_GPU_DRAW_TIMING "Enable sparse GPU completion timing diagnostics" OFF)
    if(MERCENARIES2_GPU_DRAW_TIMING)
        target_compile_definitions(mercenaries2 PRIVATE MERCENARIES2_GPU_DRAW_TIMING)
    endif()
    # Off for real hardware; Eden runs need ON (see switch_emulator_memory_access.h).
    option(MERCENARIES2_EMULATOR_GUARDS "Route watched units through the emulator shadow-access path" OFF)
    if(MERCENARIES2_EMULATOR_GUARDS)
        target_compile_definitions(mercenaries2_recomp PRIVATE MERCENARIES2_EMULATOR_GUARDS)
    endif()
    foreach(t mercenaries2 mercenaries2_recomp)
        target_compile_options(${t} PRIVATE -ffp-contract=off -fno-strict-aliasing)
    endforeach()
    rexglue_switch_add_nro(mercenaries2 NAME "Mercenaries 2 (development)" AUTHOR "ReXGlue port" VERSION "0.0.1")
endif()
