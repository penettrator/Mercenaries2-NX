"""Prepare an SD-card folder without duplicating the original game data on D:."""
from pathlib import Path
import os,shutil,json,hashlib,struct
ROOT=Path(__file__).resolve().parents[1]
nro=ROOT/'out/nx/mercenaries2.nro';data=nro.read_bytes()
if data[0x10:0x14]!=b'NRO0':raise RuntimeError('Invalid NRO header')
image_size=struct.unpack_from('<I',data,0x18)[0]
if image_size>len(data) or data[image_size:image_size+4]!=b'ASET':raise RuntimeError('Missing NRO asset section')
dest=ROOT/'out/sdcard/switch/Mercenaries2';dest.mkdir(parents=True,exist_ok=True)
shutil.copy2(nro,dest/nro.name)
source=ROOT/'assets/game_root';count=0;total=0
for path in source.rglob('*'):
 if not path.is_file():continue
 target=dest/'game_root'/path.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True)
 if not target.exists():os.link(path,target)
 if target.stat().st_size!=path.stat().st_size:raise RuntimeError('Game file size mismatch')
 count+=1;total+=path.stat().st_size
report={'stage':'built_unverified','nro':str(dest/nro.name),'nro_size':len(data),'nro_sha256':hashlib.sha256(data).hexdigest(),'game_files':count,'game_bytes':total,'pc_boot_probe_seconds':20,'console_launch_verified':False,'menu_or_gameplay_verified':False}
(ROOT/'out/package-report.json').write_text(json.dumps(report,indent=2))
(ROOT/'out/switch-pipeline-status.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
