"""Native-only adaptation of project8 SDK patch0015 texture-sign specialization.
No cvar in SDK: caller opts in before translating; false preserves universal UBO path.
Native cvar/key/plumbing is in native_renderer.cpp. FSI SDK callers remain default false.
"""
from pathlib import Path
import sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'reference/masseffect-nx/sdk'
def edit(rel,old,new):
 p=root/rel; text=p.read_text(encoding='utf-8')
 if new in text:return
 if text.count(old)!=1:raise RuntimeError('Unexpected source anchor: '+rel)
 p.write_text(text.replace(old,new),encoding='utf-8')
edit('include/rex/graphics/pipeline/shader/spirv_translator.h', '  uint64_t GetDefaultVertexShaderModification(', '''  // project8 SDK0015, native caller opt-in; SDK FSI retains the universal path.
  void SetTextureSignSpecializationEnabled(bool enabled) {
    texture_sign_specialization_enabled_ = enabled;
  }

  uint64_t GetDefaultVertexShaderModification(''')
edit('include/rex/graphics/pipeline/shader/spirv_translator.h', '  spv::Id uniform_system_constants_;', '''  spv::Id uniform_system_constants_;
  bool texture_sign_specialization_enabled_ = false;
  // SpecId 0..7, four complete 8-bit fetch signs per word (including gamma).
  spv::Id texture_swizzled_signs_spec_constants_[8];''')
edit('src/graphics/pipeline/shader/spirv_translator.cpp', 'void SpirvShaderTranslator::StartTranslation() {', '''void SpirvShaderTranslator::StartTranslation() {
  for (spv::Id& id : texture_swizzled_signs_spec_constants_) id = spv::NoResult;''')
old='''      id_vector_temp_.clear();
      id_vector_temp_.push_back(builder_->makeIntConstant(kSystemConstantTextureSwizzledSigns));
      id_vector_temp_.push_back(builder_->makeIntConstant(fetch_constant_index >> 4));
      id_vector_temp_.push_back(builder_->makeIntConstant((fetch_constant_index >> 2) & 3));
      // All 32 bits containing the values for 4 fetch constants (use
      // OpBitFieldUExtract to get the signednesses for the specific components
      // of this texture).
      spv::Id swizzled_signs_word = builder_->createLoad(
          builder_->createAccessChain(spv::StorageClassUniform, uniform_system_constants_,
                                      id_vector_temp_),
          spv::NoPrecision);'''
new='''      // project8 SDK0015: specialize the complete sign/gamma word at pipeline creation.
      // Sampling and conversion code below stays unchanged; native supplies exact words.
      spv::Id swizzled_signs_word;
      if (texture_sign_specialization_enabled_) {
        spv::Id& spec = texture_swizzled_signs_spec_constants_[fetch_constant_index >> 2];
        if (spec == spv::NoResult) {
          spec = builder_->makeUintConstant(0, true);
          builder_->addDecoration(spec, spv::DecorationSpecId, int(fetch_constant_index >> 2));
        }
        swizzled_signs_word = spec;
      } else {
        id_vector_temp_.clear();
        id_vector_temp_.push_back(builder_->makeIntConstant(kSystemConstantTextureSwizzledSigns));
        id_vector_temp_.push_back(builder_->makeIntConstant(fetch_constant_index >> 4));
        id_vector_temp_.push_back(builder_->makeIntConstant((fetch_constant_index >> 2) & 3));
        // All 32 bits containing values for four fetch constants.
        swizzled_signs_word = builder_->createLoad(
            builder_->createAccessChain(spv::StorageClassUniform, uniform_system_constants_,
                                        id_vector_temp_),
            spv::NoPrecision);
      }'''
edit('src/graphics/pipeline/shader/spirv_translator_fetch.cpp',old,new)
print('Texture signs patch present: native-only opt-in; universal default retained')
