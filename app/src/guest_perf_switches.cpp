// Run-time switches of the patched generated code (tools/prepare_switch_codegen.py, HANDOFF
// section 67). Applied from OnPreSetup, before any guest code runs; never changed after.
#include <rex/cvar.h>
#include <rex/logging.h>

REXCVAR_DEFINE_BOOL(mercs2_lockfree_atomics, true, "Mercs2",
                    "Guest atomic brackets (mfmsr/mtmsrd around lwarx/stwcx.) skip the SDK global "
                    "mutex; the atomics are compare-and-swap either way");

extern "C" bool g_mercs2_lockfree_atomics;
bool g_mercs2_lockfree_atomics = false;

void mercs2_ApplyGuestPerfSwitches() {
  g_mercs2_lockfree_atomics = REXCVAR_GET(mercs2_lockfree_atomics);
  REXLOG_INFO("Mercenaries 2 guest atomics: {}",
              g_mercs2_lockfree_atomics ? "lock-free (compare-and-swap only)" : "global lock");
}
