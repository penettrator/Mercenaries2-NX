"""Summarize per-thread hardware samples; PC percentages exclude kernel waits.
Usage: python tools/summarize_hardware_stacks.py SYMBOLIZED_LOG --last-blocks 12
Percentages in logs are rounded and histograms truncated, so totals are approximate.
"""
import argparse, collections, json, re
from pathlib import Path

def summarize(text, last_blocks):
    blocks = re.split(r'(?=^==== )', text, flags=re.M)[1:]
    selected = list(enumerate(blocks, 1))[-last_blocks:]
    output = []
    for index, block in selected:
        row = {'block': index, 'header': block.splitlines()[0], 'threads': []}
        for thread in re.split(r'(?=^-- thread )', block, flags=re.M)[1:]:
            header = thread.splitlines()[0]
            if 'Main XThread' not in header and 'GPU Commands' not in header:
                continue
            count = re.search(r'(\d+) samples, (\d+)% waiting in the kernel', thread)
            if not count:
                continue
            by_symbol = collections.Counter()
            for percent, symbol in re.findall(r'^\s+([\d.]+)%  pc image\+0x[0-9a-f]+ \[(.+)\+0x[0-9a-f]+\]$', thread, re.M):
                by_symbol[symbol] += float(percent)
            stacks = re.findall(r'^\s+([\d.]+)%  stack (.+)$', thread, re.M)
            row['threads'].append({'header': header, 'samples': int(count[1]),
                'kernel_wait_percent': int(count[2]),
                'pc_percent_of_non_kernel_samples_approx': dict(by_symbol.most_common(10)),
                'top_stacks_percent_of_all_samples': [{'percent': float(p), 'stack': s} for p,s in stacks[:3]]})
        output.append(row)
    return {'selected_blocks': len(selected), 'total_blocks': len(blocks),
            'limitations': 'PC percentages are rounded, exclude kernel waits, and list at most 80 PCs. Stack frames are return addresses, not the current PC. Sampling is intrusive.',
            'blocks': output}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile', type=Path)
    parser.add_argument('--last-blocks', type=int, default=12)
    args=parser.parse_args()
    if args.last_blocks < 1: parser.error('--last-blocks must be positive')
    text=args.profile.read_text(encoding='utf-8-sig')
    if not text.startswith('NRO SHA256: ') or 'Stack sampling: active' not in text:
        raise RuntimeError('Use an active log produced by the hash-validating hardware symbolizer')
    result=summarize(text,args.last_blocks)
    result['nro_sha256']=text.splitlines()[0].split(': ',1)[1]
    result['profile']=str(args.profile)
    target=args.profile.with_name('stacks-summary.json')
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(target),'blocks':result['selected_blocks']}))
if __name__=='__main__': main()
