#if defined(_WIN32)
#include "generated/default/mercenaries2_funcs.h"
#include <rex/hook.h>
#include <cstdlib>
#include <atomic>
#include <fstream>
#include <filesystem>
#include <rex/memory.h>
#include <vector>
extern std::atomic<uint32_t> mercenaries2_enumeration_overlap;
namespace {
bool Enabled() { return std::getenv("MERCENARIES2_TEST_KERNEL_TRACE") != nullptr; }
}
REX_HOOK_RAW(sub_82583030) {
  const bool trace = Enabled();
  const uint32_t stateptr = ctx.r4.u32;
  const uint32_t user = ctx.r3.u32;
  const uint32_t caller = uint32_t(ctx.lr);
  __imp__sub_82583030(ctx, base);
  if (trace && ctx.r3.u32 == 0 && stateptr && user == 0) {
    const uint16_t buttons = __builtin_bswap16(*reinterpret_cast<uint16_t*>(base + stateptr + 4));
    static std::atomic<int> logged{0};
    if (buttons && logged.fetch_add(1) < 20)
      REXLOG_INFO("Guest input caller={:08X} state={:08X} buttons={:04X}", caller, stateptr, buttons);
  }
}
void mercenaries2_DumpDiagnosticState(uint8_t* base, const std::filesystem::path& file) {
  if (!Enabled()) return;
  const uint32_t overlap = mercenaries2_enumeration_overlap.load();
  if (!overlap) return;
  std::ofstream out(file);
  out << std::hex << "enumeration_overlap=" << overlap << "\n";
  for (uint32_t offset=0; offset<28; offset+=4)
    out << offset << "=" << __builtin_bswap32(*reinterpret_cast<uint32_t*>(base + overlap + offset)) << "\n";
}

void mercenaries2_DumpReadOnlyImage(rex::memory::Memory* memory, const std::filesystem::path& folder) {
  // Read-only snapshot of the loaded XEX region preceding .text. Skip uncommitted
  // or inaccessible pages. This is opt-in analysis data and never changes the guest.
  constexpr uint32_t image_base = 0x82000000, length = 0x150000, chunk = 0x1000;
  std::vector<char> bytes(length, 0);
  uint32_t skipped = 0;
  for (uint32_t offset = 0; offset < length; offset += chunk) {
    auto* heap = memory->LookupHeap(image_base + offset);
    if (!heap || heap->QueryRangeAccess(image_base + offset, image_base + offset + chunk - 1) == rex::memory::PageAccess::kNoAccess) {
      ++skipped; continue;
    }
    std::memcpy(bytes.data() + offset, memory->TranslateVirtual(image_base + offset), chunk);
  }
  std::filesystem::create_directories(folder);
  std::ofstream out(folder / "loaded-rdata.bin", std::ios::binary);
  out.write(bytes.data(), bytes.size());
  std::ofstream status(folder / "loaded-rdata.txt");
  status << "base=0x82000000 length=0x150000 skipped_pages=" << skipped << "\n";
}
#endif
