"""Rank sparse GPU completion deltas from the hardware game log.
These are timestamp brackets with overlapping GPU work, not isolated shader times.
Sampled totals are not per-frame cost and must not be multiplied blindly by stride.
"""
import argparse,collections,json,math,statistics,re
from pathlib import Path
from datetime import datetime,timedelta
PATTERN=re.compile(r'GPU_DRAW_SAMPLE submission=(\d+) vs=([0-9A-F]{16}) ps=([0-9A-F]{16}) vertices=(\d+) pitch=(\d+) ticks=(\d+) delta_us=([\d.]+)')
def analyze(text):
    groups=collections.defaultdict(list)
    for submission,vs,ps,vertices,pitch,ticks,us in PATTERN.findall(text):
        groups[(vs,ps,int(pitch))].append({'submission':int(submission),'vertices':int(vertices),'ticks':int(ticks),'us':float(us)})
    rows=[]
    for (vs,ps,pitch),samples in groups.items():
        times=sorted(x['us'] for x in samples)
        rows.append({'vs':vs,'ps':ps,'surface_pitch':pitch,'samples':len(times),'sampled_total_us':sum(times),'median_us':statistics.median(times),'p95_us':times[max(0,math.ceil(.95*len(times))-1)],'max_us':times[-1],'vertices_min':min(x['vertices'] for x in samples),'vertices_max':max(x['vertices'] for x in samples),'zero_ticks':sum(x['ticks']==0 for x in samples)})
    rows.sort(key=lambda r:r['sampled_total_us'],reverse=True)
    return {'samples':sum(r['samples'] for r in rows),'groups':rows,'initialization':re.findall(r'GPU_DRAW_TIMING enabled=[^\n]+',text),'discarded_result_messages':text.count('GPU_DRAW_TIMING result discarded'),'limitations':__doc__}
def tail_samples(text, seconds):
    dated=[]
    for line in text.splitlines():
        if not PATTERN.search(line): continue
        stamp=re.match(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)\]',line)
        if not stamp: raise ValueError('Sample timestamp missing; cannot select a time window')
        dated.append((datetime.fromisoformat(stamp[1]),line))
    if not dated: raise ValueError('No timestamped GPU samples')
    end=max(d for d,_ in dated);start=end-timedelta(seconds=seconds)
    lines=[l for d,l in dated if d>=start]
    return '\n'.join(lines), {'requested_seconds':seconds,'cutoff':start.isoformat(),'last_sample':end.isoformat(),'scope':'Tail time window; gameplay attribution still requires user observation'}

def attach_shader_sources(result, mapping):
    # Runtime SDK hashes raw Xenos bytes. Swapped candidates are never silently
    # accepted as identities, and dynamically generated VS may remain unmatched.
    lookup = collections.defaultdict(list)
    for record in mapping['records']:
        lookup[(record['stage'], record['raw_hash'])].append(record['file'])
    matched = collections.Counter()
    for group in result['groups']:
        for stage in ('vs', 'ps'):
            files = lookup[(stage, group[stage])]
            group[stage + '_containers'] = files
            if files: matched[stage] += 1
    result['shader_mapping'] = {
        'hash': mapping['hash'], 'source_sha256': mapping['source_sha256'],
        'match': 'Exact raw microcode XXH3; no word-swapped fallback',
        'matched_groups': dict(matched),
        'limitations': 'Container identity only. Offline HLSL is not the runtime SPIR-V translator; missing VS matches may be generated variants.'}
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('log',type=Path)
    p.add_argument('--last-seconds',type=int);p.add_argument('--shader-map',type=Path);a=p.parse_args()
    if a.last_seconds is not None and a.last_seconds<=0:p.error('--last-seconds must be positive')
    text=a.log.read_text(encoding='utf-8-sig',errors='replace')
    selected,window=tail_samples(text,a.last_seconds) if a.last_seconds else (text,None)
    result=analyze(selected);result['time_window']=window
    result['initialization']=analyze(text)['initialization']
    if a.shader_map: attach_shader_sources(result,json.loads(a.shader_map.read_text(encoding='utf-8')))
    name=f'gpu-draw-summary-last{a.last_seconds}s.json' if a.last_seconds else 'gpu-draw-summary.json'
    target=a.log.with_name(name);target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(target),'samples':result['samples'],'shader_groups':len(result['groups'])}))
if __name__=='__main__':main()
