"""Translate containers independently; keep diagnostics for every failure."""
import concurrent.futures
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CONTAINERS = ROOT / 'out/shaders/containers'
OUTPUT = ROOT / 'out/shaders/hlsl'
TOOL = ROOT / 'out/tools/xenos_hlsl'
COMMON = ROOT / 'reference/masseffect-nx/shaders/XenosRecomp/shader_common.h'

def translate(record):
    source = CONTAINERS / record['file']
    with tempfile.TemporaryDirectory(prefix='mercenaries2-shader-') as work:
        temp = Path(work)
        os.symlink(source, temp / source.name)
        result = subprocess.run([str(TOOL), str(temp), str(temp/'output'), str(COMMON)],
                                capture_output=True, timeout=60)
        generated = temp/'output'/source.with_suffix('.hlsl').name
        valid = result.returncode == 0 and generated.is_file() and generated.stat().st_size > 0
        if valid:
            shutil.copy2(generated, OUTPUT/generated.name)
            (OUTPUT/(source.stem+'.error.txt')).unlink(missing_ok=True)
        else:
            (OUTPUT/(source.stem+'.error.txt')).write_bytes(result.stdout+result.stderr)
        return {'file': source.name, 'exit_code': result.returncode, 'translated': valid}

def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    records = json.loads((CONTAINERS/'index.json').read_text())['records']
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(translate, records))
    summary = {'total': len(results), 'translated': sum(r['translated'] for r in results),
               'failed': [r for r in results if not r['translated']]}
    (OUTPUT.parent/'translation.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    if summary['failed']:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
