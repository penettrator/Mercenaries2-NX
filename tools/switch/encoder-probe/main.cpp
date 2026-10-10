#include <switch.h>
#include <cstdio>
#include <cstring>
#include <rex/ppc/context.h>
extern "C" { u32 __nx_applet_type = AppletType_Application; u64 __nx_heap_size = 16*1024*1024; }
alignas(32) static uint8_t memory[0x10000];
static FILE* log_file;
static unsigned loads, stores;
static uint8_t* Checked(uint8_t* base, uint32_t at, unsigned size, bool write) {
  unsigned& count = write ? stores : loads;
  if (++count > 2048 || at > sizeof(memory)-size) {
    fprintf(log_file,"FAIL bounded memory access: at=%08X write=%d loads=%u stores=%u\n",at,write,loads,stores);
    fclose(log_file);svcExitProcess();
  }
  return base+at;
}
#define REX_FUNC_PROLOGUE() ((void)0)
#define REX_LOAD_U32(x) __builtin_bswap32(*(volatile uint32_t*)Checked(base,uint32_t(x),4,false))
#define REX_LOAD_U64(x) __builtin_bswap64(*(volatile uint64_t*)Checked(base,uint32_t(x),8,false))
#define REX_STORE_U32(x,y) (*(volatile uint32_t*)Checked(base,uint32_t(x),4,true)=__builtin_bswap32(uint32_t(y)))
#define REX_STORE_U64(x,y) (*(volatile uint64_t*)Checked(base,uint32_t(x),8,true)=__builtin_bswap64(uint64_t(y)))
void sub_825AA170(PPCContext&,uint8_t*) {
 fprintf(log_file,"FAIL unexpected capacity path\n");fclose(log_file);svcExitProcess();
}
void __savegprlr_26(PPCContext& ctx, uint8_t* base) {
	REX_FUNC_PROLOGUE();
	// std r26,-56(r1)
	REX_STORE_U64(ctx.r1.u32 + -56, ctx.r26.u64);
	// std r27,-48(r1)
	REX_STORE_U64(ctx.r1.u32 + -48, ctx.r27.u64);
	// std r28,-40(r1)
	REX_STORE_U64(ctx.r1.u32 + -40, ctx.r28.u64);
	// std r29,-32(r1)
	REX_STORE_U64(ctx.r1.u32 + -32, ctx.r29.u64);
	// std r30,-24(r1)
	REX_STORE_U64(ctx.r1.u32 + -24, ctx.r30.u64);
	// std r31,-16(r1)
	REX_STORE_U64(ctx.r1.u32 + -16, ctx.r31.u64);
	// stw r12,-8(r1)
	REX_STORE_U32(ctx.r1.u32 + -8, ctx.r12.u32);
	// blr 
	return;
}

void __restgprlr_26(PPCContext& ctx, uint8_t* base) {
	REX_FUNC_PROLOGUE();
	// ld r26,-56(r1)
	ctx.r26.u64 = REX_LOAD_U64(ctx.r1.u32 + -56);
	// ld r27,-48(r1)
	ctx.r27.u64 = REX_LOAD_U64(ctx.r1.u32 + -48);
	// ld r28,-40(r1)
	ctx.r28.u64 = REX_LOAD_U64(ctx.r1.u32 + -40);
	// ld r29,-32(r1)
	ctx.r29.u64 = REX_LOAD_U64(ctx.r1.u32 + -32);
	// ld r30,-24(r1)
	ctx.r30.u64 = REX_LOAD_U64(ctx.r1.u32 + -24);
	// ld r31,-16(r1)
	ctx.r31.u64 = REX_LOAD_U64(ctx.r1.u32 + -16);
	// lwz r12,-8(r1)
	ctx.r12.u64 = REX_LOAD_U32(ctx.r1.u32 + -8);
	// mtlr r12
	ctx.lr = ctx.r12.u64;
	// blr 
	return;
}

