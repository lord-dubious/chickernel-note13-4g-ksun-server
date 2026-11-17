#define VK_NO_PROTOTYPES
#include <vulkan/vulkan.h>
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define LOAD(name) PFN_##name name=(PFN_##name)dlsym(library,#name); if(!name){fprintf(stderr,"Missing %s\n",#name);return 2;}
#define CHECK(call) do { VkResult r=(call); if(r!=VK_SUCCESS){fprintf(stderr,"%s failed: %d\n",#call,r);return 3;} } while(0)

int main(int argc,char **argv) {
    void *library=dlopen("/system/lib64/libvulkan.so",RTLD_NOW|RTLD_LOCAL);
    if(!library){fprintf(stderr,"Vulkan loader: %s\n",dlerror());return 1;}
    LOAD(vkCreateInstance); LOAD(vkDestroyInstance); LOAD(vkEnumeratePhysicalDevices);
    LOAD(vkGetPhysicalDeviceProperties); LOAD(vkGetPhysicalDeviceQueueFamilyProperties);
    LOAD(vkGetPhysicalDeviceMemoryProperties); LOAD(vkCreateDevice); LOAD(vkDestroyDevice);
    LOAD(vkCreateBuffer); LOAD(vkDestroyBuffer); LOAD(vkGetBufferMemoryRequirements);
    LOAD(vkAllocateMemory); LOAD(vkFreeMemory); LOAD(vkBindBufferMemory); LOAD(vkMapMemory); LOAD(vkUnmapMemory);
    LOAD(vkCreateShaderModule); LOAD(vkDestroyShaderModule);
    LOAD(vkCreateDescriptorSetLayout); LOAD(vkDestroyDescriptorSetLayout);
    LOAD(vkCreatePipelineLayout); LOAD(vkDestroyPipelineLayout); LOAD(vkCreateComputePipelines); LOAD(vkDestroyPipeline);
    LOAD(vkCreateDescriptorPool); LOAD(vkDestroyDescriptorPool); LOAD(vkAllocateDescriptorSets); LOAD(vkUpdateDescriptorSets);
    LOAD(vkCreateCommandPool); LOAD(vkDestroyCommandPool); LOAD(vkAllocateCommandBuffers);
    LOAD(vkBeginCommandBuffer); LOAD(vkEndCommandBuffer); LOAD(vkCmdPipelineBarrier);
    LOAD(vkCmdBindPipeline); LOAD(vkCmdBindDescriptorSets); LOAD(vkCmdDispatch);
    LOAD(vkGetDeviceQueue); LOAD(vkCreateFence); LOAD(vkDestroyFence); LOAD(vkQueueSubmit); LOAD(vkWaitForFences);
    VkApplicationInfo app={.sType=VK_STRUCTURE_TYPE_APPLICATION_INFO,.pApplicationName="SapphireComputeProof",.apiVersion=VK_API_VERSION_1_0};
    VkInstanceCreateInfo instance_info={.sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,.pApplicationInfo=&app};
    VkInstance instance; CHECK(vkCreateInstance(&instance_info,NULL,&instance));
    uint32_t count=0; CHECK(vkEnumeratePhysicalDevices(instance,&count,NULL));
    if(!count || count>16)return 4;
    VkPhysicalDevice devices[16],physical=VK_NULL_HANDLE;
    CHECK(vkEnumeratePhysicalDevices(instance,&count,devices));
    VkPhysicalDeviceProperties properties;
    for(uint32_t i=0;i<count;i++){
        vkGetPhysicalDeviceProperties(devices[i],&properties);
        if(properties.vendorID==0x5143 && properties.deviceType!=VK_PHYSICAL_DEVICE_TYPE_CPU && strstr(properties.deviceName,"Adreno") && strstr(properties.deviceName,"610")){physical=devices[i];break;}
    }
    if(physical==VK_NULL_HANDLE){fputs("No hardware Adreno 610 device; software fallback rejected\n",stderr);return 5;}
    printf("GPU_DEVICE=%s vendor=0x%x api=%u.%u.%u\n",properties.deviceName,properties.vendorID,VK_VERSION_MAJOR(properties.apiVersion),VK_VERSION_MINOR(properties.apiVersion),VK_VERSION_PATCH(properties.apiVersion));
    if(argc==1){vkDestroyInstance(instance,NULL);puts("GPU_DEVICE_ACCESS=PASS");return 0;}
    uint32_t families_count=0;vkGetPhysicalDeviceQueueFamilyProperties(physical,&families_count,NULL);
    if(!families_count || families_count>32)return 6;
    VkQueueFamilyProperties families[32];vkGetPhysicalDeviceQueueFamilyProperties(physical,&families_count,families);
    uint32_t family=UINT32_MAX;
    for(uint32_t i=0;i<families_count;i++)if(families[i].queueCount && (families[i].queueFlags&VK_QUEUE_COMPUTE_BIT)){family=i;break;}
    if(family==UINT32_MAX)return 7;
    float priority=0.5f;
    VkDeviceQueueCreateInfo queue_info={.sType=VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,.queueFamilyIndex=family,.queueCount=1,.pQueuePriorities=&priority};
    VkDeviceCreateInfo device_info={.sType=VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,.queueCreateInfoCount=1,.pQueueCreateInfos=&queue_info};
    VkDevice device;CHECK(vkCreateDevice(physical,&device_info,NULL,&device));
    VkBufferCreateInfo buffer_info={.sType=VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,.size=256*sizeof(uint32_t),.usage=VK_BUFFER_USAGE_STORAGE_BUFFER_BIT,.sharingMode=VK_SHARING_MODE_EXCLUSIVE};
    VkBuffer buffer;CHECK(vkCreateBuffer(device,&buffer_info,NULL,&buffer));
    VkMemoryRequirements requirements;vkGetBufferMemoryRequirements(device,buffer,&requirements);
    VkPhysicalDeviceMemoryProperties memory_properties;vkGetPhysicalDeviceMemoryProperties(physical,&memory_properties);
    uint32_t memory_type=UINT32_MAX;
    for(uint32_t i=0;i<memory_properties.memoryTypeCount;i++){
        VkMemoryPropertyFlags flags=memory_properties.memoryTypes[i].propertyFlags;
        if((requirements.memoryTypeBits&(1u<<i)) && (flags&(VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT))==(VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)){memory_type=i;break;}
    }
    if(memory_type==UINT32_MAX || requirements.size>1024*1024)return 8;
    VkMemoryAllocateInfo allocation={.sType=VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,.allocationSize=requirements.size,.memoryTypeIndex=memory_type};
    VkDeviceMemory memory;CHECK(vkAllocateMemory(device,&allocation,NULL,&memory));
    CHECK(vkBindBufferMemory(device,buffer,memory,0));
    uint32_t *mapped;CHECK(vkMapMemory(device,memory,0,VK_WHOLE_SIZE,0,(void **)&mapped));
    for(uint32_t i=0;i<256;i++)mapped[i]=i;
    FILE *file=fopen(argv[1],"rb");if(!file)return 9;
    if(fseek(file,0,SEEK_END))return 9;
    long shader_size=ftell(file);rewind(file);
    if(shader_size<=0 || shader_size>65536 || shader_size%4)return 10;
    uint32_t *code=malloc((size_t)shader_size);if(!code)return 11;
    if(fread(code,1,(size_t)shader_size,file)!=(size_t)shader_size)return 12;
    fclose(file);
    VkShaderModuleCreateInfo shader_info={.sType=VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,.codeSize=(size_t)shader_size,.pCode=code};
    VkShaderModule shader;CHECK(vkCreateShaderModule(device,&shader_info,NULL,&shader));free(code);
    VkDescriptorSetLayoutBinding binding={.binding=0,.descriptorType=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,.descriptorCount=1,.stageFlags=VK_SHADER_STAGE_COMPUTE_BIT};
    VkDescriptorSetLayoutCreateInfo set_info={.sType=VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,.bindingCount=1,.pBindings=&binding};
    VkDescriptorSetLayout set_layout;CHECK(vkCreateDescriptorSetLayout(device,&set_info,NULL,&set_layout));
    VkPipelineLayoutCreateInfo layout_info={.sType=VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,.setLayoutCount=1,.pSetLayouts=&set_layout};
    VkPipelineLayout layout;CHECK(vkCreatePipelineLayout(device,&layout_info,NULL,&layout));
    VkComputePipelineCreateInfo pipeline_info={.sType=VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO,.stage={.sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,.stage=VK_SHADER_STAGE_COMPUTE_BIT,.module=shader,.pName="main"},.layout=layout};
    VkPipeline pipeline;CHECK(vkCreateComputePipelines(device,VK_NULL_HANDLE,1,&pipeline_info,NULL,&pipeline));
    VkDescriptorPoolSize pool_size={.type=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,.descriptorCount=1};
    VkDescriptorPoolCreateInfo pool_info={.sType=VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,.maxSets=1,.poolSizeCount=1,.pPoolSizes=&pool_size};
    VkDescriptorPool pool;CHECK(vkCreateDescriptorPool(device,&pool_info,NULL,&pool));
    VkDescriptorSetAllocateInfo set_alloc={.sType=VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,.descriptorPool=pool,.descriptorSetCount=1,.pSetLayouts=&set_layout};
    VkDescriptorSet set;CHECK(vkAllocateDescriptorSets(device,&set_alloc,&set));
    VkDescriptorBufferInfo descriptor={.buffer=buffer,.offset=0,.range=256*sizeof(uint32_t)};
    VkWriteDescriptorSet write={.sType=VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,.dstSet=set,.dstBinding=0,.descriptorCount=1,.descriptorType=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,.pBufferInfo=&descriptor};
    vkUpdateDescriptorSets(device,1,&write,0,NULL);
    VkCommandPoolCreateInfo command_pool_info={.sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,.queueFamilyIndex=family};
    VkCommandPool command_pool;CHECK(vkCreateCommandPool(device,&command_pool_info,NULL,&command_pool));
    VkCommandBufferAllocateInfo command_alloc={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,.commandPool=command_pool,.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY,.commandBufferCount=1};
    VkCommandBuffer command;CHECK(vkAllocateCommandBuffers(device,&command_alloc,&command));
    VkCommandBufferBeginInfo begin={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};CHECK(vkBeginCommandBuffer(command,&begin));
    VkBufferMemoryBarrier barrier={.sType=VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER,.srcAccessMask=VK_ACCESS_HOST_WRITE_BIT,.dstAccessMask=VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT,.srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.buffer=buffer,.offset=0,.size=256*sizeof(uint32_t)};
    vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_HOST_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,0,0,NULL,1,&barrier,0,NULL);
    vkCmdBindPipeline(command,VK_PIPELINE_BIND_POINT_COMPUTE,pipeline);
    vkCmdBindDescriptorSets(command,VK_PIPELINE_BIND_POINT_COMPUTE,layout,0,1,&set,0,NULL);
    vkCmdDispatch(command,4,1,1);
    barrier.srcAccessMask=VK_ACCESS_SHADER_WRITE_BIT;barrier.dstAccessMask=VK_ACCESS_HOST_READ_BIT;
    vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,0,NULL,1,&barrier,0,NULL);
    CHECK(vkEndCommandBuffer(command));
    VkQueue queue;vkGetDeviceQueue(device,family,0,&queue);
    VkFenceCreateInfo fence_info={.sType=VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};VkFence fence;CHECK(vkCreateFence(device,&fence_info,NULL,&fence));
    VkSubmitInfo submit={.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO,.commandBufferCount=1,.pCommandBuffers=&command};CHECK(vkQueueSubmit(queue,1,&submit,fence));
    CHECK(vkWaitForFences(device,1,&fence,VK_TRUE,5000000000ULL));
    for(uint32_t i=0;i<256;i++)if(mapped[i]!=i*3+7){fprintf(stderr,"GPU result mismatch at %u\n",i);return 13;}
    puts("GPU_COMPUTE_RESULT=PASS elements=256");
    vkDestroyFence(device,fence,NULL);vkDestroyCommandPool(device,command_pool,NULL);vkDestroyDescriptorPool(device,pool,NULL);
    vkDestroyPipeline(device,pipeline,NULL);vkDestroyPipelineLayout(device,layout,NULL);vkDestroyDescriptorSetLayout(device,set_layout,NULL);vkDestroyShaderModule(device,shader,NULL);
    vkUnmapMemory(device,memory);vkDestroyBuffer(device,buffer,NULL);vkFreeMemory(device,memory,NULL);vkDestroyDevice(device,NULL);vkDestroyInstance(instance,NULL);dlclose(library);
    return 0;
}
