// Independent NVK execution check: no Xbox code or game assets.
#include <switch.h>
#include <vulkan/vulkan.h>
#include <cstdio>
#include <cstdlib>
#include <cstdarg>
#include <vector>
#include <cstring>
extern "C" { u32 __nx_applet_type=AppletType_Application; u64 __nx_heap_size=128*1024*1024; }
static FILE* log_file;
static void log(const char* fmt, ...) {
 va_list args; va_start(args,fmt);vfprintf(log_file,fmt,args);va_end(args);
 fputc('\n',log_file);fflush(log_file);
}
static bool checked(VkResult r,const char* step) {
 log("%s result=%d",step,int(r));return r==VK_SUCCESS;
}
// SPIR-V 1.3: one std430 storage buffer of three uints; output=a op b.
static std::vector<uint32_t> shader(int test) {
 std::vector<uint32_t> s={0x07230203,0x00010300,0,64,0};
 auto op=[&](uint32_t code,std::initializer_list<uint32_t> args) {
  s.push_back(((args.size()+1)<<16)|code);s.insert(s.end(),args.begin(),args.end());
 };
 op(17,{1});op(14,{0,1}); // Shader, Logical GLSL450
 op(15,{5,13,0x6e69616d,0});op(16,{13,17,1,1,1}); // main, LocalSize
 op(71,{4,6,4});op(71,{5,2});op(72,{5,0,35,0}); // stride, block, offset
 op(71,{7,34,0});op(71,{7,33,0}); // set 0 binding 0
 op(19,{1});op(33,{2,1});op(21,{3,32,0});op(29,{4,3});op(30,{5,4});
 op(30,{22,3,3});op(21,{23,32,1});op(30,{24,23,23});
 op(32,{6,12,5});op(59,{6,7,12});op(32,{8,12,3});
 op(43,{3,9,0});op(43,{3,10,1});op(43,{3,11,2});
 op(43,{3,30,8});op(43,{3,31,16});op(43,{3,32,24});op(43,{3,33,255});
 op(54,{1,13,0,2});op(248,{14});
 op(65,{8,15,7,9,9});op(65,{8,16,7,9,10});op(65,{8,17,7,9,11});
 op(61,{3,18,15});op(61,{3,19,16});
 if(test==6) {op(194,{3,34,18,30});op(199,{3,20,34,33});}
 else if(test==7) {op(196,{3,34,18,31});op(195,{3,20,34,32});}
 else if(test==4||test==8) {
  if(test==8) {
   op(199,{3,34,18,33});op(194,{3,43,19,30});op(199,{3,35,43,33});
   op(194,{3,44,18,31});op(199,{3,36,44,33});
   op(194,{3,45,19,32});op(199,{3,37,45,33});
  } else {
   op(203,{3,34,18,9,30});op(203,{3,35,19,30,30});
   op(203,{3,36,18,31,30});op(203,{3,37,19,32,30});
  }
  op(196,{3,38,35,30});op(196,{3,39,36,31});op(196,{3,40,37,32});
  op(197,{3,41,34,38});op(197,{3,42,41,39});op(197,{3,20,42,40});
 }else if(test==5) {op(202,{3,20,18,30,30});}
 else if(test==2) {op(151,{22,21,18,19});op(81,{3,20,21,1});} // unsigned high32
 else if(test==3) {
  op(124,{23,25,18});op(124,{23,26,19});op(152,{24,27,25,26});
  op(81,{23,28,27,1});op(124,{3,20,28}); // signed high32, raw bits
 }else op(test?132:128,{3,20,18,19});
 op(62,{17,20});op(253,{});op(56,{});return s;
}
int main() {
 log_file=fopen("/switch/Mercenaries2/nvk-compute-probe.log","w");if(!log_file)return 2;
 setenv("MESA_SHADER_CACHE_DISABLE","true",1);
 bool compat=false;
 if(FILE* flag=fopen("/switch/Mercenaries2/nvk-compute-probe-compat.flag","r")){compat=true;fclose(flag);}
 if(compat)setenv("NAK_DEBUG","emu_sm50,emu_sm50_high",1);
 log("NVK isolated compute probe v2 compatibility=%d",compat);
 char selected[24]="both";
 if(FILE* selection=fopen("/switch/Mercenaries2/nvk-compute-probe-case.txt","r")) {fscanf(selection,"%23s",selected);fclose(selection);}
 log("selected=%s",selected);
 const bool submit_only=strcmp(selected,"high-submit-only")==0;
 const bool compile_only=strcmp(selected,"high-unsigned-compile")==0||submit_only;
 const bool single_dispatch=strcmp(selected,"high-unsigned-once")==0;
 const int first=(compile_only||single_dispatch)?2:strcmp(selected,"multiply")==0?1:strcmp(selected,"high-unsigned")==0?2:strcmp(selected,"high-signed")==0?3:strcmp(selected,"byte-mix")==0?4:strcmp(selected,"signed-byte")==0?5:strcmp(selected,"byte-mask")==0?6:strcmp(selected,"byte-sign-shift")==0?7:strcmp(selected,"byte-mix-masks")==0?8:0;
 const int last=first>=2?first+1:strcmp(selected,"add")==0?1:2;
 const bool capture_assembly=first>=4||compile_only;
 VkApplicationInfo ai{VK_STRUCTURE_TYPE_APPLICATION_INFO};ai.pApplicationName="NVK compute probe";ai.apiVersion=VK_API_VERSION_1_1;
 VkInstanceCreateInfo ici{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};ici.pApplicationInfo=&ai;
 VkInstance instance;if(!checked(vkCreateInstance(&ici,nullptr,&instance),"instance"))return 3;
 uint32_t n=0;vkEnumeratePhysicalDevices(instance,&n,nullptr);log("physical devices=%u",n);if(!n)return 4;
 std::vector<VkPhysicalDevice> devices(n);vkEnumeratePhysicalDevices(instance,&n,devices.data());auto physical=devices[0];
 VkPhysicalDeviceProperties props;vkGetPhysicalDeviceProperties(physical,&props);log("GPU=%s",props.deviceName);
 vkGetPhysicalDeviceQueueFamilyProperties(physical,&n,nullptr);std::vector<VkQueueFamilyProperties> families(n);vkGetPhysicalDeviceQueueFamilyProperties(physical,&n,families.data());
 uint32_t family=0;while(family<n&&!(families[family].queueFlags&VK_QUEUE_COMPUTE_BIT))family++;if(family==n)return 5;
 float priority=1;VkDeviceQueueCreateInfo qci{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};qci.queueFamilyIndex=family;qci.queueCount=1;qci.pQueuePriorities=&priority;
 VkDeviceCreateInfo dci{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};dci.queueCreateInfoCount=1;dci.pQueueCreateInfos=&qci;
 VkPhysicalDevicePipelineExecutablePropertiesFeaturesKHR executable_features{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PIPELINE_EXECUTABLE_PROPERTIES_FEATURES_KHR};
 executable_features.pipelineExecutableInfo=VK_TRUE;
 const char* executable_extension=VK_KHR_PIPELINE_EXECUTABLE_PROPERTIES_EXTENSION_NAME;
 if(capture_assembly){dci.pNext=&executable_features;dci.enabledExtensionCount=1;dci.ppEnabledExtensionNames=&executable_extension;}
 VkDevice device;if(!checked(vkCreateDevice(physical,&dci,nullptr,&device),"device"))return 6;
 VkQueue queue;vkGetDeviceQueue(device,family,0,&queue);
 VkBufferCreateInfo bci{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};bci.size=65536;bci.usage=VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;bci.sharingMode=VK_SHARING_MODE_EXCLUSIVE;
 VkBuffer buffer;if(!checked(vkCreateBuffer(device,&bci,nullptr,&buffer),"buffer"))return 7;
 VkMemoryRequirements req;vkGetBufferMemoryRequirements(device,buffer,&req);VkPhysicalDeviceMemoryProperties mp;vkGetPhysicalDeviceMemoryProperties(physical,&mp);
 uint32_t type=0;while(type<mp.memoryTypeCount&&(!(req.memoryTypeBits&(1u<<type))||!(mp.memoryTypes[type].propertyFlags&VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT)))type++;if(type==mp.memoryTypeCount)return 8;
 VkMemoryAllocateInfo mai{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};mai.allocationSize=req.size;mai.memoryTypeIndex=type;VkDeviceMemory memory;
 if(!checked(vkAllocateMemory(device,&mai,nullptr,&memory),"allocate"))return 9;
 if(!checked(vkBindBufferMemory(device,buffer,memory,0),"bind"))return 10;
 void* mapped;if(!checked(vkMapMemory(device,memory,0,VK_WHOLE_SIZE,0,&mapped),"map"))return 11;
 log("mapped=%p allocation_bytes=%llu buffer_bytes=65536 result_bytes=12",mapped,(unsigned long long)req.size);
 memset(mapped,0xa5,size_t(req.size));
 VkDescriptorSetLayoutBinding binding{0,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,1,VK_SHADER_STAGE_COMPUTE_BIT,nullptr};
 VkDescriptorSetLayoutCreateInfo slci{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};slci.bindingCount=1;slci.pBindings=&binding;VkDescriptorSetLayout layout;
 if(!checked(vkCreateDescriptorSetLayout(device,&slci,nullptr,&layout),"set layout"))return 12;
 VkPipelineLayoutCreateInfo plci{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};plci.setLayoutCount=1;plci.pSetLayouts=&layout;VkPipelineLayout pipeline_layout;
 if(!checked(vkCreatePipelineLayout(device,&plci,nullptr,&pipeline_layout),"pipeline layout"))return 13;
 VkDescriptorPoolSize pool_size{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,1};VkDescriptorPoolCreateInfo dpci{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};dpci.maxSets=1;dpci.poolSizeCount=1;dpci.pPoolSizes=&pool_size;VkDescriptorPool pool;
 if(!checked(vkCreateDescriptorPool(device,&dpci,nullptr,&pool),"descriptor pool"))return 14;
 VkDescriptorSetAllocateInfo dsai{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};dsai.descriptorPool=pool;dsai.descriptorSetCount=1;dsai.pSetLayouts=&layout;VkDescriptorSet set;
 if(!checked(vkAllocateDescriptorSets(device,&dsai,&set),"descriptor set"))return 15;
 VkDescriptorBufferInfo dbi{buffer,0,12};VkWriteDescriptorSet write{VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};write.dstSet=set;write.descriptorCount=1;write.descriptorType=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;write.pBufferInfo=&dbi;vkUpdateDescriptorSets(device,1,&write,0,nullptr);
 VkCommandPoolCreateInfo cpci{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};cpci.queueFamilyIndex=family;cpci.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;VkCommandPool command_pool;
 if(!checked(vkCreateCommandPool(device,&cpci,nullptr,&command_pool),"command pool"))return 16;
 VkCommandBufferAllocateInfo cbai{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};cbai.commandPool=command_pool;cbai.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;cbai.commandBufferCount=1;VkCommandBuffer command;
 if(!checked(vkAllocateCommandBuffers(device,&cbai,&command),"command buffer"))return 17;
 bool all_ok=true;
 for(int test=first;test<last;test++) {
  const char* cases[]={"add","multiply","high-unsigned","high-signed","byte-mix","signed-byte","byte-mask","byte-sign-shift","byte-mix-masks"};log("case=%s",cases[test]);auto code=shader(test);
  VkShaderModuleCreateInfo smci{VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO};smci.codeSize=code.size()*4;smci.pCode=code.data();VkShaderModule module;
  if(!checked(vkCreateShaderModule(device,&smci,nullptr,&module),"shader module"))return 18;
  VkComputePipelineCreateInfo pci{VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO};pci.flags=capture_assembly?VK_PIPELINE_CREATE_CAPTURE_INTERNAL_REPRESENTATIONS_BIT_KHR:0;pci.layout=pipeline_layout;pci.stage={VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO};pci.stage.stage=VK_SHADER_STAGE_COMPUTE_BIT;pci.stage.module=module;pci.stage.pName="main";VkPipeline pipeline;
  if(!checked(vkCreateComputePipelines(device,VK_NULL_HANDLE,1,&pci,nullptr,&pipeline),"pipeline"))return 19;
  if(capture_assembly) {
  auto get_properties=reinterpret_cast<PFN_vkGetPipelineExecutablePropertiesKHR>(vkGetDeviceProcAddr(device,"vkGetPipelineExecutablePropertiesKHR"));
  auto get_representations=reinterpret_cast<PFN_vkGetPipelineExecutableInternalRepresentationsKHR>(vkGetDeviceProcAddr(device,"vkGetPipelineExecutableInternalRepresentationsKHR"));
  if(!get_properties||!get_representations)return 28;
  VkPipelineInfoKHR pipeline_info{VK_STRUCTURE_TYPE_PIPELINE_INFO_KHR};pipeline_info.pipeline=pipeline;
  uint32_t executable_count=0;if(!checked(get_properties(device,&pipeline_info,&executable_count,nullptr),"executable count"))return 29;
  if(FILE* assembly=fopen("/switch/Mercenaries2/nvk-probe-compiler.log","w")) {
   for(uint32_t executable=0;executable<executable_count;executable++) {
    VkPipelineExecutableInfoKHR info{VK_STRUCTURE_TYPE_PIPELINE_EXECUTABLE_INFO_KHR};info.pipeline=pipeline;info.executableIndex=executable;
    uint32_t count=0;if(get_representations(device,&info,&count,nullptr)!=VK_SUCCESS)continue;
    std::vector<VkPipelineExecutableInternalRepresentationKHR> representations(count);
    for(auto& representation:representations)representation.sType=VK_STRUCTURE_TYPE_PIPELINE_EXECUTABLE_INTERNAL_REPRESENTATION_KHR;
    if(get_representations(device,&info,&count,representations.data())!=VK_SUCCESS)continue;
    std::vector<std::vector<char>> contents(count);
    for(uint32_t i=0;i<count;i++){contents[i].resize(representations[i].dataSize);representations[i].pData=contents[i].data();}
    if(get_representations(device,&info,&count,representations.data())!=VK_SUCCESS)continue;
    for(uint32_t i=0;i<count;i++) {
     fprintf(assembly,"REPRESENTATION %s size=%zu text=%u\n",representations[i].name,representations[i].dataSize,representations[i].isText);
     if(representations[i].isText)fwrite(contents[i].data(),1,contents[i].size(),assembly);
     fputc('\n',assembly);
    }
   }
   fclose(assembly);
  }
  }
  if(compile_only) {
   if(submit_only) {
    VkCommandBufferBeginInfo empty_begin{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
    if(!checked(vkBeginCommandBuffer(command,&empty_begin),"empty begin"))return 30;
    if(!checked(vkEndCommandBuffer(command),"empty end"))return 31;
    VkFenceCreateInfo empty_fci{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};VkFence empty_fence;
    if(!checked(vkCreateFence(device,&empty_fci,nullptr,&empty_fence),"empty fence"))return 32;
    VkSubmitInfo empty_submit{VK_STRUCTURE_TYPE_SUBMIT_INFO};empty_submit.commandBufferCount=1;empty_submit.pCommandBuffers=&command;
    if(!checked(vkQueueSubmit(queue,1,&empty_submit,empty_fence),"empty submit"))return 33;
    if(!checked(vkWaitForFences(device,1,&empty_fence,VK_TRUE,2000000000ULL),"empty wait"))return 34;
    vkDestroyFence(device,empty_fence,nullptr);
   }
   log("COMPILE_ONLY=1; no GPU dispatch submitted");fclose(log_file);
   log_file=fopen("/switch/Mercenaries2/nvk-compute-probe.log","a");if(!log_file)return 27;
   vkDestroyPipeline(device,pipeline,nullptr);vkDestroyShaderModule(device,module,nullptr);
   log("COMPILE_TEARDOWN_PASS=1");log("ALL_PASS=1");fclose(log_file);return 0;
  }
  const uint32_t inputs[][2]={{37,19},{0xffffffffu,19},{0x80000000u,2},{0,0xffffffffu},{0xffffffffu,0xffffffffu},{65536,65536},{0x80000000u,0xffffffffu},{0x7fffffffu,0x7fffffffu},{0x12345678u,0xabcdef01u}};
  for(unsigned sample=0;sample<(test?(single_dispatch?1u:9u):1u);sample++) {
  auto* values=static_cast<uint32_t*>(mapped);values[0]=inputs[sample][0];values[1]=inputs[sample][1];values[2]=0xdeadbeef;
  VkMappedMemoryRange range{VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE};range.memory=memory;range.size=VK_WHOLE_SIZE;
  if(!checked(vkFlushMappedMemoryRanges(device,1,&range),"flush"))return 20;
  VkCommandBufferBeginInfo begin{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};if(!checked(vkBeginCommandBuffer(command,&begin),"begin"))return 21;
  vkCmdBindPipeline(command,VK_PIPELINE_BIND_POINT_COMPUTE,pipeline);vkCmdBindDescriptorSets(command,VK_PIPELINE_BIND_POINT_COMPUTE,pipeline_layout,0,1,&set,0,nullptr);vkCmdDispatch(command,1,1,1);
  VkMemoryBarrier barrier{VK_STRUCTURE_TYPE_MEMORY_BARRIER};barrier.srcAccessMask=VK_ACCESS_SHADER_WRITE_BIT;barrier.dstAccessMask=VK_ACCESS_HOST_READ_BIT;
  vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,1,&barrier,0,nullptr,0,nullptr);
  if(!checked(vkEndCommandBuffer(command),"end"))return 22;
  VkFenceCreateInfo fci{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};VkFence fence;if(!checked(vkCreateFence(device,&fci,nullptr,&fence),"fence"))return 23;
  VkSubmitInfo submit{VK_STRUCTURE_TYPE_SUBMIT_INFO};submit.commandBufferCount=1;submit.pCommandBuffers=&command;
  if(!checked(vkQueueSubmit(queue,1,&submit,fence),"submit"))return 24;
  VkResult waited=vkWaitForFences(device,1,&fence,VK_TRUE,2000000000ULL);bool completed=checked(waited,"wait");
  if(completed) {
   if(!checked(vkInvalidateMappedMemoryRanges(device,1,&range),"invalidate"))return 25;
   size_t guard_errors=0, first_guard_error=0;
   for(size_t offset=12;offset<size_t(req.size);offset++)if(static_cast<unsigned char*>(mapped)[offset]!=0xa5){if(!guard_errors)first_guard_error=offset;guard_errors++;}
   log("buffer_guard sample=%u errors=%zu first_offset=%zu",sample,guard_errors,first_guard_error);
   all_ok &= guard_errors==0;
   uint64_t product = test==3 ? uint64_t(int64_t(int32_t(inputs[sample][0]))*int64_t(int32_t(inputs[sample][1]))) : uint64_t(inputs[sample][0])*inputs[sample][1];
   uint32_t expected = test==6 ? ((inputs[sample][0]>>8)&255u) : test==7 ? uint32_t(int32_t(int8_t(inputs[sample][0]>>8))) : (test==4||test==8) ? ((inputs[sample][0]&0x00ff00ffu)|(inputs[sample][1]&0xff00ff00u)) : test==5 ? uint32_t(int32_t(int8_t(inputs[sample][0]>>8))) : test>=2 ? uint32_t(product>>32) : test ? uint32_t(product) : inputs[sample][0]+inputs[sample][1];bool ok=values[2]==expected;all_ok &= ok;log("sample=%u a=%u b=%u output=%u expected=%u pass=%d",sample,inputs[sample][0],inputs[sample][1],values[2],expected,ok);
   vkDestroyFence(device,fence,nullptr);vkResetCommandBuffer(command,0);
   if(!ok) { log("Baseline calculation failed; stopping before another dispatch");break; }
  }else {log("GPU completion unverified; stopping without waiting for device idle");all_ok=false;break;}
  // Leave failed GPU work alone; the bounded runner terminates the process.
  }
  if(!all_ok)break;
  // Persist arithmetic evidence before driver teardown, which is separately tested.
  log("CASE_PASS=1 samples=%u",test?(single_dispatch?1u:9u):1u);fclose(log_file);
  log_file=fopen("/switch/Mercenaries2/nvk-compute-probe.log","a");
  if(!log_file)return 27;
  log("teardown begin");
  vkDestroyPipeline(device,pipeline,nullptr);vkDestroyShaderModule(device,module,nullptr);
  log("teardown complete");
 }
 log("ALL_PASS=%d",all_ok);fclose(log_file);
 // Let the bounded runner collect logs; teardown may wait on a broken emulator queue.
 svcSleepThread(2000000000LL);return all_ok?0:26;
}
