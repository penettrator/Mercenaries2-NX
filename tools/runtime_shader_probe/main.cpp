#include <rex/graphics/pipeline/shader/spirv_translator.h>
#include <rex/string/buffer.h>
#include <fstream>
#include <iterator>
#include <iostream>
#include <cstdlib>
extern bool probe_cvar_gpu_vs_contraction_outside_position;
int main(int argc, char** argv) {
 if(argc < 4) { std::cerr << "usage: probe input.bin output-prefix modification-hex [all|default] [fsi|host|native] [signs|universal] [ps|vs] [precise|contract]\n"; return 2; }
 std::ifstream in(argv[1], std::ios::binary);
 std::vector<char> bytes((std::istreambuf_iterator<char>(in)), {});
 if(bytes.empty() || bytes.size()%4) return 3;
 std::vector<uint32_t> words(bytes.size()/4); std::memcpy(words.data(),bytes.data(),bytes.size());
 using namespace rex::graphics;
 bool vertex = argc>7 && std::string(argv[7])=="vs";
 probe_cvar_gpu_vs_contraction_outside_position = argc>8 && std::string(argv[8])=="contract";
 Shader shader(vertex ? xenos::ShaderType::kVertex : xenos::ShaderType::kPixel,0,words.data(),words.size(),std::endian::big);
 rex::string::StringBuffer disasm; shader.AnalyzeUcode(disasm);
 std::cout << "kills=" << shader.kills_pixels() << " depth=" << shader.writes_depth()
           << " memexport=" << bool(shader.memexport_eM_written())
           << " rt0=" << shader.writes_color_target(0)
           << " modification_bytes=" << sizeof(SpirvShaderTranslator::Modification) << "\n";
 SpirvShaderTranslator::Features features(argc>4 && std::string(argv[4])=="all");
 features.spirv_version=spv::Spv_1_5;
 // FSI's capabilities are required even in the conservative feature profile.
 features.fragment_shader_sample_interlock=true; features.fragment_stores_and_atomics=true;
 bool fsi=argc<6 || std::string(argv[5])=="fsi";
 bool native=argc>5 && std::string(argv[5])=="native";
 SpirvShaderTranslator translator(features,native,native,fsi);
#ifdef MERCS_TEXTURE_SIGN_PROBE
 translator.SetTextureSignSpecializationEnabled(argc>6 && std::string(argv[6])=="signs");
#endif
#ifdef MERCS_STRUCTURED_JUMPS_PROBE
 // HANDOFF B:94: environment STRUCTURED_JUMPS=1 enables structured forward jumps.
 if(const char* sj=std::getenv("STRUCTURED_JUMPS")) translator.SetStructuredForwardJumpsEnabled(std::string(sj)=="1");
#endif
 uint64_t mod=std::strtoull(argv[3],nullptr,16);
 auto* translation=shader.GetOrCreateTranslation(mod);
 if(!translator.TranslateAnalyzedShader(*translation)) { std::cerr << "translation failed\n"; return 4; }
 auto& binary=translation->translated_binary();
 std::ofstream out(std::string(argv[2])+".spv",std::ios::binary); out.write(reinterpret_cast<const char*>(binary.data()),binary.size());
 std::ofstream asmout(std::string(argv[2])+".ucode.txt"); asmout << shader.ucode_disassembly();
 std::cout << "bytes=" << binary.size() << " modification=" << std::hex << mod << " fsi=" << fsi << "\n";
}
