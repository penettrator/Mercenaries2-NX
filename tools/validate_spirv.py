import concurrent.futures, json, subprocess
from pathlib import Path
root=Path('/work/out/shaders'); files=sorted((root/'spirv').glob('*.spv'))
def check(p):
 r=subprocess.run(['spirv-val','--target-env','vulkan1.2',str(p)],capture_output=True,text=True)
 return {'file':p.name,'exit_code':r.returncode,'diagnostic':r.stdout+r.stderr}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(check,files))
report={'checked':len(results),'failed':sum(x['exit_code']!=0 for x in results),'results':results}
(root/'spirv-validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='results'}))
