// Copyright Axelera AI, 2025
// Simple tensor decoder to place tensors directly into meta for Python side consumption

#include "AxDataInterface.h"
#include "AxLog.hpp"
#include "AxMetaRawTensor.hpp"
#include "AxOpUtils.hpp"
#include "AxUtils.hpp"

#include <algorithm>
#include <chrono>
#include <sstream>
#include <unordered_set>

// Properties structure for the decoder
struct properties {
  std::string meta_name = "TensorMeta"; // Name of the meta object created
  std::string master_meta{};
};

extern "C" {

std::shared_ptr<void>
init_and_set_static_properties(
    const std::unordered_map<std::string, std::string> &input, Ax::Logger &logger)
{
  auto props = std::make_shared<properties>();

  props->meta_name = Ax::get_property(input, "meta_key",
      "decode_to_raw_tensor_static_properties", props->meta_name);
  props->master_meta = Ax::get_property(input, "master_meta",
      "decode_to_raw_tensor_static_properties", props->master_meta);
  return props;
}

const std::unordered_set<std::string> &
allowed_properties()
{
  static const std::unordered_set<std::string> allowed_properties{ "meta_key", "master_meta" };
  return allowed_properties;
}

void
set_dynamic_properties(const std::unordered_map<std::string, std::string> &input,
    void *properties_ptr, Ax::Logger &logger)
{
  // No dynamic properties needed
  logger(AX_DEBUG) << "No dynamic properties to set for tensor decoder.";
}

void
decode_to_meta(const AxTensorsInterface &in_tensors, const properties *prop,
    unsigned int subframe_index, unsigned int subframe_number,
    std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> &map,
    const AxDataInterface &video_interface, Ax::Logger &logger)
{
  auto start_time = std::chrono::high_resolution_clock::now();

  logger(AX_DEBUG) << "Processing " << in_tensors.size() << " tensors to meta...";

  ax_utils::insert_meta<AxMetaRawTensor>(
      map, prop->meta_name, prop->master_meta, subframe_index, subframe_number);
  auto *meta = dynamic_cast<AxMetaRawTensor *>(map[prop->meta_name].get());
  if (!meta) {
    logger(AX_ERROR) << "Failed to create AxMetaRawTensor meta object";
    throw std::runtime_error("Failed to create AxMetaRawTensor meta object");
  }

  // Process each input tensor - simply add to meta without modification
  for (size_t i = 0; i < in_tensors.size(); ++i) {
    const auto &tensor = in_tensors[i];

    // Skip empty tensors
    if (tensor.total() == 0) {
      logger(AX_WARN) << "Skipping empty tensor at index " << i;
      continue;
    }

    // Convert sizes to int64_t for AxMetaRawTensor
    std::vector<int64_t> dims;
    for (int size : tensor.sizes) {
      dims.push_back(static_cast<int64_t>(size));
    }

    // Add tensor to meta (generic, supports any type)
    meta->add_tensor(tensor.data, tensor.total(), tensor.bytes, dims);

    // Log shape information
    std::stringstream shape_str;
    for (const auto &dim : dims) {
      shape_str << dim << "x";
    }
    if (!shape_str.str().empty()) {
      shape_str.seekp(-1, std::ios_base::end); // Remove trailing 'x'
    }
    logger(AX_DEBUG) << "Added tensor " << i << " with shape: " << shape_str.str();
  }

  auto end_time = std::chrono::high_resolution_clock::now();
  auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time);
  logger(AX_INFO) << "Tensor decoder completed in " << duration.count() << " microseconds";
}

} // extern "C"
