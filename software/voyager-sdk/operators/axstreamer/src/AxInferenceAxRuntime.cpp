// Copyright Axelera AI, 2025
#include "AxInference.hpp"
#include "AxStreamerUtils.hpp"

#include <algorithm>
#include <axruntime/axruntime.hpp>
#include <fstream>

using namespace std::string_literals;
using axr::to_ptr;

namespace
{

template <size_t N>
void
fill_char_array(char (&arr)[N], const std::string &str)
{
  std::fill(std::begin(arr), std::end(arr), 0);
  std::copy(str.begin(), str.begin() + std::min(N - 1, str.size()), arr);
}

axr::ptr<axrProperties>
create_properties(axrContext *context, bool input_dmabuf, bool output_dmabuf,
    bool double_buffer, int num_sub_devices)
{
  std::string s;
  s += "input_dmabuf=" + std::to_string(int(input_dmabuf)) + "\n";
  s += "output_dmabuf=" + std::to_string(int(output_dmabuf)) + "\n";
  s += "num_sub_devices=" + std::to_string(num_sub_devices) + "\n";
  s += "aipu_cores=" + std::to_string(num_sub_devices) + "\n";
  s += "double_buffer=" + std::to_string(int(double_buffer)) + "\n";
  return to_ptr(axr_create_properties(context, s.c_str()));
}

axr::ptr<axrProperties>
create_conn_properties(axrContext *context)
{
  std::string s;
  s += "device_firmware_check=0"; // AF checks this further up
  return to_ptr(axr_create_properties(context, s.c_str()));
}

static std::mutex second_slice_workaround_mutex;

class AxRuntimeInference : public Ax::BasicInference
{
  public:
  AxRuntimeInference(Ax::Logger &logger, axrContext *ctx, axrModel *model,
      const Ax::InferenceProperties &props)
      : logger(logger)
  {
    // level-zero/triton/kmd has issues if we try to load the model from
    // multiple threads. So lock here to load a model at a time. This is a
    // workaround for the issue, and it needs fixing lower down.
    // Proper fix tracked here https://axeleraai.atlassian.net/browse/SDK-6708
    std::lock_guard lock(second_slice_workaround_mutex);
    auto inputs = axr_num_model_inputs(model);
    auto input0 = axr_get_model_input(model, 0);
    input_args.resize(inputs);
    auto outputs = axr_num_model_outputs(model);
    output_args.resize(outputs);
    logger(AX_INFO) << "Loaded model " << props.model << " with " << inputs
                    << " inputs and " << outputs << " outputs" << std::endl;

    auto device = axrDeviceInfo{};
    fill_char_array(device.name, props.devices);
    const auto *pdevice = props.devices.empty() ? nullptr : &device;
    const auto num_sub_devices = input0.dims[0];
    const auto conn_props = create_conn_properties(ctx);
    connection = to_ptr(
        axr_device_connect(ctx, pdevice, num_sub_devices, conn_props.get()));
    if (!connection) {
      throw std::runtime_error(
          "axr_device_connect failed : "s + axr_last_error_string(AXR_OBJECT(ctx)));
    }
    const auto load_props = create_properties(ctx, props.dmabuf_inputs,
        props.dmabuf_outputs, props.double_buffer, num_sub_devices);
    instance
        = to_ptr(axr_load_model_instance(connection.get(), model, load_props.get()));
    if (!instance) {
      throw std::runtime_error("axr_load_model_instance failed : "s
                               + axr_last_error_string(AXR_OBJECT(ctx)));
    }
  }

  Ax::InferenceParams execute(Ax::InferenceParams p) override
  {
    if (p.input_ptrs.empty()) {
      assert(p.input_fds.size() == input_args.size());
      for (auto &&[i, shared_fd] : Ax::Internal::enumerate(p.input_fds)) {
        input_args[i].fd = shared_fd->fd;
        input_args[i].ptr = nullptr;
        input_args[i].offset = 0;
      }
    } else {
      assert(p.input_ptrs.size() == input_args.size());
      for (auto &&[i, ptr] : Ax::Internal::enumerate(p.input_ptrs)) {
        input_args[i].fd = 0;
        input_args[i].ptr = ptr.get();
        input_args[i].offset = 0;
      }
    }
    if (!p.output_ptrs.empty()) {
      assert(p.output_ptrs.size() == output_args.size());
      for (auto &&[i, ptr] : Ax::Internal::enumerate(p.output_ptrs)) {
        output_args[i].fd = 0;
        output_args[i].ptr = ptr.get();
        output_args[i].offset = 0;
      }
    } else if (!p.output_fds.empty()) {
      assert(p.output_fds.size() == output_args.size());
      for (auto &&[i, shared_fd] : Ax::Internal::enumerate(p.output_fds)) {
        output_args[i].fd = shared_fd->fd;
        output_args[i].ptr = nullptr;
        output_args[i].offset = 0;
      }
    }
    auto res = axr_run_model_instance(instance.get(), input_args.data(),
        input_args.size(), output_args.data(), output_args.size());
    if (res != AXR_SUCCESS) {
      throw std::runtime_error("axr_run_model failed with "s
                               + axr_last_error_string(AXR_OBJECT(instance.get())));
    }
    return p;
  }

  private:
  Ax::Logger &logger;
  axr::ptr<axrConnection> connection;
  axr::ptr<axrModelInstance> instance;
  std::vector<axrArgument> input_args;
  std::vector<axrArgument> output_args;
};
} // namespace

std::unique_ptr<Ax::BasicInference>
Ax::create_axruntime_inference(Ax::Logger &logger, axrContext *ctx,
    axrModel *model, const InferenceProperties &props)
{
  return std::make_unique<AxRuntimeInference>(logger, ctx, model, props);
}
