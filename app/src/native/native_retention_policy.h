// SPDX-License-Identifier: GPL-3.0-or-later
// Idle retention/invalidation mechanism from Prototype2-NX texture_eviction.h.
#pragma once
#include <cstdint>
#ifndef MERCENARIES2_MATERIAL_RETENTION
#define MERCENARIES2_MATERIAL_RETENTION 0
#endif
namespace mercs2::native {
inline bool IdleMaterialExpired(uint64_t frame, uint64_t last_used, bool pending) {
  return !pending && frame > last_used && frame - last_used > 600;
}
inline bool DiscardUnusedMaterialStream(uint64_t frame, uint64_t last_request,
                                        bool done, bool gpu_image, bool has_views) {
  return done && !gpu_image && !has_views && IdleMaterialExpired(frame, last_request, false);
}
template<class Memo, class Evicted>
void InvalidateRetiredMaterial(Memo& memo, const Evicted& evicted) {
  if (!memo.texture || !evicted.count(memo.texture)) return;
  memo.view = {}; memo.texture = nullptr; memo.valid_until = 0;
}
// After age-only eviction would have removed a material, retaining its GPU
// image must not extend trust in guest memory that wasn't checked meanwhile.
template<class Checked>
void RevalidateInactiveMaterial(uint64_t frame, Checked& checked) {
  if (frame > checked.frame && frame - checked.frame > 600) checked = Checked{};
}
}  // namespace mercs2::native
