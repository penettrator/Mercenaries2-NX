"""Fetch pinned Xenia resolve sources and recursively required local includes.
Sources are BSD licensed; no console writes. Build uses original GLSL flags.
"""
from pathlib import Path, PurePosixPath
import urllib.request, re, json, hashlib
ROOT=Path(__file__).resolve().parents[1]
REV='8444a2b5a33a5ca41e5fb75b89f002b7a5b0583b'
BASE=f'https://raw.githubusercontent.com/xenia-canary/xenia-canary/{REV}/'
DEST=ROOT/'tools/patches/xenia-water-vulkan/source'
SHADERS=PurePosixPath('src/xenia/gpu/shaders')
def main():
    pending=[SHADERS/f'resolve_full_{b}bpp{suffix}.cs.xesl' for b in [8,16,32,64,128] for suffix in ['', '_scaled']]
    pending.append(PurePosixPath('LICENSE'))
    records={}
    while pending:
        rel=pending.pop()
        if str(rel) in records: continue
        if '..' in rel.parts: raise RuntimeError(f'Unsafe include {rel}')
        data=urllib.request.urlopen(BASE+str(rel),timeout=30).read()
        target=DEST/str(rel);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        records[str(rel)]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'url':BASE+str(rel)}
        for inc in re.findall(r'^\s*#\s*include\s+"([^"]+)"',data.decode('utf-8'),re.M):
            # Xenia GPU shaders refer to the UI language shim by relative path.
            parts=[]
            for part in (rel.parent/PurePosixPath(inc)).parts:
                if part=='..': parts.pop()
                elif part!='.': parts.append(part)
            pending.append(PurePosixPath(*parts))
    (DEST.parent/'provenance.json').write_text(json.dumps({'revision':REV,'license':'BSD-3-Clause, Xenia','source':'https://github.com/xenia-canary/xenia-canary/pull/898','files':records},indent=2)+'\n')
    print(f'Fetched {len(records)} pinned source files')
if __name__=='__main__':main()
