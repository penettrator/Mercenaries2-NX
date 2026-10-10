"""Map game shader containers to SDK XXH3 hashes without modifying microcode."""
import argparse,ctypes,json,struct
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--library',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 lib=ctypes.CDLL(str(a.library.resolve()));h=lib.merc_shader_hash;h.argtypes=[ctypes.c_void_p,ctypes.c_ulong];h.restype=ctypes.c_ulonglong
 root=Path('out/shaders/containers');idx=json.loads((root/'index.json').read_text());matches=[]
 for r in idx['records']:
  data=(root/r['file']).read_bytes();virtual=struct.unpack_from('>I',data,4)[0];header=struct.unpack_from('>I',data,24)[0];offset,size=struct.unpack_from('>II',data,header);code=data[virtual+offset:virtual+offset+size]
  if len(code)!=size:raise ValueError('Truncated microcode '+r['file'])
  row={'file':r['file'],'stage':r['stage'],'microcode_bytes':size,'raw_hash':f'{h(code,len(code)):016X}','word_swapped_hash':f'{h(b"".join(code[i:i+4][::-1] for i in range(0,len(code),4)),len(code)):016X}'};matches.append(row)
 a.output.write_text(json.dumps({'hash':'SDK XXH3_64bits','source_sha256':idx['source_sha256'],'records':matches},indent=2)+'\n');print('Mapped',len(matches),'containers')
if __name__=='__main__':main()
