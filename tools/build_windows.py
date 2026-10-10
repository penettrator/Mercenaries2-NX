"""Use portable Clang and the installed VS Windows SDK; no global PATH changes."""
import argparse
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
VS=Path(r'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools')
CMAKE=VS/'Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe'
NINJA=VS/'Common7/IDE/CommonExtensions/Microsoft/CMake/Ninja/ninja.exe'
CLANG=ROOT/'tools/bin/llvm-19/bin/clang-cl.exe'
LINKER=ROOT/'tools/bin/llvm-19/bin/lld-link.exe'
SDK=ROOT/'tools/bin/rexglue-0.10.0/win-amd64'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stock-gpu', action='store_true', help='Use the unmodified portable SDK GPU plugin')
    parser.add_argument('--configure-only',action='store_true')
    parser.add_argument('-j','--jobs',type=int,default=2)
    args=parser.parse_args()
    for tool in (CMAKE,NINJA,CLANG,LINKER):
        if not tool.is_file():
            raise SystemExit(f'Missing tool: {tool}')
    # Capture VS's environment privately: do not print inherited user variables.
    setup_script=ROOT/'out/setup-vs-env.cmd'
    setup_script.parent.mkdir(parents=True,exist_ok=True)
    setup_script.write_text('@echo off\ncall "'+str(VS/'Common7/Tools/VsDevCmd.bat')+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b 1\nset\n',encoding='utf-8')
    result=subprocess.run(['cmd.exe','/d','/c',str(setup_script)],capture_output=True,check=True)
    env=os.environ.copy()
    for line in result.stdout.decode('utf-8',errors='replace').splitlines():
        if '=' in line and not line.startswith('='):
            name,value=line.split('=',1)
            env[name.upper()]=value
    sdk_bin=Path(r'C:/Program Files (x86)/Windows Kits/10/bin/10.0.26100.0/x64')
    build=ROOT/'out/windows'
    subprocess.run([str(CMAKE),'-S',str(ROOT/'app'),'-B',str(build),'-G','Ninja',
                    '-DCMAKE_BUILD_TYPE=Release',f'-DCMAKE_MAKE_PROGRAM={NINJA.as_posix()}',
                    f'-DCMAKE_C_COMPILER={CLANG.as_posix()}',f'-DCMAKE_CXX_COMPILER={CLANG.as_posix()}',
                    f'-DCMAKE_LINKER={LINKER.as_posix()}',f'-DCMAKE_PREFIX_PATH={SDK.as_posix()}',
                    f'-DCMAKE_RC_COMPILER={(sdk_bin / "rc.exe").as_posix()}',
                    f'-DCMAKE_MT={(sdk_bin / "mt.exe").as_posix()}'],env=env,check=True)
    if not args.configure_only:
        subprocess.run([str(CMAKE),'--build',str(build),'--target','mercenaries2','-j',str(args.jobs)],env=env,check=True)
        patched = ROOT / 'out/windows-gpu/graphics/rexgpu-xenos.dll'
        if not args.stock_gpu and patched.is_file():
            import shutil
            shutil.copy2(patched, build / 'rexgpu-xenos.dll')
            print('Staged locally built Xenos GPU plugin with signed EDRAM fix')

if __name__=='__main__':
    main()
