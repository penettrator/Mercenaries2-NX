from pathlib import Path
import subprocess, concurrent.futures, json
root=Path('/work'); sdk=root/'reference/masseffect-nx/sdk'
incs=[root/'app/generated/default',sdk/'include',sdk/'thirdparty/fmt/include',sdk/'thirdparty/spdlog/include',sdk/'thirdparty/simde',Path('/opt/devkitpro/libnx/include')]
base=['/opt/devkitpro/devkitA64/bin/aarch64-none-elf-g++','-std=gnu++23','-D__SWITCH__','-DNX','-D_GNU_SOURCE','-DSPDLOG_NO_TZ_OFFSET','-march=armv8-a+crc+crypto','-mtp=soft','-fsyntax-only']+['-I'+str(p) for p in incs]
files=sorted((root/'app/generated/default').glob('*recomp*.cpp'))
logs=root/'out/arm64-check';logs.mkdir(parents=True,exist_ok=True)
def check(p):
 r=subprocess.run(base+[str(p)],capture_output=True,text=True)
 if r.returncode:(logs/(p.name+'.log')).write_text(r.stdout+r.stderr)
 return {'file':p.name,'exit_code':r.returncode}
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for i,r in enumerate(pool.map(check,files),1):
  results.append(r)
  if i%10==0 or r['exit_code']:print(f"{i}/{len(files)} checked; {r}",flush=True)
report={'checked':len(results),'failed':sum(r['exit_code']!=0 for r in results),'results':results}
(logs/'report.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='results'}),flush=True)
raise SystemExit(bool(report['failed']))
