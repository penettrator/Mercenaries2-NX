"""SDK patch: vertex-shader NoContraction only on the position slice (HANDOFF section 67).

cvar gpu_vs_contraction_outside_position (default false). Edits, all idempotent (marker checks):
- spirv_builder.h/.cpp: SetNoContractionEnabled(); the NoContraction helpers honour it.
- translator.h/.cpp: current_alu_instruction_offset() around ProcessAluInstruction.
- spirv_translator.h/.cpp/_alu.cpp: ComputeVertexPositionSlice (backward slice over temp
  registers from the position / point size export, ignoring control flow), applied per ALU
  instruction; bails out on dynamic register addressing, memexport and predication.
usage: python tools/sdk_patch_position_slice.py [sdk dir]
"""
import os, sys

root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reference', 'masseffect-nx', 'sdk')
if 'PreparePositionSlice' in open(root + '/src/graphics/pipeline/shader/spirv_translator_alu.cpp',
                                  encoding='utf-8').read():
    print('position slice already present')
    sys.exit(0)

# spirv_builder.h / .cpp
h = root + '/include/rex/graphics/pipeline/shader/spirv_builder.h'
s = open(h, newline='').read()
old = '''  spv::Id createNoContractionUnaryOp(spv::Op op_code, spv::Id type_id, spv::Id operand);'''
new = '''  // Mercenaries 2 (HANDOFF section 67): false while translating guest ALU instructions that do
  // not feed the vertex position, so the driver may fuse multiply-add there. The helpers below
  // then create plain operations.
  void SetNoContractionEnabled(bool enabled) { no_contraction_enabled_ = enabled; }
  bool IsNoContractionEnabled() const { return no_contraction_enabled_; }

  spv::Id createNoContractionUnaryOp(spv::Op op_code, spv::Id type_id, spv::Id operand);'''
assert s.count(old) == 1
s = s.replace(old, new)
i = s.index('class SpirvBuilder : public spv::Builder {')
NL = chr(10)
j = s.index(NL + '};' + NL + NL + '}  // namespace', i)
s = s[:j] + NL + NL + ' private:' + NL + '  bool no_contraction_enabled_ = true;' + s[j:]
open(h, 'w', newline='').write(s)
c = root + '/src/graphics/pipeline/shader/spirv_builder.cpp'
s = open(c, newline='').read()
assert s.count('  addDecoration(result, spv::DecorationNoContraction);') == 2
s = s.replace('  addDecoration(result, spv::DecorationNoContraction);',
              '  if (no_contraction_enabled_) addDecoration(result, spv::DecorationNoContraction);')
open(c, 'w', newline='').write(s)

# translator.h / .cpp
h = root + '/include/rex/graphics/pipeline/shader/translator.h'
s = open(h, newline='').read()
old = '''  virtual void ProcessAluInstruction(const ParsedAluInstruction& /*instr*/,
                                     uint8_t /*memexport_eM_potentially_written_before*/) {}
'''
assert s.count(old) == 1
s = s.replace(old, old + '''
  // Ucode instruction index (dword offset / 3) of the ALU instruction being processed, valid
  // inside ProcessAluInstruction (Mercenaries 2, HANDOFF section 67).
  uint32_t current_alu_instruction_offset() const { return current_alu_instruction_offset_; }
''')
old = '''  // Kept for supporting vfetch_mini.
  ucode::VertexFetchInstruction previous_vfetch_full_;
};'''
assert s.count(old) == 1
s = s.replace(old, '''  // Kept for supporting vfetch_mini.
  ucode::VertexFetchInstruction previous_vfetch_full_;

  uint32_t current_alu_instruction_offset_ = UINT32_MAX;
};''')
open(h, 'w', newline='').write(s)
c = root + '/src/graphics/pipeline/shader/translator.cpp'
s = open(c, newline='').read()
old = '''      ParseAluInstruction(op, current_shader().type(), alu_instr);
      ProcessAluInstruction(alu_instr, eM_potentially_written_before);'''
assert s.count(old) == 1
s = s.replace(old, '''      ParseAluInstruction(op, current_shader().type(), alu_instr);
      current_alu_instruction_offset_ = instr_offset;
      ProcessAluInstruction(alu_instr, eM_potentially_written_before);
      current_alu_instruction_offset_ = UINT32_MAX;''')
open(c, 'w', newline='').write(s)

# spirv_translator.h members
h = root + '/include/rex/graphics/pipeline/shader/spirv_translator.h'
s = open(h, 'rb').read().decode()
CRLF = chr(13) + chr(10)
old = '  std::unique_ptr<SpirvBuilder> builder_;' + CRLF
assert s.count(old) == 1
s = s.replace(old, old + CRLF + CRLF.join([
    '  // Mercenaries 2 (HANDOFF section 67, cvar gpu_vs_contraction_outside_position): per ucode',
    '  // instruction index of a vertex shader, 1 if the ALU instruction may feed the position (or the',
    '  // point size / vertex kill export) and keeps NoContraction; others may be fused by the driver.',
    '  std::vector<uint8_t> position_slice_alu_;',
    '  bool position_slice_active_ = false;']) + CRLF)
