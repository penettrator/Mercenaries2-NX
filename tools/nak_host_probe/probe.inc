/* Offline fragment compiler. Included into the isolated nvk_shader.c snapshot. */
#include "vk_nir.h"
#include "nvk_descriptor_types.h"
#include "compiler/spirv/spirv_info.h"
#include <stdio.h>
static struct vk_descriptor_set_layout **probe_layouts(struct nvk_device *dev, nir_shader *nir, uint32_t *count) {
   struct nvk_descriptor_set_layout *layouts[NVK_MAX_SETS] = {0};
   nir_foreach_variable_with_modes(var, nir, nir_var_uniform | nir_var_image | nir_var_mem_ubo | nir_var_mem_ssbo) {
      unsigned set = var->data.descriptor_set, binding = var->data.binding;
      if (set >= NVK_MAX_SETS || binding >= 256) { fprintf(stderr, "layout limit\n"); exit(3); }
      if (!layouts[set]) layouts[set] = calloc(1, sizeof(*layouts[set]) + 256 * sizeof(layouts[set]->binding[0]));
      struct nvk_descriptor_set_layout *l = layouts[set];
      const struct glsl_type *t = glsl_without_array(var->type);
      VkDescriptorType type;
      if (var->data.mode == nir_var_mem_ubo) type = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
      else if (var->data.mode == nir_var_mem_ssbo) type = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
      else if (glsl_type_is_texture(t)) type = VK_DESCRIPTOR_TYPE_SAMPLED_IMAGE;
      else if (glsl_type_is_bare_sampler(t)) type = VK_DESCRIPTOR_TYPE_SAMPLER;
      else { fprintf(stderr, "unsupported descriptor %s\n", var->name); exit(3); }
      uint32_t stride, alignment;
      nvk_descriptor_stride_align_for_type(nvk_device_physical(dev), 0, type, NULL, &stride, &alignment);
      l->binding[binding].type = type;
      l->binding[binding].array_size = glsl_type_is_array(var->type) ? glsl_get_aoa_size(var->type) : 1;
      l->binding[binding].stride = stride;
      l->binding_count = MAX2(l->binding_count, binding + 1);
      *count = MAX2(*count, set + 1);
   }
   /* SDK constant layout has all 5 UBO bindings, including unused vertex float constants. */
   if (!layouts[1]) layouts[1] = calloc(1, sizeof(*layouts[1]) + 256 * sizeof(layouts[1]->binding[0]));
   layouts[1]->binding_count = 5; *count = MAX2(*count, 2);
   for (unsigned b = 0; b < 5; b++) {
      layouts[1]->binding[b].type = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
      layouts[1]->binding[b].array_size = 1;
      layouts[1]->binding[b].stride = sizeof(union nvk_buffer_descriptor);
   }
   struct vk_descriptor_set_layout **result = calloc(*count, sizeof(*result));
   for (unsigned s = 0; s < *count; s++) {
      if (!layouts[s]) layouts[s] = calloc(1, sizeof(*layouts[s]));
      struct nvk_descriptor_set_layout *l = layouts[s];
      unsigned offset = 0;
      for (unsigned b = 0; b < l->binding_count; b++) {
         unsigned stride = l->binding[b].stride;
         if (!stride) continue;
         offset = align(offset, stride);
         l->binding[b].offset = offset;
         fprintf(stderr, "LAYOUT set=%u binding=%u type=%u count=%u stride=%u offset=%u\n", s, b, (unsigned)l->binding[b].type, l->binding[b].array_size, stride, offset);
         offset += stride * l->binding[b].array_size;
      }
      l->non_variable_descriptor_buffer_size = offset;
      l->max_buffer_size = offset;
      result[s] = &l->vk;
   }
   return result;
}
int main(int argc, char **argv) {
   if (argc < 3 || argc > 4) { fprintf(stderr, "usage: nak-host-probe INPUT.spv OUTPUT_PREFIX [ps|vs]\n"); return 2; }
   mesa_shader_stage stage = argc > 3 && strcmp(argv[3], "vs") == 0 ? MESA_SHADER_VERTEX : MESA_SHADER_FRAGMENT;
   FILE *f = fopen(argv[1], "rb"); if (!f) return 2;
   fseek(f, 0, SEEK_END); size_t bytes = ftell(f); rewind(f);
   uint32_t *words = malloc(bytes); if (fread(words, 1, bytes, f) != bytes) return 2; fclose(f);
   struct nvk_instance instance = {0};
   struct nvk_physical_device pdev = {0};
   struct nvk_device dev = {0};
   pdev.vk.instance = &instance.vk;
   pdev.info = (struct nv_device_info) { .type = NV_DEVICE_TYPE_SOC, .sm = 53, .chipset = 0x12b, .cls_eng3d = 0xb197, .cls_compute = 0xb1c0, .max_warps_per_mp = 64, .mp_per_tpc = 1 };
   pdev.nak = nak_compiler_create(&pdev.info);
   dev.vk.physical = &pdev.vk;
   struct vk_pipeline_robustness_state rs = { .uniform_buffers = VK_PIPELINE_ROBUSTNESS_BUFFER_BEHAVIOR_ROBUST_BUFFER_ACCESS_EXT, .storage_buffers = VK_PIPELINE_ROBUSTNESS_BUFFER_BEHAVIOR_ROBUST_BUFFER_ACCESS_EXT };
   rs.null_uniform_buffer_descriptor = true; rs.null_storage_buffer_descriptor = true;
   struct spirv_to_nir_options opts = nvk_get_spirv_options(&pdev.vk, stage, &rs);
   struct spirv_capabilities caps; memset(&caps, 1, sizeof(caps)); opts.capabilities = &caps;
   glsl_type_singleton_init_or_ref();
   nir_shader *nir = spirv_to_nir(words, bytes / 4, NULL, stage, "main", &opts, nak_nir_options(pdev.nak));
   if (!nir) return 3;
   NIR_PASS(_, nir, nir_lower_variable_initializers, nir_var_function_temp);
   NIR_PASS(_, nir, nir_lower_returns);
   NIR_PASS(_, nir, nir_inline_functions);
   NIR_PASS(_, nir, nir_opt_copy_prop);
   NIR_PASS(_, nir, nir_opt_constant_folding);
   NIR_PASS(_, nir, nir_opt_deref);
   nir_remove_non_cmat_call_entrypoints(nir);
   NIR_PASS(_, nir, nir_lower_variable_initializers, ~0);
   NIR_PASS(_, nir, nir_split_var_copies);
   NIR_PASS(_, nir, nir_split_per_member_structs);
   NIR_PASS(_, nir, nir_remove_dead_variables, nir_var_shader_in | nir_var_shader_out | nir_var_system_value, NULL);
   NIR_PASS(_, nir, nir_propagate_invariant, false);
   nir->info.api_subgroup_size = 32; nir->info.min_subgroup_size = 32; nir->info.max_subgroup_size = 32;
   uint32_t count = 0;
   struct vk_descriptor_set_layout **layouts = probe_layouts(&dev, nir, &count);
   nvk_preprocess_nir(&pdev.vk, nir, &rs);
   struct nvk_cbuf_map cbuf = {0};
   nvk_lower_nir(&dev, nir, 0, &rs, count, layouts, &cbuf);
   struct nak_fs_key key = {0};
   struct nak_shader_bin *bin = nak_compile_shader(nir, true, pdev.nak, 0, stage == MESA_SHADER_FRAGMENT ? &key : NULL, true);
   if (!bin) return 4;
   char path[4096]; snprintf(path, sizeof(path), "%s.sass", argv[2]);
   f = fopen(path, "w"); if (!f) return 2; fputs(bin->asm_str, f); fclose(f);
   snprintf(path, sizeof(path), "%s.json", argv[2]); f = fopen(path, "w");
   fprintf(f, "{\"sm\":53,\"registers\":%u,\"local_bytes\":%u,\"warps_per_sm\":%u,\"instructions\":%u,\"static_cycles\":%llu,\"spills_to_memory\":%u,\"fills_from_memory\":%u,\"code_bytes\":%u}\n", bin->info.num_gprs, bin->info.slm_size, bin->info.max_warps_per_sm, bin->info.num_instrs, (unsigned long long)bin->info.num_static_cycles, bin->info.num_spills_to_mem, bin->info.num_fills_from_mem, bin->code_size); fclose(f);
   return 0;
}







