"""Predict whether NAK's narrowed Maxwell interlock applies to SPIR-V shaders.

reference/mesa-switch-src/src/nouveau/compiler/nak_nir.c (nak_nir_lower_interlock)
waits at OpBeginInvocationInterlockEXT and releases at OpEndInvocationInterlockEXT
only when each occurs exactly once, on the outermost control-flow level of the
entry point, Begin before End. Otherwise the whole shader stays serialized.

Outermost level is approximated on the SPIR-V CFG: the block lies on every
path from the entry to every return and is not part of any cycle. Shaders with
OpKill/OpTerminateInvocation are reported as fallback (nir_lower_returns wraps
the code after them in branches).

Usage: python -I tools/check_nak_narrow_interlock.py <dir-or-.spv>... [--json out.json]
"""
import json
import struct
import sys
from pathlib import Path

OP_ENTRY_POINT, OP_FUNCTION, OP_FUNCTION_END, OP_LABEL = 15, 54, 56, 248
OP_BRANCH, OP_BRANCH_CONDITIONAL, OP_SWITCH = 249, 250, 251
OP_KILL, OP_RETURN, OP_RETURN_VALUE, OP_UNREACHABLE = 252, 253, 254, 255
OP_TERMINATE_INVOCATION, OP_BEGIN, OP_END = 4416, 5364, 5365


def parse(path):
    words = Path(path).read_bytes()
    n = len(words) // 4
    w = struct.unpack("<%dI" % n, words[: n * 4])
    if w[0] != 0x07230203:
        raise ValueError("not SPIR-V")
    entry = None
    functions = {}
    cur_fn = cur_block = None
    i = 5
    while i < n:
        op, wc = w[i] & 0xFFFF, w[i] >> 16
        args = w[i + 1 : i + wc]
        if op == OP_ENTRY_POINT:
            entry = args[1]
        elif op == OP_FUNCTION:
            cur_fn = {"blocks": {}, "order": []}
            functions[args[1]] = cur_fn
        elif op == OP_FUNCTION_END:
            cur_fn = None
        elif op == OP_LABEL and cur_fn is not None:
            cur_block = {"succ": [], "ret": False, "kill": False, "begin": 0, "end": 0,
                         "begin_before_end": None}
            cur_fn["blocks"][args[0]] = cur_block
            cur_fn["order"].append(args[0])
        elif cur_block is not None:
            if op == OP_BRANCH:
                cur_block["succ"] = [args[0]]
            elif op == OP_BRANCH_CONDITIONAL:
                cur_block["succ"] = [args[1], args[2]]
            elif op == OP_SWITCH:
                cur_block["succ"] = [args[1]] + list(args[3::2])
            elif op in (OP_RETURN, OP_RETURN_VALUE):
                cur_block["ret"] = True
            elif op in (OP_KILL, OP_TERMINATE_INVOCATION):
                cur_block["kill"] = True
            elif op == OP_BEGIN:
                cur_block["begin"] += 1
                if cur_block["begin_before_end"] is None:
                    cur_block["begin_before_end"] = cur_block["end"] == 0
            elif op == OP_END:
                cur_block["end"] += 1
        i += wc
    return entry, functions


def reachable(blocks, start, removed=None):
    seen, stack = set(), [start]
    while stack:
        b = stack.pop()
        if b in seen or b == removed:
            continue
        seen.add(b)
        stack.extend(blocks[b]["succ"])
    return seen


def analyze(path):
    entry, functions = parse(path)
    fn = functions.get(entry)
    if fn is None:
        return {"result": "error", "reason": "no entry function"}
    blocks = fn["blocks"]
    other = sum(b["begin"] + b["end"] for f, x in functions.items() if f != entry
                for b in x["blocks"].values())
    begins = [k for k, b in blocks.items() for _ in range(b["begin"])]
    ends = [k for k, b in blocks.items() for _ in range(b["end"])]
    if not begins and not ends and not other:
        return {"result": "no_interlock"}
    if other:
        return {"result": "fallback", "reason": "markers outside entry point"}
    if any(b["kill"] for b in blocks.values()):
        return {"result": "fallback", "reason": "OpKill/OpTerminateInvocation"}
    if len(begins) != 1 or len(ends) != 1:
        return {"result": "fallback", "reason": f"{len(begins)} Begin / {len(ends)} End"}
    start = fn["order"][0]
    returns = [k for k, b in blocks.items() if b["ret"]]

    def outermost(block):
        if block == start:
            return True
        # Every return must become unreachable without the block, and the
        # block must not be on a cycle.
        if any(r in reachable(blocks, start, removed=block) for r in returns):
            return False
        return not any(block in reachable(blocks, s) for s in blocks[block]["succ"])

    b, e = begins[0], ends[0]
    if not outermost(b):
        return {"result": "fallback", "reason": "Begin not on outermost level"}
    if not outermost(e):
        return {"result": "fallback", "reason": "End not on outermost level"}
    if b == e:
        ok = blocks[b]["begin_before_end"]
    else:
        ok = e in reachable(blocks, b) and b not in reachable(blocks, e)
    if not ok:
        return {"result": "fallback", "reason": "End before Begin"}
    # Fraction of the CFG left outside the critical section (blocks before Begin).
    before = reachable(blocks, start, removed=b)
    return {"result": "narrow", "blocks_total": len(blocks),
            "blocks_before_begin": len(before)}


def main(argv):
    out = None
    if "--json" in argv:
        k = argv.index("--json")
        out = argv[k + 1]
        argv = argv[:k] + argv[k + 2 :]
    files = []
    for a in argv:
        p = Path(a)
        files += sorted(p.glob("*.spv")) if p.is_dir() else [p]
    results = {}
    for f in files:
        try:
            results[f.name] = analyze(f)
        except Exception as ex:  # report and continue
            results[f.name] = {"result": "error", "reason": str(ex)}
    summary = {}
    for r in results.values():
        key = r["result"] + (": " + r["reason"] if "reason" in r else "")
        summary[key] = summary.get(key, 0) + 1
    print(json.dumps(summary, indent=1))
    if out:
        Path(out).write_text(json.dumps({"summary": summary, "shaders": results}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
