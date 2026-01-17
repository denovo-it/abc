// Copyright Axelera AI, 2025
#pragma once

#define CL_TARGET_OPENCL_VERSION 210
#define CL_USE_DEPRECATED_OPENCL_1_2_APIS
#ifdef __APPLE__
#include <OpenCL/opencl.h>
#else
#include <CL/cl.h>
#include <CL/cl_ext.h>
#endif

#ifdef HAVE_LIBVA
#include <va/va.h>
#if __has_include("CL//cl_va_api_media_sharing_intel.h")
#include "CL/cl_va_api_media_sharing_intel.h"
#define HAS_VAAPI_MEDIA_SHARING
#endif
#endif

#include "AxDataInterface.h"
//#include "AxOpenCl.hpp"

#include <memory>
#include <span>
#include <variant>

extern "C" {
#if defined(__aarch64__)
using clImportMemoryARM_fn = cl_mem (*)(cl_context context, cl_mem_flags flags,
    const cl_import_properties_arm *properties, void *memory, size_t size,
    cl_int *errorcode_ret);

#elif defined(__x86_64__)
#if defined(HAS_VAAPI_MEDIA_SHARING)
using clGetDeviceIDsFromVA_APIMediaINTEL_fn
    = cl_int (*)(cl_platform_id, cl_va_api_device_source_intel, void *,
        cl_va_api_device_set_intel, cl_uint, cl_device_id *, cl_uint *);

using clCreateFromVA_fn = cl_mem (*)(cl_context context, cl_mem_flags flags,
    VASurfaceID_proxy *surface, cl_uint plane, cl_int *errcode_ret);

using clEnqueueAcquireVA_fn = cl_int (*)(cl_command_queue command_queue,
    cl_uint num_objects, const cl_mem *mem_objects, cl_uint num_events_in_wait_list,
    const cl_event *event_wait_list, cl_event *event);

using clEnqueueReleaseVA_fn = cl_int (*)(cl_command_queue command_queue,
    cl_uint num_objects, const cl_mem *mem_objects, cl_uint num_events_in_wait_list,
    const cl_event *event_wait_list, cl_event *event);
#endif
#endif
}

#if defined(__aarch64__)
struct cl_extensions {
  clImportMemoryARM_fn clImportMemoryARM_host;
  clImportMemoryARM_fn clImportMemoryARM_dmabuf;
  bool unified_memory{ false };
};
#elif defined(__x86_64__)
struct cl_extensions {
#ifdef HAS_VAAPI_MEDIA_SHARING
  VADisplay display;
  clGetDeviceIDsFromVA_APIMediaINTEL_fn clGetDeviceIDsFromVA{};
  clCreateFromVA_fn clCreateFromVA{};
  clEnqueueAcquireVA_fn clEnqueueAcquireVA{};
  clEnqueueReleaseVA_fn clEnqueueReleaseVA{};
#else
  void *display;
#endif
  bool unified_memory{ false };
};
#elif
#error "Unsupported architecture"
#endif

cl_extensions init_extensions(cl_platform_id platform, void *display);

std::vector<cl_mem> create_optimal_buffer(cl_context ctx,
    const cl_extensions extensions, int elem_size, int num_elems, int flags,
    const std::variant<void *, int, VASurfaceID_proxy *, opencl_buffer *> &ptr,
    int plane, cl_int &error);

cl_context create_context(cl_platform_id platform, cl_device_id device,
    const cl_extensions &extensions);

bool can_import_dmabuf(const cl_extensions &extensions);

bool can_import_va(const cl_extensions &extensions);

int get_device_id(cl_platform_id platform, cl_device_id *device_id,
    cl_uint *num_devices, const cl_extensions &extensions);

cl_int acquire_va(cl_command_queue commands, const cl_extensions &extensions,
    std::span<cl_mem> buffers);

cl_int release_va(cl_command_queue commands, const cl_extensions &extensions,
    std::span<cl_mem> buffers);

struct opencl_buffer {
  cl_mem buffer{ nullptr };
  cl_event event{ nullptr };
  std::span<uint8_t> data{};
  //  This is all of the GstMemory that the buffer depends on. i.e they
  //  must be around until the kernel that creates this buffer has finished
  //  executing.
  void *mapped{ nullptr };
  std::vector<void *> gst_memories{};
};
