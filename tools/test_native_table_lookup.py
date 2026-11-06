"""Compare exact generated table functions against native kernels, including all ctx bytes and read/barrier traces."""
from pathlib import Path
import subprocess
r=Path(__file__).resolve().parents[1];o=r/'out/perf-pass-15/host-tests';o.mkdir(parents=True,exist_ok=True)
def function(path,name,new):
 s=(r/path).read_text();a=s.index('DEFINE_REX_FUNC('+name+') {');b=s.find('\nDEFINE_REX_FUNC(',a+10);return s[a:b if b>=0 else len(s)].replace('DEFINE_REX_FUNC('+name+')','void '+new+'(PPCContext& ctx,uint8_t* base)')
a=function('app/generated/default/mercenaries2_recomp.81.cpp','sub_823D9740','ReferenceFind');b=function('app/generated/default/mercenaries2_recomp.84.cpp','sub_823DB370','ReferenceSlot')
code=r"""
#include <rex/ppc/context.h>
#include "app/src/native_table_lookup.h"
#include "app/src/native_lookup_fixture.h"
#include <array>
#include <algorithm>
#include <bit>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <memory>
#include <random>
#include <vector>
struct Trace {uint32_t address;std::array<unsigned char,sizeof(PPCContext)> context;bool operator==(const Trace&)const=default;};
std::vector<Trace> events;unsigned char* mem=nullptr;unsigned barriers=0;int mutation=0;uint32_t desired=0;
void Record(PPCContext& c,uint32_t address){Trace t{address,{}};std::memcpy(t.context.data(),&c,sizeof(c));events.push_back(t);if(events.size()==512)throw 2;}
uint32_t Get(uint8_t* p,uint32_t a){assert(uint64_t(a)+4<=65536);uint32_t v;std::memcpy(&v,p+a,4);return __builtin_bswap32(v);}
void Put(uint8_t* p,uint32_t a,uint32_t v){assert(uint64_t(a)+4<=65536);v=__builtin_bswap32(v);std::memcpy(p+a,&v,4);}
uint32_t Load(PPCContext& c,uint8_t* base,uint32_t a){Record(c,a);return Get(base,a);}
void Barrier(PPCContext& c){Record(c,0xfffffff0);++barriers;if(mutation==1&&barriers==1)Put(mem,16384,desired);if(mutation==2&&barriers==1)Put(mem,256+8,2);asm volatile("":::"memory");}
void Trap(PPCContext& c){Record(c,0xfffffff4);throw 1;}
#define REX_FUNC_PROLOGUE() ((void)0)
#define REX_LOAD_U32(x) Load(ctx,base,uint32_t(x))
#define REX_COMPILER_BARRIER() Barrier(ctx)
#define ppc_trap(c,b,k) Trap(c)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wtype-limits"
REF_A
REF_B
#pragma GCC diagnostic pop
struct alignas(64) Fixture {std::array<uint8_t,65536> bytes;};
int main(){std::mt19937_64 rng(0x823d9740);auto fa=std::make_unique<Fixture>();auto fb=std::make_unique<Fixture>();unsigned cases=0;
for(unsigned n=0;n<4096;++n)for(unsigned which=0;which<2;++which){
 auto& data=fa->bytes;data.fill(0);uint32_t cap=1+rng()%257,key=uint32_t(rng());if(key==UINT32_MAX)--key;uint32_t factor=uint32_t(rng());uint32_t slot=uint32_t(int64_t(int32_t(factor))*int64_t(int32_t(key)))%cap;bool hashed=(n&1);if(!hashed)slot=rng()%cap;
 Put(data.data(),256,1);Put(data.data(),264,cap);Put(data.data(),268,factor);Put(data.data(),272,16384);Put(data.data(),276,which?factor:4096);Put(data.data(),284,16384);
 if(which)slot=uint32_t(int64_t(int32_t(factor))*int64_t(int32_t(key)))%cap;
 for(unsigned i=0;i<cap;++i){Put(data.data(),4096+i*4,UINT32_MAX);Put(data.data(),16384+i*4,UINT32_MAX);}
 unsigned probes=rng()%std::min(cap,9u);bool hit=n%3!=0;
 for(unsigned i=0;i<=probes;++i){unsigned s=(slot+i)%cap;bool last=i==probes;if(which)Put(data.data(),16384+s*4,last?(hit?key:UINT32_MAX):(key^0x31415926));else{Put(data.data(),4096+s*4,last&&!hit?UINT32_MAX:s);Put(data.data(),16384+s*4,last&&hit?key:(key^0x31415926));}}
 PPCContext original{};for(unsigned i=0;i<32;++i){uint64_t v=rng();std::memcpy(reinterpret_cast<uint8_t*>(&original.r0)+i*sizeof(original.r0),&v,8);}original.lr=rng();original.ctr.u64=rng();original.r3.u64=256;original.r4.u64=uint64_t(rng())<<32|key;original.r5.u64=hashed?UINT64_MAX:((rng()<<32)|slot);
 // Capacity sign bit and nonzero high GPR halves must retain exact PPC effects.
 if(n%97==0){const uint32_t wide=(n&1)?UINT32_MAX:0x80000000u;Put(data.data(),264,wide);Put(data.data(),268,0);if(which)Put(data.data(),276,0);original.r4.u64&=0xffffffff00000000ULL;original.r5.u64=UINT64_MAX;Put(data.data(),4096,0);Put(data.data(),4100,1);Put(data.data(),16384,(n%4==3)?0:1);Put(data.data(),16388,0);}
 if(n%41==0)Put(data.data(),256,0);if(n%43==0)Put(data.data(),264,0);
 mutation=0;if((n==2||n==4)&&!which){mutation=n==2?1:2;cap=1;slot=0;Put(data.data(),256,1);Put(data.data(),264,1);Put(data.data(),4096,0);Put(data.data(),4100,1);Put(data.data(),16384,key^0x31415926);Put(data.data(),16388,key);original.r5.u64=0;}
 desired=key;PPCContext native{};std::memcpy(&native,&original,sizeof(native));fb->bytes=data;
 events.clear();barriers=0;mem=data.data();int ta=0,tb=0;try{if(which)ReferenceSlot(original,mem);else ReferenceFind(original,mem);}catch(int e){ta=e;}auto trace=events;
 events.clear();barriers=0;mem=fb->bytes.data();try{auto load=[&](uint32_t a){return Load(native,mem,a);};auto bar=[&]{Barrier(native);};auto trap=[&]{Trap(native);};if(which)mercs2::lookup::Slot(native,load,bar,trap);else mercs2::lookup::Find(native,load,bar,trap);}catch(int e){tb=e;}
 if(ta!=tb||std::memcmp(&original,&native,sizeof(native))||data!=fb->bytes||trace!=events){printf("FAIL seed=823d9740 case=%u which=%u trap=%d/%d trace=%zu/%zu ctx=%d\n",n,which,ta,tb,trace.size(),events.size(),std::memcmp(&original,&native,sizeof(native)));return 1;}++cases;
 }
for(unsigned n=0;n<128;++n)for(unsigned which=0;which<2;++which){
 PPCContext ref{},native{};mercs2::lookup::Fixture(ref,fa->bytes.data(),n,which);std::memcpy(&native,&ref,sizeof(ref));fb->bytes=fa->bytes;mutation=0;events.clear();barriers=0;mem=fa->bytes.data();
 if(which)ReferenceSlot(ref,mem);else ReferenceFind(ref,mem);auto trace=events;events.clear();barriers=0;mem=fb->bytes.data();
 auto load=[&](uint32_t a){return Load(native,mem,a);};auto bar=[&]{Barrier(native);};auto trap=[&]{Trap(native);};if(which)mercs2::lookup::Slot(native,load,bar,trap);else mercs2::lookup::Find(native,load,bar,trap);
 assert(!std::memcmp(&ref,&native,sizeof(ref))&&fa->bytes==fb->bytes&&trace==events);++cases;
}
printf("PASS %u actual PPCContext/generated-vs-native cases; full context/memory/load+barrier traces/traps, signed64 hash residue, wrap, misses, zero capacity, concurrent-memory mutation\n",cases);}
""".replace('REF_A',a).replace('REF_B',b)
cpp=o/'lookup.cpp';cpp.write_text(code);exe=o/'lookup'
subprocess.run(['g++','-std=c++23','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-Wno-ignored-attributes','-Wno-unused-but-set-variable','-fsanitize=address,undefined','-I'+str(r),'-I'+str(r/'reference/masseffect-nx/sdk/include'),'-I'+str(r/'reference/masseffect-nx/sdk/thirdparty/simde'),str(cpp),'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
