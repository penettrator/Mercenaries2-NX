"""Mercenaries 2: generated-code patches of the 2026-10-16 optimisation round (ported from Prototype 2).

Idempotent; refuses loudly when an anchor is not found exactly once. Called at the end of
tools/prepare_switch_codegen.py (after codegen_no_volatile.py), and can be run on its own.

1. Guest D3D flip scheduling (sub_825A0130) -> mercs2_flip_target() (app/src/switch_frame_pacing.cpp).
   Same D3D code as Prototype 2 sub_82C746D8 (WORKLOG #81/#82): device+16548 = current vblank count,
   +16556 = last flip vblank, r30 = present interval, r27 = late threshold (%), r11 = target vblank.
2. dcbt -> __builtin_prefetch (Prototype 2 WORKLOG #82). ReXGlue drops the guest's cache-touch hints;
   loops written around them (copies, decompression, skinning) lose their prefetch. A prefetch never faults.

Original versions of every file this script changes are copied once to out/opt-2026-10-16/backup/generated/.
"""
from pathlib import Path
import re
import shutil
import sys

root = Path(__file__).resolve().parents[1]
gen = root / 'app/generated/default'
backup = root / 'out/opt-2026-10-16/backup/generated'


def read(p):
    return p.read_bytes().decode('utf-8', errors='surrogateescape')


def write(p, text):
    backup.mkdir(parents=True, exist_ok=True)
    b = backup / p.name
    if not b.exists():
        shutil.copy2(p, b)
    p.write_bytes(text.encode('utf-8', errors='surrogateescape'))


units = sorted(gen.glob('mercenaries2_recomp.*.cpp'))
if not units:
    sys.exit('no generated sources')

# --- 1. flip hook -------------------------------------------------------------------------------
flip = 'sub_825A0130'
flip_re = re.compile(
    r'(loc_825A0234:\n\t// lwz r10,16548\(r31\)\n\tctx\.r10\.u64 = REX_LOAD(?:_V)?_U32\(((?:ctx\.)?)r31\.u32 \+ 16548\);\n)')
done = False
for f in units:
    src = read(f)
    if f'DEFINE_REX_FUNC({flip})' not in src:
        continue
    if 'mercs2_flip_target(' in src:
        print('Flip hook already present in', f.name)
        done = True
        break
    head = src.index(f'DEFINE_REX_FUNC({flip})')
    nxt = src.find('\nDEFINE_REX_FUNC(', head + 10)
    end = nxt if nxt >= 0 else len(src)
    body = src[head:end]
    m = list(flip_re.finditer(body))
    if len(m) != 1:
        sys.exit(f'{flip}: flip anchor found {len(m)} times; refusing to patch')
    p = m[0].group(2)  # '' (register locals) or 'ctx.'
    # Sanity: the registers the hook reads must be what the PPC code above says they are.
    for need in ('// rlwinm r30,r29,24,28,31', '// clrlwi r27,r29,24', '// lwz r8,16556(r31)',
                 '// stw r11,16556(r31)', '// lis r11,32712', '// stw r28,24848(r11)'):
        if need not in body:
            sys.exit(f'{flip}: expected instruction "{need}" not found; refusing to patch')
    call = (f'\tctx.r11.u64 = mercs2_flip_target(ctx.r11.u32, ctx.r10.u32, {p}r30.u32, {p}r27.u32, '
            f'REX_LOAD_U32({p}r31.u32 + 16556));\n')
    body = body[:m[0].end()] + call + body[m[0].end():]
    src = src[:head] + body + src[end:]
    decl = ('extern "C" uint32_t mercs2_flip_target(uint32_t target, uint32_t now, uint32_t interval, '
            'uint32_t threshold, uint32_t last_flip);\n')
    b = src.find('DEFINE_REX_FUNC(')
    src = src[:b] + decl + src[b:]
    write(f, src)
    print('Flip hook inserted in', f.name)
    done = True
    break
if not done:
    sys.exit(f'{flip} not found in the generated code')

# --- 2. dcbt -> prefetch ------------------------------------------------------------------------
dcbt = re.compile(r'^(\t// dcbt (r\d+),(r\d+)(\r?\n))(?!\t__builtin_prefetch)', re.M)  # some units are CRLF


def dcbt_sub(m):
    ra, rb = m.group(2), m.group(3)
    ea = f'ctx.{rb}.u32' if ra == 'r0' else f'ctx.{ra}.u32 + ctx.{rb}.u32'
    return m.group(1) + f'\t__builtin_prefetch(REX_RAW_ADDR((uint32_t)({ea})));' + m.group(4)


total = 0
for f in units:
    src = read(f)
    new, k = dcbt.subn(dcbt_sub, src)
    if not k:
        continue
    # Register locals (non_volatile_as_local etc.): r14-r31 live in C++ locals of the function.
    parts = re.split(r'(?=^DEFINE_REX_FUNC\()', new, flags=re.M)
    for i, part in enumerate(parts):
        if '__builtin_prefetch(REX_RAW_ADDR' not in part:
            continue

        def localize(m, part=part):
            t = m.group(0)
            for r in re.findall(r'ctx\.(r\d+)\.u32', t):
                if '\tPPCRegister ' + r + '{};' in part:
                    t = t.replace('ctx.' + r + '.u32', r + '.u32')
            return t
        parts[i] = re.sub(r'__builtin_prefetch\(REX_RAW_ADDR\(\(uint32_t\)\([^;]*\)\)\);', localize, part)
    write(f, ''.join(parts))
    total += k
print('dcbt prefetches inserted:', total)
