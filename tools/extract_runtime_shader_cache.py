"""Extract the SDK packed XESH cache without changing its guest-endian code.
Checks framing/version and (when --library is supplied) every SDK XXH3 hash.
"""
import argparse,ctypes,hashlib,json,struct
from pathlib import Path

def parse_cache(data, hasher=None):
    if len(data)<8 or data[:4]!=b'XESH' or struct.unpack_from('>I',data,4)[0]!=0x20201219:
        raise ValueError('Unsupported XESH header/version')
    rows=[];offset=8
    while offset<len(data):
        if len(data)-offset<12:raise ValueError(f'Truncated shader header at {offset}')
        identity,packed=struct.unpack_from('<QI',data,offset);header_offset=offset;offset+=12
        dwords=packed&0x7fffffff;stage='ps' if packed>>31 else 'vs';size=dwords*4
        if not size or size>len(data)-offset:raise ValueError(f'Truncated/empty microcode at {offset}')
        code=data[offset:offset+size];offset+=size
        if hasher and hasher(code)!=identity:raise ValueError(f'Hash mismatch at {header_offset}')
        rows.append(({'hash':f'{identity:016X}','stage':stage,'dwords':dwords,'header_offset':header_offset,'sha256':hashlib.sha256(code).hexdigest(),'file':f'{stage}_{identity:016X}.bin'},code))
    return rows

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('cache',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--library',type=Path);a=p.parse_args()
    hasher=None
    if a.library:
        lib=ctypes.CDLL(str(a.library.resolve()));f=lib.merc_shader_hash;f.argtypes=[ctypes.c_void_p,ctypes.c_ulong];f.restype=ctypes.c_ulonglong
        hasher=lambda code:f(code,len(code))
    data=a.cache.read_bytes();rows=parse_cache(data,hasher);a.output.mkdir(parents=True,exist_ok=True)
    for row,code in rows:(a.output/row['file']).write_bytes(code)
    result={'source':str(a.cache),'source_sha256':hashlib.sha256(data).hexdigest(),'xxh3_validated':hasher is not None,'records':[r for r,_ in rows]}
    (a.output/'index.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'records':len(rows),'hashes_validated':hasher is not None,'output':str(a.output)}))
if __name__=='__main__':main()
