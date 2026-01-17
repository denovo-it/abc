// Copyright Axelera AI, 2025

#include "GstAxBufferPool.hpp"
#include <gst/gst.h>
#include <gst/video/video.h>
#include "GstAxDataUtils.hpp"

GST_DEBUG_CATEGORY_STATIC(gst_ax_buffer_pool_debug);
#define GST_CAT_DEFAULT gst_ax_buffer_pool_debug

#define gst_ax_buffer_pool_parent_class parent_class
G_DEFINE_TYPE(GstAxBufferPool, gst_ax_buffer_pool, GST_TYPE_BUFFER_POOL);

///
/// @brief Reset buffer when it's released back to the pool
///
/// This function is called when a buffer is released back into the pool.
/// It's responsible for cleaning up OpenCL resources and resetting the
/// buffer to a clean state for reuse.
/// @param pool The buffer pool
/// @param buffer The buffer being reset
///
static void
gst_ax_buffer_pool_reset_buffer(GstBufferPool *pool, GstBuffer *buffer)
{
  GST_LOG_OBJECT(pool, "Resetting buffer %p", buffer);
  // Get the number of memory blocks in the buffer
  guint n_mem = gst_buffer_n_memory(buffer);
  // Iterate through all memory blocks
  for (guint i = 0; i < n_mem; i++) {
    if (GstMemory *mem = gst_buffer_peek_memory(buffer, i)) {
      gst_opencl_mem_reset(mem);
    }
  }
  // Call parent class reset_buffer to handle standard cleanup
  GST_BUFFER_POOL_CLASS(parent_class)->reset_buffer(pool, buffer);
}

///
/// @brief Free a buffer from the pool
///
/// @param pool The buffer pool
/// @param buffer The buffer being freed
///
static void
gst_ax_buffer_pool_free_buffer(GstBufferPool *pool, GstBuffer *buffer)
{
  GST_DEBUG_OBJECT(pool, "Freeing buffer %p", buffer);

  // Ensure all OpenCL resources are cleaned up before freeing
  guint n_mem = gst_buffer_n_memory(buffer);
  for (guint i = 0; i < n_mem; i++) {
    if (GstMemory *mem = gst_buffer_peek_memory(buffer, i)) {
      gst_opencl_mem_reset(mem);
    }
  }
  // Call parent to actually free the buffer
  GST_BUFFER_POOL_CLASS(parent_class)->free_buffer(pool, buffer);
}

///
/// @brief Initialize the GstAxBufferPool class
///
static void
gst_ax_buffer_pool_class_init(GstAxBufferPoolClass *klass)
{
  GstBufferPoolClass *pool_class = GST_BUFFER_POOL_CLASS(klass);

  pool_class->reset_buffer = GST_DEBUG_FUNCPTR(gst_ax_buffer_pool_reset_buffer);
  pool_class->free_buffer = GST_DEBUG_FUNCPTR(gst_ax_buffer_pool_free_buffer);

  GST_DEBUG_CATEGORY_INIT(gst_ax_buffer_pool_debug, "axbufferpool", 0, "Axelera AI Buffer Pool");
}

///
/// @brief Initialize a GstAxBufferPool instance
///
static void
gst_ax_buffer_pool_init(GstAxBufferPool *pool)
{
  GST_DEBUG_OBJECT(pool, "Initializing Ax buffer pool");
}

///
/// @brief Create a new GstAxBufferPool instance
///
/// @return A new GstAxBufferPool, or NULL on failure
GstBufferPool *
gst_ax_buffer_pool_new()
{
  GstBufferPool *pool = (GstBufferPool *) g_object_new(GST_TYPE_AX_BUFFER_POOL, NULL);

  if (!pool) {
    GST_ERROR("Failed to create Ax buffer pool");
  }
  return pool;
}
