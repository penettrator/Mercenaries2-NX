// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#ifndef MERCENARIES2_IMAGE_REUSE
#define MERCENARIES2_IMAGE_REUSE 0
#endif
#ifndef MERCENARIES2_READY_TEXTURES
#define MERCENARIES2_READY_TEXTURES 0
#endif
#include <vulkan/vulkan.h>
#include <array>
#include <cstdint>
#include <mutex>
#include <unordered_map>
#include <vector>

namespace mercs2::native {
// Only the caller knows GPU completion. RetainCompleted must never receive a
// resource still referenced by a submission. Views are destroyed before entry.
class ImageReuse {
 public:
  using Key = std::array<uint32_t, 13>;
  static constexpr uint64_t kBudget = 16ull << 20;
  static constexpr size_t kMaxIdle = 128, kMaxTracked = 4096;
  struct Stats { uint64_t hits=0, misses=0, retained=0, rejected=0, bytes=0, idle=0; };
  static bool MakeKey(const VkImageCreateInfo& i, Key& key) {
    if (i.pNext || i.queueFamilyIndexCount || i.sharingMode != VK_SHARING_MODE_EXCLUSIVE ||
        i.initialLayout != VK_IMAGE_LAYOUT_UNDEFINED) return false;
    key = {i.flags, uint32_t(i.imageType), uint32_t(i.format), i.extent.width,
           i.extent.height, i.extent.depth, i.mipLevels, i.arrayLayers,
           uint32_t(i.samples), uint32_t(i.tiling), i.usage,
           uint32_t(i.sharingMode), uint32_t(i.initialLayout)};
    return true;
  }
  VkImage Take(const VkImageCreateInfo& info) {
    Key key;
    if (!MakeKey(info, key)) return VK_NULL_HANDLE;
    std::lock_guard<std::mutex> lock(mutex_);
    for (auto it=idle_.begin(); it!=idle_.end(); ++it) {
      auto& r = tracked_.at(*it);
      if (r.key != key) continue;
      VkImage result = *it;
      stats_.bytes -= r.bytes; r.idle = false;
      idle_.erase(it); ++stats_.hits;
      return result;
    }
    ++stats_.misses;
    return VK_NULL_HANDLE;
  }
  void Remember(VkImage image, const VkImageCreateInfo& info, uint64_t bytes) {
    Key key;
    if (!image || bytes > (4ull<<20) || !MakeKey(info,key)) return;
    std::lock_guard<std::mutex> lock(mutex_);
    if (tracked_.size() >= kMaxTracked) return;
    tracked_.emplace(image, Record{key,bytes,0,false});
  }
  bool RetainCompleted(VkImage image, uint64_t frame) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it=tracked_.find(image);
    if (it==tracked_.end() || it->second.idle || idle_.size()>=kMaxIdle ||
        it->second.bytes > kBudget-stats_.bytes) { ++stats_.rejected; return false; }
    auto& r=it->second; r.idle=true; r.frame=frame;
    stats_.bytes+=r.bytes; idle_.push_back(image); ++stats_.retained;
    return true;
  }
  void Forget(VkImage image) {
    std::lock_guard<std::mutex> lock(mutex_);
    // Only used on resources that weren't retained, or after Expire removed it.
    auto it=tracked_.find(image);
    if (it!=tracked_.end() && !it->second.idle) tracked_.erase(it);
  }
  std::vector<VkImage> Expire(uint64_t frame, bool all=false) {
    std::lock_guard<std::mutex> lock(mutex_);
    std::vector<VkImage> result;
    for (auto it=idle_.begin(); it!=idle_.end();) {
      auto& r=tracked_.at(*it);
      if (!all && (frame < r.frame || frame-r.frame < 120)) { ++it; continue; }
      result.push_back(*it); stats_.bytes-=r.bytes;
      tracked_.erase(*it); it=idle_.erase(it);
    }
    return result;
  }
  Stats stats() {
    std::lock_guard<std::mutex> lock(mutex_);
    auto result=stats_; result.idle=idle_.size(); return result;
  }
 private:
  struct Record { Key key; uint64_t bytes,frame; bool idle; };
  std::mutex mutex_;
  std::unordered_map<VkImage, Record> tracked_;
  std::vector<VkImage> idle_;
  Stats stats_;
};
}  // namespace mercs2::native
