"""Collect Windows exception events from an owned, bounded Eden process."""
import argparse, ctypes as C, json, struct, subprocess, time
from ctypes import wintypes as W
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument("--label", required=True)
p.add_argument("--seconds", type=int, default=15)
a=p.parse_args()
if not a.label.replace("-", "").replace("_", "").isalnum() or not 1 <= a.seconds <= 60:
 p.error("Invalid label or duration")
out=ROOT/"out/emulator-check"/a.label
out.mkdir(exist_ok=False)
K=C.WinDLL("kernel32",use_last_error=True)
K.WaitForDebugEvent.argtypes=[C.c_void_p,W.DWORD]
K.ContinueDebugEvent.argtypes=[W.DWORD,W.DWORD,W.DWORD]
K.CloseHandle.argtypes=[W.HANDLE]
K.OpenThread.argtypes=[W.DWORD,W.BOOL,W.DWORD];K.OpenThread.restype=W.HANDLE
K.GetThreadContext.argtypes=[W.HANDLE,C.c_void_p]
K.ReadProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.c_void_p]
K.GetFinalPathNameByHandleW.argtypes=[W.HANDLE,W.LPWSTR,W.DWORD,W.DWORD]
si=subprocess.STARTUPINFO(); si.dwFlags|=subprocess.STARTF_USESHOWWINDOW; si.wShowWindow=0
emu=ROOT/"tools/bin/eden-0.2.1"
nro=emu/"user/sdmc/switch/Mercenaries2/mercenaries2.nro"
process=subprocess.Popen([str(emu/"eden-cli.exe"),str(nro)],cwd=emu,startupinfo=si,creationflags=2)
modules=[]; exceptions=[]; exited=False
started=time.monotonic()
def ptr(raw,offset): return struct.unpack_from("<Q",raw,offset)[0]
def module(address):
 candidates=[x for x in modules if x["base_int"]<=address]
 if not candidates:return {}
 m=max(candidates,key=lambda x:x["base_int"])
 return {"module":m["path"],"module_offset":hex(address-m["base_int"])}
try:
 while time.monotonic()-started<a.seconds:
  event=C.create_string_buffer(176)
  if not K.WaitForDebugEvent(event,100):continue
  raw=event.raw; code,pid,tid=struct.unpack_from("<III",raw)
  data=raw[16:]; status=0x10002
  if code in (3,6):
   handle=ptr(data,0); base=ptr(data,24 if code==3 else 8)
   name=C.create_unicode_buffer(32768)
   path=name.value if not handle else ""
   if handle:
    K.GetFinalPathNameByHandleW(handle,name,len(name),0);path=name.value;K.CloseHandle(handle)
   modules.append({"base_int":base,"base":hex(base),"path":path})
  elif code==1:
   ec=struct.unpack_from("<I",data)[0];addr=ptr(data,16);count=struct.unpack_from("<I",data,24)[0]
   first=struct.unpack_from("<I",data,152)[0]
   parameters=[ptr(data,32+i*8) for i in range(min(count,15))]
   if ec not in (0x80000003,0x80000004):
    exceptions.append({"code":hex(ec),"address":hex(addr),"first_chance":bool(first),"thread":tid,"parameters":[hex(x) for x in parameters],**module(addr)})
    status=0x80010001
    thread=K.OpenThread(0x8,False,tid)
    storage=C.create_string_buffer(1248); aligned=(C.addressof(storage)+15)&~15
    C.c_uint32.from_address(aligned+48).value=0x100003
    if thread and K.GetThreadContext(thread,aligned):
     offsets={"rax":120,"rcx":128,"rdx":136,"rbx":144,"rsp":152,"rsi":168,"rdi":176,"r8":184,"rip":248}
     regs={name:C.c_uint64.from_address(aligned+off).value for name,off in offsets.items()}
     exceptions[-1]["registers"]={k:hex(v) for k,v in regs.items()}
     for name,length in [("rcx",0x200),("rsp",0x400)]:
      data_buffer=C.create_string_buffer(length);read=C.c_size_t()
      if K.ReadProcessMemory(int(process._handle),regs[name],data_buffer,length,C.byref(read)):
       exceptions[-1][name+"_memory"]=data_buffer.raw[:read.value].hex()
    if thread:K.CloseHandle(thread)
  elif code==5:
   exited=True;exit_code=struct.unpack_from("<I",data)[0]
  K.ContinueDebugEvent(pid,tid,status)
  if exited:break
finally:
 if not exited:process.terminate()
 process.wait(timeout=5)
 result={"exceptions":exceptions,"modules":modules,"exit_code":process.returncode,"timed_out":not exited,"seconds":round(time.monotonic()-started,2)}
 (out/"result.json").write_text(json.dumps(result,indent=2))
 print(json.dumps({k:v for k,v in result.items() if k!="modules"},indent=2))