open(h, 'wb').write(s.encode())

alu = root + '/src/graphics/pipeline/shader/spirv_translator_alu.cpp'
s = open(alu, encoding='utf-8', newline='').read()

helper = r'''namespace rex::graphics {

namespace {

// Mercenaries 2 (HANDOFF section 67): ALU instructions of a vertex shader that may feed the
// position export (or the point size / edge flag / vertex kill export), found by a backward
// slice over temporary registers that ignores control flow (so it can only over-approximate).
// Everything else may be fused into multiply-add by the driver: the NoContraction decoration
// only matters where two passes must compute bit-identical depth. Returns false (everything
// stays precise) where the analysis would not be exact enough: dynamically addressed
// registers, memory export, predication.
bool ComputeVertexPositionSlice(const Shader& shader, std::vector<uint8_t>& precise) {
  using namespace ucode;
  const std::vector<uint32_t>& ucode_dwords = shader.ucode_data();
  const uint32_t instruction_count = uint32_t(ucode_dwords.size() / 3);
  precise.assign(instruction_count, 1);
  if (shader.uses_register_dynamic_addressing() || shader.memexport_eM_written()) {
    return false;
  }
  struct Alu {
    uint32_t offset;
    ParsedAluInstruction parsed;
    AluOpChangedState changed_state;
  };
  std::vector<Alu> alus;
  for (uint32_t i = 0; i < shader.cf_pair_index_bound(); ++i) {
    ControlFlowInstruction cf_ab[2];
    UnpackControlFlowInstructions(ucode_dwords.data() + i * 3, cf_ab);
    for (uint32_t j = 0; j < 2; ++j) {
      const ControlFlowInstruction& cf = cf_ab[j];
      ParsedExecInstruction exec;
      switch (cf.opcode()) {
        case ControlFlowOpcode::kExec:
        case ControlFlowOpcode::kExecEnd:
          ParseControlFlowExec(cf.exec, i * 2 + j, exec);
          break;
        case ControlFlowOpcode::kCondExec:
        case ControlFlowOpcode::kCondExecEnd:
        case ControlFlowOpcode::kCondExecPredClean:
        case ControlFlowOpcode::kCondExecPredCleanEnd:
          ParseControlFlowCondExec(cf.cond_exec, i * 2 + j, exec);
          break;
        case ControlFlowOpcode::kCondExecPred:
        case ControlFlowOpcode::kCondExecPredEnd:
          return false;
        default:
          continue;
      }
      uint32_t sequence = exec.sequence;
      for (uint32_t offset = exec.instruction_address;
           offset < exec.instruction_address + exec.instruction_count; ++offset, sequence >>= 2) {
        if (sequence & 0b01) {
          continue;  // Fetch.
        }
        if (offset >= instruction_count) {
          return false;
        }
        const auto& op = *reinterpret_cast<const AluInstruction*>(ucode_dwords.data() + offset * 3);
        Alu alu;
        alu.offset = offset;
        ParseAluInstruction(op, shader.type(), alu.parsed);
        if (alu.parsed.IsNop()) {
          continue;
        }
        alu.changed_state = AluOpChangedState(
            GetAluVectorOpcodeInfo(op.vector_opcode()).changed_state |
            GetAluScalarOpcodeInfo(op.scalar_opcode()).changed_state);
        if (alu.parsed.is_predicated || (alu.changed_state & kAluOpChangedStatePredicate)) {
          return false;
        }
        alus.push_back(alu);
      }
    }
  }

  auto is_root = [](const InstructionResult& result) {
    return result.GetUsedWriteMask() &&
           (result.storage_target == InstructionStorageTarget::kPosition ||
            result.storage_target == InstructionStorageTarget::kPointSizeEdgeFlagKillVertex);
  };
  auto reads_previous_scalar = [](AluScalarOpcode opcode) {
    return opcode == AluScalarOpcode::kAddsPrev || opcode == AluScalarOpcode::kMulsPrev ||
           opcode == AluScalarOpcode::kMulsPrev2 || opcode == AluScalarOpcode::kSubsPrev ||
           opcode == AluScalarOpcode::kRetainPrev;
  };
  uint64_t needed_registers = 0;
  bool needed_previous_scalar = false;
  bool needed_address_register = false;
  std::vector<uint8_t> marked(alus.size(), 0);
  auto mark = [&](size_t index) {
    marked[index] = 1;
    const ParsedAluInstruction& p = alus[index].parsed;
    auto add_operand = [&](const InstructionOperand& operand) {
      if (operand.storage_source == InstructionStorageSource::kRegister) {
        needed_registers |= uint64_t(1) << (operand.storage_index & 63);
      }
      if (operand.storage_addressing_mode ==
          InstructionStorageAddressingMode::kAddressRegisterRelative) {
        needed_address_register = true;
      }
    };
    for (uint32_t k = 0; k < p.vector_operand_count; ++k) add_operand(p.vector_operands[k]);
    for (uint32_t k = 0; k < p.scalar_operand_count; ++k) add_operand(p.scalar_operands[k]);
    if (reads_previous_scalar(p.scalar_opcode)) {
      needed_previous_scalar = true;
    }
  };
  auto writes_needed_register = [&](const InstructionResult& result) {
    return result.GetUsedWriteMask() &&
           result.storage_target == InstructionStorageTarget::kRegister &&
           (needed_registers & (uint64_t(1) << (result.storage_index & 63)));
  };
  for (bool changed = true; changed;) {
    changed = false;
    for (size_t index = 0; index < alus.size(); ++index) {
      if (marked[index]) {
        continue;
      }
      const Alu& alu = alus[index];
      const ParsedAluInstruction& p = alu.parsed;
      bool needed = is_root(p.vector_and_constant_result) || is_root(p.scalar_result) ||
                    writes_needed_register(p.vector_and_constant_result) ||
                    writes_needed_register(p.scalar_result) ||
                    (needed_previous_scalar && p.scalar_opcode != AluScalarOpcode::kRetainPrev) ||
                    (needed_address_register &&
                     (alu.changed_state & kAluOpChangedStateAddressRegister));
      if (needed) {
        mark(index);
        changed = true;
      }
    }
  }
  for (size_t index = 0; index < alus.size(); ++index) {
    precise[alus[index].offset] = marked[index];
  }
  return true;
}

}  // namespace
'''
old_ns = 'namespace rex::graphics {\n\nspv::Id SpirvShaderTranslator::ZeroIfAnyOperandIsZero('
assert s.count(old_ns) == 1
s = s.replace(old_ns, helper + '\nspv::Id SpirvShaderTranslator::ZeroIfAnyOperandIsZero(', 1)

