// Copyright Axelera AI, 2025
#pragma once

#include <gst/gst.h>

G_BEGIN_DECLS

#define GST_TYPE_AX_BUFFER_POOL (gst_ax_buffer_pool_get_type())
#define GST_AX_BUFFER_POOL(obj) \
  (G_TYPE_CHECK_INSTANCE_CAST((obj), GST_TYPE_AX_BUFFER_POOL, GstAxBufferPool))
#define GST_AX_BUFFER_POOL_CLASS(klass) \
  (G_TYPE_CHECK_CLASS_CAST((klass), GST_TYPE_AX_BUFFER_POOL, GstAxBufferPoolClass))
#define GST_IS_AX_BUFFER_POOL(obj) \
  (G_TYPE_CHECK_INSTANCE_TYPE((obj), GST_TYPE_AX_BUFFER_POOL))
#define GST_IS_AX_BUFFER_POOL_CLASS(klass) \
  (G_TYPE_CHECK_CLASS_TYPE((klass), GST_TYPE_AX_BUFFER_POOL))
#define GST_AX_BUFFER_POOL_GET_CLASS(obj) \
  (G_TYPE_INSTANCE_GET_CLASS((obj), GST_TYPE_AX_BUFFER_POOL, GstAxBufferPoolClass))

typedef struct _GstAxBufferPool GstAxBufferPool;
typedef struct _GstAxBufferPoolClass GstAxBufferPoolClass;

///
/// GstAxBufferPool:
///
/// A custom buffer pool for GstAxTransform that handles cleanup of
/// OpenCL buffer resources when buffers are returned to the pool.
///
/// This pool ensures that:
/// - OpenCL buffer dependencies on GstBuffers are released
/// - cl_mem objects are properly managed for reuse
/// - Buffers are reset to a clean state before being reused
///
struct _GstAxBufferPool {
  GstBufferPool parent;

  /*< private >*/
  gpointer _gst_reserved[GST_PADDING];
};

struct _GstAxBufferPoolClass {
  GstBufferPoolClass parent_class;

  /*< private >*/
  gpointer _gst_reserved[GST_PADDING];
};

GType gst_ax_buffer_pool_get_type(void);

///
/// gst_ax_buffer_pool_new:
///
/// Create a new #GstAxBufferPool instance.
///
/// Returns: (transfer full): a new #GstAxBufferPool instance
///
GstBufferPool *gst_ax_buffer_pool_new(void);

G_END_DECLS
