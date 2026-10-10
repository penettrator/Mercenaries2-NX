"""Find untranslated entries next to runtime-proven virtual callbacks.

Reads a captured, decrypted XEX data region only. Candidate pointer groups are
heuristic evidence: review exact codegen before adding any entry to the runtime.
"""
import argparse
import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("dump", type=Path)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--base", type=lambda value: int(value, 0), default=0x82000000)
args = parser.parse_args()
roots = set(json.loads((ROOT / "app/bootstrap_callbacks.json").read_text()))
known = set(int(value, 16) for value in re.findall(
    r"DECLARE_REX_FUNC\(sub_([0-9A-F]{8})\)",
    (ROOT / "app/generated/default/mercenaries2_funcs.h").read_text()))
known.update(int(value, 16) for value in re.findall(
    r"\{\s*0x([0-9A-Fa-f]{8})",
    (ROOT / "app/generated/default/mercenaries2_init.cpp").read_text()))
data = args.dump.read_bytes()
if len(data) % 4:
    parser.error("Dump must contain aligned 32-bit words")
words = [value[0] for value in struct.iter_unpack(">I", data)]
groups = []
start = 0
while start < len(words):
    end = start
    while end < len(words) and 0x82150000 <= words[end] < 0x82A4E648 and words[end] % 4 == 0:
        end += 1
    entries = set(words[start:end])
    if end - start >= 3 and entries & roots:
        groups.append({"table": hex(args.base + start * 4), "slots": end - start,
                       "known_runtime_roots": [hex(value) for value in sorted(entries & roots)],
                       "new_candidates": [hex(value) for value in sorted(entries - known - roots)]})
    start = max(end, start + 1)
candidates = sorted({entry for group in groups for entry in group["new_candidates"]})
record = {"method": "Aligned executable pointer groups containing runtime-proven callbacks; exact translation review required",
          "source_dump": str(args.dump), "base": hex(args.base),
          "groups": groups, "unique_new_candidates": len(candidates), "candidates": candidates}
args.output.write_text(json.dumps(record, indent=2))
print(json.dumps({"groups": len(groups), "candidates": candidates}))