void sub_825AA7C0(PPCContext& ctx, uint8_t* base) {
	REX_FUNC_PROLOGUE();
	uint32_t ea{};
	// mflr r12
	ctx.r12.u64 = ctx.lr;
	// bl 0x82861bd0
	ctx.lr = 0x825AA7C8;
	__savegprlr_26(ctx, base);
	// stwu r1,-144(r1)
	ea = -144 + ctx.r1.u32;
	REX_STORE_U32(ea, ctx.r1.u32);
	ctx.r1.u32 = ea;
	// mr r26,r3
	ctx.r26.u64 = ctx.r3.u64;
	// mr r31,r4
	ctx.r31.u64 = ctx.r4.u64;
	// addi r29,r6,-4
	ctx.r29.s64 = ctx.r6.s64 + -4;
	// lwz r4,48(r26)
	ctx.r4.u64 = REX_LOAD_U32(ctx.r26.u32 + 48);
loc_825AA7DC:
	// cntlzd r11,r31
	ctx.r11.u64 = ctx.r31.u64 == 0 ? 64 : __builtin_clzll(ctx.r31.u64);
	// lwz r9,52(r26)
	ctx.r9.u64 = REX_LOAD_U32(ctx.r26.u32 + 52);
	// clrldi r8,r11,32
	ctx.r8.u64 = ctx.r11.u64 & 0xFFFFFFFF;
	// rlwinm r10,r11,2,0,29
	ctx.r10.u64 = __builtin_rotateleft64(ctx.r11.u32 | (ctx.r11.u64 << 32), 2) & 0xFFFFFFFC;
	// sld r31,r31,r8
	ctx.r31.u64 = ctx.r8.u8 & 0x40 ? 0 : (ctx.r31.u64 << (ctx.r8.u8 & 0x7F));
	// not r8,r31
	ctx.r8.u64 = ~ctx.r31.u64;
	// add r29,r10,r29
	ctx.r29.u64 = ctx.r10.u64 + ctx.r29.u64;
	// cntlzd r30,r8
	ctx.r30.u64 = ctx.r8.u64 == 0 ? 64 : __builtin_clzll(ctx.r8.u64);
	// add r28,r11,r5
	ctx.r28.u64 = ctx.r11.u64 + ctx.r5.u64;
	// rlwinm r27,r30,2,0,29
	ctx.r27.u64 = __builtin_rotateleft64(ctx.r30.u32 | (ctx.r30.u64 << 32), 2) & 0xFFFFFFFC;
	// mr r11,r30
	ctx.r11.u64 = ctx.r30.u64;
	// add r10,r27,r4
	ctx.r10.u64 = ctx.r27.u64 + ctx.r4.u64;
	// cmplw cr6,r10,r9
	ctx.cr6.compare<uint32_t>(ctx.r10.u32, ctx.r9.u32, ctx.xer);
	// blt cr6,0x825aa844
	if (ctx.cr6.lt) goto loc_825AA844;
	// li r8,1
	ctx.r8.s64 = 1;
	// mr r7,r30
	ctx.r7.u64 = ctx.r30.u64;
	// mr r6,r29
	ctx.r6.u64 = ctx.r29.u64;
	// mr r5,r28
	ctx.r5.u64 = ctx.r28.u64;
	// mr r3,r26
	ctx.r3.u64 = ctx.r26.u64;
	// bl 0x825aa170
	ctx.lr = 0x825AA82C;
	sub_825AA170(ctx, base);
	// clrldi r11,r30,32
	ctx.r11.u64 = ctx.r30.u64 & 0xFFFFFFFF;
	// mr r4,r3
	ctx.r4.u64 = ctx.r3.u64;
	// add r29,r27,r29
	ctx.r29.u64 = ctx.r27.u64 + ctx.r29.u64;
	// add r5,r30,r28
	ctx.r5.u64 = ctx.r30.u64 + ctx.r28.u64;
	// sld r31,r31,r11
	ctx.r31.u64 = ctx.r11.u8 & 0x40 ? 0 : (ctx.r31.u64 << (ctx.r11.u8 & 0x7F));
	// b 0x825aa86c
	goto loc_825AA86C;
loc_825AA844:
	// addi r10,r30,-1
	ctx.r10.s64 = ctx.r30.s64 + -1;
	// add r5,r30,r28
	ctx.r5.u64 = ctx.r30.u64 + ctx.r28.u64;
	// rlwinm r10,r10,16,0,15
	ctx.r10.u64 = __builtin_rotateleft64(ctx.r10.u32 | (ctx.r10.u64 << 32), 16) & 0xFFFF0000;
	// or r10,r10,r28
	ctx.r10.u64 = ctx.r10.u64 | ctx.r28.u64;
	// stwu r10,4(r4)
	ea = 4 + ctx.r4.u32;
	REX_STORE_U32(ea, ctx.r10.u32);
	ctx.r4.u32 = ea;
loc_825AA858:
	// lwzu r10,4(r29)
	ea = 4 + ctx.r29.u32;
	ctx.r10.u64 = REX_LOAD_U32(ea);
	ctx.r29.u32 = ea;
	// addic. r11,r11,-1
	ctx.xer.ca = ctx.r11.u32 > 0;
	ctx.r11.s64 = ctx.r11.s64 + -1;
	ctx.cr0.compare<int32_t>(ctx.r11.s32, 0, ctx.xer);
	// rldicr r31,r31,1,62
	ctx.r31.u64 = __builtin_rotateleft64(ctx.r31.u64, 1) & 0xFFFFFFFFFFFFFFFE;
	// stwu r10,4(r4)
	ea = 4 + ctx.r4.u32;
	REX_STORE_U32(ea, ctx.r10.u32);
	ctx.r4.u32 = ea;
	// bne 0x825aa858
	if (!ctx.cr0.eq) goto loc_825AA858;
loc_825AA86C:
	// cmpldi cr6,r31,0
	ctx.cr6.compare<uint64_t>(ctx.r31.u64, 0, ctx.xer);
	// bne cr6,0x825aa7dc
	if (!ctx.cr6.eq) goto loc_825AA7DC;
	// stw r4,48(r26)
	REX_STORE_U32(ctx.r26.u32 + 48, ctx.r4.u32);
	// addi r1,r1,144
	ctx.r1.s64 = ctx.r1.s64 + 144;
	// b 0x82861c20
	__restgprlr_26(ctx, base);
	return;
}

int main() {
 log_file=fopen("/switch/Mercenaries2/encoder-probe.log","w"); if(!log_file)svcExitProcess();
 uint8_t* base=memory;
 for (uint64_t mask : {0xFFF0000000000000ULL,0xE004000000000000ULL,0x600020F000000000ULL}) {
  memset(memory,0,sizeof(memory)); PPCContext ctx{};
  ctx.r1.u64=0x8000;ctx.r3.u64=0x1000;ctx.r4.u64=mask;ctx.r5.u64=8704;ctx.r6.u64=0x3000;
  REX_STORE_U32(0x1030,0x4000);REX_STORE_U32(0x1034,0x6000);
  for(unsigned i=0;i<64;i++)REX_STORE_U32(0x3000+i*4,0xABC00000+i);
  loads=stores=0;fprintf(log_file,"enter mask=%016lX\n",mask);fflush(log_file);
  sub_825AA7C0(ctx,base);
  const unsigned words=(REX_LOAD_U32(0x1030)-0x4000)/4;
  fprintf(log_file,"returned: words=%u loads=%u stores=%u\n",words,loads,stores);fflush(log_file);
 }
 fprintf(log_file,"probe_complete\n");fclose(log_file);svcExitProcess();
}
