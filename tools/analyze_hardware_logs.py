"""Summarize saved real-Switch profiler blocks; never reads console/SD.
Usage: python tools/analyze_hardware_logs.py [out/hardware-runs/RUN ...]
FPS blocks are not automatically identified as menu/cutscene/gameplay.
"""
import argparse, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def analyze(run):
    profiles=list(run.rglob('rex_profile.log'))
    if len(profiles)!=1: raise ValueError(f'{run}: expected one profiler log')
    text=profiles[0].read_text(encoding='utf-8-sig',errors='replace')
    blocks=[]
    for index,chunk in enumerate(re.split(r'(?m)(?=^==== )',text)):
        header=re.search(r'^==== ([\d.]+) s \| mode: (.*?) \| game ([\d.]+) fps \| CPU total ([\d.]+)%',chunk,re.M)
        if not header: continue
        row={'block':len(blocks)+1,'seconds':float(header[1]),'mode':header[2],'fps':float(header[3]),'cpu_total_percent':float(header[4])}
        patterns={'cpu_mhz':r'clocks: CPU ([\d.]+) MHz','gpu_mhz':r'GPU ([\d.]+) MHz','draws_per_frame':r'per frame: ([\d.]+) draws','resolves_per_frame':r'\| ([\d.]+) resolves','transfer_calls_per_frame':r'transfers: ([\d.]+) calls','pipelines_in_interval':r'pipelines created in the interval: (\d+)','main_thread_cpu_percent':r'"Main XThread[^\n]*?CPU ([\d.]+)%','audio_requests_without_data':r'(\d+) requests without data'}
        for key,pattern in patterns.items():
            match=re.search(pattern,chunk)
            row[key]=float(match[1]) if match else None
        blocks.append(row)
    errors=[]
    saved_logs=sorted(run.rglob('mercenaries2_*.log'))
    # Captures may contain prior runs' logs; only newest numbered log belongs
    # to this captured run. Preserve the list for audit, never sum history.
    for p in saved_logs[-1:]:
        log=p.read_text(encoding='utf-8-sig',errors='replace')
        errors.append({'file':str(p.relative_to(ROOT)),'spirv_parse_failures':log.count('SPIR-V parsing FAILED'),'pipeline_failures':log.count('vkCreateGraphicsPipelines failed'),'failed_vs_counts':{h:len(re.findall(r'vkCreateGraphicsPipelines failed[^\n]*vs='+h,log)) for h in ['FB0614F28843002E','0B895494F668718D']},'shader_storage_started':'Initializing shader storage for title 45410828' in log,'skipped_present_warnings':log.count('Skipping Vulkan frame presentation due to async placeholder')})
    return {'run':run.name,'source':str(profiles[0].relative_to(ROOT)),'interpretation_limit':'Blocks are chronological; stage labels need user observation. Successful pipeline counts exclude failed attempts. Audio no-data counts alone do not prove audible stutter.','blocks':blocks,'saved_game_log_names':[p.name for p in saved_logs],'game_logs':errors}
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs',nargs='*',type=Path)
    args=parser.parse_args()
    runs=args.runs or sorted((ROOT/'out/hardware-runs').glob('run*'))
    report=[analyze(p if p.is_absolute() else ROOT/p) for p in runs if p.is_dir()]
    out=ROOT/'out/hardware-analysis';out.mkdir(exist_ok=True)
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    for item in report:
        print(item['run'], 'blocks=',len(item['blocks']), 'errors=',sum(x['spirv_parse_failures'] for x in item['game_logs']))
        if item['run']=='run4-a7d55cac-fsi':
            for row in item['blocks']:
                if row.get('pipelines_in_interval',0) or 0:
                    print(' ',row)
if __name__=='__main__':main()
