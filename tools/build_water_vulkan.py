"""Build and validate pinned corrected resolve SPIR-V; install only after all checks.
Run inside devkita64 with glslang-tools, spirv-tools and libglm-dev installed.
"""
from pathlib import Path
import re, json, subprocess, struct, hashlib, shutil
ROOT=Path('/work');SRC=ROOT/'tools/patches/xenia-water-vulkan/source/src/xenia/gpu/shaders'
OUT=ROOT/'out/water-vulkan-build';OUT.mkdir(exist_ok=True)
SDK=ROOT/'reference/masseffect-nx/sdk/src/graphics/shaders/vulkan_spirv'
def run(args,**kw):return subprocess.run(args,check=True,**kw)
def words(data):return struct.unpack('<'+'I'*(len(data)//4),data)
def interface(data):
    w=words(data);i=5;decor={};ptr={};vars=[];offsets={};local=[];entries=[]
    while i<len(w):
        n=w[i]>>16;op=w[i]&65535;a=w[i+1:i+n]
        if not n:raise ValueError('Zero-length instruction')
        if op==71 and a[1] in [33,34]:decor.setdefault(a[0],{})[a[1]]=a[2]
        if op==72 and a[2]==35:offsets.setdefault(a[0],{})[a[1]]=a[3]
        if op==32:ptr[a[0]]=(a[1],a[2])
        if op==59:vars.append(a[:3])
        if op==16 and a[1]==17:local.append(list(a[2:]))
        if op==15:entries.append(a[0])
        i+=n
    push=[]
    for typ,vid,storage in vars:
        if storage==9:push.append(sorted(offsets.get(ptr[typ][1],{}).items()))
    return {'descriptors':sorted((d[34],d[33]) for d in decor.values() if 33 in d and 34 in d),'push_offsets':push,'local_sizes':local,'entry_models':entries}
def old_binary(path):
    text=path.read_text();body=text[text.index('const uint32_t'):]
    return b''.join(struct.pack('<I',int(x,16)) for x in re.findall(r'0x([0-9A-Fa-f]{8})',body))
wrapper='#version 460\n#extension GL_EXT_control_flow_attributes : require\n#extension GL_EXT_samplerless_texture_functions : require\n#extension GL_GOOGLE_include_directive : require\n#include "%s"\n'
reports=[]
for bits in [8,16,32,64,128]:
    for suffix in ['', '_scaled']:
        name=f'resolve_full_{bits}bpp{suffix}_cs';raw=OUT/f'{name}.raw.spv';binary=OUT/f'{name}.spv'
        run(['glslangValidator','--stdin','-DSHADING_LANGUAGE_GLSL_XE=1','-S','comp','-o',str(raw),'-V',f'-I{SRC}'],input=wrapper%f'resolve_full_{bits}bpp{suffix}.cs.xesl',text=True,capture_output=True)
        run(['spirv-opt','-O','--compact-ids',str(raw),'-o',str(binary)])
        run(['spirv-val','--target-env','vulkan1.0',str(binary)])
        dis=run(['spirv-dis',str(binary)],capture_output=True,text=True).stdout
        data=binary.read_bytes();old=interface(old_binary(SDK/f'{name}.h'));new=interface(data)
        if old!=new:raise RuntimeError(f'{name} descriptor/push/local ABI mismatch: {old} != {new}')
        h=OUT/f'{name}.h'
        rows=['    '+', '.join(f'0x{x:08X}' for x in words(data)[i:i+8])+',' for i in range(0,len(words(data)),8)]
        h.write_text('// Generated from pinned BSD Xenia sources via tools/build_water_vulkan.py.\n#if 0\n'+dis+'#endif\nconst uint32_t '+name+'[] = {\n'+'\n'.join(rows)+'\n};\n')
        reports.append({'name':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'interface':new,'spirv_val':True,'interface_matches_original':True})
# Execute the actual upstream pack helper on host with GLM vector constructors.
text=(SRC/'pixel_formats.xesli').read_text();start=text.index('uint XePackR16G16Edram(');end=text.index('\n}',start)+2
helper=text[start:end]
start4=text.index('uint2_xe XePackR16G16B16A16Edram(');end4=text.index('\n}',start4)+2
helper+='\n'+text[start4:end4]
cpp='''#include <glm/glm.hpp>
#include <cstdint>
#include <cstdio>
using uint=uint32_t;using float2_xe=glm::vec2;using int2_xe=glm::ivec2;
using float4_xe=glm::vec4;using int4_xe=glm::ivec4;using uint2_xe=glm::uvec2;
#define float_x2_xe glm::vec2
#define float_x4_xe glm::vec4
using glm::min;using glm::max;
'''+helper+'''
int main(){ struct Case {float v;uint16_t bits;};
Case cases[]={{-40,0x8001},{-32,0x8001},{-16,0xc001},{-1,0xfc01},{0,0},{1,0x03ff},{16,0x3fff},{32,0x7fff},{40,0x7fff}};
for(auto c:cases){uint p=XePackR16G16Edram(glm::vec2(c.v,c.v));
uint expected=uint(c.bits)|(uint(c.bits)<<16);
auto p4=XePackR16G16B16A16Edram(glm::vec4(c.v));
if(p!=expected || p4.x!=expected || p4.y!=expected){printf("FAIL %f %08x expected %08x\\n",c.v,p,expected);return 1;}}
puts("18 signed range/boundary pack cases passed (actual pinned helper)");}
'''
(OUT/'pack_probe.cpp').write_text(cpp);run(['g++','-std=c++17','-fsanitize=undefined','-o',str(OUT/'pack_probe'),str(OUT/'pack_probe.cpp')]);run([str(OUT/'pack_probe')])
(OUT/'validation.json').write_text(json.dumps({'kernels':reports,'actual_source_host_pack_cases':18,'gpu_execution_tested':False,'tools':run(['glslangValidator','--version'],capture_output=True,text=True).stdout},indent=2)+'\n')
backup=OUT/'original-headers';backup.mkdir(exist_ok=True)
for r in reports:
    name=r['name']+'.h';dest=SDK/name
    if not (backup/name).exists():shutil.copy2(dest,backup/name)
    shutil.copy2(OUT/name,dest)
print('Validated and installed all 10 kernels; console unchanged')
