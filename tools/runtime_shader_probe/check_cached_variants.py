"""Validate real cached PS variants using isolated baseline/candidate translators."""
import argparse,ctypes,json,struct,subprocess,hashlib,re
from pathlib import Path
CANDIDATE='candidate';BIT=49
ROOT=Path('/work');OUT=ROOT/'out/runtime-shader-probe/batch';RUN=ROOT/'out/hardware-runs/run10-06a07d7a-gpu-timing'

def translate():
    OUT.mkdir(parents=True,exist_ok=True)
    lib=ctypes.CDLL(str(ROOT/'out/gpu-draw-timing/hash-probe.so'));f=lib.merc_shader_hash;f.argtypes=[ctypes.c_void_p,ctypes.c_ulong];f.restype=ctypes.c_ulonglong
    data=(RUN/'runtime-cache/shaders/shareable/45410828.fsi.vk.xpso').read_bytes()
    if data[:8]!=b'XEPS\x01\x00\x00\x00' or data[8:12]!=bytes.fromhex('20260228'):raise ValueError('Unknown pipeline storage header')
    # This SDK packed PipelineDescription is 58 bytes + stored XXH3 (8).
    if (len(data)-12)%66:raise ValueError('Unexpected packed description framing')
    keys=set()
    for off in range(12,len(data),66):
        h=struct.unpack_from('<Q',data,off)[0];desc=data[off+8:off+66]
        if f(desc,len(desc))!=h:raise ValueError('Pipeline description hash mismatch')
        _,_,ps,mod=struct.unpack_from('<QQQQ',desc)
        if ps:keys.add((f'{ps:016X}',mod))
    results=[]
    for identity,mod in sorted(keys):
        source=RUN/f'runtime-microcode/ps_{identity}.bin'
        if not source.exists():raise ValueError('Cached pipeline PS missing from XSH')
        prefixes={kind:OUT/f'{identity}-{mod:016X}-{kind}' for kind in ('baseline','unchanged','late')}
        row={'hash':identity,'modification':f'{mod:016X}','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
        for kind in ('baseline','unchanged'):
            probe=ROOT/'out/runtime-shader-probe'/('probe' if kind=='baseline' else CANDIDATE+'/probe')
            run=subprocess.run([str(probe),str(source),str(prefixes[kind]),f'{mod:X}','all','fsi'],capture_output=True,text=True)
            if run.returncode:raise RuntimeError(identity+' '+kind+run.stderr)
            row[kind+'_metadata']=run.stdout
        row['bit0_identical']=prefixes['baseline'].with_suffix('.spv').read_bytes()==prefixes['unchanged'].with_suffix('.spv').read_bytes()
        if not row['bit0_identical']:raise ValueError('Noncandidate output changed')
        row['shader_body_eligible']=bool(re.search(r'kills=0 depth=0 memexport=0 ',row['baseline_metadata']))
        if row['shader_body_eligible']:
            run=subprocess.run([str(ROOT/'out/runtime-shader-probe'/CANDIDATE/'probe'),str(source),str(prefixes['late']),f'{mod|(1<<BIT):X}','all','fsi'],capture_output=True,text=True)
            if run.returncode:raise RuntimeError(identity+' late '+run.stderr)
            row['late_metadata']=run.stdout
        results.append(row)
    (OUT/'translations.json').write_text(json.dumps({'pipeline_records':(len(data)-12)//66,'packed_description_hashes_validated':True,'variants':results,'limitation':'No depth/stencil/alpha draw-state capture; candidate forced only on eligible guest bodies for local translator validation'},indent=2)+'\n')
    print(json.dumps({'cached_ps_variants':len(results),'unchanged_byte_matches':sum(r['bit0_identical'] for r in results),'potential_late_variants':sum(r['shader_body_eligible'] for r in results)}))

def validate():
    result=json.loads((OUT/'translations.json').read_text());checks=[]
    for p in sorted(OUT.glob('*.spv')):
        run=subprocess.run(['/usr/local/bin/spirv-val','--target-env','vulkan1.2','--scalar-block-layout',str(p)],capture_output=True,text=True)
        checks.append({'file':p.name,'exit_code':run.returncode,'diagnostic':run.stderr+run.stdout})
    result['validation']=checks;result['failures']=sum(c['exit_code']!=0 for c in checks)
    (OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'checked':len(checks),'failed':result['failures']}))
    if result['failures']:raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=['translate','validate']);p.add_argument('--candidate',default='candidate');p.add_argument('--bit',type=int,choices=[49,50],default=49);p.add_argument('--output',default='batch');a=p.parse_args()
    CANDIDATE=a.candidate;BIT=a.bit;OUT=ROOT/'out/runtime-shader-probe'/a.output
    translate() if a.phase=='translate' else validate()
