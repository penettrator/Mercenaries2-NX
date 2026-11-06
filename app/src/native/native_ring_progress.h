// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <cstdint>
#ifndef MERCENARIES2_RING_WRITEBACK
#define MERCENARIES2_RING_WRITEBACK 0
#endif
namespace mercs2::native {
// Reader positions are modulo a power-of-two ring. Publish only after Packet
// finishes consuming/copying its payload; never acknowledge a partial packet.
inline bool RingProgressReached(uint32_t previous, uint32_t current,
                                uint32_t mask, uint32_t threshold) {
  return threshold && ((current - previous) & mask) >= threshold;
}
}  // namespace mercs2::native
