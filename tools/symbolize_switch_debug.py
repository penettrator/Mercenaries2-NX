"""Symbolize a saved GDB snapshot against the matching local Switch nm listing."""
import argparse, bisect, hashlib, json, re
from pathlib import Path
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument("label")
args=parser.parse_args()
if not re.fullmatch(r"[a-zA-Z0-9_-]+",args.label):parser.error("Invalid label")
p=root/"out/emulator-check"/args.label/"result.json"
d=json.loads(p.read_text())
if d.get("nro_sha256") != hashlib.sha256((root/"out/nx/mercenaries2.nro").read_bytes()).hexdigest():
    raise RuntimeError("Snapshot belongs to another NRO; use its matching symbol file")
base=int(re.search(r'address="(0x[0-9a-fA-F]+)"',d["libraries"]).group(1),16)
symbols=[]
for line in (root/"out/nx/symbols-current.txt").read_text(encoding="utf-8-sig").splitlines():
    m=re.match(r"^([0-9a-fA-F]+) [A-Za-z] (.+)$",line)
    if m:symbols.append((int(m[1],16),m[2]))
symbols.sort();addresses=[v[0] for v in symbols]
def symbol(raw):
    offset=int(raw,16)-base;i=bisect.bisect_right(addresses,offset)-1
    return symbols[i][1]+"+"+hex(offset-symbols[i][0]) if i>=0 else "unknown"
for t in d["threads"]:
    t["pc_symbol"]=symbol(t["pc"]);t["lr_symbol"]=symbol(t["lr"])
    for f in t.get("frame_records",[]):f["return_symbol"]=symbol(f["words"][1])
    if "thread:"+t["id"]+";" in d["sample_stop"]:
        print(json.dumps({k:t.get(k) for k in ["id","pc_symbol","lr_symbol","x_registers","possible_ppc_registers"]},indent=2))
        for f in t.get("frame_records",[]):print("FRAME",f["return_symbol"],f["words"][:6])
        for f in t.get("frame_records",[]):
            raw=f.get("saved_x19_candidate_bytes","")
            if len(raw)!=0x130*2:continue
            b=bytes.fromhex(raw);offsets={"r3":0,"r0":8,"r1":16,"r2":24}
            offsets.update({f"r{i}":i*8 for i in range(4,32)});offsets.update(lr=256,ctr=264)
            print("FRAME PPC CANDIDATE",f["words"][2],{k:hex(int.from_bytes(b[v:v+8],"little")) for k,v in offsets.items()})
            break
p.with_name("symbolized.json").write_text(json.dumps(d,indent=2)+"\n")
print("FAULTS")
print("\n".join(l for l in p.with_name("eden.log").read_text(errors="replace").splitlines() if "Stopping execution" in l or "Break:" in l))
