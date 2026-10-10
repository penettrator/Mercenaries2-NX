// XamEnumerate async error compatibility for the embedded Xbox XAPI.
// The PPC consumer at 0x8227D458 expects ERROR_FUNCTION_FAILED (1627)
// and obtains the actual HRESULT with XGetOverlappedExtendedError.
// Preserve enumeration results; do not fabricate saves or suppress failures.
#include "generated/default/mercenaries2_funcs.h"
#include <rex/hook.h>
#include <rex/system/xenumerator.h>
#include <atomic>
#include <cstdlib>
std::atomic<uint32_t> mercenaries2_enumeration_overlap{0};
namespace {
using namespace rex;
using namespace rex::system;
u32 EnumerateAsync(u32 handle, u32 flags, mapped_void buffer, u32 buffer_length,
                   mapped_u32 items_returned, mapped_void overlapped) {
  auto* kernel = REX_KERNEL_STATE();
  auto enumerator = kernel->object_table()->LookupObject<XEnumerator>(handle);
  if (!enumerator) return X_ERROR_INVALID_HANDLE;
  if (flags || items_returned || !overlapped) return X_ERROR_INVALID_PARAMETER;
  kernel->CompleteOverlappedDeferredEx(
    [enumerator, buffer](uint32_t& error, uint32_t& length) -> X_RESULT {
      uint32_t count = 0;
      const X_RESULT result = buffer
        ? enumerator->WriteItems(buffer.guest_address(), buffer.as<uint8_t*>(), &count)
        : X_ERROR_INVALID_PARAMETER;
      error = X_HRESULT_FROM_WIN32(result);
      length = count;
      return result == X_ERROR_SUCCESS ? X_ERROR_SUCCESS : X_ERROR_FUNCTION_FAILED;
    }, overlapped.guest_address());
  return X_ERROR_IO_PENDING;
}
}
REX_HOOK_RAW(sub_8257BBE8) {
  if (!ctx.r7.u32) {
    __imp__sub_8257BBE8(ctx, base);
    return;
  }
#if defined(_WIN32)
  if (std::getenv("MERCENARIES2_TEST_KERNEL_TRACE")) {
    mercenaries2_enumeration_overlap.store(ctx.r7.u32);
    REXLOG_INFO("Guest async enumerate caller={:08X} handle={:08X} overlap={:08X}",
      uint32_t(ctx.lr), ctx.r3.u32, ctx.r7.u32);
  }
#endif
  // Exact register shuffle from the original PPC tail wrapper.
  ctx.r8.u64 = ctx.r7.u64; ctx.r7.u64 = ctx.r6.u64;
  ctx.r6.u64 = ctx.r5.u64; ctx.r5.u64 = ctx.r4.u64; ctx.r4.s64 = 0;
  rex::ppc::HostToGuestFunction<EnumerateAsync>(ctx, base);
}
