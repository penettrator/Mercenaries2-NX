from pathlib import Path
root = Path('/work/out/nak-host-probe')
shader = root / 'src/nouveau/vulkan/nvk_shader.c'
s = shader.read_text()
marker = '\n/* NAK_HOST_PROBE_ENTRY */\n'
if marker in s: s = s.split(marker)[0]
shader.write_text(s + marker + Path('/work/tools/nak_host_probe/probe.inc').read_text(encoding='utf-8-sig'))
m = root / 'src/nouveau/vulkan/meson.build'
s = m.read_text()
if marker in s: s = s.split(marker)[0]
if "# NAK_HOST_PROBE_ENTRY" in s: s = s.split("# NAK_HOST_PROBE_ENTRY")[0]
s += "\n# NAK_HOST_PROBE_ENTRY\n" + "\nexecutable('nak-host-probe', dependencies : nvk_deps, link_with : libnvk, install : false)\n"
m.write_text(s)

# Host-only restoration of a POSIX include commented out by the Switch port.
p = root / 'src/vulkan/runtime/vk_instance.c'
s = p.read_text().replace('// #include "dlfcn.h"', '#include "dlfcn.h"')
p.write_text(s)
# Existing definition is misplaced after its Linux-only first use in this port.
p = root / 'src/nouveau/winsys/nouveau_context.c'
s = p.read_text().replace('#define NOUVEAU_WS_CONTEXT_MAX_CLASSES 16\n', '')
s = '#define NOUVEAU_WS_CONTEXT_MAX_CLASSES 16\n' + s
p.write_text(s)
