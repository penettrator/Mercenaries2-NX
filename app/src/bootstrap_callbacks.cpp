// Exact PPC translations imported from probe codegen; no substitute behavior.
#include "generated/default/mercenaries2_funcs.h"
#include <rex/system/function_dispatcher.h>
namespace {
REX_FUNC(callback_82163E10);
REX_FUNC(callback_828ACBC8);
REX_FUNC(callback_823D9128);
REX_FUNC(callback_82382CE8);
REX_FUNC(callback_82389690);
REX_FUNC(callback_82897088);
REX_FUNC(callback_82731E88);
REX_FUNC(callback_8271C668);
REX_FUNC(callback_8278EE80);
REX_FUNC(callback_82834C10);
REX_FUNC(callback_826FC5E0);
REX_FUNC(callback_82720550);
REX_FUNC(callback_82731F58);
REX_FUNC(callback_8222EE70);
REX_FUNC(callback_8238FDA8);
REX_FUNC(callback_823D9140);
REX_FUNC(callback_8271C618);
REX_FUNC(callback_8271C640);
REX_FUNC(callback_82720560);
REX_FUNC(callback_82731F40);
REX_FUNC(callback_8277F398);
REX_FUNC(callback_828ACC10);
REX_FUNC(callback_82163E10) {
REX_FUNC_PROLOGUE();
	// cmplwi cr6,r4,0
	ctx.cr6.compare<uint32_t>(ctx.r4.u32, 0, ctx.xer);
	// beqlr cr6
	if (ctx.cr6.eq) return;
	// lis r11,-32090
	ctx.r11.s64 = -2103050240;
	// mr r3,r4
	ctx.r3.u64 = ctx.r4.u64;
	// lwz r10,-7156(r11)
	ctx.r10.u64 = REX_LOAD_U32(ctx.r11.u32 + -7156);
	// mtctr r10
	ctx.ctr.u64 = ctx.r10.u64;
	// bctr 
	REX_CALL_INDIRECT_FUNC(ctx.ctr.u32);
	return;
}

REX_FUNC(callback_828ACBC8) {
REX_FUNC_PROLOGUE();
	// lbz r10,60(r3)
	ctx.r10.u64 = REX_LOAD_U8(ctx.r3.u32 + 60);
	// clrlwi r11,r4,24
	ctx.r11.u64 = ctx.r4.u32 & 0xFF;
	// mr r9,r5
	ctx.r9.u64 = ctx.r5.u64;
	// mr r5,r6
	ctx.r5.u64 = ctx.r6.u64;
	// cmplw cr6,r11,r10
	ctx.cr6.compare<uint32_t>(ctx.r11.u32, ctx.r10.u32, ctx.xer);
	// blt cr6,0x828acbec
	if (ctx.cr6.lt) goto loc_828ACBEC;
	// lis r3,-32761
	ctx.r3.s64 = -2147024896;
	// ori r3,r3,87
	ctx.r3.u64 = ctx.r3.u64 | 87;
	// blr 
	return;
loc_828ACBEC:
	// lwz r10,36(r3)
	ctx.r10.u64 = REX_LOAD_U32(ctx.r3.u32 + 36);
	// rlwinm r11,r11,3,0,28
	ctx.r11.u64 = __builtin_rotateleft64(ctx.r11.u32 | (ctx.r11.u64 << 32), 3) & 0xFFFFFFF8;
	// mr r6,r7
	ctx.r6.u64 = ctx.r7.u64;
	// mr r4,r9
	ctx.r4.u64 = ctx.r9.u64;
	// lwzx r3,r11,r10
	ctx.r3.u64 = REX_LOAD_U32(ctx.r11.u32 + ctx.r10.u32);
	// lwz r11,0(r3)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r3.u32 + 0);
	// lwz r10,16(r11)
	ctx.r10.u64 = REX_LOAD_U32(ctx.r11.u32 + 16);
	// mtctr r10
	ctx.ctr.u64 = ctx.r10.u64;
	// bctr 
	REX_CALL_INDIRECT_FUNC(ctx.ctr.u32);
	return;
}

REX_FUNC(callback_823D9128) {
REX_FUNC_PROLOGUE();
	// b 0x823d9c58
	sub_823D9C58(ctx, base);
	return;
}

REX_FUNC(callback_82382CE8) {
REX_FUNC_PROLOGUE();
	// stb r4,83(r3)
	REX_STORE_U8(ctx.r3.u32 + 83, ctx.r4.u8);
	// blr 
	return;
}

REX_FUNC(callback_82389690) {
REX_FUNC_PROLOGUE();
	// lwz r8,296(r3)
	ctx.r8.u64 = REX_LOAD_U32(ctx.r3.u32 + 296);
	// cmplwi cr6,r8,0
	ctx.cr6.compare<uint32_t>(ctx.r8.u32, 0, ctx.xer);
	// beqlr cr6
	if (ctx.cr6.eq) return;
	// lis r11,-31898
	ctx.r11.s64 = -2090467328;
	// li r10,0
	ctx.r10.s64 = 0;
	// addi r9,r11,-7520
	ctx.r9.s64 = ctx.r11.s64 + -7520;
	// addi r11,r9,208
	ctx.r11.s64 = ctx.r9.s64 + 208;
loc_823896AC:
	// lwz r7,0(r11)
	ctx.r7.u64 = REX_LOAD_U32(ctx.r11.u32 + 0);
	// cmplw cr6,r7,r8
	ctx.cr6.compare<uint32_t>(ctx.r7.u32, ctx.r8.u32, ctx.xer);
	// beq cr6,0x823896d0
	if (ctx.cr6.eq) goto loc_823896D0;
	// addi r11,r11,1456
	ctx.r11.s64 = ctx.r11.s64 + 1456;
	// addi r7,r9,6032
	ctx.r7.s64 = ctx.r9.s64 + 6032;
	// addi r10,r10,1
	ctx.r10.s64 = ctx.r10.s64 + 1;
	// cmpw cr6,r11,r7
	ctx.cr6.compare<int32_t>(ctx.r11.s32, ctx.r7.s32, ctx.xer);
	// blt cr6,0x823896ac
	if (ctx.cr6.lt) goto loc_823896AC;
	// blr 
	return;
loc_823896D0:
	// mulli r11,r10,1456
	ctx.r11.s64 = static_cast<int64_t>(ctx.r10.u64 * static_cast<uint64_t>(1456));
	// add r11,r11,r9
	ctx.r11.u64 = ctx.r11.u64 + ctx.r9.u64;
	// cmplwi cr6,r11,0
	ctx.cr6.compare<uint32_t>(ctx.r11.u32, 0, ctx.xer);
	// beqlr cr6
	if (ctx.cr6.eq) return;
	// lis r10,-32034
	ctx.r10.s64 = -2099380224;
	// addi r3,r11,16
	ctx.r3.s64 = ctx.r11.s64 + 16;
	// lwz r11,31264(r10)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r10.u32 + 31264);
	// lhz r4,11154(r11)
	ctx.r4.u64 = REX_LOAD_U16(ctx.r11.u32 + 11154);
	// b 0x824b6fc8
	sub_824B6FC8(ctx, base);
	return;
}

REX_FUNC(callback_82897088) {
REX_FUNC_PROLOGUE();
	// mr r10,r3
	ctx.r10.u64 = ctx.r3.u64;
	// lwz r11,4(r10)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r10.u32 + 4);
	// addi r3,r11,1
	ctx.r3.s64 = ctx.r11.s64 + 1;
	// stw r3,4(r10)
	REX_STORE_U32(ctx.r10.u32 + 4, ctx.r3.u32);
	// blr 
	return;
}

REX_FUNC(callback_82731E88) {
REX_FUNC_PROLOGUE();
	PPCRegister temp{};
	// lwz r11,24(r3)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r3.u32 + 24);
	// lwz r11,16(r11)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r11.u32 + 16);
	// lfs f1,60(r11)
	ctx.fpscr.disableFlushMode();
	temp.u32 = REX_LOAD_U32(ctx.r11.u32 + 60);
	ctx.f1.f64 = double(temp.f32);
	// blr 
	return;
}

REX_FUNC(callback_8271C668) {
REX_FUNC_PROLOGUE();
	// lwz r11,48(r3)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r3.u32 + 48);
	// cmplwi cr6,r11,0
	ctx.cr6.compare<uint32_t>(ctx.r11.u32, 0, ctx.xer);
	// bne cr6,0x8271c67c
	if (!ctx.cr6.eq) goto loc_8271C67C;
	// li r3,0
	ctx.r3.s64 = 0;
	// blr 
	return;
loc_8271C67C:
	// lwz r3,48(r3)
	ctx.r3.u64 = REX_LOAD_U32(ctx.r3.u32 + 48);
	// lwz r11,0(r3)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r3.u32 + 0);
	// lwz r11,28(r11)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r11.u32 + 28);
	// mtctr r11
	ctx.ctr.u64 = ctx.r11.u64;
	// bctr 
	REX_CALL_INDIRECT_FUNC(ctx.ctr.u32);
	return;
}

REX_FUNC(callback_8278EE80) {
REX_FUNC_PROLOGUE();
	PPCRegister temp{};
	// lfs f0,72(r4)
	ctx.fpscr.disableFlushMode();
	temp.u32 = REX_LOAD_U32(ctx.r4.u32 + 72);
	ctx.f0.f64 = double(temp.f32);
	// lfs f13,76(r4)
	temp.u32 = REX_LOAD_U32(ctx.r4.u32 + 76);
	ctx.f13.f64 = double(temp.f32);
	// lfs f12,80(r4)
	temp.u32 = REX_LOAD_U32(ctx.r4.u32 + 80);
	ctx.f12.f64 = double(temp.f32);
	// lfs f11,84(r4)
	temp.u32 = REX_LOAD_U32(ctx.r4.u32 + 84);
	ctx.f11.f64 = double(temp.f32);
	// stfs f0,0(r3)
	temp.f32 = float(ctx.f0.f64);
	REX_STORE_U32(ctx.r3.u32 + 0, temp.u32);
	// stfs f13,4(r3)
	temp.f32 = float(ctx.f13.f64);
	REX_STORE_U32(ctx.r3.u32 + 4, temp.u32);
	// stfs f12,8(r3)
	temp.f32 = float(ctx.f12.f64);
	REX_STORE_U32(ctx.r3.u32 + 8, temp.u32);
	// stfs f11,12(r3)
	temp.f32 = float(ctx.f11.f64);
	REX_STORE_U32(ctx.r3.u32 + 12, temp.u32);
	// blr 
	return;
}

REX_FUNC(callback_82834C10) {
REX_FUNC_PROLOGUE();
	PPCRegister temp{};
	// lfs f1,484(r3)
	ctx.fpscr.disableFlushMode();
	temp.u32 = REX_LOAD_U32(ctx.r3.u32 + 484);
	ctx.f1.f64 = double(temp.f32);
	// blr 
	return;
}

REX_FUNC(callback_826FC5E0) {
REX_FUNC_PROLOGUE();
	// li r11,-1
	ctx.r11.s64 = -1;
	// lis r10,4
	ctx.r10.s64 = 262144;
	// stw r11,0(r3)
	REX_STORE_U32(ctx.r3.u32 + 0, ctx.r11.u32);
	// stw r10,4(r3)
	REX_STORE_U32(ctx.r3.u32 + 4, ctx.r10.u32);
	// blr 
	return;
}

REX_FUNC(callback_82720550) {
REX_FUNC_PROLOGUE();
	// lwz r11,0(r3)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r3.u32 + 0);
	// lwz r11,104(r11)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r11.u32 + 104);
	// mtctr r11
	ctx.ctr.u64 = ctx.r11.u64;
	// bctr 
	REX_CALL_INDIRECT_FUNC(ctx.ctr.u32);
	return;
}

REX_FUNC(callback_82731F58) {
REX_FUNC_PROLOGUE();
	// lwz r11,24(r3)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r3.u32 + 24);
	// lwz r11,16(r11)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r11.u32 + 16);
	// lwz r11,32(r11)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r11.u32 + 32);
	// addi r3,r11,12
	ctx.r3.s64 = ctx.r11.s64 + 12;
	// blr 
	return;
}

REX_FUNC(callback_8222EE70) {
REX_FUNC_PROLOGUE();
	// mr r10,r3
	ctx.r10.u64 = ctx.r3.u64;
	// li r6,0
	ctx.r6.s64 = 0;
	// li r5,1
	ctx.r5.s64 = 1;
	// lwz r11,4(r10)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r10.u32 + 4);
	// lwz r9,1032(r10)
	ctx.r9.u64 = REX_LOAD_U32(ctx.r10.u32 + 1032);
	// addi r11,r11,-1
	ctx.r11.s64 = ctx.r11.s64 + -1;
	// addi r8,r11,2
	ctx.r8.s64 = ctx.r11.s64 + 2;
	// stw r11,4(r10)
	REX_STORE_U32(ctx.r10.u32 + 4, ctx.r11.u32);
	// rlwinm r7,r8,2,0,29
	ctx.r7.u64 = __builtin_rotateleft64(ctx.r8.u32 | (ctx.r8.u64 << 32), 2) & 0xFFFFFFFC;
	// lwz r3,8(r9)
	ctx.r3.u64 = REX_LOAD_U32(ctx.r9.u32 + 8);
	// lwzx r4,r7,r10
	ctx.r4.u64 = REX_LOAD_U32(ctx.r7.u32 + ctx.r10.u32);
	// b 0x82427548
	sub_82427548(ctx, base);
	return;
}

REX_FUNC(callback_8238FDA8) {
REX_FUNC_PROLOGUE();
	PPCRegister temp{};
	// lwz r11,96(r3)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r3.u32 + 96);
	// cmpwi cr6,r11,2
	ctx.cr6.compare<int32_t>(ctx.r11.s32, 2, ctx.xer);
	// beq cr6,0x8238fde4
	if (ctx.cr6.eq) goto loc_8238FDE4;
	// cmpwi cr6,r11,3
	ctx.cr6.compare<int32_t>(ctx.r11.s32, 3, ctx.xer);
	// beq cr6,0x8238fdd4
	if (ctx.cr6.eq) goto loc_8238FDD4;
	// cmpwi cr6,r11,4
	ctx.cr6.compare<int32_t>(ctx.r11.s32, 4, ctx.xer);
	// bnelr cr6
	if (!ctx.cr6.eq) return;
	// lfs f0,44(r3)
	ctx.fpscr.disableFlushMode();
	temp.u32 = REX_LOAD_U32(ctx.r3.u32 + 44);
	ctx.f0.f64 = double(temp.f32);
	// fsubs f13,f0,f1
	ctx.f13.f64 = double(float(ctx.f0.f64 - ctx.f1.f64));
	// stfs f13,36(r3)
	temp.f32 = float(ctx.f13.f64);
	REX_STORE_U32(ctx.r3.u32 + 36, temp.u32);
	// blr 
	return;
loc_8238FDD4:
	// lfs f0,36(r3)
	ctx.fpscr.disableFlushMode();
	temp.u32 = REX_LOAD_U32(ctx.r3.u32 + 36);
	ctx.f0.f64 = double(temp.f32);
	// fadds f13,f0,f1
	ctx.f13.f64 = double(float(ctx.f0.f64 + ctx.f1.f64));
	// stfs f13,44(r3)
	temp.f32 = float(ctx.f13.f64);
	REX_STORE_U32(ctx.r3.u32 + 44, temp.u32);
	// blr 
	return;
loc_8238FDE4:
	// lfs f0,36(r3)
	ctx.fpscr.disableFlushMode();
	temp.u32 = REX_LOAD_U32(ctx.r3.u32 + 36);
	ctx.f0.f64 = double(temp.f32);
	// lis r11,-32242
	ctx.r11.s64 = -2113011712;
	// lfs f13,44(r3)
	temp.u32 = REX_LOAD_U32(ctx.r3.u32 + 44);
	ctx.f13.f64 = double(temp.f32);
	// fadds f12,f13,f0
	ctx.f12.f64 = double(float(ctx.f13.f64 + ctx.f0.f64));
	// lfs f0,-24852(r11)
	temp.u32 = REX_LOAD_U32(ctx.r11.u32 + -24852);
	ctx.f0.f64 = double(temp.f32);
	// fmuls f11,f12,f0
	ctx.f11.f64 = double(float(ctx.f12.f64 * ctx.f0.f64));
	// fmadds f10,f1,f0,f11
	ctx.f10.f64 = double(float(std::fma(ctx.f1.f64, ctx.f0.f64, ctx.f11.f64)));
	// stfs f10,36(r3)
	temp.f32 = float(ctx.f10.f64);
	REX_STORE_U32(ctx.r3.u32 + 36, temp.u32);
	// blr 
	return;
}

REX_FUNC(callback_823D9140) {
REX_FUNC_PROLOGUE();
	// b 0x823d9e10
	sub_823D9E10(ctx, base);
	return;
}

REX_FUNC(callback_8271C618) {
REX_FUNC_PROLOGUE();
	// lwz r11,48(r3)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r3.u32 + 48);
	// cmplwi cr6,r11,0
	ctx.cr6.compare<uint32_t>(ctx.r11.u32, 0, ctx.xer);
	// bne cr6,0x8271c62c
	if (!ctx.cr6.eq) goto loc_8271C62C;
	// li r3,0
	ctx.r3.s64 = 0;
	// blr 
	return;
loc_8271C62C:
	// lwz r3,48(r3)
	ctx.r3.u64 = REX_LOAD_U32(ctx.r3.u32 + 48);
	// lwz r11,0(r3)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r3.u32 + 0);
	// lwz r11,12(r11)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r11.u32 + 12);
	// mtctr r11
	ctx.ctr.u64 = ctx.r11.u64;
	// bctr 
	REX_CALL_INDIRECT_FUNC(ctx.ctr.u32);
	return;
}

REX_FUNC(callback_8271C640) {
REX_FUNC_PROLOGUE();
	// lwz r11,48(r3)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r3.u32 + 48);
	// cmplwi cr6,r11,0
	ctx.cr6.compare<uint32_t>(ctx.r11.u32, 0, ctx.xer);
	// bne cr6,0x8271c654
	if (!ctx.cr6.eq) goto loc_8271C654;
	// li r3,0
	ctx.r3.s64 = 0;
	// blr 
	return;
loc_8271C654:
	// lwz r3,48(r3)
	ctx.r3.u64 = REX_LOAD_U32(ctx.r3.u32 + 48);
	// lwz r11,0(r3)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r3.u32 + 0);
	// lwz r11,24(r11)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r11.u32 + 24);
	// mtctr r11
	ctx.ctr.u64 = ctx.r11.u64;
	// bctr 
	REX_CALL_INDIRECT_FUNC(ctx.ctr.u32);
	return;
}

REX_FUNC(callback_82720560) {
REX_FUNC_PROLOGUE();
	// addi r3,r3,-16
	ctx.r3.s64 = ctx.r3.s64 + -16;
	// b 0x827212e0
	sub_827212E0(ctx, base);
	return;
}

REX_FUNC(callback_82731F40) {
REX_FUNC_PROLOGUE();
	// lwz r11,24(r3)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r3.u32 + 24);
	// lwz r3,16(r11)
	ctx.r3.u64 = REX_LOAD_U32(ctx.r11.u32 + 16);
	// lwz r11,0(r3)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r3.u32 + 0);
	// lwz r11,68(r11)
	ctx.r11.u64 = REX_LOAD_U32(ctx.r11.u32 + 68);
	// mtctr r11
	ctx.ctr.u64 = ctx.r11.u64;
	// bctr 
	REX_CALL_INDIRECT_FUNC(ctx.ctr.u32);
	return;
}

REX_FUNC(callback_8277F398) {
REX_FUNC_PROLOGUE();
	// addi r3,r3,-100
	ctx.r3.s64 = ctx.r3.s64 + -100;
	// b 0x82780850
	sub_82780850(ctx, base);
	return;
}

REX_FUNC(callback_828ACC10) {
REX_FUNC_PROLOGUE();
	// lbz r10,60(r3)
	ctx.r10.u64 = REX_LOAD_U8(ctx.r3.u32 + 60);
	// clrlwi r11,r4,24
	ctx.r11.u64 = ctx.r4.u32 & 0xFF;
	// cmplw cr6,r11,r10
	ctx.cr6.compare<uint32_t>(ctx.r11.u32, ctx.r10.u32, ctx.xer);
	// blt cr6,0x828acc2c
	if (ctx.cr6.lt) goto loc_828ACC2C;
	// lis r3,-32761
	ctx.r3.s64 = -2147024896;
	// ori r3,r3,87
	ctx.r3.u64 = ctx.r3.u64 | 87;
	// blr 
	return;
loc_828ACC2C:
	// lwz r10,36(r3)
	ctx.r10.u64 = REX_LOAD_U32(ctx.r3.u32 + 36);
	// rlwinm r11,r11,3,0,28
	ctx.r11.u64 = __builtin_rotateleft64(ctx.r11.u32 | (ctx.r11.u64 << 32), 3) & 0xFFFFFFF8;
	// li r3,0
	ctx.r3.s64 = 0;
	// add r11,r11,r10
	ctx.r11.u64 = ctx.r11.u64 + ctx.r10.u64;
	// lbz r11,5(r11)
	ctx.r11.u64 = REX_LOAD_U8(ctx.r11.u32 + 5);
	// stb r11,0(r5)
	REX_STORE_U8(ctx.r5.u32 + 0, ctx.r11.u8);
	// blr 
	return;
}

}
void mercenaries2_RegisterAdditionalFunctions(rex::runtime::IModuleRegistrar* registrar) {
  if (!registrar->SetFunction(0x82163E10, callback_82163E10))
    REX_FATAL("Cannot register Mercenaries 2 callback 0x82163E10");
  if (!registrar->SetFunction(0x828ACBC8, callback_828ACBC8))
    REX_FATAL("Cannot register Mercenaries 2 callback 0x828ACBC8");
  if (!registrar->SetFunction(0x823D9128, callback_823D9128))
    REX_FATAL("Cannot register Mercenaries 2 callback 0x823D9128");
  if (!registrar->SetFunction(0x82382CE8, callback_82382CE8))
    REX_FATAL("Cannot register Mercenaries 2 callback 0x82382CE8");
  if (!registrar->SetFunction(0x82389690, callback_82389690))
    REX_FATAL("Cannot register Mercenaries 2 callback 0x82389690");
  if (!registrar->SetFunction(0x82897088, callback_82897088))
    REX_FATAL("Cannot register Mercenaries 2 callback 0x82897088");
  if (!registrar->SetFunction(0x82731E88, callback_82731E88))
    REX_FATAL("Cannot register Mercenaries 2 callback 0x82731E88");
  if (!registrar->SetFunction(0x8271C668, callback_8271C668))
    REX_FATAL("Cannot register Mercenaries 2 callback 0x8271C668");
  if (!registrar->SetFunction(0x8278EE80, callback_8278EE80))
    REX_FATAL("Cannot register Mercenaries 2 callback 0x8278EE80");
  if (!registrar->SetFunction(0x82834C10, callback_82834C10))
    REX_FATAL("Cannot register Mercenaries 2 callback 0x82834C10");
  if (!registrar->SetFunction(0x826FC5E0, callback_826FC5E0))
    REX_FATAL("Cannot register Mercenaries 2 callback 0x826FC5E0");
  if (!registrar->SetFunction(0x82720550, callback_82720550))
    REX_FATAL("Cannot register Mercenaries 2 callback 0x82720550");
  if (!registrar->SetFunction(0x82731F58, callback_82731F58))
    REX_FATAL("Cannot register Mercenaries 2 callback 0x82731F58");
  if (!registrar->SetFunction(0x8222EE70, callback_8222EE70))
    REX_FATAL("Cannot register Mercenaries 2 callback 0x8222EE70");
  if (!registrar->SetFunction(0x8238FDA8, callback_8238FDA8))
    REX_FATAL("Cannot register Mercenaries 2 callback 0x8238FDA8");
  if (!registrar->SetFunction(0x823D9140, callback_823D9140))
    REX_FATAL("Cannot register Mercenaries 2 callback 0x823D9140");
  if (!registrar->SetFunction(0x8271C618, callback_8271C618))
    REX_FATAL("Cannot register Mercenaries 2 callback 0x8271C618");
  if (!registrar->SetFunction(0x8271C640, callback_8271C640))
    REX_FATAL("Cannot register Mercenaries 2 callback 0x8271C640");
  if (!registrar->SetFunction(0x82720560, callback_82720560))
    REX_FATAL("Cannot register Mercenaries 2 callback 0x82720560");
  if (!registrar->SetFunction(0x82731F40, callback_82731F40))
    REX_FATAL("Cannot register Mercenaries 2 callback 0x82731F40");
  if (!registrar->SetFunction(0x8277F398, callback_8277F398))
    REX_FATAL("Cannot register Mercenaries 2 callback 0x8277F398");
  if (!registrar->SetFunction(0x828ACC10, callback_828ACC10))
    REX_FATAL("Cannot register Mercenaries 2 callback 0x828ACC10");
}
