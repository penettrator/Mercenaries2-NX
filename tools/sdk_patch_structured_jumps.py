"""Structured forward jumps in the SPIR-V shader translator (HANDOFF B:94).

Xenos shaders with any jump are translated as `loop { switch (pc) { case label: ... } }`
with DontUnroll/DontFlatten, which the driver cannot simplify (Mercenaries 2's lighting
shaders: 50-77k NAK static cycles). When every jump of a shader goes forward, the jump
regions nest, and there are no loops, calls or returns, each jump is emitted instead as
`if (!taken) { code up to the label }` and the program counter switch is not created.
The single-iteration main loop stays (exece breaks out of it), as for shaders without
jumps. Same semantics: the code between a taken jump and its label is skipped.

No cvar in the SDK: the caller opts in per translator instance
(SetStructuredForwardJumpsEnabled) before translating; default false keeps the original
code byte for byte. Idempotent; fails loudly if an anchor changed.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else \
    Path(__file__).resolve().parents[1] / 'reference/masseffect-nx/sdk'
H = 'include/rex/graphics/pipeline/shader/spirv_translator.h'
C = 'src/graphics/pipeline/shader/spirv_translator.cpp'


def edit(rel, old, new, count=1):
    p = root / rel
    text = p.read_text(encoding='utf-8')
    if new in text:
        return
    if text.count(old) != count:
        raise RuntimeError(f'Unexpected source anchor in {rel}: {old[:60]!r}')
    p.write_text(text.replace(old, new), encoding='utf-8')


edit(H, '''  uint64_t GetDefaultVertexShaderModification(
      uint32_t dynamic_addressable_register_count,''', '''  // Mercenaries 2 (HANDOFF B:94), native caller opt-in: shaders whose jumps all go forward
  // and nest are emitted with structured ifs instead of the program counter switch.
  void SetStructuredForwardJumpsEnabled(bool enabled) {
    structured_forward_jumps_enabled_ = enabled;
  }

  uint64_t GetDefaultVertexShaderModification(
      uint32_t dynamic_addressable_register_count,''')
edit(H, '''  spv::Id main_loop_pc_next_;
''', '''  spv::Id main_loop_pc_next_;
  // Structured forward jumps (SetStructuredForwardJumpsEnabled).
  bool structured_forward_jumps_enabled_ = false;
  bool structured_jumps_active_ = false;
  struct StructuredJumpRegion {
    uint32_t end;
    spv::Block* merge;
  };
  std::vector<StructuredJumpRegion> structured_jump_regions_;
  bool IsStructuredJumpsEligible() const;
  void CloseStructuredJumpRegions(uint32_t cf_index);
  bool HasMainSwitch() const {
    return !current_shader().label_addresses().empty() && !structured_jumps_active_;
  }
''')

edit(C, '''  main_switch_op_.reset();
  main_switch_next_pc_phi_operands_.clear();
  main_loop_exit_ = nullptr;
''', '''  main_switch_op_.reset();
  main_switch_next_pc_phi_operands_.clear();
  main_loop_exit_ = nullptr;
  structured_jumps_active_ = false;
  structured_jump_regions_.clear();
''')
edit(C, '''  // If no jumps, don't create a switch, but still create a loop so exece can
  // break.
  bool has_main_switch = !current_shader().label_addresses().empty();
''', '''  // If no jumps, don't create a switch, but still create a loop so exece can
  // break.
  structured_jumps_active_ = structured_forward_jumps_enabled_ &&
                             !current_shader().label_addresses().empty() &&
                             IsStructuredJumpsEligible();
  bool has_main_switch = HasMainSwitch();
''')
edit(C, '''    // Close flow control within the last switch case.
    CloseExecConditionals();
    bool has_main_switch = !current_shader().label_addresses().empty();
''', '''    // Close flow control within the last switch case.
    CloseExecConditionals();
    if (structured_jumps_active_) {
      // Jumps to the end of the program have no label instruction to close them.
      CloseStructuredJumpRegions(UINT32_MAX);
    }
    bool has_main_switch = HasMainSwitch();
''')
edit(C, '''void SpirvShaderTranslator::ProcessLabel(uint32_t cf_index) {
  if (cf_index == 0) {
    // 0 already added in the beginning.
    return;
  }
''', '''void SpirvShaderTranslator::ProcessLabel(uint32_t cf_index) {
  if (structured_jumps_active_) {
    // The end of every jump region that targets this label.
    CloseExecConditionals();
    CloseStructuredJumpRegions(cf_index);
    return;
  }
  if (cf_index == 0) {
    // 0 already added in the beginning.
    return;
  }
''')
edit(C, '''      builder_->createBranch(current_shader().label_addresses().empty() ? main_loop_merge_
                                                                        : main_switch_merge_);''',
     '''      builder_->createBranch(HasMainSwitch() ? main_switch_merge_ : main_loop_merge_);''')
edit(C, '''void SpirvShaderTranslator::ProcessJumpInstruction(const ParsedJumpInstruction& instr) {
''', '''bool SpirvShaderTranslator::IsStructuredJumpsEligible() const {
  const Shader& shader = current_shader();
  const uint32_t* ucode_dwords = shader.ucode_data().data();
  std::vector<std::pair<uint32_t, uint32_t>> regions;
  for (uint32_t i = 0; i < shader.cf_pair_index_bound(); ++i) {
    ucode::ControlFlowInstruction cf_ab[2];
    ucode::UnpackControlFlowInstructions(ucode_dwords + i * 3, cf_ab);
    for (uint32_t j = 0; j < 2; ++j) {
      const uint32_t cf_index = i * 2 + j;
      switch (cf_ab[j].opcode()) {
        case ucode::ControlFlowOpcode::kLoopStart:
        case ucode::ControlFlowOpcode::kLoopEnd:
        case ucode::ControlFlowOpcode::kCondCall:
        case ucode::ControlFlowOpcode::kReturn:
          return false;
        case ucode::ControlFlowOpcode::kCondJmp: {
          ParsedJumpInstruction instr;
          ParseControlFlowCondJmp(cf_ab[j].cond_jmp, cf_index, instr);
          if (instr.target_address <= cf_index) {
            return false;
          }
          regions.emplace_back(cf_index, instr.target_address);
        } break;
        default:
          break;
      }
    }
  }
  // Regions (jump, label] must nest: a jump inside a region cannot go past its end.
  std::vector<uint32_t> open_ends;
  for (const auto& [start, end] : regions) {
    while (!open_ends.empty() && open_ends.back() <= start) {
      open_ends.pop_back();
    }
    if (!open_ends.empty() && end > open_ends.back()) {
      return false;
    }
    open_ends.push_back(end);
  }
  // Every label must be the target of one of these jumps.
  for (uint32_t label : shader.label_addresses()) {
    bool targeted = false;
    for (const auto& region : regions) {
      if (region.second == label) {
        targeted = true;
        break;
      }
    }
    if (!targeted) {
      return false;
    }
  }
  return true;
}

void SpirvShaderTranslator::CloseStructuredJumpRegions(uint32_t cf_index) {
  while (!structured_jump_regions_.empty() && structured_jump_regions_.back().end <= cf_index) {
    spv::Block* merge = structured_jump_regions_.back().merge;
    structured_jump_regions_.pop_back();
    spv::Block& inner_block = *builder_->getBuildPoint();
    if (!inner_block.isTerminated()) {
      builder_->createBranch(merge);
    }
    inner_block.getParent().addBlock(merge);
    builder_->setBuildPoint(merge);
  }
}

void SpirvShaderTranslator::ProcessJumpInstruction(const ParsedJumpInstruction& instr) {
  if (structured_jumps_active_) {
    // if (!taken) { the code up to the target label }, closed by ProcessLabel.
    CloseExecConditionals();
    EnsureBuildPointAvailable();
    spv::Id taken;
    if (instr.type == ParsedJumpInstruction::Type::kConditional) {
      id_vector_temp_.clear();
      // Bool constants (member 0), as UpdateExecConditionals reads them.
      id_vector_temp_.push_back(const_int_0_);
      id_vector_temp_.push_back(builder_->makeIntConstant(int(instr.bool_constant_index >> 7)));
      id_vector_temp_.push_back(
          builder_->makeIntConstant(int((instr.bool_constant_index >> 5) & 3)));
      spv::Id bool_constant_scalar = builder_->createLoad(
          builder_->createAccessChain(spv::StorageClassUniform, uniform_bool_loop_constants_,
                                      id_vector_temp_),
          spv::NoPrecision);
      taken = builder_->createBinOp(
          spv::OpINotEqual, type_bool_,
          builder_->createBinOp(
              spv::OpBitwiseAnd, type_uint_, bool_constant_scalar,
              builder_->makeUintConstant(uint32_t(1) << (instr.bool_constant_index & 31))),
          const_uint_0_);
      if (!instr.condition) {
        taken = builder_->createUnaryOp(spv::OpLogicalNot, type_bool_, taken);
      }
    } else if (instr.type == ParsedJumpInstruction::Type::kPredicated) {
      taken = builder_->createLoad(var_main_predicate_, spv::NoPrecision);
      if (!instr.condition) {
        taken = builder_->createUnaryOp(spv::OpLogicalNot, type_bool_, taken);
      }
    } else {
      taken = builder_->makeBoolConstant(true);
    }
    spv::Block* merge =
        new spv::Block(builder_->getUniqueId(), builder_->getBuildPoint()->getParent());
    builder_->createSelectionMerge(merge, spv::SelectionControlMaskNone);
    spv::Block& not_taken = builder_->makeNewBlock();
    builder_->createConditionalBranch(taken, merge, &not_taken);
    builder_->setBuildPoint(&not_taken);
    structured_jump_regions_.push_back({instr.target_address, merge});
    return;
  }
''')
print('structured forward jumps patch applied (or already present) in', root)
