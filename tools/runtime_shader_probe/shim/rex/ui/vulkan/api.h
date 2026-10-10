#pragma once
// Host probe has no window system or Vulkan calls; preserve core Vulkan types.
#define VK_NO_PROTOTYPES
#define VK_ENABLE_BETA_EXTENSIONS
#include <vulkan/vulkan.h>
