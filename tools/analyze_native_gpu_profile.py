"""Read native per-pass/per-draw reports without mixing menu and gameplay windows.
Reported times are raw driver timestamps; individual draw timestamps add overhead.
Only top-N entries are logged, so absent entries are unknown, not zero.
"""
import argparse,json,re
from pathlib import Path
REPORT=re.compile(r'GPU by pass, ms per frame .*?: total ([0-9.]+)(.*)$')
ITEM=re.compile(r' \| (.+?): ([0-9.]+) \(([0-9.]+)x, ([0-9.]+) draws(?:, ([0-9.]+)k elements)?\)')
DRAW=re.compile(r'draw VS \.\.([0-9A-Fa-f]{8}) PS \.\.([0-9A-Fa-f]{8})$')
def analyze(text):
    full_hashes=set(re.findall(r'(?<![0-9A-Fa-f])[0-9A-Fa-f]{16}(?![0-9A-Fa-f])',text))
    windows=[]
    for number,line in enumerate(text.splitlines(),1):
        match=REPORT.search(line)
        if not match: continue
        entries=[]
        for name,ms,count,draws,elements in ITEM.findall(match[2]):
            entry={'name':name,'raw_ms_per_frame':float(ms),'segments_per_frame':float(count),'draws_per_frame':float(draws)}
            # Builds from B:90 on also log index/vertex counts (thousands per frame).
            if elements: entry['kilo_elements_per_frame']=float(elements)
            pair=DRAW.fullmatch(name)
            if pair:
                for stage,low in zip(('vs','ps'),pair.groups()):
                    entry[stage+'_low30']=low.upper()
                    entry[stage+'_full_hash_candidates']=sorted({h.upper() for h in full_hashes if int(h,16)&0x3fffffff==int(low,16)})
            entries.append(entry)
        windows.append({'line':number,'timestamp':line[1:24] if line.startswith('[') else None,
                        'raw_total_ms_per_frame':float(match[1]),'entries':entries})
    return {'windows':windows,'draw_windows':sum(any('vs_low30' in e for e in w['entries']) for w in windows),
            'limitations':['Scene classification requires captures/user observation; windows are kept separate.',
                            'Raw driver timestamps, no automatic 1.6 multiplier.',
                            'Top-N truncation: omitted entries are unknown, not zero.',
                            'Low-30-bit hash matches are candidates; collisions and absent full hashes are preserved.',
                            'Per-draw timestamps drain the recording queue and may alter pacing; confirm gains with profiling off.']}
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('log',type=Path);ap.add_argument('--output',required=True,type=Path)
    args=ap.parse_args();result=analyze(args.log.read_text(encoding='utf-8-sig',errors='replace'));result['log']=str(args.log)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'windows':len(result['windows']),'draw_windows':result['draw_windows'],'output':str(args.output)}))
