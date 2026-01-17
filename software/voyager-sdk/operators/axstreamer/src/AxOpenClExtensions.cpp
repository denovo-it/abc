// Copyright Axelera AI, 2025
#include "AxOpenClExtensions.hpp"

#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include <algorithm>
#include <vector>

#include <iostream>
#include <optional>

#include <sys/sysmacros.h>

using namespace std::string_literals;

namespace ax_utils
{
std::string cl_error_to_string(cl_int code);
}

bool
has_extension(cl_platform_id platform, const std::string &name)
{
  size_t extSize;
  clGetPlatformInfo(platform, CL_PLATFORM_EXTENSIONS, 0, NULL, &extSize);

  auto extensions = std::vector<char>(extSize);
  clGetPlatformInfo(platform, CL_PLATFORM_EXTENSIONS, extSize, extensions.data(), NULL);
  return std::search(extensions.begin(), extensions.end(), name.begin(), name.end())
         != extensions.end();
}

/// @brief Load an OpenCL extension
/// @param name - The name of the extension
/// @return Pointer to the extension function
void *
load_extension(cl_platform_id platform, const std::string &feature_name,
    const std::string &function_name)
{
  return has_extension(platform, feature_name) ?
             clGetExtensionFunctionAddress(function_name.c_str()) :
             nullptr;
}

#if defined(__aarch64__)
cl_extensions
init_extensions(cl_platform_id platform, void *display)
{
  cl_extensions extensions{
    .clImportMemoryARM_host = reinterpret_cast<clImportMemoryARM_fn>(
        load_extension(platform, "cl_arm_import_memory_host", "clImportMemoryARM")),
    .clImportMemoryARM_dmabuf = reinterpret_cast<clImportMemoryARM_fn>(
        load_extension(platform, "cl_arm_import_memory_dma_buf", "clImportMemoryARM")),
  };


  return extensions;
}

bool
is_aligned(void *ptr, size_t alignment)
{
  return (reinterpret_cast<uintptr_t>(ptr) % alignment) == 0;
}

cl_mem
create_buffer(void *ptr, cl_context ctx, cl_extensions extensions,
    int elem_size, int num_elems, int flags, int plane, int &error)
{
  if ((flags & CL_MEM_READ_ONLY) != 0) {
    flags &= ~(CL_MEM_USE_HOST_PTR | CL_MEM_ALLOC_HOST_PTR | CL_MEM_COPY_HOST_PTR);
    if (extensions.unified_memory) {
      flags |= CL_MEM_USE_HOST_PTR;
    } else {
      flags |= CL_MEM_COPY_HOST_PTR;
    }
  }
  if ((flags & CL_MEM_WRITE_ONLY) != 0 && !ptr) {
    //  Output buffers are best allocated in device memory
    //  when we have an opencl buffer
    flags &= ~(CL_MEM_USE_HOST_PTR | CL_MEM_ALLOC_HOST_PTR | CL_MEM_COPY_HOST_PTR);
    flags |= CL_MEM_ALLOC_HOST_PTR;
  }

  const auto unaligned_size = elem_size * num_elems;
  constexpr size_t cache_size = 64;
  if (extensions.clImportMemoryARM_host && is_aligned(ptr, cache_size)) {
    if ((flags & CL_MEM_WRITE_ONLY) == 0) {
      cl_import_properties_arm properties[] = {
        CL_IMPORT_TYPE_ARM,
        CL_IMPORT_TYPE_HOST_ARM,
        0,
      };
      auto buffer = extensions.clImportMemoryARM_host(
          ctx, CL_MEM_READ_ONLY, properties, ptr, unaligned_size, &error);
      if (error == CL_SUCCESS) {
        return { buffer };
      }
    }
  }
  const int page_size = 4096;
  const auto aligned_size = (elem_size * num_elems + page_size - 1) & ~(page_size - 1);
  const auto size = ptr != 0 ? unaligned_size : aligned_size;
  auto buffer = clCreateBuffer(ctx, flags, size, ptr, &error);
  if (error != CL_SUCCESS) {
    throw std::runtime_error("Failed to create OpenCL buffer, error = " + std::to_string(error)
                             + ", flags = " + std::to_string(flags));
  }
  return buffer;
}

