// Copyright Axelera AI, 2025
#pragma once

#include <atomic>
#include <gst/gst.h>
#include <memory>
#include <queue>
#include <unordered_set>
#include "GstAxStreamerUtils.hpp"

G_BEGIN_DECLS

#define GST_TYPE_AXINFERENCENET (gst_axinferencenet_get_type())
#define GST_AXINFERENCENET(obj) \
  (G_TYPE_CHECK_INSTANCE_CAST((obj), GST_TYPE_AXINFERENCENET, GstAxInferenceNet))
#define GST_AXINFERENCENET_CLASS(klass) \
  (G_TYPE_CHECK_CLASS_CAST((klass), GST_TYPE_AXINFERENCENET, GstAxInferenceNetClass))
#define GST_IS_AXINFERENCENET(obj) \
  (G_TYPE_CHECK_INSTANCE_TYPE((obj), GST_TYPE_AXINFERENCENET))
#define GST_IS_AXINFERENCENET_CLASS(klass) \
  (G_TYPE_CHECK_CLASS_TYPE((klass), GST_TYPE_AXINFERENCENET))

typedef struct _GstAxInferenceNet GstAxInferenceNet;
typedef struct _GstAxInferenceNetClass GstAxInferenceNetClass;

namespace Ax
{
class InferenceNet;
class InferenceNetProperties;
} // namespace Ax

struct delayed_event {
  GstPad *pad;
  Ax::GstHandle<GstEvent> event;
};

struct event_queue {
  std::mutex mutex;
  std::queue<delayed_event> queue;
};

class GstAxStreamSelect;

struct _GstAxInferenceNet {
  GstElement parent;
  GstTracerRecord *element_latency;
  std::unique_ptr<Ax::InferenceNet> net;
  std::unique_ptr<Ax::InferenceNetProperties> properties;
  std::unique_ptr<event_queue> event_queue;
  Ax::GstHandle<GstAllocator> allocator;
  Ax::GstHandle<GstBufferPool> pool;
  bool at_eos = false;
  gboolean loop = false;
  std::unique_ptr<std::unordered_set<GstPad *>> flushing_pads;
  std::unique_ptr<std::mutex> flushing_mutex;
  std::unique_ptr<GstAxStreamSelect> stream_select;
  std::unique_ptr<Ax::Logger> logger;
};

struct _GstAxInferenceNetClass {
  GstElementClass parent_class;
};

G_GNUC_INTERNAL GType gst_axinferencenet_get_type(void);

G_END_DECLS
