#!/usr/bin/env python3
"""Parse opt-in SHADER_STATS counters without conflating variants or shader stages."""
import argparse
import json
import re
from pathlib import Path

PATTERN = re.compile(
    r'SHADER_STATS vs=([0-9A-Fa-f]{16}) vs_mod=([0-9A-Fa-f]{16}) '
    r'ps=([0-9A-Fa-f]{16}) ps_mod=([0-9A-Fa-f]{16}) placeholder=([01]) '
    r'executable=(\d+) stages=0x([0-9A-Fa-f]+) subgroup=(\d+) name="([^"]+)" value=(\d+)')

def analyze(text):
    records = {}
    conflicts = []
    for number, line in enumerate(text.splitlines(), 1):
        match = PATTERN.search(line)
        if not match:
            continue
        vs, vm, ps, pm, placeholder, executable, stages, subgroup, name, value = match.groups()
        key = (vs.upper(), vm.upper(), ps.upper(), pm.upper(), int(placeholder), int(executable), int(stages, 16), int(subgroup))
        record = records.setdefault(key, dict(zip(
            ('vs', 'vs_mod', 'ps', 'ps_mod', 'placeholder', 'executable', 'stages', 'subgroup'), key)))
        counters = record.setdefault('counters', {})
        value = int(value)
        if name in counters and counters[name] != value:
            conflicts.append({'line': number, 'key': list(key), 'name': name,
                              'previous': counters[name], 'value': value})
        counters[name] = value
        record['counter_lines'] = record.get('counter_lines', 0) + 1
    return {'schema_version': 1, 'records': list(records.values()), 'conflicts': conflicts,
            'requested_enabled': re.findall(r'SHADER_STATS requested=1 enabled=([01])', text),
            'query_errors': [line for line in text.splitlines() if 'SHADER_STATS' in line and
                             any(word in line for word in ('failed', 'unavailable'))],
            'limitations': ['Static compiler counters, not measured execution cycles.',
                            'SLM size is per-thread scratch allocation; spill/fill counters are static instructions.',
                            'Max warps/SM is an upper bound, not measured occupancy.',
                            'Different pipeline state may produce different counters even with identical guest hashes/modifications; conflicts are reported.',
                            'Placeholder executables are recorded separately; do not use them as final guest shader statistics.']}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = analyze(args.log.read_text(encoding='utf-8', errors='replace'))
    result['log'] = str(args.log)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + '\n', encoding='utf-8')
    else:
        print(rendered)
