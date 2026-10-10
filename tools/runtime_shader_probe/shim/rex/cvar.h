#pragma once
// Isolated translator probe only: no app registry, position-contraction cvar stays false.
#define REXCVAR_GET(name) probe_cvar_##name
#define REXCVAR_DEFINE_BOOL(name, value, category, description) bool probe_cvar_##name = value
#define REXCVAR_DECLARE(type, name) extern type probe_cvar_##name
