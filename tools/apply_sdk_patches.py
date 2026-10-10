"""Apply local Switch SDK fixes without resetting or modifying unrelated files."""
from pathlib import Path
import subprocess, sys
ROOT = Path(__file__).resolve().parents[1]
SDK_REPO = ROOT / "reference/masseffect-nx"
patch = ROOT / "tools/patches/switch-process-handle.patch"
source = SDK_REPO / "sdk/src/core/guest_memory_switch.cpp"
if "struct ProcessHandleRequest" in source.read_text():
    print("Switch process-handle fallback already present")
else:
    subprocess.run(["git", "apply", "--check", str(patch)], cwd=SDK_REPO, check=True)
    subprocess.run(["git", "apply", str(patch)], cwd=SDK_REPO, check=True)
    print("Applied Switch process-handle fallback")

# Older copies of the fallback patch initialize lazily inside virtmemLock.
text = source.read_text()
marker = "    (void)Proc();\n"
if marker not in text:
    text = text.replace("uint8_t* RexGmInit(size_t size) {\n",
                        "uint8_t* RexGmInit(size_t size) {\n"
                        "    // Thread creation in the fallback also takes virtmemLock.\n"
                        "    (void)Proc();\n", 1)
    source.write_text(text)
    print("Initialized process handle before virtual-memory locks")

if "RexGmMapCommittedRange" not in (SDK_REPO / "sdk/src/core/memory_switch.cpp").read_text():
    patch = ROOT / "tools/patches/switch-map-allocated-view.patch"
    subprocess.run(["git", "apply", "--check", str(patch)], cwd=SDK_REPO, check=True)
    subprocess.run(["git", "apply", str(patch)], cwd=SDK_REPO, check=True)
    print("Mapped writable allocations into their requested guest view")

if "REX_SWITCH_HEAP_MB" not in (SDK_REPO / "sdk/src/ui/runtime_switch.cpp").read_text():
    patch = ROOT / "tools/patches/switch-configurable-heap.patch"
    subprocess.run(["git", "apply", "--check", str(patch)], cwd=SDK_REPO, check=True)
    subprocess.run(["git", "apply", str(patch)], cwd=SDK_REPO, check=True)

if "pthread_create failed: error=" not in (SDK_REPO / "sdk/src/core/threading_posix.cpp").read_text():
    patch = ROOT / "tools/patches/switch-thread-create-diagnostics.patch"
    subprocess.run(["git", "apply", "--check", str(patch)], cwd=SDK_REPO, check=True)
    subprocess.run(["git", "apply", str(patch)], cwd=SDK_REPO, check=True)
    print("Added original thread-creation error diagnostics")

if "REX_SWITCH_HOST_STACK_MB" not in (SDK_REPO / "sdk/src/system/xthread.cpp").read_text():
    patch = ROOT / "tools/patches/switch-configurable-host-stack.patch"
    subprocess.run(["git", "apply", "--check", str(patch)], cwd=SDK_REPO, check=True)
    subprocess.run(["git", "apply", str(patch)], cwd=SDK_REPO, check=True)
    print("Added configurable per-port Switch host stacks")

if "bad-indirect-%08X-%08X.bin" not in (SDK_REPO / "sdk/src/graphics/command_processor.cpp").read_text():
    patch = ROOT / "tools/patches/switch-gpu-command-diagnostics.patch"
    subprocess.run(["git", "apply", "--check", str(patch)], cwd=SDK_REPO, check=True)
    subprocess.run(["git", "apply", str(patch)], cwd=SDK_REPO, check=True)
    print("Added opt-in failing GPU stream diagnostics")
# Keep the runtime SPIR-V texture LOD state independent of integer vfetch bounds.
# An earlier insertion accidentally chained both IDs to the integer variable.
spirv_source = SDK_REPO / 'sdk/src/graphics/pipeline/shader/spirv_translator.cpp'
spirv_text = spirv_source.read_text()
if '    var_main_tfetch_lod_ =\n    var_main_vfetch_bound_ =' in spirv_text:
    spirv_patch = ROOT / 'tools/patches/switch-spirv-lod-initialization.patch'
    subprocess.run(['git', 'apply', '--check', str(spirv_patch)], cwd=SDK_REPO, check=True)
    subprocess.run(['git', 'apply', str(spirv_patch)], cwd=SDK_REPO, check=True)
    print('Separated float texture LOD from integer vertex fetch bounds')
else:
    lod_initializer = ('    var_main_tfetch_lod_ =\n'
                       '        builder_->createVariable(spv::NoPrecision, spv::StorageClassFunction, type_float_,\n'
                       '                                 "xe_var_tfetch_lod", const_float_0_);')
    if lod_initializer not in spirv_text:
        raise RuntimeError('Unexpected SPIR-V LOD initializer; inspect before patching')
    print('SPIR-V float texture LOD initializer already present')

