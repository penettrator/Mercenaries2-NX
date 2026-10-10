// Host-only dependency implementations. No shader translation is replaced.
#include <rex/graphics/util/draw.h>
#include <filesystem>
#include <string_view>
#include <cstdio>
#include <cstdint>
#include <cstring>
namespace rex {
bool bit_scan_forward(uint32_t v,uint32_t* p){int i=__builtin_ffs(v);*p=i-1;return i!=0;}
namespace filesystem { FILE* OpenFile(const std::filesystem::path& p,std::string_view m){return fopen(p.c_str(),std::string(m).c_str());} }
namespace memory {
void copy_and_swap_32_unaligned(void* d,const void* s,size_t n){auto* a=(unsigned char*)d;auto* b=(const unsigned char*)s;for(size_t i=0;i<n;i++){uint32_t x;memcpy(&x,b+4*i,4);x=__builtin_bswap32(x);memcpy(a+4*i,&x,4);}}
void copy_and_swap_32_aligned(void* d,const void* s,size_t n){copy_and_swap_32_unaligned(d,s,n);}
}
namespace graphics::draw_util {
const int8_t kD3D10StandardSamplePositions2x[2][2]={{4,4},{-4,-4}};
const int8_t kD3D10StandardSamplePositions4x[4][2]={{-2,-6},{6,-2},{-6,2},{2,6}};
}
}