std::vector<cl_mem>
create_optimal_buffer(cl_context ctx, cl_extensions extensions, int elem_size,
    int num_elems, int flags,
    const std::variant<void *, int, VASurfaceID_proxy *, opencl_buffer *> &ptr,
    int plane, int &error)
{
  if (std::holds_alternative<int>(ptr)) {
    auto fd = std::get<int>(ptr);
    if (extensions.clImportMemoryARM_dmabuf) {
      cl_import_properties_arm properties[]
          = { CL_IMPORT_TYPE_ARM, CL_IMPORT_TYPE_DMA_BUF_ARM, 0 };
      auto buffer = extensions.clImportMemoryARM_dmabuf(
          ctx, flags, properties, &fd, elem_size * num_elems, &error);
      if (error != CL_SUCCESS) {
        throw std::runtime_error("Failed to create buffer, error: "
                                 + ax_utils::cl_error_to_string(error));
      }
      return { buffer };
    } else {
      throw std::runtime_error("Import of dmabuf is not supported");
    }
  }

  if (std::holds_alternative<opencl_buffer *>(ptr)) {
    //  If we have an opencl buffer, then we can use it directly
    auto *ocl_buffer = std::get<opencl_buffer *>(ptr);
    if (!ocl_buffer->buffer) {
      ocl_buffer->buffer = create_buffer(ocl_buffer->data.data(), ctx,
          extensions, elem_size, num_elems, flags, plane, error);
      //  Here we currently do not have a buffer so we create one.
      if (error != CL_SUCCESS) {
        throw std::runtime_error("Failed to create OpenCL buffer, error: "
                                 + ax_utils::cl_error_to_string(error)
                                 + ", flags = " + std::to_string(flags));
      }
    }
    //  This ensures that the buffer lasts after its final use in this element
    clRetainMemObject(ocl_buffer->buffer);
    return { ocl_buffer->buffer };
  }
  auto buffer = create_buffer(std::get<void *>(ptr), ctx, extensions, elem_size,
      num_elems, flags, plane, error);
  if (error != CL_SUCCESS) {
    throw std::runtime_error("Failed to create OpenCL buffer, error = " + std::to_string(error)
                             + ", flags = " + std::to_string(flags));
  }
  return { buffer };
}

int
get_device_id(cl_platform_id platform, cl_device_id *device_id,
    cl_uint *num_devices, const cl_extensions &extensions)
{
  return clGetDeviceIDs(platform, CL_DEVICE_TYPE_GPU, 1, device_id, num_devices);
}

bool
can_import_dmabuf(const cl_extensions &extensions)
{
  return extensions.clImportMemoryARM_dmabuf != nullptr;
}

bool
can_import_va(const cl_extensions &extensions)
{
  return false;
}

cl_context
create_context(cl_platform_id platform, cl_device_id device, const cl_extensions &extensions)
{
  cl_int error;
  cl_context_properties props[] = {
    // clang-format off
    CL_CONTEXT_PLATFORM, (cl_context_properties)platform,
    0,
    // clang-format on
  };

  auto context = clCreateContext(props, 1, &device, NULL, NULL, &error);
  if (error != CL_SUCCESS) {
    throw std::runtime_error("Failed to create OpenCL context, error: "
                             + ax_utils::cl_error_to_string(error));
  }
  return context;
}

cl_int
acquire_va(cl_command_queue, const cl_extensions &, std::span<cl_mem>)
{
  return CL_SUCCESS;
}

cl_int
release_va(cl_command_queue, const cl_extensions &, std::span<cl_mem>)
{
  return CL_SUCCESS;
}

