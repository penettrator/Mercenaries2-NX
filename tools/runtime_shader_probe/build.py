#!/usr/bin/env python3
"""Isolated actual-runtime translator probe; no SDK modifications or downloads.
First: build.py baseline --reuse (uses existing source/header baseline snapshot).
Fresh candidate: build.py candidate --snapshot (copies live SDK before compiling).
"""
from pathlib import Path
import subprocess,hashlib,json,shutil,sys,concurrent.futures
root=Path('/work'); sdk=root/'reference/masseffect-nx/sdk'; base=root/'out/runtime-shader-probe'
label=sys.argv[1] if len(sys.argv)>1 else 'baseline'; out=base if label=='baseline' else base/label; out.mkdir(parents=True,exist_ok=True)
files=['shader.cpp','translator.cpp','translator_disasm.cpp','spirv_builder.cpp','spirv.cpp','spirv_translator.cpp','spirv_translator_alu.cpp','spirv_translator_fetch.cpp','spirv_translator_memexport.cpp','spirv_translator_rb.cpp']
sources=[sdk/'src/graphics/pipeline/shader'/f for f in files]+[sdk/'src/core/string_buffer.cpp',sdk/'src/graphics/format/ucode.cpp']
gls=sdk/'thirdparty/glslang'
sources += [gls/'SPIRV'/f for f in ['SpvBuilder.cpp','SpvPostProcess.cpp','Logger.cpp','InReadableOrder.cpp']]
if '--snapshot' in sys.argv:
 for src in sources:
  dst=out/'sources'/src.relative_to(sdk); dst.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(src,dst)
 shutil.copytree(sdk/'include/rex',out/'headers/rex',dirs_exist_ok=True)
manifest=[]; copies=[]
for src in sources:
 dst=out/'sources'/src.relative_to(sdk); copies.append(dst)
 manifest.append({'source':str(src.relative_to(root)),'sha256':hashlib.sha256(dst.read_bytes()).hexdigest()})
for hdr in sorted((out/'headers').rglob('*')):
 if hdr.is_file(): manifest.append({'header':str(hdr.relative_to(out/'headers')),'sha256':hashlib.sha256(hdr.read_bytes()).hexdigest()})
(out/'sources.json').write_text(json.dumps(manifest,indent=2))
cmd=['g++','-std=c++23','-O0','-DNDEBUG','-DFMT_HEADER_ONLY','-ffunction-sections','-fdata-sections','-include','cstring','-include','algorithm']
if '--texture-signs' in sys.argv: cmd += ['-DMERCS_TEXTURE_SIGN_PROBE']
if '--structured-jumps' in sys.argv: cmd += ['-DMERCS_STRUCTURED_JUMPS_PROBE']
for p in [root/'tools/runtime_shader_probe/shim',out/'headers',gls,gls/'SPIRV',sdk/'thirdparty/fmt/include',sdk/'thirdparty/spirv-headers/include',sdk/'thirdparty/vulkan-headers/include',sdk/'thirdparty/simde',sdk/'thirdparty/renderdoc']:
 cmd+=['-I'+str(p)]
all_sources=[root/'tools/runtime_shader_probe/main.cpp',root/'tools/runtime_shader_probe/support.cpp']+copies
objects=[out/'objects'/(s.stem+'.o') for s in all_sources]; objects[0].parent.mkdir(exist_ok=True)
def compile_one(pair):
 source,obj=pair; command=cmd+[str(source),'-c','-o',str(obj)]
 if '--relink' in sys.argv and obj.exists(): return command,0,''
 p=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 return command,p.returncode,p.stdout
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(compile_one,zip(all_sources,objects)))
(out/'build-command.json').write_text(json.dumps([r[0] for r in results],indent=2))
log=''.join(r[2] for r in results); code=max(r[1] for r in results)
if not code:
 p=subprocess.run(['g++']+list(map(str,objects))+['-Wl,--gc-sections','-o',str(out/'probe')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True); log+=p.stdout; code=p.returncode
(out/'build.log').write_text(log); print(log[-18000:]); raise SystemExit(code)

