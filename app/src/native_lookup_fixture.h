// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <cstdint>
#include <cstring>
namespace mercs2::lookup {
inline uint64_t Random(uint64_t& s) {s^=s<<13;s^=s>>7;s^=s<<17;return s;}
inline void Store(uint8_t* m,uint32_t a,uint32_t v){v=__builtin_bswap32(v);std::memcpy(m+a,&v,4);}
template<class Context> void Fixture(Context& c,uint8_t* m,unsigned test,bool slot_lookup) {
  std::memset(m,0,65536);c=Context{};uint64_t s=0x823d9740823db370ULL+test;
  for(unsigned i=0;i<32;++i){uint64_t v=Random(s);std::memcpy(reinterpret_cast<uint8_t*>(&c.r0)+i*sizeof(c.r0),&v,8);}
  const uint32_t count=1+Random(s)%257,factor=uint32_t(Random(s));uint32_t key=uint32_t(Random(s));if(key==UINT32_MAX)--key;
  const bool hashed=(test&1)||slot_lookup;uint32_t first=hashed?uint32_t(int64_t(int32_t(factor))*int64_t(int32_t(key)))%count:Random(s)%count;
  Store(m,256,1);Store(m,264,count);Store(m,268,factor);Store(m,272,16384);Store(m,276,slot_lookup?factor:4096);Store(m,284,16384);
  for(uint32_t i=0;i<count;++i){Store(m,4096+4*i,UINT32_MAX);Store(m,16384+4*i,UINT32_MAX);}
  const unsigned probes=Random(s)%(count<9?count:9);const bool hit=test%3!=0;
  for(unsigned i=0;i<=probes;++i){const uint32_t pos=(first+i)%count;const bool last=i==probes;
    if(slot_lookup)Store(m,16384+4*pos,last?(hit?key:UINT32_MAX):(key^0x31415926));
    else {Store(m,4096+4*pos,last&&!hit?UINT32_MAX:pos);Store(m,16384+4*pos,last&&hit?key:(key^0x31415926));}}
  c.r3.u64=256;c.r4.u64=Random(s)<<32|key;c.r5.u64=hashed?UINT64_MAX:first;
  if(test%41==0)Store(m,256,0);if(test%43==0&&slot_lookup)Store(m,264,0);
}
}  // namespace mercs2::lookup