#elif defined(__x86_64__)
cl_extensions
init_extensions(cl_platform_id platform, void *display)
{
  cl_extensions extensions
  {
#if defined(HAS_VAAPI_MEDIA_SHARING)
    .display = display,
    .clGetDeviceIDsFromVA = reinterpret_cast<clGetDeviceIDsFromVA_APIMediaINTEL_fn>(
        load_extension(platform, "cl_intel_va_api_media_sharing",
            "clGetDeviceIDsFromVA_APIMediaAdapterINTEL")),
    .clCreateFromVA = reinterpret_cast<clCreateFromVA_fn>(load_extension(platform,
        "cl_intel_va_api_media_sharing", "clCreateFromVA_APIMediaSurfaceINTEL")),
    .clEnqueueAcquireVA = reinterpret_cast<clEnqueueAcquireVA_fn>(load_extension(platform,
        "cl_intel_va_api_media_sharing", "clEnqueueAcquireVA_APIMediaSurfacesINTEL")),
    .clEnqueueReleaseVA = reinterpret_cast<clEnqueueReleaseVA_fn>(load_extension(platform,
        "cl_intel_va_api_media_sharing", "clEnqueueReleaseVA_APIMediaSurfacesINTEL"))
  };

  if (!extensions.clGetDeviceIDsFromVA || !extensions.clCreateFromVA
      || !extensions.clEnqueueAcquireVA || !extensions.clEnqueueReleaseVA) {
    extensions.display = nullptr;
#else
    .display = nullptr
#endif
  };
  return extensions;
}

bool
should_check_cpu(const std::string_view platform_name)
{
  // For Intel and POCL platforms, prefer CPU devices
  return platform_name.find("Intel") != std::string::npos
         || platform_name.find("Portable Computing Language") != std::string::npos;
}

int
get_device_id(cl_platform_id platform, cl_device_id *device_id,
    cl_uint *num_devices, const cl_extensions &extensions)
{
  if (extensions.display) {
#if defined(HAS_VAAPI_MEDIA_SHARING)
    return extensions.clGetDeviceIDsFromVA(platform, CL_VA_API_DISPLAY_INTEL,
        extensions.display, CL_PREFERRED_DEVICES_FOR_VA_API_INTEL, 1, device_id, num_devices);
#endif
  }

  // Check platform type for intelligent device selection
  char platform_name[256];
  clGetPlatformInfo(platform, CL_PLATFORM_NAME, sizeof(platform_name), platform_name, nullptr);

  auto device_types = should_check_cpu(platform_name) ?
                          std::array<cl_device_type, 3>{
                            CL_DEVICE_TYPE_CPU,
                            CL_DEVICE_TYPE_GPU,
                            CL_DEVICE_TYPE_ALL,
                          } :
                          std::array<cl_device_type, 3>{
                            CL_DEVICE_TYPE_GPU,
                            CL_DEVICE_TYPE_CPU,
                            CL_DEVICE_TYPE_ALL,
                          };

  cl_int result = CL_DEVICE_NOT_AVAILABLE;
  for (const auto &device_type : device_types) {
    result = clGetDeviceIDs(platform, device_type, 1, device_id, num_devices);
    if (result == CL_SUCCESS) {
      break;
    }
  }
  return result;
}

cl_context
create_context(cl_platform_id platform, cl_device_id device, const cl_extensions &extensions)
{
  cl_int error;
#if defined(HAS_VAAPI_MEDIA_SHARING)
  if (extensions.display == nullptr) {
    cl_context_properties props[] = {
      // clang-format off
      CL_CONTEXT_PLATFORM, (cl_context_properties)platform,
      0,
      // clang-format on
    };
    auto context = clCreateContext(props, 1, &device, NULL, NULL, &error);
    if (error != CL_SUCCESS) {
      throw std::runtime_error("Failed to create OpenCL context, error: "s
                               + ax_utils::cl_error_to_string(error));
    }
    return context;
  }
  cl_context_properties props[] = {
    // clang-format off
    CL_CONTEXT_PLATFORM, (cl_context_properties)platform,
    CL_CONTEXT_VA_API_DISPLAY_INTEL, (cl_context_properties) extensions.display,
    CL_CONTEXT_INTEROP_USER_SYNC, CL_FALSE,
    0,
    // clang-format on
  };

  auto context = clCreateContext(props, 1, &device, NULL, NULL, &error);
  if (error != CL_SUCCESS) {
    throw std::runtime_error("Failed to create OpenCL context, error: "
                             + ax_utils::cl_error_to_string(error));
  }
  return context;
#else
  cl_context_properties props[] = {
    // clang-format off
  CL_CONTEXT_PLATFORM, (cl_context_properties)platform,
  0,
    // clang-format on
  };
  auto context = clCreateContext(props, 1, &device, NULL, NULL, &error);
  if (error != CL_SUCCESS) {
    throw std::runtime_error("Failed to create OpenCL context, error: "
                             + ax_utils::cl_error_to_string(error));
  }
  return context;

#endif
}

