"""Compile HLSL to Vulkan 1.2 SPIR-V; report failures without accepting them."""
import concurrent.futures
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DXC = ROOT/'tools/bin/dxc-linux/bin/dxc'
INPUT = ROOT/'out/shaders/hlsl'
OUTPUT = ROOT/'out/shaders/spirv'

def one(source):
    target = OUTPUT/source.with_suffix('.spv').name
    args = [str(DXC), '-spirv', '-T', 'ps_6_6' if source.name.startswith('ps_') else 'vs_6_6',
            '-E', 'main', '-HV', '2021', '-fspv-target-env=vulkan1.2', '-fvk-use-dx-layout',
            '-Werror=parameter-usage', '-Fo', str(target), str(source)]
    if source.name.startswith('vs_'):
        args.append('-fvk-invert-y')
    result = subprocess.run(args, capture_output=True, timeout=120)
    valid = result.returncode == 0 and target.is_file() and target.read_bytes()[:4] == b'\x03\x02\x23\x07'
    log = OUTPUT/(source.stem+'.error.txt')
    if valid:
        log.unlink(missing_ok=True)
    else:
        log.write_bytes(result.stdout+result.stderr)
        target.unlink(missing_ok=True)
    return {'source': source.name, 'exit_code': result.returncode, 'compiled': valid}

def main():
    subprocess.run([str(DXC), '--version'], capture_output=True, check=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    sources = sorted(INPUT.glob('*.hlsl'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(one, sources))
    report={'total':len(results),'compiled':sum(r['compiled'] for r in results),
            'failed':[r for r in results if not r['compiled']],
            'external_spirv_validation':False}
    (OUTPUT.parent/'spirv.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'total':report['total'], 'compiled':report['compiled'], 'failure_count':len(report['failed'])},indent=2))
    if not sources or report['failed']:
        raise SystemExit(1)

if __name__=='__main__':
    main()
