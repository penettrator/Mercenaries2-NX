"""Check actual disassembled fragment shader CFG and ordered EDRAM accesses.
Rejects function calls: this narrowly checks inline SDK depth-AA output only.
"""
import argparse,json,re
from pathlib import Path

def check(text):
    lines=text.splitlines();entry=re.search(r'OpEntryPoint Fragment (%\d+)',text)[1]
    root=re.search(r'OpName (%\d+) "xe_edram"',text)[1]
    blocks={};current=None;in_main=False;pointers={root};ops=[]
    for line in lines:
        t=line.strip().split()
        if not t:continue
        if 'OpFunction' in t:in_main=t[0]==entry
        if not in_main:continue
        if 'OpLabel' in t:current=t[0];blocks[current]={'ops':[],'edges':set()};continue
        if current is None:continue
        op=next((x for x in t if x.startswith('Op')),None)
        if not op:continue
        args=t[t.index(op)+1:];result=t[0] if len(t)>1 and t[1]=='=' else None
        index=len(ops);ops.append((current,op,args));blocks[current]['ops'].append(index)
        if op in ('OpAccessChain','OpInBoundsAccessChain','OpPtrAccessChain','OpCopyObject') and any(a in pointers for a in args):pointers.add(result)
        if op=='OpBranch':blocks[current]['edges'].add(args[0])
        if op=='OpBranchConditional':blocks[current]['edges'].update(args[1:3])
        if op=='OpSwitch':blocks[current]['edges'].update(args[1::2])
        if op=='OpFunctionEnd':in_main=False
    assert not any(op=='OpFunctionCall' for _,op,_ in ops),'Non-inline calls require a separate interprocedural audit'
    start=next(iter(blocks));reachable=set();pending=[start]
    while pending:
        b=pending.pop()
        if b in reachable:continue
        reachable.add(b);pending.extend(blocks[b]['edges'])
    pred={b:set() for b in reachable}
    for b in reachable:
        for e in blocks[b]['edges']:pred[e].add(b)
    def fixed(neighbors, anchors):
        dom={b:({b} if b in anchors else set(reachable)) for b in reachable}
        while True:
            new={b:({b} if b in anchors else {b}|set.intersection(*(dom[p] for p in neighbors[b]))) for b in reachable}
            if new==dom:return dom
            dom=new
    exits={b for b in reachable if not blocks[b]['edges']}
    dom=fixed(pred,{start});post=fixed({b:blocks[b]['edges'] for b in reachable},exits)
    begins=[i for i,(b,op,a) in enumerate(ops) if op=='OpBeginInvocationInterlockEXT'];ends=[i for i,(b,op,a) in enumerate(ops) if op=='OpEndInvocationInterlockEXT']
    assert len(begins)==len(ends)==1,'Require a single static pair'
    begin,end=begins[0],ends[0];bb,eb=ops[begin][0],ops[end][0]
    assert bb in dom[eb] and eb in post[bb],'Begin/End must occur on every path'
    assert all(bb in dom[x] and eb in dom[x] for x in exits),'Exit bypasses the pair'
    def encloses(i):
        b=ops[i][0]
        return bb in dom[b] and eb in post[b] and (b!=bb or i>begin) and (b!=eb or i<end)
    memory=[i for i,(_,op,a) in enumerate(ops) if (op=='OpLoad' and a[1] in pointers) or (op=='OpStore' and a[0] in pointers)]
    assert memory and all(encloses(i) for i in memory),'EDRAM access outside protected region'
    images=[i for i,(_,op,_) in enumerate(ops) if op.startswith('OpImageSample')]
    assert images and all(not encloses(i) and begin>i for i in images),'Texture sampling still inside interlock'
    # Reject any back edge that could re-enter Begin or End.
    for marker in (bb,eb):
        seen=set();pending=list(blocks[marker]['edges'])
        while pending:
            b=pending.pop()
            assert b!=marker,'Marker can execute more than once'
            if b not in seen:seen.add(b);pending.extend(blocks[b]['edges'])
    return {'reachable_blocks':len(reachable),'begin_block':bb,'end_block':eb,'one_pair_on_all_paths':True,'edram_memory_accesses':len(memory),'edram_all_protected':True,'image_samples':len(images),'all_samples_before_begin':True,'limitations':'Inline main only; structural proof, not hardware visual/performance validation'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('assembly',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=check(a.assembly.read_text());a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
