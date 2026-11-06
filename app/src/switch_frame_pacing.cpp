// Mercenaries 2 (Switch): the guest D3D's frame pacing and its wait for GPU ring space.
// Ported 2026-10-16 from Prototype 2 (project/src/switch_sim_priority.cpp, WORKLOG #81, #82, #91): both games
// link the same Xbox 360 D3D library, so the functions are the same code at other addresses.
//
// 1. Flip scheduling (sub_825A0130, hook inserted by tools/prepare_switch_codegen.py). At each swap the game's
//    D3D picks the vblank its flip happens at: last flip + present interval, or one vblank later still when
//    the swap arrives "late" in the current vblank period. Queued flips are performed by the vblank interrupt,
//    and the next frame waits for them, so 35-45 ms of work became 50 ms (or 67) frames: run75-79 logged
//    hundreds of 50-52 ms frames with the GPU ring idle for 15-22 ms in each. Prototype 2 measured the same
//    thing (frame times of exactly 50/67/83 ms, a CPU overclock gave 0 fps) and gained ~25 % in gameplay.
//    The screen itself is paced by the host presenter (Vulkan FIFO), so the guest flip can happen at once:
//    target = max(last flip + max(interval, mercs2_min_present_interval), now). Faster frames still wait for
//    their vblank (a steady 30 fps cap with 2), slower ones are no longer rounded up to the next vblank.
// 2. The wait for GPU command-buffer space (sub_82599EF0 loops on sub_82590C80: 32 db16cyc pauses, a GPU hang
//    check, returns 1 = keep waiting). On the console this spins a hardware thread; here it spun a whole core
//    the job workers needed (run70: "game spins on command-buffer space"). A short real sleep instead.
#include "generated/default/mercenaries2_pch.h"

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <thread>

#include <rex/cvar.h>
#include <rex/logging.h>

REXCVAR_DEFINE_BOOL(mercs2_immediate_flip, false, "Mercs2",
                    "Flip the guest's frontbuffer at the swap instead of at a later vblank (the screen is paced "
                    "by the host presenter); frames faster than mercs2_min_present_interval still wait. false = "
                    "the game's own present interval and late-swap wait")
    .lifecycle(rex::cvar::Lifecycle::kInitOnly);

REXCVAR_DEFINE_UINT32(mercs2_min_present_interval, 2, "Mercs2",
                      "With mercs2_immediate_flip: a frame faster than this many vblanks still waits for that "
                      "vblank (2 = at most 30 fps, 1 = 60)")
    .lifecycle(rex::cvar::Lifecycle::kInitOnly);

REXCVAR_DEFINE_UINT32(mercs2_ring_wait_sleep_us, 0, "Mercs2",
                      "Sleep per step of the game's wait for GPU command-buffer space, in microseconds (0 = spin "
                      "as on the Xbox 360)");

extern "C" uint32_t mercs2_flip_target(uint32_t target, uint32_t now, uint32_t interval, uint32_t threshold,
                                       uint32_t last_flip) {
  static uint32_t swaps = 0, queued = 0, capped = 0, last_interval = 0xFFFFFFFFu, last_threshold = 0xFFFFFFFFu;
  ++swaps;
  if (target != now) ++queued;
  if (interval != last_interval || threshold != last_threshold) {
    last_interval = interval;
    last_threshold = threshold;
    REXLOG_INFO("[flip] present interval {} late threshold {}% (target {} now {} last {})", interval, threshold,
                target, now, last_flip);
  }
  uint32_t result = target;
  if (REXCVAR_GET(mercs2_immediate_flip)) {
    const uint32_t cap = last_flip + std::max<uint32_t>(interval, REXCVAR_GET(mercs2_min_present_interval));
    if (int32_t(cap - now) > 0) {
      result = cap;  // faster than the cap: flip at that vblank (frame rate limit, even pacing)
      ++capped;
    } else {
      result = now;  // slower: at once, not rounded up to the next vblank
    }
  }
  if (swaps % 600 == 0) {
    REXLOG_INFO("[flip] last 600 swaps: {} the game queued for a later vblank, {} held by the frame cap{}", queued,
                capped, REXCVAR_GET(mercs2_immediate_flip) ? "" : " (immediate flip off)");
    queued = 0;
    capped = 0;
  }
  return result;
}

REX_EXTERN(__imp__sub_82590C80);
extern "C" REX_FUNC(sub_82590C80) {
  __imp__sub_82590C80(ctx, base);
  const uint32_t us = REXCVAR_GET(mercs2_ring_wait_sleep_us);
  if (ctx.r3.u32 == 1 && us) {
    std::this_thread::sleep_for(std::chrono::microseconds(us));
  }
}
