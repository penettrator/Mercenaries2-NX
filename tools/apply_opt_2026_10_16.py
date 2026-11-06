#!/usr/bin/env python3
"""Mercenaries 2 optimisation round 2026-10-16 (ported from Prototype 2 + X360_TO_SWITCH_PORTING_GUIDE).

Idempotent text edits of the SDK (reference/masseffect-nx/sdk) and the app sources. Every edit must match
exactly once (or already be applied); line endings (CRLF/LF) of each file are preserved.
Run from anywhere: python3 tools/apply_opt_2026_10_16.py (also called by tools/apply_sdk_patches.py)
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SDK = ROOT / 'reference/masseffect-nx/sdk'


def edit(path, pairs):
    p = Path(path)
    raw = p.read_bytes().decode('utf-8')
    crlf = '\r\n' in raw
    text = raw.replace('\r\n', '\n')
    changed = False
    for old, new in pairs:
        if new in text and (old in new or old not in text):
            continue  # already applied
        n = text.count(old)
        if n != 1:
            sys.exit(f'{p}: anchor found {n} times, refusing to patch:\n{old[:200]}')
        text = text.replace(old, new)
        changed = True
    if changed:
        out = text.replace('\n', '\r\n') if crlf else text
        p.write_bytes(out.encode('utf-8'))
        print('patched', p.relative_to(ROOT))
    else:
        print('already', p.relative_to(ROOT))


# ---------------------------------------------------------------------------------------------
# SDK 1: thread core masks with core 3 (Prototype 2 WORKLOG #100: RexSwitchSetCurrentThreadMask).
# ---------------------------------------------------------------------------------------------
edit(SDK / 'src/core/threading_switch.h', [(
    '/* Which core the calling thread is running on right now. It can only be asked about oneself. */\n'
    'int RexSwitchCurrentCore(void);\n',
    '/* Which core the calling thread is running on right now. It can only be asked about oneself. */\n'
    'int RexSwitchCurrentCore(void);\n'
    '\n'
    '/* Cores this process may use (svcGetInfo CoreMask): 0x7 with the stock hbmenu loader, 0xF when the\n'
    ' * process descriptor allows core 3 (NSP forwarder built with cores 0-3). */\n'
    'uint32_t RexSwitchProcessCoreMask(void);\n'
    '\n'
    '/* The current thread may run only on the cores of `mask` (bits 0-3). Cores outside the process mask are\n'
    ' * dropped. Preferred core: with spread >= 0 the (spread % n)-th core of the mask (round-robin over\n'
    ' * threads), otherwise the current preferred core if it stays in the mask, else the lowest one.\n'
    ' * Returns whether the kernel accepted it (false: nothing usable in the mask). */\n'
    'bool RexSwitchSetCurrentThreadMask(uint32_t mask, int spread);\n')])

edit(SDK / 'src/core/threading_switch.cpp', [(
    'bool RexSwitchPinCurrentThreadToCore(int core) {\n',
    '/*\n'
    ' * Fourth core (Prototype 2 WORKLOG #100-#121): Horizon gives a process the cores of its descriptor\n'
    ' * (NPDM). The hbmenu loader allows cores 0-2; the NSP forwarder of this port allows 0-3. A thread only\n'
    ' * runs where its own mask says, so the guest threads are given the wider mask explicitly.\n'
    ' */\n'
    'uint32_t RexSwitchProcessCoreMask(void) {\n'
    '  static uint32_t cached = 0;\n'
    '  if (!cached) {\n'
    '    u64 mask = 0;\n'
    '    if (R_FAILED(svcGetInfo(&mask, InfoType_CoreMask, CUR_PROCESS_HANDLE, 0)) || !(mask & 0xF)) {\n'
    '      mask = 0x7;\n'
    '    }\n'
    '    cached = uint32_t(mask & 0xF);\n'
    '  }\n'
    '  return cached;\n'
    '}\n'
    '\n'
    'bool RexSwitchSetCurrentThreadMask(uint32_t want, int spread) {\n'
    '  Thread* self = threadGetSelf();\n'
    '  Handle h = (self != nullptr) ? self->handle : CUR_THREAD_HANDLE;\n'
    '  s32 preferred = 0;\n'
    '  u64 mask = 0;\n'
    '  if (R_FAILED(svcGetThreadCoreMask(&preferred, &mask, h))) {\n'
    '    if (h == CUR_THREAD_HANDLE ||\n'
    '        R_FAILED(svcGetThreadCoreMask(&preferred, &mask, CUR_THREAD_HANDLE))) {\n'
    '      return false;\n'
    '    }\n'
    '    h = CUR_THREAD_HANDLE;\n'
    '  }\n'
    '  const u64 use = u64(want) & u64(RexSwitchProcessCoreMask()) & 0xF;\n'
    '  if (!use) return false;\n'
    '  int core = __builtin_ctzll(use);\n'
    '  if (spread >= 0) {\n'
    '    int k = spread % __builtin_popcountll(use);\n'
    '    for (int c = 0; c < 4; ++c) {\n'
    '      if (!((use >> c) & 1)) continue;\n'
    '      if (k-- == 0) {\n'
    '        core = c;\n'
    '        break;\n'
    '      }\n'
    '    }\n'
    '  } else if (preferred >= 0 && preferred < 4 && ((use >> preferred) & 1)) {\n'
    '    core = preferred;\n'
    '  }\n'
    '  return R_SUCCEEDED(svcSetThreadCoreMask(h, core, use));\n'
    '}\n'
    '\n'
    'bool RexSwitchPinCurrentThreadToCore(int core) {\n')])

edit(SDK / 'src/system/xthread.cpp', [
    ('REXCVAR_DEFINE_UINT32(thread_delay0_main_sleep_us, 100, "Kernel",\n'
     '                      "Like thread_delay0_sleep_us, for the game\'s entry-point (main) thread only");\n',
     'REXCVAR_DEFINE_UINT32(thread_delay0_main_sleep_us, 100, "Kernel",\n'
     '                      "Like thread_delay0_sleep_us, for the game\'s entry-point (main) thread only");\n'
     '\n'
     '// Mercenaries 2 optimisation 2026-10-16 (from Prototype 2 WORKLOG #80/#100/#121): thread core masks, so\n'
     '// the fourth core can be used. Core 3 needs a process descriptor that allows it (the NSP forwarder built\n'
     '// by tools/build_forwarder.sh); with the stock hbmenu loader (process mask 0x7) the core-3 bit is dropped\n'
     '// and the layout falls back to cores 0-2. run79: the game used 311 % of 300 % - all three cores full.\n'
     'REXCVAR_DEFINE_UINT32(switch_guest_core_mask, 0, "Kernel",\n'
     '                      "Switch: core mask of the guest threads (job workers, streaming, the game\'s own audio). "\n'
     '                      "0xF = all four cores when core 3 is allowed. 0 = unchanged")\n'
     '    .lifecycle(rex::cvar::Lifecycle::kInitOnly);\n'
     'REXCVAR_DEFINE_UINT32(switch_main_thread_mask, 0, "Kernel",\n'
     '                      "Switch: core mask of the guest \\"Main XThread\\" (the game\'s entry-point thread). "\n'
     '                      "0 = like switch_guest_core_mask")\n'
     '    .lifecycle(rex::cvar::Lifecycle::kInitOnly);\n'
     'REXCVAR_DEFINE_UINT32(switch_host_core_mask, 0, "Kernel",\n'
     '                      "Switch: core mask of the host service XThreads (native GPU ring, VSync, kernel "\n'
     '                      "dispatch) and of the native draw recorder. 0 = unchanged")\n'
     '    .lifecycle(rex::cvar::Lifecycle::kInitOnly);\n'
     'REXCVAR_DEFINE_UINT32(switch_audio_core_mask, 0, "Kernel",\n'
     '                      "Switch: core mask of the host Audio Worker / XMA Decoder threads (0x8 = core 3; "\n'
     '                      "ignored without core 3). 0 = switch_host_core_mask")\n'
     '    .lifecycle(rex::cvar::Lifecycle::kInitOnly);\n'),
    ('  return REX_SWITCH_PRIO_PRESENT;  // GPU Commands, GPU VSync, Kernel Dispatch\n'
     '}\n',
     '  return REX_SWITCH_PRIO_PRESENT;  // GPU Commands, GPU VSync, Kernel Dispatch\n'
     '}\n'
     '\n'
     '// switch_*_core_mask. Guest threads get their preferred core round-robin over their mask, so they do\n'
     '// not all start queued on the process default core (the kernel still migrates them inside the mask).\n'
     'void ApplySwitchCoreMask(bool guest_thread, std::string_view name) {\n'
     '  static std::atomic<uint32_t> next_guest{0};\n'
     '  static std::atomic<bool> logged{false};\n'
     '  uint32_t mask = 0;\n'
     '  int spread = -1;\n'
     '  bool audio_thread = false;\n'
     '  if (guest_thread) {\n'
     '    mask = REXCVAR_GET(switch_guest_core_mask) & 0xFu;\n'
     '    const uint32_t main_mask = REXCVAR_GET(switch_main_thread_mask) & 0xFu;\n'
     '    if (main_mask && name.starts_with("Main XThread")) mask = main_mask;\n'
     '    spread = int(next_guest.fetch_add(1, std::memory_order_relaxed) & 0xFFFF);\n'
     '  } else {\n'
     '    mask = REXCVAR_GET(switch_host_core_mask) & 0xFu;\n'
     '    const uint32_t audio = REXCVAR_GET(switch_audio_core_mask) & 0xFu;\n'
     '    if (audio && (name.starts_with("Audio Worker") || name.starts_with("XMA Decoder"))) {\n'
     '      audio_thread = true;\n'
     '      if (RexSwitchSetCurrentThreadMask(audio, -1)) mask = 0;  // done; else the host mask\n'
     '    }\n'
     '  }\n'
     '  if (mask) (void)RexSwitchSetCurrentThreadMask(mask, spread);\n'
     '  if (!logged.exchange(true, std::memory_order_relaxed)) {\n'
     '    REXSYS_INFO("[sched] process core mask 0x{:X}; thread masks: guest 0x{:X}, main 0x{:X}, host 0x{:X}, "\n'
     '                "audio 0x{:X} (0 = unchanged)",\n'
     '                RexSwitchProcessCoreMask(), REXCVAR_GET(switch_guest_core_mask),\n'
     '                REXCVAR_GET(switch_main_thread_mask), REXCVAR_GET(switch_host_core_mask),\n'
     '                REXCVAR_GET(switch_audio_core_mask));\n'
     '  }\n'
     '  (void)audio_thread;\n'
     '}\n'),
    ('    RexSwitchSetCurrentThreadPriority(SwitchPriorityFor(guest_thread_, thread_name_));\n'
     '#endif\n'
     '    runtime::ThreadState::Bind(thread_state_.get());\n',
     '    RexSwitchSetCurrentThreadPriority(SwitchPriorityFor(guest_thread_, thread_name_));\n'
     '    ApplySwitchCoreMask(guest_thread_, thread_name_);\n'
     '#endif\n'
     '    runtime::ThreadState::Bind(thread_state_.get());\n'),
])

# ---------------------------------------------------------------------------------------------
# SDK 2: achievement popups off by default on Switch (guide, Prototype 2 2026-10-15): the toast window
# registers an ImGui dialog for the whole session and can move presentation onto the UI thread/mailbox.
# ---------------------------------------------------------------------------------------------
edit(SDK / 'src/ui/rex_app.cpp', [
    ('namespace rex {\n',
     '#if REX_PLATFORM_SWITCH\n'
     'REXCVAR_DEFINE_BOOL(achievement_notifications, false, "UI",\n'
     '                    "Show achievement popups (requires restart)")\n'
     '    .lifecycle(rex::cvar::Lifecycle::kRequiresRestart);\n'
     '#else\n'
     'REXCVAR_DEFINE_BOOL(achievement_notifications, true, "UI",\n'
     '                    "Show achievement popups (requires restart)")\n'
     '    .lifecycle(rex::cvar::Lifecycle::kRequiresRestart);\n'
     '#endif\n'
     '\n'
     'namespace rex {\n'),
    ('  if (!imgui_drawer_ || !immediate_drawer_ || !runtime_) {\n',
     '  if (!REXCVAR_GET(achievement_notifications) || !imgui_drawer_ || !immediate_drawer_ || !runtime_) {\n'),
    ('    if (achievement_notification_listener_ == 0 && runtime_ && runtime_->kernel_state()) {\n',
     '    if (REXCVAR_GET(achievement_notifications) && achievement_notification_listener_ == 0 &&\n'
     '        runtime_ && runtime_->kernel_state()) {\n'),
])

# ---------------------------------------------------------------------------------------------
# SDK 3: no ts (temperature) session for the whole game (Prototype 2 runs 5-6: with sys-clk/hoc-clk an
# open ts session coincided with pcv/ptm crashes under load). Only the profiler's temperature column.
# ---------------------------------------------------------------------------------------------
edit(SDK / 'src/ui/switch_perf.cpp', [(
    '      if (R_SUCCEEDED(tsInitialize())) {\n',
    '      // Off (Prototype 2 runs 5-6): an open ts session for the whole game coincided with the overclock\n'
    '      // sysmodule crashing pcv/ptm under load. The clock sysmodule owns the sensors.\n'
    '      if (false && R_SUCCEEDED(tsInitialize())) {\n')])

# ---------------------------------------------------------------------------------------------
# App 1: native renderer - event-driven draw recorder queue (Prototype 2 WORKLOG #70, hardware-tested
# run49), recorder core mask from switch_host_core_mask, range-hash table pruned instead of cleared
# (WORKLOG #97/#103).
# ---------------------------------------------------------------------------------------------
NR = ROOT / 'app/src/native/native_renderer.cpp'
edit(NR, [
    ('#include "native_resolve_probe.h"\n#include <rex/thread.h>\n',
     '#include "native_resolve_probe.h"\n#include "blocking_record_queue.h"\n#include <rex/thread.h>\n'),
    ('REXCVAR_DEFINE_BOOL(gpu_specialize_texture_signs, false, "Mercs2",\n',
     'REXCVAR_DECLARE(uint32_t, switch_host_core_mask);  // SDK xthread.cpp\n'
     '#if defined(__SWITCH__)\n'
     'extern "C" bool RexSwitchSetCurrentThreadMask(uint32_t mask, int spread);  // SDK threading_switch\n'
     '#endif\n'
     'REXCVAR_DEFINE_BOOL(gpu_specialize_texture_signs, false, "Mercs2",\n'),
    ('  static constexpr uint32_t kRecordQueueSize = 4096;\n'
     '  std::unique_ptr<DrawCommand[]> record_queue;\n'
     '  std::atomic<uint32_t> record_head{0};\n'
     '  std::atomic<uint32_t> record_tail{0};\n'
     '  std::atomic<bool> record_stop{false};\n'
     '  std::atomic<bool> record_sleeping{false};\n'
     '  std::mutex record_mutex;\n'
     '  std::condition_variable record_cv;\n'
     '  std::thread record_thread;\n'
     '  bool record_threaded = false;\n'
     '\n'
     '  void WakeRecorder() {\n'
     '    if (record_sleeping.load(std::memory_order_seq_cst)) {\n'
     '      std::lock_guard<std::mutex> lock(record_mutex);\n'
     '      record_cv.notify_one();\n'
     '    }\n'
     '  }\n'
     '\n'
     '  void RecordThread() {\n'
     '    rex::thread::set_current_thread_name("GPU record");\n'
     '#if defined(__SWITCH__)\n'
     '    svcSetThreadPriority(CUR_THREAD_HANDLE, 0x2C);\n'
     '    // Off the ring thread\'s core.\n'
     '    svcSetThreadCoreMask(CUR_THREAD_HANDLE, 1, 0x3);\n'
     '#endif\n'
     '    uint32_t idle = 0;\n'
     '    while (true) {\n'
     '      uint32_t tail = record_tail.load(std::memory_order_relaxed);\n'
     '      if (tail != record_head.load(std::memory_order_acquire)) {\n'
     '        ExecuteDrawCommand(record_queue[tail % kRecordQueueSize]);\n'
     '        record_tail.store(tail + 1, std::memory_order_release);\n'
     '        idle = 0;\n'
     '        continue;\n'
     '      }\n'
     '      if (record_stop.load(std::memory_order_acquire)) return;\n'
     '      // Briefly: spinning longer took cores from the game\'s own threads.\n'
     '      if (++idle < 16) {\n'
     '        std::this_thread::yield();\n'
     '        continue;\n'
     '      }\n'
     '      std::unique_lock<std::mutex> lock(record_mutex);\n'
     '      record_sleeping.store(true, std::memory_order_seq_cst);\n'
     '      if (record_head.load(std::memory_order_seq_cst) == tail &&\n'
     '          !record_stop.load(std::memory_order_acquire)) {\n'
     '        record_cv.wait_for(lock, std::chrono::milliseconds(2));\n'
     '      }\n'
     '      record_sleeping.store(false, std::memory_order_relaxed);\n'
     '      idle = 0;\n'
     '    }\n'
     '  }\n'
     '\n'
     '  void SubmitDraw(const DrawCommand& d) {\n'
     '    if (!record_threaded) {\n'
     '      ExecuteDrawCommand(d);\n'
     '      return;\n'
     '    }\n'
     '    uint32_t head = record_head.load(std::memory_order_relaxed);\n'
     '    while (head - record_tail.load(std::memory_order_acquire) >= kRecordQueueSize) {\n'
     '      WakeRecorder();\n'
     '      std::this_thread::yield();\n'
     '    }\n'
     '    record_queue[head % kRecordQueueSize] = d;\n'
     '    record_head.store(head + 1, std::memory_order_seq_cst);\n'
     '    // In batches: the recording thread kept up draw by draw, slept between\n'
     '    // them, and waking it for every draw (a lock and a system call) showed as\n'
     '    // 6% of this thread in lock contention. It is also woken when this\n'
     '    // thread is about to wait for the game (KickRecorder), and anything\n'
     '    // recording into the command buffer drains the queue first.\n'
     '    if (head + 1 - record_tail.load(std::memory_order_relaxed) >= kRecordBatch) WakeRecorder();\n'
     '  }\n'
     '  static constexpr uint32_t kRecordBatch = 32;\n'
     '\n'
     '  void KickRecorder() {\n'
     '    if (record_threaded &&\n'
     '        record_tail.load(std::memory_order_acquire) != record_head.load(std::memory_order_relaxed)) {\n'
     '      WakeRecorder();\n'
     '    }\n'
     '  }\n'
     '\n'
     '  void DrainRecorder() {\n'
     '    if (!record_threaded) return;\n'
     '    uint32_t head = record_head.load(std::memory_order_relaxed);\n'
     '    if (record_tail.load(std::memory_order_acquire) == head) return;\n'
     '    uint64_t start = NowNs();\n'
     '    uint32_t spins = 0;\n'
     '    while (record_tail.load(std::memory_order_acquire) != head) {\n'
     '      WakeRecorder();\n'
     '      if (++spins > 32) std::this_thread::yield();\n'
     '    }\n'
     '    frame_drain_wait_ns += NowNs() - start;\n'
     '  }\n',
     '  static constexpr uint32_t kRecordQueueSize = 4096;\n'
     '  // 2026-10-16 (Prototype 2 WORKLOG #70/#71, hardware-tested): an event-driven queue. The old one\n'
     '  // spun (16 yields, then 2 ms timed waits; a full queue and DrainRecorder yielded in a loop) on cores\n'
     '  // the game\'s threads need: run79 had all three cores full. Work is woken in batches of 32 draws,\n'
     '  // by KickRecorder before the ring thread waits for the game, and by DrainRecorder.\n'
     '  BlockingRecordQueue<DrawCommand, kRecordQueueSize, 32> record_work;\n'
     '  std::thread record_thread;\n'
     '  bool record_threaded = false;\n'
     '\n'
     '  void WakeRecorder() { record_work.WakeConsumer(); }\n'
     '\n'
     '  void RecordThread() {\n'
     '    rex::thread::set_current_thread_name("GPU record");\n'
     '#if defined(__SWITCH__)\n'
     '    svcSetThreadPriority(CUR_THREAD_HANDLE, 0x2C);\n'
     '    {\n'
     '      // switch_host_core_mask (cores of the host service threads) when set; before: cores 0-1.\n'
     '      const uint32_t host_mask = REXCVAR_GET(switch_host_core_mask) & 0xFu;\n'
     '      if (!host_mask || !RexSwitchSetCurrentThreadMask(host_mask, -1)) {\n'
     '        svcSetThreadCoreMask(CUR_THREAD_HANDLE, 1, 0x3);\n'
     '      }\n'
     '    }\n'
     '#endif\n'
     '    while (const DrawCommand* draw = record_work.FrontOrWait()) {\n'
     '      ExecuteDrawCommand(*draw);\n'
     '      record_work.CompleteFront();\n'
     '    }\n'
     '  }\n'
     '\n'
     '  void SubmitDraw(const DrawCommand& d) {\n'
     '    if (!record_threaded) {\n'
     '      ExecuteDrawCommand(d);\n'
     '      return;\n'
     '    }\n'
     '    if (!record_work.Push(d)) {\n'
     '      ExecuteDrawCommand(d);  // closed (shutdown): never lose a draw\n'
     '    }\n'
     '  }\n'
     '  // In batches: the recording thread kept up draw by draw, slept between\n'
     '  // them, and waking it for every draw (a lock and a system call) showed as\n'
     '  // 6% of this thread in lock contention. It is also woken when this\n'
     '  // thread is about to wait for the game (KickRecorder), and anything\n'
     '  // recording into the command buffer drains the queue first.\n'
     '  void KickRecorder() {\n'
     '    if (record_threaded && record_work.Pending()) WakeRecorder();\n'
     '  }\n'
     '\n'
     '  void DrainRecorder() {\n'
     '    if (!record_threaded || !record_work.Pending()) return;\n'
     '    const uint64_t start = NowNs();\n'
     '    record_work.Drain();\n'
     '    frame_drain_wait_ns += NowNs() - start;\n'
     '  }\n'),
    ('    record_queue = std::make_unique<DrawCommand[]>(kRecordQueueSize);\n'
     '    record_thread = std::thread([this]() { RecordThread(); });\n',
     '    record_thread = std::thread([this]() { RecordThread(); });\n'),
    ('    DrainRecorder();\n'
     '    record_stop.store(true, std::memory_order_release);\n'
     '    {\n'
     '      std::lock_guard<std::mutex> lock(record_mutex);\n'
     '      record_cv.notify_all();\n'
     '    }\n'
     '    record_thread.join();\n',
     '    DrainRecorder();\n'
     '    record_work.Close();\n'
     '    record_thread.join();\n'),
    ('  if (vertex_hashes.size() > 65536) {\n'
     '    vertex_hashes.clear();\n'
     '  }\n',
     '  if (vertex_hashes.size() > 65536) {\n'
     '    // 2026-10-16 (Prototype 2 WORKLOG #97/#103): dropping everything every few seconds (ranges in\n'
     '    // per-frame dynamic allocations add ~1000 keys a frame) reset every range\'s change history, so\n'
     '    // the sampled/unique-hash shortcuts restarted from zero. Keep what was used in the last frames.\n'
     '    const uint64_t now_frame = frame;\n'
     '    vertex_hashes.retain([now_frame](const VertexHash& v) {\n'
     '      if (v.frame == UINT64_MAX || v.frame + 16 < now_frame) return false;\n'
     '      return v.frame + 2 >= now_frame || v.changes > 0 || v.detector.unchanged() > 0 ||\n'
     '             v.detector.changes() > 0;\n'
     '    });\n'
     '    if (vertex_hashes.size() > 49152) vertex_hashes.clear();\n'
     '  }\n'),
])

edit(ROOT / 'app/src/native/native_hash.h', [
    ('    checked_ = true;\n'
     '    return hash;\n'
     '  }\n'
     '\n'
     ' private:\n'
     '  static constexpr size_t kSamples = 8;\n',
     '    checked_ = true;\n'
     '    return hash;\n'
     '  }\n'
     '\n'
     '  // Times the content was found changed, exact checks in a row that found it unchanged (both\n'
     '  // saturating), and the last hash (Prototype 2 WORKLOG #96/#97).\n'
     '  uint32_t changes() const { return changes_; }\n'
     '  uint32_t unchanged() const { return unchanged_; }\n'
     '  uint64_t last_hash() const { return hash_; }\n'
     '\n'
     ' private:\n'
     '  static constexpr size_t kSamples = 8;\n'),
    ('  void clear() {\n'
     '    std::fill(keys_.begin(), keys_.end(), kEmpty);\n'
     '    size_ = 0;\n'
     '  }\n',
     '  void clear() {\n'
     '    std::fill(keys_.begin(), keys_.end(), kEmpty);\n'
     '    size_ = 0;\n'
     '  }\n'
     '\n'
     '  // Keeps only the entries for which keep(value) is true (rebuilds the table at the same capacity).\n'
     '  template <typename F>\n'
     '  void retain(F&& keep) {\n'
     '    std::vector<uint64_t> old_keys = std::move(keys_);\n'
     '    std::vector<V> old_values = std::move(values_);\n'
     '    keys_.assign(old_keys.size(), kEmpty);\n'
     '    values_.assign(old_keys.size(), V());\n'
     '    size_ = 0;\n'
     '    for (size_t i = 0; i < old_keys.size(); ++i) {\n'
     '      if (old_keys[i] != kEmpty && keep(old_values[i])) (*this)[old_keys[i]] = std::move(old_values[i]);\n'
     '    }\n'
     '  }\n'),
])
print('done')
