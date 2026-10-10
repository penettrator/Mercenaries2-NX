from pathlib import Path
import json, hashlib
root=Path('/work')
probe=root/'out/nak-host-probe'
sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
files=[]
for folder in ['src/nouveau/compiler','src/nouveau/vulkan','src/nouveau/nil','src/compiler/nir','src/compiler/spirv']:
    for p in sorted((probe/folder).rglob('*')):
        if p.is_file() and p.suffix in ['.c','.h','.rs','.py']:
            rel=p.relative_to(probe)
            original=root/'reference/mesa-switch-src'/rel
            files.append({'path':str(rel),'snapshot_sha256':sha(p),'production_sha256':sha(original) if original.is_file() else None})
summary=json.loads((probe/'results/summary.json').read_text())
for s in summary['results']:
    s['histogram_total_instructions']=sum(s['nak_assembly_opcode_counts'].values())
    s['histogram_matches_nak_num_instrs']=s['histogram_total_instructions']==s['instructions']
    prefix=Path(s['input']).stem
    s['layout_log']=str((probe/'results'/f'{prefix}.log').relative_to(root))
(probe/'results/summary.json').write_text(json.dumps(summary,indent=2)+'\n')
artifacts=[probe/'build/src/nouveau/vulkan/nak-host-probe', *sorted((probe/'results').glob('*'))]
manifest={
 'status':'completed_provisional_host_stats_not_hardware_performance',
 'target':'GM20B Maxwell SM53',
 'robustness':'VK_PIPELINE_ROBUSTNESS_BUFFER_BEHAVIOR_ROBUST_BUFFER_ACCESS_EXT for UBO+SSBO',
 'fs_key':{'zs_self_dep':False,'force_sample_shading':False,'uses_underestimate':False},
 'cached_pipeline_evidence':'run12 FSI PipelineDescription: heavy4 MSAA1x, sample_rate_shading0',
 'host_image':'mercenaries2-nak-host-full:dev',
 'host_image_id':'sha256:61825560640c8956915963cbf9b2e727f83ce8a6949e6e399c3710dec96a4bb4',
 'build_command':'bash /work/tools/nak_host_probe/build.sh',
 'snapshot_adaptations':['Probe entry appended to nvk_shader.c; meson executable target added','vk_instance.c dlfcn.h restored for Linux','nouveau_context.c existing MAX_CLASSES16 moved before first Linux use'],
 'compiler_sources':files,
 'tools':{str(p.relative_to(root)):sha(p) for p in sorted((root/'tools/nak_host_probe').glob('*')) if p.is_file()},
 'artifacts':{str(p.relative_to(root)):sha(p) for p in artifacts if p.is_file()},
 'limitations':['Host static instruction/statistics not dynamic GPUtime.','Static cycles exclude texture/global memory variable latency.','ld/st histogram includes all loads/stores, not EDRAM-only.','Hardware P0.1 code/register/spill counters still required for exact matching.','Run13 maxStorageBufferRange4294967295 confirms shared binding0 count1, EDRAMoffset16; SDK5UBO layout and cached MSAA1x/fs_key verified. Hardware stats still pending.']
}
(probe/'host-probe-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps([{'hash':s['guest_ps_hash'],'instruction_count':s['instructions'],'histogram_count':s['histogram_total_instructions'],'matches':s['histogram_matches_nak_num_instrs']} for s in summary['results']]))
