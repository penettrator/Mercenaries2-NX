"""Build only the opt-in NAK emulator diagnostic and missing Rust dependencies."""
from pathlib import Path
import subprocess, json, shutil
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"reference/mesa-switch-src"
IMAGE="mercenaries2-mesa-build:dev"
CONTAINER="mercenaries2-nak-compile"
api=SOURCE/"src/nouveau/compiler/nak/api.rs"
if "EmuSm50" not in api.read_text():
 subprocess.run(["git","apply",str(ROOT/"tools/patches/nak-emu-sm50-low-multiply.patch")],cwd=SOURCE,check=True)
base=["docker","run","--rm","--mount",f"type=bind,source={ROOT},target=/work","--mount",f"type=bind,source={SOURCE},target=/project","-w","/project/builddir-switch",IMAGE]
commands=[]
for target,crate in [("src/nouveau/headers/libnvidia_headers.rlib","nvidia_headers"),("src/nouveau/compiler/libnak_bindings.rlib","nak_bindings"),("src/nouveau/compiler/libnak_rs.a","nak_rs")]:
 if crate != "nak_rs" and (SOURCE/"builddir-switch"/target).exists(): continue
 result=subprocess.run(base+["ninja","-t","commands",target],capture_output=True,text=True,check=True)
 matches=[line for line in result.stdout.splitlines() if "--crate-name "+crate+" " in line]
 if len(matches)!=1: raise RuntimeError("Expected exact Rust command for "+crate)
 commands.append(matches[0].replace("/usr/local/libexec/rustc ","/root/.cargo/bin/rustc --target=aarch64-unknown-linux-gnu ",1))
(ROOT/"out/compile-nak-emulator.sh").write_bytes(("set -e\nrustup target add aarch64-unknown-linux-gnu\n"+"\n".join(commands)+"\n").encode())
backup=ROOT/"out/libnak_rs-before-emu.a"
if not backup.exists(): shutil.copy2(SOURCE/"builddir-switch/src/nouveau/compiler/libnak_rs.a",backup)
inspected=subprocess.run(["docker","inspect",CONTAINER],capture_output=True,text=True)
if inspected.returncode == 0:
 info=json.loads(inspected.stdout)[0]
 sources={m["Destination"]:Path(m["Source"]).resolve() for m in info["Mounts"]}
 if info["Config"]["Image"] != IMAGE or sources.get("/work") != ROOT.resolve() or sources.get("/project") != SOURCE.resolve():
  raise RuntimeError("Container does not belong to this project")
 if info["State"]["Running"]: raise RuntimeError("NAK build is already running")
else:
 subprocess.run(["docker","create","--name",CONTAINER,"--label","mercenaries2.role=nak-compile",*base[3:-1],IMAGE,"bash","/work/out/compile-nak-emulator.sh"],check=True)
subprocess.run(["docker","start","-a",CONTAINER],check=True)
print("NAK built. Refresh the merged Mesa archive and validate the probe before relinking the game.")
