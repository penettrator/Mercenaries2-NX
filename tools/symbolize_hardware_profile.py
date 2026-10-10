"""Symbolize hardware sampling logs with an immutable, hash-matched manifest.
Example: python tools/symbolize_hardware_profile.py RUN/logs/rex/rex_profile.log
No console access. Nearest native symbol does not prove an original PPC PC.
"""
import argparse,bisect,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile',type=Path)
    parser.add_argument('--manifest',type=Path,default=ROOT/'out/stack-profile-enable-71c41b96/symbols-manifest.json')
    args=parser.parse_args();profile=args.profile.resolve();manifest=args.manifest.resolve()
    m=json.loads(manifest.read_text());folder=manifest.parent
    if digest(ROOT/m['nro_archive'])!=m['nro_sha256']:raise RuntimeError('NRO archive hash mismatch')
    if digest(folder/m['symbols'])!=m['symbols_sha256']:raise RuntimeError('Symbol listing hash mismatch')
    if digest(folder/m['elf'])!=m['elf_sha256']:raise RuntimeError('ELF hash mismatch')
    text=profile.read_text(encoding='utf-8-sig',errors='replace')
    header=re.search(r'image 0x([0-9a-fA-F]+), code up to 0x([0-9a-fA-F]+)',text)
    if not header:raise RuntimeError('Profiler image range absent')
    limit=int(header[2],16)-int(header[1],16)
    syms=[]
    for line in (folder/m['symbols']).read_text().splitlines():
        match=re.match(r'^([0-9a-fA-F]+) [tTwW] (.+)$',line)
        if match:syms.append((int(match[1],16),match[2]))
    syms.sort();addresses=[s[0] for s in syms];count=0
    def symbolize(match):
        nonlocal count
        offset=int(match[1],16);i=bisect.bisect_right(addresses,offset)-1
        if i<0 or offset>=limit:return match[0]+' [outside known text]'
        count+=1;addr,name=syms[i]
        return match[0]+f' [{name}+0x{offset-addr:x}]'
    output=re.sub(r'image\+0x([0-9a-fA-F]+)',symbolize,text)
    target=profile.with_name('rex_profile.symbolized.txt')
    target.write_text('NRO SHA256: '+m['nro_sha256']+'\nNative nearest-symbol candidates; profiler log does not independently embed NRO hash.\n'+output,encoding='utf-8')
    print(json.dumps({'output':str(target),'annotated_addresses':count,'stack_sampling_active':'Stack sampling: active' in text,'nro_sha256':m['nro_sha256']}))
if __name__=='__main__':main()