# Preserve independently validated Vulkan EDRAM signed-range resolve kernels.
import hashlib, json, shutil
water_dir = ROOT / 'tools/patches/xenia-water-vulkan'
water_manifest = json.loads((water_dir / 'generated-manifest.json').read_text())
water_targets = SDK_REPO / 'sdk/src/graphics/shaders/vulkan_spirv'
for record in water_manifest['files']:
    supplied = water_dir / 'generated' / record['file']
    target = water_targets / record['file']
    if hashlib.sha256(supplied.read_bytes()).hexdigest() != record['sha256']:
        raise RuntimeError('Vendored Vulkan water kernel hash mismatch: ' + record['file'])
    current = hashlib.sha256(target.read_bytes()).hexdigest()
    if current == record['sha256']:
        continue
    if current != record['original_sha256']:
        raise RuntimeError('Unexpected SDK Vulkan resolve kernel; inspect before replacing: ' + record['file'])
    shutil.copy2(supplied, target)
print('Validated Vulkan signed EDRAM resolve kernels present')

# Sparse GPU diagnostics: no skipped game work, pools recycled after existing fences.
timing_patch = ROOT / 'tools/patches/switch-gpu-draw-timing.patch'
timing_marker = 'VulkanCommandProcessor::BeginDrawTiming'
timing_source = SDK_REPO / 'sdk/src/graphics/vulkan/draw_timing_switch.inc'
if not timing_source.exists():
    subprocess.run(['git', 'apply', '--check', str(timing_patch)], cwd=SDK_REPO, check=True)
    subprocess.run(['git', 'apply', str(timing_patch)], cwd=SDK_REPO, check=True)
else:
    timing_checks = {
        timing_source: timing_marker,
        SDK_REPO / 'sdk/src/graphics/vulkan/command_processor.cpp': 'EndDrawTiming(timing_sample)',
        SDK_REPO / 'sdk/include/rex/graphics/vulkan/deferred_command_buffer.h': 'kVkWriteTimestamp',
        SDK_REPO / 'sdk/src/graphics/vulkan/deferred_command_buffer.cpp': 'reinterpret_cast<PFN_vkCmdWriteTimestamp>',
        SDK_REPO / 'sdk/src/ui/switch_perf.cpp': 'Timing builds retain every command',
    }
    for source, marker in timing_checks.items():
        if marker not in source.read_text(encoding='utf-8-sig'):
            raise RuntimeError('Incomplete GPU timing patch: ' + str(source))
print('Sparse GPU draw timing diagnostic patch present (opt-in build option)')

# Reject the failed 78f533c6 shared-table expansion; timestamps are resolved separately.
import re
original_vk_functions = json.loads((ROOT / 'tools/patches/switch-gpu-draw-timing-original-functions.json').read_text())
current_vk_functions = re.findall(r'^XE_UI_VULKAN_FUNCTION\((\w+)\)',
    (SDK_REPO / 'sdk/include/rex/ui/vulkan/functions/device_1_0.inc').read_text(), re.M)
if current_vk_functions != original_vk_functions:
    raise RuntimeError('Shared Vulkan function table changed; inspect/rebuild ABI before proceeding')

# Narrow Switch-only FSI specialization; no shared Vulkan table changes.
fsi_patch = ROOT / 'tools/patches/switch-fsi-no-depth-late-interlock.patch'
fsi_header = SDK_REPO / 'sdk/include/rex/graphics/pipeline/shader/spirv_translator.h'
if 'kFSINoDepthLateInterlock' not in fsi_header.read_text():
    subprocess.run(['git', 'apply', '--check', str(fsi_patch)], cwd=SDK_REPO, check=True)
    subprocess.run(['git', 'apply', str(fsi_patch)], cwd=SDK_REPO, check=True)
else:
    for filename, marker in {
        'sdk/include/rex/graphics/pipeline/shader/spirv_translator.h': 'kFSINoDepthLateInterlock = uint64_t(1) << 49',
        'sdk/src/graphics/pipeline/shader/spirv_translator_rb.cpp': 'helper/zero-coverage invocations',
        'sdk/src/graphics/vulkan/pipeline_cache.cpp': 'FSI_NO_DEPTH_LATE ps=',
    }.items():
        if marker not in (SDK_REPO / filename).read_text():
            raise RuntimeError('Incomplete no-depth FSI specialization: ' + filename)
print('Switch no-depth late-interlock specialization present')

