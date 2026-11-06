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
        # 2026-10-16 optimisation round (Prototype 2 ports): guest flip pacing + GPU ring wait, PGO dumper.
        src/switch_frame_pacing.cpp src/switch_pgo.cpp
        # Native renderer (GPL-3.0, from project8-sw / nfsmw-nx, see src/native/README.md).
        # Selected at run time with mercs2_renderer = "native"; FSI emulation stays the default.
        src/native/mercs2_native_system.cpp src/native/native_renderer.cpp
        src/native/native_textures.cpp src/native/native_geometry_shaders.cpp
        src/native/native_tessellation.cpp)
endif()
# Native hot-function pilot; original weak guest aliases remain intact in OFF builds.
target_sources(mercenaries2 PRIVATE src/native_table_lookup.cpp)
option(MERCENARIES2_NATIVE_TABLE_LOOKUP "Native integer table probes with startup differential verification" OFF)
option(MERCENARIES2_LOOKUP_FRAME_CSV "Ring-only frame capture, without changing the profiled renderer" OFF)
set_property(SOURCE src/native_table_lookup.cpp APPEND PROPERTY COMPILE_DEFINITIONS
    MERCENARIES2_NATIVE_TABLE_LOOKUP=$<BOOL:${MERCENARIES2_NATIVE_TABLE_LOOKUP}>)
