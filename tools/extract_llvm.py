import tarfile, shutil
from pathlib import Path
root=Path('tools/bin/llvm-19').resolve();root.mkdir(parents=True,exist_ok=True)
allowed={'bin/clang.exe','bin/clang-cl.exe','bin/lld.exe','bin/lld-link.exe'}
aliases=[];count=0
with tarfile.open('tools/bin/clang-llvm-19.1.7-windows.tar.xz','r|xz') as archive:
 for member in archive:
  rel=member.name.partition('/')[2]
  if rel not in allowed and not rel.startswith('lib/clang/19/'): continue
  target=(root/rel).resolve()
  if not target.is_relative_to(root):raise RuntimeError('Unsafe archive path')
  if member.isdir(): target.mkdir(parents=True,exist_ok=True)
  elif member.isfile():
   target.parent.mkdir(parents=True,exist_ok=True)
   with archive.extractfile(member) as source, target.open('wb') as dest:shutil.copyfileobj(source,dest,1024*1024)
   count+=1
   if rel in allowed: print('Extracted '+rel,flush=True)
  elif member.islnk():aliases.append((target,root/member.linkname.partition('/')[2]))
for target,source in aliases:
 if not source.resolve().is_relative_to(root):raise RuntimeError('Unsafe archive link')
 shutil.copyfile(source,target);count+=1
print(f'Extracted {count} LLVM files',flush=True)
