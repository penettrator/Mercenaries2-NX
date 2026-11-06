// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <cstdint>
namespace mercs2::lookup {
// Exact PPC GPR effects, read order and loop barriers are retained. Only registers
// which this function never changes are kept as immutable native values.
template<class Context, class Load, class Barrier, class Trap>
inline void Find(Context& c, Load load, Barrier barrier, Trap trap) {
  const uint32_t table=c.r3.u32, key=c.r4.u32;
  c.r11.u64=load(table);
  if (!c.r11.u32) {c.r3.s64=-1;return;}
  if (c.r5.s32<0) {
    c.r11.u64=load(table+12);
    c.r10.u64=load(table+8);
    c.r9.s64=int64_t(c.r11.s32)*int64_t(int32_t(key));
    c.r8.u64=c.r10.u32 ? c.r9.u32/c.r10.u32 : 0;
    if (!c.r10.u32) trap();
    c.r7.s64=int64_t(c.r8.s32)*int64_t(c.r10.s32);
    c.r5.u64=c.r9.u64-c.r7.u64;
  }
  const uint32_t indices=load(table+20);c.r10.u64=indices;
  uint64_t slot=c.r5.u64;
  c.r11.u64=uint32_t(slot)<<2;
  uint32_t entry=load(indices+c.r11.u32);c.r11.u64=entry;
  if (entry==UINT32_MAX) {c.r3.s64=-1;return;}
  const uint32_t keys=load(table+16);c.r9.u64=keys;
  for (;;) {
    barrier();
    c.r11.u64=entry<<2;
    c.r8.u64=load(keys+c.r11.u32);
    if (c.r8.u32==key) {c.r3.u64=slot;return;}
    c.r8.u64=load(table+8);
    c.r11.u64=slot+1;
    c.r7.u64=c.r11.u64-c.r8.u64;
    c.r6.s64=c.r7.s32>>31;
    slot=c.r6.u64&c.r11.u64;c.r5.u64=slot;
    c.r11.u64=uint32_t(slot)<<2;
    entry=load(indices+c.r11.u32);c.r11.u64=entry;
    if (entry==UINT32_MAX) {c.r3.s64=-1;return;}
  }
}
template<class Context, class Load, class Barrier, class Trap>
inline void Slot(Context& c, Load load, Barrier barrier, [[maybe_unused]] Trap trap) {
  const uint32_t table=c.r3.u32,key=c.r4.u32;
  c.r10.u64=load(table+8);
  if (!c.r10.u32) {c.r3.s64=-1;return;}
  const uint32_t count=c.r10.u32;
  c.r11.u64=load(table+20);
  if (!count) trap();
  const uint32_t keys=load(table+28);c.r9.u64=keys;
  c.r8.s64=int64_t(c.r11.s32)*int64_t(int32_t(key));
  c.r7.u64=c.r8.u32/count;
  c.r6.s64=int64_t(c.r7.s32)*int64_t(c.r10.s32);
  uint64_t slot=c.r8.u64-c.r6.u64;c.r3.u64=slot;
  c.r5.u64=uint32_t(slot)<<2;
  uint32_t value=load(keys+c.r5.u32);c.r11.u64=value;
  if (value==key) return;
  for (;;) {
    barrier();
    if (value==UINT32_MAX) return;
    c.r11.u64=slot+1;
    c.r8.u64=c.r11.u64-count;
    c.r7.s64=c.r8.s32>>31;
    slot=c.r7.u64&c.r11.u64;c.r3.u64=slot;
    c.r6.u64=uint32_t(slot)<<2;
    value=load(keys+c.r6.u32);c.r11.u64=value;
    if (value==key) return;
  }
}
}  // namespace mercs2::lookup