std::vector<cl_mem>
create_optimal_buffer(cl_context ctx, cl_extensions extensions, int elem_size,
    int num_elems, int flags,
    const std::variant<void *, int, VASurfaceID_proxy *, opencl_buffer *> &ptr,
    int num_planes, int &error)
{
#if defined(HAS_VAAPI_MEDIA_SHARING)
  if (std::holds_alternative<VASurfaceID_proxy *>(ptr)) {
    auto surface = std::get<VASurfaceID_proxy *>(ptr);
    if (extensions.clCreateFromVA) {
      flags &= ~CL_MEM_USE_HOST_PTR;
      auto buffers = std::vector<cl_mem>{};
      for (int i = 0; i != num_planes; ++i) {
        auto buffer = extensions.clCreateFromVA(ctx, flags, surface, i, &error);
        if (error != CL_SUCCESS) {
          throw std::runtime_error("Failed to create buffer, error: "
                                   + ax_utils::cl_error_to_string(error));
        }
        cl_image_format format;
        clGetImageInfo(buffer, CL_IMAGE_FORMAT, sizeof(cl_image_format), &format, NULL);
        buffers.push_back(buffer);
      }
      return buffers;
    } else {
      throw std::runtime_error("Import of VA surfaces is not supported");
    }
  }
#endif
  if ((flags & CL_MEM_READ_ONLY) != 0) {
    flags &= ~(CL_MEM_USE_HOST_PTR | CL_MEM_ALLOC_HOST_PTR | CL_MEM_COPY_HOST_PTR);
    if (extensions.unified_memory) {
      flags |= CL_MEM_USE_HOST_PTR;
    } else {
      flags |= CL_MEM_COPY_HOST_PTR;
    }
  }
  if (std::holds_alternative<opencl_buffer *>(ptr)) {
    //  If we have an opencl buffer, then we can use it directly
    auto *ocl_buffer = std::get<opencl_buffer *>(ptr);
    if (!ocl_buffer->buffer) {
      //  Here we currently do not have a buffer so we create one.
      void *buffer = ocl_buffer->data.data();
      if ((flags & CL_MEM_WRITE_ONLY) != 0) {
        flags |= CL_MEM_HOST_READ_ONLY;
      }
      cl_int error = CL_SUCCESS;
      const int page_size = 4096;
      auto size = (elem_size * num_elems + page_size - 1) & ~(page_size - 1);
      ocl_buffer->buffer = clCreateBuffer(ctx, flags, size, buffer, &error);
      if (error != CL_SUCCESS) {
        throw std::runtime_error("Failed to create OpenCL buffer, error: "
                                 + ax_utils::cl_error_to_string(error)
                                 + ", flags = " + std::to_string(flags));
      }
    }
    //  This ensures that the buffer lasts after its final use in this element
    clRetainMemObject(ocl_buffer->buffer);
    return { ocl_buffer->buffer };
  }
  return { clCreateBuffer(ctx, flags, elem_size * num_elems, std::get<void *>(ptr), &error) };
}


bool
can_import_dmabuf(const cl_extensions &extensions)
{
  return false;
}

bool
can_import_va(const cl_extensions &extensions)
{
  return extensions.display != nullptr;
}

int
acquire_va(cl_command_queue commands, const cl_extensions &extensions, std::span<cl_mem> buffers)
{
#if defined(HAS_VAAPI_MEDIA_SHARING)
  if (extensions.clEnqueueAcquireVA) {
    return extensions.clEnqueueAcquireVA(
        commands, buffers.size(), buffers.data(), 0, NULL, NULL);
  }
#endif
  return CL_SUCCESS;
}

int
release_va(cl_command_queue commands, const cl_extensions &extensions, std::span<cl_mem> buffers)
{
#if defined(HAS_VAAPI_MEDIA_SHARING)
  if (extensions.clEnqueueReleaseVA) {
    return extensions.clEnqueueReleaseVA(
        commands, buffers.size(), buffers.data(), 0, NULL, NULL);
  }
#endif
  return CL_SUCCESS;
}

#elif
#error unsupported architecture
#endif