# Separate full-depth mode retains tests and keeps derivatives outside coverage branch.
full_patch = ROOT / 'tools/patches/switch-fsi-full-depth-late-interlock.patch'
if 'kFSIFullDepthLateInterlock' not in fsi_header.read_text():
    subprocess.run(['git', 'apply', '--check', str(full_patch)], cwd=SDK_REPO, check=True)
    subprocess.run(['git', 'apply', str(full_patch)], cwd=SDK_REPO, check=True)
else:
    for filename, marker in {
        'sdk/include/rex/graphics/pipeline/shader/spirv_translator.h': 'kVersion = 0x20261009',
        'sdk/src/graphics/pipeline/shader/spirv_translator_rb.cpp': 'stencil-fail writes must not be skipped',
        'sdk/src/graphics/vulkan/pipeline_cache.cpp': 'FSI_FULL_DEPTH_LATE ps=',
    }.items():
        if marker not in (SDK_REPO / filename).read_text():
            raise RuntimeError('Incomplete full-depth FSI specialization: ' + filename)
print('Switch full-depth late-interlock specialization present')

# P0 opt-in executable statistics; entrypoints resolved independently (ABI unchanged).
stats_patch = ROOT / 'tools/patches/switch-shader-statistics.patch'
stats_marker = 'SHADER_STATS capture creation failed'
stats_source = SDK_REPO / 'sdk/src/graphics/vulkan/pipeline_cache.cpp'
if stats_marker not in stats_source.read_text():
    subprocess.run(['git', 'apply', '--check', str(stats_patch)], cwd=SDK_REPO, check=True)
    subprocess.run(['git', 'apply', str(stats_patch)], cwd=SDK_REPO, check=True)
else:
    for filename, marker in {
        'sdk/include/rex/ui/vulkan/switch_shader_stats.h': 'shader_stats.flag',
        'sdk/src/ui/vulkan/vulkan_device.cpp': 'SHADER_STATS requested=1 enabled=',
        'sdk/src/graphics/vulkan/pipeline_cache.cpp': 'vkGetPipelineExecutableStatisticsKHR',
    }.items():
        if marker not in (SDK_REPO / filename).read_text():
            raise RuntimeError('Incomplete shader statistics patch: ' + filename)
print('Opt-in Switch shader statistics present')

# HANDOFF section 67: cvar vulkan_robust_buffer_access (false = no robustBufferAccess and no
# robustness2 nullDescriptor, so NVK stops bounds-checking every buffer access in shaders).
if "vulkan_robust_buffer_access" not in (SDK_REPO / "sdk/src/ui/vulkan/vulkan_device.cpp").read_text():
    patch = ROOT / "tools/patches/switch-vulkan-robustness-cvar.patch"
    subprocess.run(["git", "apply", "--check", str(patch)], cwd=SDK_REPO, check=True)
    subprocess.run(["git", "apply", str(patch)], cwd=SDK_REPO, check=True)
    print("Added vulkan_robust_buffer_access")

# HANDOFF section 67: vertex-shader NoContraction only on the position slice (cvar
# gpu_vs_contraction_outside_position, default false). Idempotent script, not a git patch: the
# files carry other local patches.
subprocess.run([sys.executable, str(ROOT / "tools/sdk_patch_position_slice.py"),
                str(SDK_REPO / "sdk")], check=True)

# HANDOFF B:94: structured forward jumps in the SPIR-V translator (per-translator opt-in, native
# cvar mercs2_native_structured_jumps). Idempotent script.
subprocess.run([sys.executable, str(ROOT / "tools/sdk_patch_structured_jumps.py"),
                str(SDK_REPO / "sdk")], check=True)

# HANDOFF B:125: cvar thread_delay0_sleep_us (Sleep(0) of a below-normal thread: host sleep in us,
# 0 = yield). The marker check keeps it idempotent.
if "thread_delay0_sleep_us" not in (SDK_REPO / "sdk/src/system/xthread.cpp").read_text():
    patch = ROOT / "tools/patches/switch-thread-delay0-cvar.patch"
    subprocess.run(["git", "apply", "--check", str(patch)], cwd=SDK_REPO, check=True)
    subprocess.run(["git", "apply", str(patch)], cwd=SDK_REPO, check=True)
    print("Added thread_delay0_sleep_us")

# HANDOFF B:130: XGetLanguage returns the user_language cvar (was always English).
if "HANDOFF B:130" not in (SDK_REPO / "sdk/src/kernel/xam/xam_info.cpp").read_text():
    patch = ROOT / "tools/patches/switch-xgetlanguage-cvar.patch"
    subprocess.run(["git", "apply", "--check", str(patch)], cwd=SDK_REPO, check=True)
    subprocess.run(["git", "apply", str(patch)], cwd=SDK_REPO, check=True)
    print("Added XGetLanguage user_language")
