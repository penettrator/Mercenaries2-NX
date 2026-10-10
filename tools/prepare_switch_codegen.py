"""Apply only the GCC weak-alias fix from the masseffect-nx SDK template."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
target = root / 'app/generated/default/mercenaries2_pch.h'
template = (root / 'reference/masseffect-nx/sdk/resources/templates/codegen/pch_h.inja').read_text()
text = target.read_text()
marker = '#elif defined(__GNUC__) && !defined(__clang__)'
if marker in text:
    print('GCC alias support already present')
else:
    start = template.index(marker)
    end = template.index('#else', start)
    branch = template[start:end]
    # The immediately following fallback is the existing Clang implementation.
    anchor = '#else\n#define DEFINE_REX_FUNC(name)'
    if text.count(anchor) != 1:
        raise SystemExit('Unexpected generated macro; refusing to patch')
    target.write_text(text.replace(anchor, branch + anchor), encoding='utf-8')
    print('Applied GCC alias declaration fix (masseffect-nx SDK, BSD-3-Clause)')

# Only blocks with observed watched-memory accesses use the emulator shadow-access diagnostic.
# Keep these guarded includes reproducible when the PPC source is regenerated.
for unit in [10, 26, 36, 37, 49, 53, 62, 71, 86, 100, 114, 117, 133, 137]:
    source = root / f'app/generated/default/mercenaries2_recomp.{unit}.cpp'
    text = source.read_text()
    include = '#if defined(__SWITCH__)\n#include "../../src/switch_emulator_memory_access.h"\n#endif\n'
    if include not in text:
        at = text.index('\n') + 1
        source.write_text(text[:at] + include + text[at:])

# Internal resolution (HANDOFF section 64): sub_82565FE0 (Direct3D device setup) stores the
# back buffer size 1280x720 at device+11160/11164, which the engine reads to size its frame.
# The values come from the app cvars mercs2_internal_width/height (default 1280x720).
unit = root / 'app/generated/default/mercenaries2_recomp.33.cpp'
text = unit.read_text()
decl = 'extern "C" int64_t mercs2_internal_width();\nextern "C" int64_t mercs2_internal_height();\n'
fn_at = text.index('DEFINE_REX_FUNC(sub_82565FE0)')
fn_end = text.index('\nDEFINE_REX_FUNC(', fn_at + 10)
body = text[fn_at:fn_end]
old = '\t// li r11,1280\n\tctx.r11.s64 = 1280;\n\t// li r10,720\n\tctx.r10.s64 = 720;\n'
new = ('\t// li r11,1280 (internal resolution override)\n\tctx.r11.s64 = mercs2_internal_width();\n'
       '\t// li r10,720 (internal resolution override)\n\tctx.r10.s64 = mercs2_internal_height();\n')
if new in body:
    print('Internal resolution override already present')
elif body.count(old) == 1:
    text = text[:fn_at] + body.replace(old, new) + text[fn_end:]
    if decl not in text:
        at = text.index('\n') + 1
        text = text[:at] + decl + text[at:]
    unit.write_text(text)
    print('Applied internal resolution override in sub_82565FE0')
else:
    raise SystemExit('sub_82565FE0: back buffer size pattern not found; refusing to patch')

# Guest atomics without the host global lock (HANDOFF section 67; masseffect-nx
# tools/pch_no_global_lock.py, BSD-3-Clause idea). The guest wraps each atomic read-modify-write
# in mfmsr + mtmsrd ... mtmsrd (interrupts off on the Xbox 360); the codegen turns that into the
# SDK's recursive global mutex, which run31 showed every guest thread queueing on (20-70 % of
# their time). All 188 brackets (76 functions) hold exactly one lwarx/ldarx ... stwcx./stdcx.
# pair, emitted as a compare-and-swap, so atomicity does not depend on the lock.
# g_mercs2_lockfree_atomics (cvar mercs2_lockfree_atomics, default true) is set before guest code.
pch = root / 'app/generated/default/mercenaries2_pch.h'
text = pch.read_text()
if 'g_mercs2_lockfree_atomics' in text:
    print('Lock-free guest atomics already present')
else:
    BS = chr(92)  # backslash of the macro line continuations
    pairs = [
        ('#define REX_CHECK_GLOBAL_LOCK()',
         '// Mercenaries 2: tools/prepare_switch_codegen.py. Set before guest code runs, never changed after.\n'
         'extern "C" bool g_mercs2_lockfree_atomics;\n\n#define REX_CHECK_GLOBAL_LOCK()'),
        ('    auto lock_ = rex::thread::global_critical_region::AcquireDirect(); ' + BS + '\n',
         '    if (g_mercs2_lockfree_atomics) return 0x8000;                      ' + BS + '\n'
         '    auto lock_ = rex::thread::global_critical_region::AcquireDirect(); ' + BS + '\n'),
        ('    rex::thread::global_critical_region::mutex().lock(); ' + BS + '\n',
         '    if (g_mercs2_lockfree_atomics) break;                ' + BS + '\n'
         '    rex::thread::global_critical_region::mutex().lock(); ' + BS + '\n'),
        ('    auto old_count_ = ppc_global_lock_count_().fetch_sub(1);',
         'if (g_mercs2_lockfree_atomics) break;                                                 ' + BS + '\n'
         '    auto old_count_ = ppc_global_lock_count_().fetch_sub(1);'),
    ]
    for old, new in pairs:
        if text.count(old) != 1:
            raise SystemExit('global lock macro pattern not found; refusing to patch')
        text = text.replace(old, new)
    pch.write_text(text)
    print('Applied lock-free guest atomics switch')

# Guest loads/stores without volatile, with compiler barriers at polling loops and guest fences
# (HANDOFF section 67).
import subprocess, sys
subprocess.run([sys.executable, str(root / 'tools/codegen_no_volatile.py')], check=True)
