"""Bounded boot probes: import exact PPC callbacks discovered at runtime."""
import argparse, json, os, re, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'out/runtime-windows/probe-state.json'
LIST=ROOT/'app/bootstrap_callbacks.json'
MANIFEST=ROOT/'app/mercenaries2_probe.toml'
REX=ROOT/'tools/bin/rexglue-0.10.0/win-amd64/bin/rexglue.exe'

def state(stage,**details):
 record={'stage':stage,**details};STATE.write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)

parser=argparse.ArgumentParser()
parser.add_argument('--seconds',type=int,default=60)
parser.add_argument('--iterations',type=int,default=10)
parser.add_argument('--input-script',type=Path)
parser.add_argument('--headless-dialogs',action='store_true')
parser.add_argument('--label',default='long')
options=parser.parse_args()
if not options.label.replace('-', '').replace('_', '').isalnum():parser.error('Invalid label')
if not 1 <= options.seconds <= 600 or not 1 <= options.iterations <= 20:parser.error('Invalid probe bounds')
for iteration in range(1,options.iterations+1):
 addresses=json.loads(LIST.read_text())
 manifest=MANIFEST.read_text()
 for address in addresses:
  entry=f'"0x{address:08X}"'
  if entry not in manifest:manifest+='\n'+entry+' = { }\n'
 MANIFEST.write_text(manifest)
 state('generating_callbacks',iteration=iteration,count=len(addresses))
 with (ROOT/'out/probe-autocodegen.log').open('w') as log:
  subprocess.run([str(REX),'--log-file',str(ROOT/'out/probe-codegen.log'),'codegen',str(MANIFEST)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
 subprocess.run([sys.executable,str(ROOT/'tools/import_bootstrap_callbacks.py')],cwd=ROOT,check=True)
 state('building_pc',iteration=iteration)
 with (ROOT/'out/windows-build.log').open('w') as log:
  subprocess.run([sys.executable,str(ROOT/'tools/build_windows.py')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
 logfile=ROOT/f'out/runtime-windows/{options.label}{iteration:02d}.log'
 startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
 args=[str(ROOT/'out/windows/mercenaries2.exe'),f'--game_data_root={ROOT / "assets/game_root"}',f'--user_data_root={ROOT / "out/runtime-windows/user"}',f'--cache_root={ROOT / "out/runtime-windows/cache"}',f'--log_file={logfile}','--log_level=info']
 state('probing_boot',iteration=iteration)
 if options.headless_dialogs:args.append('--headless=true')
 env=os.environ.copy()
 if options.input_script:
  env['MERCENARIES2_TEST_SCRIPTED_INPUT']='1'
  env['MERCENARIES2_TEST_INPUT_FILE']=str(options.input_script.resolve())
 args.append('--log_flush_interval=1')
 process=subprocess.Popen(args,cwd=ROOT/'out/windows',startupinfo=startup,env=env)
 survived=False
 try:process.wait(timeout=options.seconds)
 except subprocess.TimeoutExpired:
  survived=True;process.terminate();process.wait(timeout=10)
 text=logfile.read_text(encoding='utf-8',errors='replace') if logfile.exists() else ''
 missing=re.findall(r'invalid or unregistered function at guest address 0x([0-9A-Fa-f]+)',text)
 if not missing:
  state('boot_probe_finished',iteration=iteration,survived_probe_window=survived,probe_seconds=options.seconds,exit_code=process.returncode,log=str(logfile),note='Menu and gameplay are not visually verified')
  break
 address=int(missing[-1],16)
 if not 0x82150000<=address<0x82A4E648 or address in addresses:
  state('requires_analysis',address=hex(address),log=str(logfile));break
 addresses.append(address);LIST.write_text(json.dumps(addresses,indent=2))
 state('new_callback',address=hex(address),iteration=iteration)
else:state('iteration_limit',count=len(json.loads(LIST.read_text())))
