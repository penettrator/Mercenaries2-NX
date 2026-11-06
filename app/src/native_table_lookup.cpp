// SPDX-License-Identifier: GPL-3.0-or-later
#include "generated/default/mercenaries2_pch.h"
#include "native_table_lookup.h"
#include "native_lookup_fixture.h"
#include <chrono>
#include <cstring>
#include <memory>
#include <new>
#ifndef MERCENARIES2_NATIVE_TABLE_LOOKUP
#define MERCENARIES2_NATIVE_TABLE_LOOKUP 0
#endif
#if MERCENARIES2_NATIVE_TABLE_LOOKUP
REX_EXTERN(__imp__sub_823D9740);
REX_EXTERN(__imp__sub_823DB370);
namespace {
static REX_FUNC(NativeFind) __attribute__((noinline));
static REX_FUNC(NativeSlot) __attribute__((noinline));
static REX_FUNC(NativeFind) {
  REX_FUNC_PROLOGUE();
  mercs2::lookup::Find(ctx,[&](uint32_t a){return REX_LOAD_U32(a);},
                      []{REX_COMPILER_BARRIER();},[&]{ppc_trap(ctx,base,0);});
}
static REX_FUNC(NativeSlot) {
  REX_FUNC_PROLOGUE();
  mercs2::lookup::Slot(ctx,[&](uint32_t a){return REX_LOAD_U32(a);},
                      []{REX_COMPILER_BARRIER();},[&]{ppc_trap(ctx,base,0);});
}
// Written only before any guest starts; afterwards immutable. No live flag branch.
PPCFunc* find_impl=__imp__sub_823D9740;
PPCFunc* slot_impl=__imp__sub_823DB370;
struct alignas(64) TestMemory {uint8_t data[65536];};
volatile uint64_t benchmark_sink=0;
uint64_t Measure(PPCFunc* fn,PPCContext& c,uint8_t* m,bool slot) {
  const auto start=std::chrono::steady_clock::now();
  for(unsigned i=0;i<4096;++i){c.r3.u64=256;if(!slot)c.r5.u64=UINT64_MAX;fn(c,m);benchmark_sink=c.r3.u64;}
  return uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-start).count());
}
}
extern "C" REX_FUNC(sub_823D9740) {find_impl(ctx,base);}
extern "C" REX_FUNC(sub_823DB370) {slot_impl(ctx,base);}
extern "C" void mercs2_InitNativeLookups() {
  auto a=std::unique_ptr<TestMemory>(new(std::nothrow)TestMemory);
  auto b=std::unique_ptr<TestMemory>(new(std::nothrow)TestMemory);
  if(!a||!b){REXLOG_WARN("PERF: native lookup fixture allocation failed; original path retained");return;}
  for(unsigned i=0;i<128;++i)for(unsigned which=0;which<2;++which){
    PPCContext reference{},native{};mercs2::lookup::Fixture(reference,a->data,i,which);
    std::memcpy(&native,&reference,sizeof(native));std::memcpy(b->data,a->data,sizeof(a->data));
    (which?__imp__sub_823DB370:__imp__sub_823D9740)(reference,a->data);
    (which?NativeSlot:NativeFind)(native,b->data);
    if(std::memcmp(&reference,&native,sizeof(native))||std::memcmp(a->data,b->data,sizeof(a->data))){
      REXLOG_ERROR("PERF: native lookup selftest FAILED case={} function={}; original path retained",i,which);return;
    }
  }
  // Controlled startup CPU benchmark, not a frame-rate claim. ABBA limits order bias.
  for(unsigned which=0;which<2;++which){
    PPCContext ref{},fast{};mercs2::lookup::Fixture(ref,a->data,127,which);std::memcpy(&fast,&ref,sizeof(ref));std::memcpy(b->data,a->data,sizeof(a->data));
    auto original=which?__imp__sub_823DB370:__imp__sub_823D9740;auto candidate=which?NativeSlot:NativeFind;
    uint64_t old_ns=Measure(original,ref,a->data,which);uint64_t new_ns=Measure(candidate,fast,b->data,which);
    new_ns+=Measure(candidate,fast,b->data,which);old_ns+=Measure(original,ref,a->data,which);
    REXLOG_WARN("PERF: native lookup startup benchmark function={} calls=8192 original_ns={} native_ns={}",which,old_ns,new_ns);
  }
  find_impl=NativeFind;slot_impl=NativeSlot;
  REXLOG_WARN("PERF: native lookup selftest PASS cases=256 full_context_and_memory; both kernels enabled; original fallback preserved");
}
#else
extern "C" void mercs2_InitNativeLookups() {}
#endif