set_property(SOURCE src/native/mercs2_native_system.cpp APPEND PROPERTY COMPILE_DEFINITIONS
    MERCENARIES2_NATIVE_TABLE_LOOKUP=$<BOOL:${MERCENARIES2_NATIVE_TABLE_LOOKUP}>
    MERCENARIES2_LOOKUP_FRAME_CSV=$<BOOL:${MERCENARIES2_LOOKUP_FRAME_CSV}>)

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
    # Pass 1: independent experimental paths; old behavior remains the default.
    option(MERCENARIES2_DESCRIPTOR_BATCH "Batch adjacent changed graphics descriptor sets" OFF)
    option(MERCENARIES2_LEAN_DRAW_TIMERS "Omit the per-draw diagnostic CPU timer" OFF)
    option(MERCENARIES2_FRAME_CSV "Capture 30 s of frame data with L3+R3, flush off the ring" OFF)
    option(MERCENARIES2_INDEX_UPLOAD_SPECIALIZATION "Specialize bulk index conversion including restart" OFF)
    option(MERCENARIES2_DYNAMIC_UPLOAD_STAMPS "Use per-range fresh upload identities and staggered checks" OFF)
    option(MERCENARIES2_TARGETED_MEMO "Invalidate texture answers only for the changed resolve base" OFF)
    option(MERCENARIES2_DEPTH_ATTACHMENT_ONLY "Allow persistent ZCULL with attachment-cleared reserved depth storage" OFF)
    option(MERCENARIES2_ALPHA_COMPARE_SPECIALIZATION "Select alpha comparison at shader translation time" OFF)
    option(MERCENARIES2_SLOT_SOURCE_EPOCH "Invalidate slot views when texture source answers change (B-001)" OFF)
    option(MERCENARIES2_IMAGE_REUSE "Reuse completed pooled texture images within 16 MiB" OFF)
    option(MERCENARIES2_READY_TEXTURES "Prepare demanded textures before drawing instead of returning an empty stream answer" OFF)
    option(MERCENARIES2_MATERIAL_RETENTION "Retain idle materials within a 128 MiB payload target" OFF)
    option(MERCENARIES2_RING_WRITEBACK "Publish consumed ring positions at packet boundaries" OFF)
    foreach(opt DESCRIPTOR_BATCH LEAN_DRAW_TIMERS FRAME_CSV INDEX_UPLOAD_SPECIALIZATION DYNAMIC_UPLOAD_STAMPS TARGETED_MEMO DEPTH_ATTACHMENT_ONLY ALPHA_COMPARE_SPECIALIZATION SLOT_SOURCE_EPOCH IMAGE_REUSE READY_TEXTURES MATERIAL_RETENTION RING_WRITEBACK)
        target_compile_definitions(mercenaries2 PRIVATE
            MERCENARIES2_${opt}=$<BOOL:${MERCENARIES2_${opt}}>)
    endforeach()
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
    # 2026-10-16 (UnleashedRecomp-NX / guide section 8): guest fsqrt and friends compile to a single
    # instruction without the errno fallback call. No -ffast-math: rounding and contraction stay exact.
    option(MERCENARIES2_NO_MATH_ERRNO "Generated code: -fno-math-errno" ON)
    if(MERCENARIES2_NO_MATH_ERRNO)
        target_compile_options(mercenaries2_recomp PRIVATE -fno-math-errno)
    endif()

    # 2026-10-16: profile-guided optimisation, as in Prototype 2 (WORKLOG #126/#127: "noticeably faster";
    # guide "Практика Prototype 2"). Use a SEPARATE build directory (out/nx-pgo) for GEN and USE:
    #   GEN: instrumented build; one representative session, periodic dumps in the game's PGO directory.
    #        tools/pgo_session.py freezes sources/flags and validates imported gcda against GEN graphs.
    #   USE: the optimised build from those profiles. Same sources and build directory as GEN.
    # -fno-profile-values: the indirect-call value profiler keeps a thread-local libgcov variable that is null
    # on guest threads (Prototype 2 run97 crash). -fprofile-correction: counters are racy (update=single).
    set(MERCENARIES2_PGO "OFF" CACHE STRING "PGO stage: OFF, GEN or USE")
    set(MERCENARIES2_PGO_DATA "${CMAKE_CURRENT_SOURCE_DIR}/../out/pgo-data" CACHE STRING
        "Directory with the .gcda files for MERCENARIES2_PGO=USE")
    set(MERCENARIES2_PGO_DEVICE_DIR "sdmc:/switch/Mercenaries2/pgo/training" CACHE STRING
        "Game-owned, session-specific directory on the console")
    option(MERCENARIES2_PGO_SKIP_TEXTURES "Exclude the changed texture TU from old PGO data (USE only)" OFF)
    option(MERCENARIES2_PGO_SKIP_RENDERER "Exclude changed native renderer from old PGO (USE only)" OFF)
    if(MERCENARIES2_PGO_SKIP_RENDERER AND NOT MERCENARIES2_PGO STREQUAL "USE")
        message(FATAL_ERROR "PGO_SKIP_RENDERER requires USE")
    endif()
    option(MERCENARIES2_PGO_SKIP_NATIVE_SYSTEM "Exclude changed native system TU from old PGO (USE only)" OFF)
    if(MERCENARIES2_PGO_SKIP_NATIVE_SYSTEM AND NOT MERCENARIES2_PGO STREQUAL "USE")
        message(FATAL_ERROR "PGO_SKIP_NATIVE_SYSTEM requires USE")
    endif()
    if(MERCENARIES2_PGO_SKIP_TEXTURES AND NOT MERCENARIES2_PGO STREQUAL "USE")
        message(FATAL_ERROR "PGO_SKIP_TEXTURES requires USE")
    endif()
    if(NOT MERCENARIES2_PGO MATCHES "^(OFF|GEN|USE)$")
        message(FATAL_ERROR "Invalid MERCENARIES2_PGO stage")
    endif()
    if(MERCENARIES2_PGO STREQUAL "GEN")
        if(NOT MERCENARIES2_PGO_DEVICE_DIR MATCHES "^sdmc:/switch/Mercenaries2/pgo/[A-Za-z0-9_-]+$")
            message(FATAL_ERROR "PGO output must be inside this game's session directory")
        endif()
        foreach(t mercenaries2 mercenaries2_recomp)
            target_compile_options(${t} PRIVATE "-fprofile-generate=${MERCENARIES2_PGO_DEVICE_DIR}"
                -fno-profile-values -ftest-coverage -fprofile-update=single
                "-fprofile-prefix-path=${CMAKE_BINARY_DIR}")
        endforeach()
        target_link_options(mercenaries2 PRIVATE "-fprofile-generate=${MERCENARIES2_PGO_DEVICE_DIR}")
        target_compile_definitions(mercenaries2 PRIVATE MERCENARIES2_PGO_GEN=1
            "MERCENARIES2_PGO_DEVICE_DIR=\"${MERCENARIES2_PGO_DEVICE_DIR}\"")
        # Never instrument the thread which walks/resets the instrumentation.
        set_source_files_properties(src/switch_pgo.cpp PROPERTIES
            COMPILE_OPTIONS "-fno-profile-generate;-fno-profile-arcs;-fno-test-coverage")
    elseif(MERCENARIES2_PGO STREQUAL "USE")
        # New TU has no original training data; keep all existing profiles strict.
        set_property(SOURCE src/native_table_lookup.cpp APPEND PROPERTY COMPILE_OPTIONS -fno-profile-use)
        # This TU changed CFG: its old profile must not be applied. Other 162
        # profiles retain strict validation. Never suppress mismatch warnings.
        if(MERCENARIES2_PGO_SKIP_TEXTURES)
            set_property(SOURCE src/native/native_textures.cpp APPEND PROPERTY
                COMPILE_OPTIONS -fno-profile-use)
        endif()
        if(MERCENARIES2_PGO_SKIP_RENDERER)
            set_property(SOURCE src/native/native_renderer.cpp APPEND PROPERTY COMPILE_OPTIONS -fno-profile-use)
        endif()
        if(MERCENARIES2_PGO_SKIP_NATIVE_SYSTEM)
            set_property(SOURCE src/native/mercs2_native_system.cpp APPEND PROPERTY COMPILE_OPTIONS -fno-profile-use)
        endif()
        foreach(t mercenaries2 mercenaries2_recomp)
            target_compile_options(${t} PRIVATE "-fprofile-use=${MERCENARIES2_PGO_DATA}"
                -fprofile-partial-training -fprofile-correction "-fprofile-prefix-path=${CMAKE_BINARY_DIR}"
                -Wmissing-profile -Werror=coverage-mismatch)
        endforeach()
        target_link_options(mercenaries2 PRIVATE "-fprofile-use=${MERCENARIES2_PGO_DATA}"
            -fprofile-partial-training)
    endif()
    rexglue_switch_add_nro(mercenaries2 NAME "Mercenaries 2 (development)" AUTHOR "ReXGlue port" VERSION "0.0.1")
endif()
