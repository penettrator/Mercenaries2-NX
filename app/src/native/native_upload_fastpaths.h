// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <algorithm>
#include <bit>
#include <cstdint>
#include <cstring>

namespace mercs2::native {

// Exact index conversion, with endian/reset decisions outside the element loop.
// The unsupported 16-bit swap modes retain the SDK's original assert/fallback.
template<class T, uint32_t Endian, bool Reset>
inline void UploadIndices(const uint8_t* source, uint8_t* dest, uint32_t count,
                          uint32_t reset_index) {
  for (uint32_t i = 0; i < count; ++i) {
    T value;
    std::memcpy(&value, source + size_t(i) * sizeof(T), sizeof(T));
    if constexpr (Endian == 1) {
      if constexpr (sizeof(T) == 2) value = std::byteswap(value);
      else value = T(((value << 8) & 0xFF00FF00u) | ((value >> 8) & 0x00FF00FFu));
    } else if constexpr (Endian == 2) value = std::byteswap(value);
    else if constexpr (Endian == 3) value = T((value >> 16) | (value << 16));
    if constexpr (Reset) {
      if (uint32_t(value) == reset_index) value = T(~T(0));
    }
    std::memcpy(dest + size_t(i) * sizeof(T), &value, sizeof(T));
  }
}

template<class T, bool Reset>
inline bool UploadIndexEndian(const uint8_t* source, uint8_t* dest, uint32_t count,
                               uint32_t endian, uint32_t reset_index) {
  switch (endian) {
    case 0: UploadIndices<T, 0, Reset>(source, dest, count, reset_index); return true;
    case 1: UploadIndices<T, 1, Reset>(source, dest, count, reset_index); return true;
    case 2:
      if constexpr (sizeof(T) == 4) { UploadIndices<T, 2, Reset>(source, dest, count, reset_index); return true; }
      return false;
    case 3:
      if constexpr (sizeof(T) == 4) { UploadIndices<T, 3, Reset>(source, dest, count, reset_index); return true; }
      return false;
    default: return false;
  }
}

inline bool TryUploadIndices(const uint8_t* source, uint8_t* dest, uint32_t count,
                             uint32_t width, uint32_t endian, bool reset, uint32_t reset_index) {
  // Preserve the already optimal memcpy path too.
  if (!reset && endian == 0 && (width == 2 || width == 4)) {
    std::memcpy(dest, source, size_t(count) * width);
    return true;
  }
  if (width == 2) return reset ? UploadIndexEndian<uint16_t, true>(source, dest, count, endian, reset_index)
                              : UploadIndexEndian<uint16_t, false>(source, dest, count, endian, reset_index);
  if (width == 4) return reset ? UploadIndexEndian<uint32_t, true>(source, dest, count, endian, reset_index)
                              : UploadIndexEndian<uint32_t, false>(source, dest, count, endian, reset_index);
  return false;
}

struct UploadStamp {
  uint64_t hash = 0, epoch = 0;
  bool fresh = false;
};

// Adapted from Prototype2 DynamicBufferStamp, with the existing Mercs2 detector
// left intact. Fresh copies do not depend on a sampled/synthetic content hash.
// Per-range cadence spreads exact rechecks instead of one global frame & 15.
class DynamicUploadStamp {
 public:
  template<class Hash>
  UploadStamp Check(uint64_t frame, bool exact, uint32_t phase, Hash&& hash) {
    if (valid_ && frame_ == frame) return stamp_;
    valid_ = true; frame_ = frame;
    if (!exact && changes_ >= 4 && ((frame + phase) & 15)) {
      stamp_ = {0, frame, true};
    } else {
      const uint64_t content = hash();
      changes_ = content != content_ ? std::min(changes_ + 1, 8u) : 0;
      content_ = content;
      stamp_ = {content, 0, false};
    }
    return stamp_;
  }
 private:
  uint64_t frame_ = 0, content_ = 0;
  uint32_t changes_ = 0;
  bool valid_ = false;
  UploadStamp stamp_{};
};

// Mercs2 GetViewUncached consults resolve destinations only at base_page<<12,
// plus the depth-words tag. Unknown entries are always invalidated. Revisit if
// composite/range-based resolve lookup is added; this is NOT P2's wider contract.
template<class Map>
void InvalidateResolveMemo(Map& memo, uint32_t address, uint64_t& dropped, uint64_t& kept) {
  const uint32_t base = address & ~uint32_t(1);
  memo.for_each_value([&](auto& entry) {
    if (!entry.view) return;
    // Pending/null/resolve answers can change as uploads finish even when
    // their base is unrelated. Keep only ready guest textures: their content
    // is independently checked at most once per frame (Impl::checked).
    if (!entry.texture || entry.resolve_address == UINT32_MAX || entry.resolve_address == base) {
      entry.view = {};
      ++dropped;
    } else ++kept;
  });
}

}  // namespace mercs2::native