old_proc = '''  UpdateInstructionPredication(instr.is_predicated, instr.predicate_condition);
'''
assert s.count(old_proc) == 1
new_proc = '''  // Mercenaries 2 (HANDOFF section 67): outside the position slice the driver may fuse
  // multiply-add; the guard restores NoContraction for everything after this instruction.
  struct NoContractionGuard {
    SpirvBuilder& builder;
    ~NoContractionGuard() { builder.SetNoContractionEnabled(true); }
  } no_contraction_guard{*builder_};
  if (position_slice_active_) {
    uint32_t offset = current_alu_instruction_offset();
    builder_->SetNoContractionEnabled(offset >= position_slice_alu_.size() ||
                                      position_slice_alu_[offset] != 0);
  }

  UpdateInstructionPredication(instr.is_predicated, instr.predicate_condition);
'''
s = s.replace(old_proc, new_proc, 1)

# Entry point called from StartTranslation.
s = s.replace('}  // namespace\n', '''}  // namespace

void SpirvShaderTranslator::PreparePositionSlice(bool enabled) {
  position_slice_active_ = false;
  position_slice_alu_.clear();
  if (!enabled || !is_vertex_shader()) {
    return;
  }
  position_slice_active_ = ComputeVertexPositionSlice(current_shader(), position_slice_alu_);
}
''', 1)
open(alu, 'w', encoding='utf-8', newline='').write(s)

# Declaration in the header.
h = root + '/include/rex/graphics/pipeline/shader/spirv_translator.h'
t = open(h, 'rb').read().decode()
old_h = '  std::vector<uint8_t> position_slice_alu_;\r\n'
assert t.count(old_h) == 1
t = t.replace(old_h, old_h.replace('  std::vector', '  void PreparePositionSlice(bool enabled);\r\n  std::vector'), 1)
open(h, 'wb').write(t.encode())

# Call it in StartTranslation, after the builder exists.
tr = root + '/src/graphics/pipeline/shader/spirv_translator.cpp'
u = open(tr, encoding='utf-8', newline='').read()
old_st = '''  builder_ = std::make_unique<SpirvBuilder>(features_.spirv_version, (kSpirvMagicToolId << 16) | 1,
                                            nullptr);
'''
assert u.count(old_st) == 1
u = u.replace(old_st, old_st + '''  PreparePositionSlice(REXCVAR_GET(gpu_vs_contraction_outside_position));
''', 1)
old_inc = '#include <rex/assert.h>\n'
assert u.count(old_inc) == 1
u = u.replace(old_inc, old_inc + '#include <rex/cvar.h>\n', 1)
old_ns2 = '\nnamespace rex::graphics {\n'
i = u.index(old_ns2)
u = u[:i] + '''

// Mercenaries 2 (HANDOFF section 67). Off: every guest ALU operation keeps NoContraction.
REXCVAR_DEFINE_BOOL(gpu_vs_contraction_outside_position, false, "GPU",
                    "Vertex shaders: let the driver fuse multiply-add in ALU instructions that "
                    "cannot affect the position (backward slice from the position export)");
''' + u[i:]
open(tr, 'w', encoding='utf-8', newline='').write(u)
print('ok')
