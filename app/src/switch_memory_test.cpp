// Opt-in preparation of watched command pages in the project-local emulator.
// Original translated functions still emit all guest commands.
#include "generated/default/mercenaries2_funcs.h"
#include <rex/hook.h>
#if defined(__SWITCH__)
#include <atomic>
#include <algorithm>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include "guest_memory_switch.h"
extern "C" bool (*g_rex_hot_read_hook)(uint64_t);
static void PrepareEncoderOutput(uint8_t* base,uint32_t object) {
  uint32_t at=0,end=0;
  const void* shadow=RexGmShadowFor(reinterpret_cast<uint64_t>(base)+object+48);
  if(!shadow)return;
  std::memcpy(&at,shadow,4);std::memcpy(&end,static_cast<const uint8_t*>(shadow)+4,4);
  at=__builtin_bswap32(at);end=__builtin_bswap32(end);
  if(!at)return;
  // The logical end is a refill threshold, not an allocation boundary: the
  // original device routines also emit terminating words in its reserved tail.
  // Each set mask bit emits one dword; at most 32 runs add one header each.
  // QueryProtect below prevents preparation of uncommitted / NOACCESS pages.
  // Other device routines append packets between these hooks. Prepare the
  // declared remaining command range as well, with a bounded diagnostic walk.
  const uint64_t remaining=end>at && uint64_t(end)-at<=0x100000 ? end : at;
  const uint64_t limit=std::min<uint64_t>(0x100000000ULL,remaining+4+96*4);
  for(uint64_t page=uint64_t(at)&~uint64_t(0xFFF);page<limit;page+=0x1000) {
    const uint64_t host=reinterpret_cast<uint64_t>(base)+page;
    size_t length=0x1000;RexGmAccess access=REX_GM_NONE;
    const bool queried=RexGmQueryProtect(reinterpret_cast<uint8_t*>(host),&length,&access);
    bool restored=false;
    if(queried && access==REX_GM_READ && g_rex_hot_read_hook)
      restored=g_rex_hot_read_hook(host); // SDK conservatively invalidates and remaps the page.
    else if(queried && access==REX_GM_WRITE)
      restored=RexGmFaultIn(host);
    if(access!=REX_GM_WRITE) if(FILE* f=std::fopen("/switch/Mercenaries2/encoder-trace.log","a")) {
      std::fprintf(f,"output page=%08lX queried=%d access=%u prepared=%d\n",page,queried,unsigned(access),restored);
      std::fclose(f);
    }
  }
}
REX_HOOK_RAW(sub_825AA7C0) {
  static const bool enabled = [] {
    std::error_code error;
    return std::filesystem::exists(
        "/switch/Mercenaries2/emulator_memory_test.flag", error);
  }();
  static std::atomic_uint calls{0};
  const unsigned call = enabled ? calls.fetch_add(1, std::memory_order_relaxed) : 0;
  if (enabled && (call < 128 || !ctx.r4.u64)) {
    REXLOG_INFO("Encoder entry: call={}, caller={:08X}, source={:08X}, mask={:016X}",
                call, uint32_t(ctx.lr), ctx.r6.u32, ctx.r4.u64);
    size_t length = 0x1000;
    RexGmAccess access = REX_GM_NONE;
    const bool queried = RexGmQueryProtect(base + ctx.r6.u32, &length, &access);
    REXLOG_INFO("Encoder source: queried={}, access={}", queried, unsigned(access));
  }
  if (enabled && call < 128) {
    uint32_t write_at=0, write_end=0;
    if (const void* shadow=RexGmShadowFor(reinterpret_cast<uint64_t>(base)+ctx.r3.u32+48)) {
      std::memcpy(&write_at,shadow,4);
      std::memcpy(&write_end,static_cast<const uint8_t*>(shadow)+4,4);
      write_at=__builtin_bswap32(write_at);write_end=__builtin_bswap32(write_end);
    }
    if (FILE* f=std::fopen("/switch/Mercenaries2/encoder-trace.log","a")) {
      std::fprintf(f,"enter call=%u lr=%08X object=%08X source=%08X mask=%016lX index=%016lX write=%08X end=%08X\n",
                   call,uint32_t(ctx.lr),ctx.r3.u32,ctx.r6.u32,ctx.r4.u64,ctx.r5.u64,write_at,write_end);
      std::fclose(f);
    }
  }
  if(enabled)PrepareEncoderOutput(base,ctx.r3.u32);
  __imp__sub_825AA7C0(ctx, base);
  if (enabled && call < 128) {
    REXLOG_INFO("Encoder return: call={}", call);
    if(FILE* f=std::fopen("/switch/Mercenaries2/encoder-trace.log","a")) {
      std::fprintf(f,"return call=%u\n",call);std::fclose(f);
    }
  }
}
// Capacity handling must preserve the PPC nonvolatile register bank.
REX_HOOK_RAW(sub_825AA170) {
  const uint64_t before[] = {ctx.r27.u64, ctx.r28.u64, ctx.r29.u64, ctx.r30.u64, ctx.r31.u64, ctx.r1.u64};
  __imp__sub_825AA170(ctx, base);
  const uint64_t after[] = {ctx.r27.u64, ctx.r28.u64, ctx.r29.u64, ctx.r30.u64, ctx.r31.u64, ctx.r1.u64};
  static const bool enabled = [] {
    std::error_code error;
    return std::filesystem::exists("/switch/Mercenaries2/emulator_memory_test.flag", error);
  }();
  if (enabled) for (unsigned i=0;i<6;i++) {
    if (before[i] != after[i])
      REXLOG_ERROR("Encoder capacity ABI mismatch: register={}, before={:016X}, after={:016X}",
                   i < 5 ? 27+i : 1, before[i], after[i]);
  }
}
static bool CommandBufferTestEnabled() {
  static const bool enabled=[] {
    std::error_code error;
    return std::filesystem::exists("/switch/Mercenaries2/emulator_memory_test.flag",error);
  }();
  return enabled;
}
extern "C" uint8_t* mercenaries2_EmulatorMemoryAddress(uint8_t* base,uint32_t address,size_t bytes,bool write) {
  uint8_t* window=base+address;
  if(!CommandBufferTestEnabled() || !bytes || uint64_t(address)+bytes>0x100000000ULL)return window;
  const uint64_t first=reinterpret_cast<uint64_t>(window);
  const uint64_t last=first+bytes-1;
  for(uint64_t page=first&~uint64_t(0xFFF);page<=last;page+=0x1000) {
    size_t length=0x1000;RexGmAccess access=REX_GM_NONE;
    if(!RexGmQueryProtect(reinterpret_cast<uint8_t*>(page),&length,&access) || access==REX_GM_NONE)return window;
    if(write && access==REX_GM_READ) {
      // READ on these physical aliases is the SDK GPU write watch. Do not
      // bypass a genuine read-only guest allocation or a missing callback.
      if(address<0xA0000000u || address>=0xE0000000u || !g_rex_hot_read_hook || !g_rex_hot_read_hook(page))return window;
    }
  }
  auto* shadow=static_cast<uint8_t*>(RexGmShadowFor(first));
  if(!shadow || RexGmShadowFor(last)!=shadow+bytes-1)return window;
  return shadow;
}
static void TraceDevicePage(uint8_t* base,uint32_t object,const char* stage,unsigned call,uint32_t caller) {
  uint32_t at=0;
  if(const void* p=RexGmShadowFor(reinterpret_cast<uint64_t>(base)+object+48)) {
    std::memcpy(&at,p,4);at=__builtin_bswap32(at);
  }
  if(!at)return;
  const uint32_t page=at&~0xFFFu;
  const void* data=RexGmShadowFor(reinterpret_cast<uint64_t>(base)+page);
  if(!data)return;
  char path[180];
  std::snprintf(path,sizeof(path),"/switch/Mercenaries2/device-%s-%03u-%08X.bin",stage,call,page);
  if(FILE* f=std::fopen(path,"wb")) {std::fwrite(data,1,0x1000,f);std::fclose(f);}
  if(FILE* f=std::fopen("/switch/Mercenaries2/device-trace.log","a")) {
    std::fprintf(f,"stage=%s call=%u lr=%08X object=%08X write_at=%08X page=%08X\n",stage,call,caller,object,at,page);std::fclose(f);
  }
}
REX_HOOK_RAW(sub_82595B98) {
  const bool enabled=CommandBufferTestEnabled();
  static std::atomic_uint calls{0};
  const unsigned call=enabled ? calls.fetch_add(1,std::memory_order_relaxed) : 0;
  const uint32_t object=ctx.r3.u32,caller=uint32_t(ctx.lr);
  if(enabled)PrepareEncoderOutput(base,object);
  if(enabled && call<8)TraceDevicePage(base,object,"scissor-before",call,caller);
  __imp__sub_82595B98(ctx,base);
  if(enabled && call<8)TraceDevicePage(base,object,"scissor-after",call,caller);
}
REX_HOOK_RAW(sub_8259A5C8) {
  const uint32_t object=ctx.r3.u32;
  const bool enabled=CommandBufferTestEnabled();
  if(enabled)PrepareEncoderOutput(base,object);
  __imp__sub_8259A5C8(ctx,base);
  if(enabled)PrepareEncoderOutput(base,object);
}
REX_HOOK_RAW(sub_8259DFC0) {
  const bool enabled=CommandBufferTestEnabled();
  static std::atomic_uint calls{0};
  const unsigned call=enabled ? calls.fetch_add(1,std::memory_order_relaxed) : 0;
  const uint32_t object=ctx.r3.u32,caller=uint32_t(ctx.lr);
  if(enabled)PrepareEncoderOutput(base,object);
  if(enabled && call<8)TraceDevicePage(base,object,"register-before",call,caller);
  __imp__sub_8259DFC0(ctx,base);
  if(enabled && call<8)TraceDevicePage(base,object,"register-after",call,caller);
}
REX_HOOK_RAW(sub_82598770) {
  if(CommandBufferTestEnabled())PrepareEncoderOutput(base,ctx.r3.u32);
  __imp__sub_82598770(ctx,base);
}
// Trace the original wait/register command emitter before its buffer is published.
REX_HOOK_RAW(sub_82599FC0) {
  const bool enabled=CommandBufferTestEnabled();
  const uint32_t object=ctx.r3.u32, first=ctx.r4.u32+4, flags=ctx.r5.u32;
  const uint32_t caller=uint32_t(ctx.lr);
  static std::atomic_uint calls{0};
  const unsigned call=enabled ? calls.fetch_add(1,std::memory_order_relaxed) : 0;
  if(enabled)PrepareEncoderOutput(base,object);
  __imp__sub_82599FC0(ctx,base);
  if(enabled && call<64 && ctx.r3.u32>=first && uint64_t(ctx.r3.u32)-first<0x1000) {
    const size_t bytes=uint64_t(ctx.r3.u32)-first+4;
    const void* data=RexGmShadowFor(reinterpret_cast<uint64_t>(base)+first);
    if(data) {
      char path[160];
      std::snprintf(path,sizeof(path),"/switch/Mercenaries2/emitter-%03u-%08X.bin",call,first);
      if(FILE* f=std::fopen(path,"wb")) {std::fwrite(data,1,bytes,f);std::fclose(f);}
      if(FILE* f=std::fopen("/switch/Mercenaries2/emitter-trace.log","a")) {
        std::fprintf(f,"call=%u lr=%08X object=%08X first=%08X last=%08X flags=%08X bytes=%zu\n",
                     call,caller,object,first,ctx.r3.u32,flags,bytes);
        std::fclose(f);
      }
    }
  }
}
#endif
