#include <switch.h>
#include <cstdio>
#include <cstdint>
#include "guest_memory_switch.h"
extern "C" { u32 __nx_applet_type=AppletType_Application; u64 __nx_heap_size=64*1024*1024; }
static unsigned notifications;
static bool Restore(uint64_t at) {
 ++notifications;
 return RexGmProtect(reinterpret_cast<uint8_t*>(at),0x1000,REX_GM_WRITE,nullptr);
}
extern "C" { bool (*g_rex_hot_read_hook)(uint64_t)=Restore; }
static bool CommandBufferTestEnabled() {return true;}
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

int main() {
 FILE* f=fopen("/switch/Mercenaries2/shadow-access-probe.log","w");
 if(!f)svcExitProcess();
 auto check=[&](const char* name,bool ok) {fprintf(f,"%s: %s result=%08X\n",name,ok?"PASS":"FAIL",RexGmLastResult());fflush(f);if(!ok){fclose(f);svcExitProcess();}};
 auto* base=RexGmInit(0x120000000ULL);check("reserve",base);
 check("cpu_view",RexGmAddView(base+0xA0000000ULL,0x100000000ULL,0x20000000));
 check("physical_view",RexGmAddView(base+0x100000000ULL,0x100000000ULL,0x20000000));
 const uint32_t address=0xB6D60000,physical=0x16D60000;
 check("commit",RexGmCommit(0x100000000ULL+physical,0x2000,REX_GM_WRITE));
 check("cpu_map",RexGmMapCommittedRange(base+address,0x2000));
 check("physical_map",RexGmMapCommittedRange(base+0x100000000ULL+physical,0x2000));
 check("watch",RexGmProtect(base+address,0x1000,REX_GM_READ,nullptr));
 auto* shadow=mercenaries2_EmulatorMemoryAddress(base,address,4,false);
 check("watched_read_uses_shadow",shadow!=base+address && shadow==RexGmShadowFor(reinterpret_cast<uint64_t>(base)+address));
 check("read_preserves_watch",notifications==0);
 auto* write=mercenaries2_EmulatorMemoryAddress(base,address,4,true);
 check("write_notifies_watch",notifications==1 && write==shadow);
 *reinterpret_cast<volatile uint32_t*>(write)=0x12345678;
 check("physical_alias_coherent",*reinterpret_cast<volatile uint32_t*>(base+0x100000000ULL+physical)==0x12345678);
 check("watch_again",RexGmProtect(base+address,0x1000,REX_GM_READ,nullptr));
 write=mercenaries2_EmulatorMemoryAddress(base,address+0xFFC,8,true);
 check("cross_page_write",write!=base+address+0xFFC && notifications==2);
 uint64_t value=0xAABBCCDD11223344;__builtin_memcpy(write,&value,8);
 uint64_t actual;__builtin_memcpy(&actual,base+0x100000000ULL+physical+0xFFC,8);
 check("cross_page_alias_coherent",actual==value);
 check("noaccess",RexGmProtect(base+address+0x1000,0x1000,REX_GM_NONE,nullptr));
 check("noaccess_not_bypassed",mercenaries2_EmulatorMemoryAddress(base,address+0x1000,4,true)==base+address+0x1000);
 check("uncommitted_not_bypassed",mercenaries2_EmulatorMemoryAddress(base,address+0x400000,4,false)==base+address+0x400000);
 RexGmShutdown();fprintf(f,"probe_complete\n");fclose(f);svcExitProcess();
}
