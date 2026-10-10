"""Rebuild a Mesa C object and refresh the whole-linked NVK SDK archive."""
import subprocess, shutil, argparse, shlex
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"reference/mesa-switch-src"
source=SOURCE/"src/nouveau/horizon/nouveau_horizon_channel.c"
if "Bind GM20B Maxwell B" not in source.read_text():
 subprocess.run(["git","apply",str(ROOT/"tools/patches/mesa-initial-engine-bind.patch")],cwd=SOURCE,check=True)
# Upgrade workspaces that already have the earlier 3D-only prefix.
text = source.read_text()
old = "   channel->cache_acquire_words = 2 +\n      nouveau_horizon_gm20b_build_cache_acquire(commands + 2);"
if old in text:
 text = text.replace(old, "   commands[2] = (1u << 29) | (1u << 16) | (4u << 13);\n"
                         "   commands[3] = 0xB0B5; /* MAXWELL_DMA_COPY_A */\n"
                         "   channel->cache_acquire_words = 4 +\n"
                         "      nouveau_horizon_gm20b_build_cache_acquire(commands + 4);", 1)
 source.write_text(text)
base=["docker","run","--rm","--mount",f"type=bind,source={ROOT},target=/work","--mount",f"type=bind,source={SOURCE},target=/project","-w","/project/builddir-switch","mercenaries2-mesa-build:dev"]
parser=argparse.ArgumentParser()
parser.add_argument("--object", choices=["src/nouveau/horizon/libnouveau_horizon.a.p/nouveau_horizon_channel.c.o", "src/nouveau/vulkan/libnvk.a.p/nvk_cmd_buffer.c.o"], default="src/nouveau/horizon/libnouveau_horizon.a.p/nouveau_horizon_channel.c.o")
args=parser.parse_args()
obj=args.object
if obj == "src/nouveau/vulkan/libnvk.a.p/nvk_cmd_buffer.c.o":
 target=SOURCE/"src/nouveau/vulkan/nvk_cmd_buffer.c"
 if "union nvk_buffer_descriptor set_desc;" not in target.read_text():
  subprocess.run(["git","apply",str(ROOT/"tools/patches/mesa-switch-resolve-set-ubo-descriptors.patch")],cwd=SOURCE,check=True)
if not obj.endswith(".c.o") or ".." in obj: parser.error("Expected a C object target inside the Mesa build directory")
result=subprocess.run(base+["ninja","-t","commands",obj],capture_output=True,text=True,check=True)
commands=[]
for line in result.stdout.splitlines():
 words=shlex.split(line)
 if words and words[0].endswith("aarch64-none-elf-gcc") and "-o" in words and words[words.index("-o")+1] == obj:
  commands.append(line)
if len(commands) != 1: raise RuntimeError("Expected exactly one compile command for " + obj)
command=commands[0]
script=ROOT/"out/compile-mesa-channel.sh"
script.write_bytes(("set -e\n"+command+"\n").encode())
subprocess.run(base+["bash","/work/out/compile-mesa-channel.sh"],check=True)
archive=ROOT/"out/mesa-sdk/opt/devkitpro/portlibs/switch/lib/libvulkan.a"
backup=ROOT/"out/libvulkan-before-engine-bind.a"
if not backup.exists():shutil.copy2(archive,backup)
# NVK is whole-linked into vulkan-dispatch.o. Appending a loose object to
# the SDK archive leaves its old definition ahead of the replacement.
# Refresh both patched components before regenerating that combined object.
ar="/opt/devkitpro/devkitA64/bin/aarch64-none-elf-ar"
for component, member in [
 ("src/nouveau/horizon/libnouveau_horizon.a", "src/nouveau/horizon/libnouveau_horizon.a.p/nouveau_horizon_channel.c.o"),
 ("src/nouveau/vulkan/libnvk.a", "src/nouveau/vulkan/libnvk.a.p/nvk_cmd_buffer.c.o"),
]:
 subprocess.run(base+[ar,"r",component,member],check=True)
result=subprocess.run(base+["ninja","-t","commands","src/nouveau/vulkan/libvulkan.a"],capture_output=True,text=True,check=True)
merge=[line for line in result.stdout.splitlines() if "nvk_archive_merge.py --ar" in line]
if len(merge) != 1: raise RuntimeError("Expected one Mesa archive merge command")
merge_command=merge[0].replace("--ar ar ","--ar " + ar + " ",1)
script.write_bytes(("set -e\n"+merge_command+"\n").encode())
subprocess.run(base+["bash","/work/out/compile-mesa-channel.sh"],check=True)
mri="CREATE /work/"+archive.relative_to(ROOT).as_posix()+"\nADDLIB src/nouveau/vulkan/libvulkan.a\nADDLIB src/nouveau/compiler/libnak_rs.a\nSAVE\nEND\n"
subprocess.run(base[:2]+["-i"]+base[2:]+[ar,"-M"],input=mri,text=True,check=True)
if "nvk_cmd_buffer.c.o" in obj:
 nm="/opt/devkitpro/devkitA64/bin/aarch64-none-elf-nm"
 symbol="nvk_cmd_buffer_get_cbuf_addr"
 member_symbols=subprocess.run(base+[nm,"-S",obj],capture_output=True,text=True,check=True).stdout
 archive_symbols=subprocess.run(base+[nm,"-S","/work/"+archive.relative_to(ROOT).as_posix()],capture_output=True,text=True,check=True).stdout
 def definitions(output):
  return [line.split()[1] for line in output.splitlines() if line.endswith(" T " + symbol)]
 expected=definitions(member_symbols)
 actual=definitions(archive_symbols)
 if len(expected) != 1 or actual != expected:
  raise RuntimeError("Combined archive does not contain exactly the refreshed NVK function: " + repr(actual))
 print("Verified unique refreshed NVK definition, size 0x" + expected[0])
print("Refreshed whole-linked Mesa archive after " + obj + "; relink NRO before testing")
