// Internal resolution override (HANDOFF section 64). The Direct3D device setup of the game
// (sub_82565FE0, patched by tools/prepare_switch_codegen.py) takes its back buffer size from
// here instead of the constants 1280x720; the engine sizes its frame from that size.
#include <cstdint>

#include <rex/cvar.h>

REXCVAR_DEFINE_INT32(mercs2_internal_width, 1280, "Mercs2",
                     "Back buffer width the game is told to render at (default 1280)");
REXCVAR_DEFINE_INT32(mercs2_internal_height, 720, "Mercs2",
                     "Back buffer height the game is told to render at (default 720)");

extern "C" int64_t mercs2_internal_width() { return REXCVAR_GET(mercs2_internal_width); }
extern "C" int64_t mercs2_internal_height() { return REXCVAR_GET(mercs2_internal_height); }
