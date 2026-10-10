from pathlib import Path
import json, hashlib, re, collections
root = Path('/work/out/nak-host-probe')
inputs = Path('/work/out/runtime-shader-probe/batch-full-depth')
items = []
for p in sorted((root/'results').glob('*.json')):
    if p.name == 'summary.json': continue
    data = json.loads(p.read_text())
    source = inputs/(p.stem+'.spv')
    data['input'] = str(source.relative_to('/work'))
    data['input_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    data['guest_ps_hash'] = p.stem.split('-')[0]
    data['modification'] = hex(int(p.stem.split('-')[1],16) | ((1<<50) if p.stem.endswith('-late') else 0))
    data['provisional'] = True
    data['configuration_evidence'] = 'run13robustBufferAccess+maxStorageBufferRange4294967295;set0shared1descriptor/EDRAMoffset16;SDK5plainUBOs;run12cached1xMSAA/sample_rate_shading0'
    counts = collections.Counter()
    for line in p.with_suffix('.sass').read_text().splitlines():
        line = line.split('//')[0].strip()
        if not line or line.startswith(('block','}', '//')): continue
        if '=' in line: line = line.split('=',1)[1].strip()
        elif line.startswith('@'): line = line.split(None,1)[1]
        op = re.match(r'([a-z][a-z0-9]*)(?:\.|\s|$)', line)
        if op: counts[op[1]] += 1
    data['nak_assembly_opcode_counts'] = dict(sorted(counts.items()))
    data['limitations'] = ['Static machine-code counts are not time measurements.', 'Static cycles exclude variable-latency texture/memory operations.', 'Layouts reconstructed from SPIRV plus SDK five-binding constant layout; compare exact code/register/spill counts to console statistics.', 'Captured NIR not from hardware; compiler flags and FSI state reconstructed.']
    items.append(data)
(root/'results'/'summary.json').write_text(json.dumps({'status':'provisional_host_diagnostic', 'results':items},indent=2)+'\n')


