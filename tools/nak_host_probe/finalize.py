from pathlib import Path
import json
r=Path('/work/out/nak-host-probe')
p=Path('/work/tools/nak_host_probe/README.md')
s=p.read_text(encoding='utf-8-sig')
s += '\nRun13 log017 line25 reports maxStorageBufferRange4294967295; SDK512MiB shared memory therefore has1 descriptor. Logged set0 binding0 count1/stride16/offset0 and binding1 offset16 match the actual SDK layout, not an unknown omission. Constants all5plain UBOs and heavy4MSAA1x/sample_rate_shading0 verified against SDK/cache. Hardware statistic agreement is still pending.\n\nFresh source snapshot (before install.py), from inside container:\n```bash\nmkdir -p /work/out/nak-host-probe\ncd /work/reference/mesa-switch-src\ntar --exclude=./builddir-native --exclude=./builddir-switch --exclude=./.git -cf - . | tar -xf - -C /work/out/nak-host-probe\nbash /work/tools/nak_host_probe/build.sh\n```\n'
p.write_text(s)
p=Path('/work/tools/nak_host_probe/manifest.py')
s=p.read_text(encoding='utf-8-sig')
s=s.replace("'Layout logs show shared binding0 exists; layouts reconstructed from SPIRV and SDK5constantUBOs.'", "'Run13 maxStorageBufferRange4294967295 confirms shared binding0 count1, EDRAMoffset16; SDK5UBO layout and cached MSAA1x/fs_key verified. Hardware stats still pending.'")
p.write_text(s)
p=Path('/work/tools/nak_host_probe/build.sh')
p.write_text(p.read_text(encoding='utf-8-sig'))
