#include <switch.h>
#include <cstdio>
#include <unistd.h>
#include "guest_memory_switch.h"
extern "C" {
u32 __nx_applet_type = AppletType_Application;
u64 __nx_heap_size = 64 * 1024 * 1024;
}
int main() {
 FILE* log = fopen("/switch/Mercenaries2/memory-probe-v3.log", "w");
 if (!log) svcExitProcess();
 auto record = [&](const char* step, bool ok) {
   fprintf(log, "%s: %s result=0x%08X\n", step, ok ? "PASS" : "FAIL", RexGmLastResult());
   fflush(log);
   return ok;
 };
 fprintf(log, "loader_process_handle=0x%08X\n", envGetOwnProcessHandle()); fflush(log);
 uint8_t* base = RexGmInit(0x120000000ULL);
 if (!record("reserve", base != nullptr)) { fclose(log); svcExitProcess(); }
 fprintf(log, "enter_primary_view\n"); fflush(log);
 bool ok = RexGmAddView(base, 0, 0x600000);
 record("primary_view", ok);
 fprintf(log, "enter_alias_view\n"); fflush(log);
 ok = ok && RexGmAddView(base + 0x600000, 0, 0x600000);
 if (!record("views", ok)) { fclose(log); svcExitProcess(); }
 fprintf(log, "enter_commit\n"); fflush(log);
 if (!record("commit", RexGmCommit(0, 0x204000, REX_GM_WRITE))) { fclose(log); svcExitProcess(); }
 if (!record("primary_map", RexGmMapCommittedRange(base, 0x204000))) { fclose(log); svcExitProcess(); }
 record("only_requested_view", RexGmMappedBytes() == RexGmCommittedBytes());
 record("idempotent_map", RexGmMapCommittedRange(base, 0x204000));
 if (!record("alias_map", RexGmMapCommittedRange(base + 0x600000, 0x1000))) { fclose(log); svcExitProcess(); }
 auto* a = reinterpret_cast<volatile uint32_t*>(base);
 auto* b = reinterpret_cast<volatile uint32_t*>(base + 0x600000);
 *a = 0x13579BDF;
 ok = *b == 0x13579BDF;
 *b = 0x2468ACE0;
 ok = ok && *a == 0x2468ACE0;
 record("alias_read_write", ok);
 auto* tail = reinterpret_cast<volatile uint32_t*>(base + 0x203ffc);
 *tail = 0x11223344;
 record("range_tail_read_write", *tail == 0x11223344);
 record("uncommitted_rejected", !RexGmMapCommittedRange(base + 0x400000, 0x1000));
 RexGmShutdown();
 fprintf(log, "probe_complete\n"); fclose(log);
 svcExitProcess();
}
