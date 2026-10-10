"""Import exact translations of boot callbacks and their missing direct callees."""
from pathlib import Path
import re,json
ROOT=Path(__file__).resolve().parents[1]
LIST=ROOT/'app/bootstrap_callbacks.json'
addresses=json.loads(LIST.read_text())
default_symbols=set(int(x,16) for x in re.findall(r'DECLARE_REX_FUNC\(sub_([0-9A-F]{8})\)',(ROOT/'app/generated/default/mercenaries2_funcs.h').read_text()))
all_blocks={}
pattern=re.compile(r'^DEFINE_REX_FUNC\(sub_([0-9A-F]{8})\) \{',re.M)
for path in (ROOT/'app/generated/probe').glob('*recomp*.cpp'):
 source=path.read_text();matches=list(pattern.finditer(source))
 for i,match in enumerate(matches):
  address=int(match.group(1),16)
  if address in default_symbols and address not in addresses:continue
  end=matches[i+1].start() if i+1<len(matches) else len(source)
  body=source[match.end():end].strip()
  if not body.endswith('}'):raise RuntimeError('Unexpected function boundary')
  all_blocks[address]=body
for address in addresses:
 if address not in all_blocks:raise RuntimeError(f'Probe is missing {address:08X}')
 body=all_blocks[address]
 if 'REX_FATAL("Unresolved' in body or '// ERROR:' in body:raise RuntimeError('Incomplete translation')
 for match in re.findall(r'\bsub_([0-9A-F]{8})\s*\(',body):
  target=int(match,16)
  if target not in default_symbols and target not in addresses:addresses.append(target)
source='// Exact PPC translations imported from probe codegen; no substitute behavior.\n#include "generated/default/mercenaries2_funcs.h"\n#include <rex/system/function_dispatcher.h>\nnamespace {\n'
for address in addresses:source+=f'REX_FUNC(callback_{address:08X});\n'
for address in addresses:
 body=all_blocks[address]
 for target in addresses:body=body.replace(f'sub_{target:08X}',f'callback_{target:08X}')
 source+=f'REX_FUNC(callback_{address:08X}) {{\n'+body+'\n\n'
source+='}\nvoid mercenaries2_RegisterAdditionalFunctions(rex::runtime::IModuleRegistrar* registrar) {\n'
for address in addresses:source+=f'  if (!registrar->SetFunction(0x{address:08X}, callback_{address:08X}))\n    REX_FATAL("Cannot register Mercenaries 2 callback 0x{address:08X}");\n'
source+='}\n'
(ROOT/'app/src/bootstrap_callbacks.cpp').write_text(source)
LIST.write_text(json.dumps(addresses,indent=2))
print(f'Imported {len(addresses)} complete functions')
