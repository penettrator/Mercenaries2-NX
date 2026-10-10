#pragma once
#if defined(__SWITCH__) && defined(MERCENARIES2_EMULATOR_GUARDS)
// Emulator-only build (CMake -DMERCENARIES2_EMULATOR_GUARDS=ON). Eden does not
// dispatch Horizon data-abort handlers, so with emulator_memory_test.flag these
// units access committed storage through the coherent shadow alias; writes
// still notify the SDK's GPU watch callbacks. Real hardware handles the aborts
// itself, and routing every load/store through this call costs speed there.
extern "C" uint8_t* mercenaries2_EmulatorMemoryAddress(uint8_t*, uint32_t, size_t, bool);
#undef REX_RAW_ADDR
#define REX_RAW_ADDR(x) mercenaries2_EmulatorMemoryAddress(base,uint32_t(x),16,true)
#undef REX_LOAD_U8
#undef REX_LOAD_U16
#undef REX_LOAD_U32
#undef REX_LOAD_U64
#define REX_LOAD_U8(x) (*(volatile u8*)mercenaries2_EmulatorMemoryAddress(base,uint32_t(x),1,false))
#define REX_LOAD_U16(x) __builtin_bswap16(*(volatile u16*)mercenaries2_EmulatorMemoryAddress(base,uint32_t(x),2,false))
#define REX_LOAD_U32(x) __builtin_bswap32(*(volatile u32*)mercenaries2_EmulatorMemoryAddress(base,uint32_t(x),4,false))
#define REX_LOAD_U64(x) __builtin_bswap64(*(volatile u64*)mercenaries2_EmulatorMemoryAddress(base,uint32_t(x),8,false))
#undef REX_STORE_U8
#undef REX_STORE_U16
#undef REX_STORE_U32
#undef REX_STORE_U64
#define REX_STORE_U8(x,y) (*(volatile u8*)mercenaries2_EmulatorMemoryAddress(base,uint32_t(x),1,true) = (y))
#define REX_STORE_U16(x,y) (*(volatile u16*)mercenaries2_EmulatorMemoryAddress(base,uint32_t(x),2,true) = __builtin_bswap16(y))
#define REX_STORE_U32(x,y) (*(volatile u32*)mercenaries2_EmulatorMemoryAddress(base,uint32_t(x),4,true) = __builtin_bswap32(y))
#define REX_STORE_U64(x,y) (*(volatile u64*)mercenaries2_EmulatorMemoryAddress(base,uint32_t(x),8,true) = __builtin_bswap64(y))
#endif
