"""Read bounded native resolve diagnostics, preserving each reporting window."""
import argparse,json,re,struct
from pathlib import Path
PATHS={0:'destination_missing',1:'color_compute',2:'depth_compute',3:'depth_scratch',4:'color_blit',5:'color_resolve_image',6:'color_copy_image',7:'depth_unsupported',8:'depth_descriptor_failed',9:'depth_words_direct'}
def analyze(text):
    windows=[]
    for number,line in enumerate(text.splitlines(),1):
        if 'RESOLVE_PROBE ' in line:
            fields={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',line.split('RESOLVE_PROBE ',1)[1])}
            windows.append({'line':number,'timestamp':line[1:24],**fields,'paths':[]})
        elif 'RESOLVE_PATH ' in line and windows:
            fields={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',line.split('RESOLVE_PATH ',1)[1])}
            fields['name']=PATHS.get(fields['path'],'unknown')
            fields['scale']=struct.unpack('<f',struct.pack('<I',fields['scale_bits']))[0]
            windows[-1]['paths'].append(fields)
    for w in windows:
        w['recorded_count']=sum(x['count'] for x in w['paths'])
        w['recorded_pixels']=sum(x['pixels'] for x in w['paths'])
        w['total_count']=w['recorded_count']+w.get('overflow',0)
        w['total_pixels']=w['recorded_pixels']+w.get('overflow_pixels',0)
        w['count_per_frame']=w['total_count']/w['frames'] if w.get('frames') else None
        w['complete_bucket_lines']=len(w['paths'])==w.get('buckets')
    return {'windows':windows,'limitations':['Aggregated CPU command-path counts, not GPU timings.',
      '128 bucket limit; overflow volume retained but parameters unknown.',
      'Texture resolved_hits counts lookup events, not alias-aware proof that every resolve is read.',
      'Compute outcomes include sized copies and color resolves; not a one-to-one branch total.',
      'No target/read-use/cold-cache correctness established by these counters.']}
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('log',type=Path);ap.add_argument('--output',required=True,type=Path)
    a=ap.parse_args();r=analyze(a.log.read_text(encoding='utf-8-sig',errors='replace'));r['log']=str(a.log)
    a.output.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8'); print(json.dumps({'windows':len(r['windows'])}))
