"""Exercise SDK LOD/fetch-bound initialization with its real SPIR-V builder.
Extract the production declarations; compile both fixed and pre-fix variants.
This checks the reported store-type defect, not whole game shader validity.
"""
from pathlib import Path
import json, subprocess
root = Path('/work')
out = root/'out/spirv-lod-probe'
out.mkdir(exist_ok=True)
spv = root/'reference/masseffect-nx/sdk/thirdparty/glslang/SPIRV'
source = (root/'reference/masseffect-nx/sdk/src/graphics/pipeline/shader/spirv_translator.cpp').read_text()
start = source.index('    var_main_vfetch_bound_ =')
end = source.index('    var_main_tfetch_gradients_h_ =', start)
fixed = source[start:end]
broken = fixed.replace('    var_main_vfetch_bound_ =', '    var_main_tfetch_lod_ =\n    var_main_vfetch_bound_ =', 1).replace('    var_main_tfetch_lod_ =\n        builder_->createVariable', '        builder_->createVariable', 1)
template = r'''
#include "SpvBuilder.h"
#include <cstdio>
int main() {
  spv::SpvBuildLogger logger;
  spv::Builder builder(0x00010000, 0, &logger);
  auto* builder_ = &builder;
  auto* fn = builder.makeEntryPoint("main");
  (void)fn;
  auto type_int_ = builder.makeIntType(32);
  auto type_float_ = builder.makeFloatType(32);
  auto const_int_0_ = builder.makeIntConstant(0);
  auto const_float_0_ = builder.makeFloatConstant(0);
  spv::Id var_main_vfetch_bound_, var_main_tfetch_lod_;
  DECLARATIONS
  bool separate = var_main_vfetch_bound_ != var_main_tfetch_lod_;
  bool bound_int = builder.getDerefTypeId(var_main_vfetch_bound_) == type_int_;
  bool lod_float = builder.getDerefTypeId(var_main_tfetch_lod_) == type_float_;
  // The real kSetTextureLod supplies a float operand; only matching stores
  // are emitted here to avoid assertions in glslang on the negative case.
  if (lod_float) builder.createStore(builder.makeFloatConstant(1.25f), var_main_tfetch_lod_);
  builder.createStore(builder.makeIntConstant(256), var_main_vfetch_bound_);
  builder.makeReturn(true);
  builder.leaveFunction();
  printf("separate=%d bound_int=%d lod_float=%d\n", separate, bound_int, lod_float);
  return separate && bound_int && lod_float ? 0 : 2;
}
'''
results = []
for label, fragment, expected in [('broken', broken, 2), ('fixed', fixed, 0)]:
    cpp = out/f'{label}.cpp'
    exe = out/label
    cpp.write_text(template.replace('DECLARATIONS', fragment))
    command = ['g++','-std=c++17','-O0','-ffunction-sections','-fdata-sections',f'-I{spv}',f'-I{spv.parent}',str(cpp),str(spv/'SpvBuilder.cpp'),str(spv/'SpvPostProcess.cpp'),str(spv/'Logger.cpp'),'-Wl,--gc-sections','-o',str(exe)]
    subprocess.run(command, check=True)
    run = subprocess.run([str(exe)], capture_output=True, text=True)
    results.append({'variant':label, 'exit_code':run.returncode,'expected':expected,'stdout':run.stdout,'passed':run.returncode==expected})
(out/'result.json').write_text(json.dumps(results, indent=2))
print(json.dumps(results, indent=2))
if not all(r['passed'] for r in results): raise SystemExit(1)
