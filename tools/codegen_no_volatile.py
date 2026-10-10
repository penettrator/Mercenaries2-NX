"""Guest loads/stores without `volatile` (HANDOFF section 67), made safe for this game.

Idea from masseffect-nx tools/pch_no_volatile.py (t153: +15-20 % fps there): the generated
REX_LOAD_*/REX_STORE_* go through volatile pointers, which stops GCC from keeping guest values in
registers, pairing accesses or scheduling them. Removing it has two risks, both closed here:

1. A loop that polls a guest address without any call could be turned into an endless loop.
   Every backward goto whose body loads from an address whose registers
   are not changed in the body gets REX_COMPILER_BARRIER() right after its label, so such loops
   re-read memory on every iteration exactly as before (the barrier emits no instruction).
2. The guest's sync/lwsync/eieio emit nothing in the generated code, so their ordering was kept
   only by volatile-to-volatile order. A compiler barrier is inserted at each of them.

MMIO macros (REX_MM_*) keep volatile. Building with -DREX_GUEST_VOLATILE=volatile restores the
old behaviour. Idempotent; run after every codegen (tools/prepare_switch_codegen.py calls it).
  usage: python tools/codegen_no_volatile.py [generated dir]
"""
import glob, os, re, sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
gen = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, 'app', 'generated', 'default')
pch = os.path.join(gen, 'mercenaries2_pch.h')
BARRIER = '\tREX_COMPILER_BARRIER();'


def read(path):
    with open(path, encoding='utf-8', errors='surrogateescape', newline='') as fh:
        return fh.read()


def write(path, s):
    with open(path, 'w', encoding='utf-8', errors='surrogateescape', newline='') as fh:
        fh.write(s)


# 1. The pch macros.
s = read(pch)
if 'REX_GUEST_VOLATILE' in s:
    print('codegen_no_volatile: pch already patched')
else:
    out, changed = [], 0
    for line in s.split('\n'):
        if line.startswith(('#define REX_LOAD_U', '#define REX_STORE_U')):
            n = line.replace('(volatile u', '(REX_GUEST_VOLATILE u')
            changed += n != line
            line = n
        out.append(line)
    if changed != 8:
        sys.exit('codegen_no_volatile: expected 8 REX_LOAD/STORE macros, found %d; refusing' % changed)
    s = '\n'.join(out)
    anchor = '#define REX_LOAD_U8(x)'
    if s.count(anchor) != 1:
        sys.exit('codegen_no_volatile: REX_LOAD_U8 anchor missing; refusing')
    s = s.replace(anchor, '''// Mercenaries 2: guest loads/stores without volatile (tools/codegen_no_volatile.py). Polling
// loops and guest sync/lwsync/eieio carry REX_COMPILER_BARRIER(). Define REX_GUEST_VOLATILE as
// volatile to restore the generated behaviour.
#ifndef REX_GUEST_VOLATILE
#define REX_GUEST_VOLATILE
#endif
#define REX_COMPILER_BARRIER() __asm__ __volatile__("" ::: "memory")
''' + anchor, 1)
    write(pch, s)
    print('codegen_no_volatile: pch patched (8 macros)')

# 2. Barriers in the generated units.

# HANDOFF B:127: registers may also be C++ locals (non_volatile_as_local etc.): match `r29.` too.
assign_re = re.compile(r'(?:ctx\.)?((?:r|f|v)\d+)\.\w+\s*=[^=]')
load_re = re.compile(r'REX_LOAD_\w+\(([^;]*?)\)\s*[;)]')
reg_re = re.compile(r'(?:ctx\.)?((?:r|f|v)\d+)')
fence_re = re.compile(r'^\s*// (sync|lwsync|eieio|isync)\b')
total_loops = total_fences = 0
for path in sorted(glob.glob(os.path.join(gen, 'mercenaries2_recomp.*.cpp'))):
    text = read(path)
    if 'REX_COMPILER_BARRIER' in text:
        continue
    nl = '\r\n' if '\r\n' in text else '\n'
    lines = text.split(nl)
    label_line = {}
    need = set()
    fences = set()
    for i, line in enumerate(lines):
        if line.startswith('DEFINE_REX_FUNC('):
            label_line = {}
        if fence_re.match(line):
            fences.add(i)
        m = re.match(r'^(loc_[0-9A-F]+):', line)
        if m:
            label_line[m.group(1)] = i
            continue
        for g in re.findall(r'goto (loc_[0-9A-F]+);', line):
            if g not in label_line or label_line[g] > i:
                continue
            # Calls are not a reason to skip: in text order a call may sit on a path that leaves
            # the loop, and the barrier costs nothing where a call already is one.
            body = '\n'.join(lines[label_line[g]:i + 1])
            assigned = set(assign_re.findall(body))
            for addr in load_re.findall(body):
                if not (set(reg_re.findall(addr)) & assigned):
                    need.add(label_line[g])
                    break
    if not need and not fences:
        continue
    out = []
    for i, line in enumerate(lines):
        out.append(line)
        if i in need or i in fences:
            out.append(BARRIER)
    write(path, nl.join(out))
    total_loops += len(need)
    total_fences += len(fences)
print('codegen_no_volatile: barriers at %d polling-loop heads and %d guest fences'
      % (total_loops, total_fences))
