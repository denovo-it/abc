// Copyright Axelera AI, 2025
#include "AxMetaTracker.hpp"
#include "AxUtils.hpp"

extern "C" const std::unordered_set<std::string> &
allowed_properties()
{
  static const std::unordered_set<std::string> allowed_properties{
    "num_subtask_runs",
  };
  return allowed_properties;
}

struct numsubtaskruns_properties {
  int num_subtask_runs = 0;
};

extern "C" std::shared_ptr<void>
init_and_set_static_properties(
    const std::unordered_map<std::string, std::string> &input, Ax::Logger &)
{
  std::shared_ptr<numsubtaskruns_properties> prop
      = std::make_shared<numsubtaskruns_properties>();
  prop->num_subtask_runs = Ax::get_property(input, "num_subtask_runs",
      "callback_numsubtaskruns", prop->num_subtask_runs);
  if (prop->num_subtask_runs < 0) {
    throw std::runtime_error("num_subtask_runs must be >= 0");
  }
  return prop;
}

extern "C" bool
filter(const numsubtaskruns_properties *input,
    const TrackingDescriptor &tracking_descriptor, Ax::Logger &)
{
  return !input->num_subtask_runs || tracking_descriptor.frame_id < input->num_subtask_runs;
}
