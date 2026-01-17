// Copyright Axelera AI, 2025
// Optimized embeddings decoder

#include "AxLog.hpp"
#include "AxMetaClassification.hpp"
#include "AxOpUtils.hpp"
#include "AxUtils.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <iterator>
#include <unordered_set>
#include <vector>

namespace embeddings
{

struct properties {
  std::string meta_name{};
  std::string master_meta{};
  std::string decoder_name{};
  std::string association_meta{};
};

} // namespace embeddings

extern "C" void
decode_to_meta(const AxTensorsInterface &in_tensors, const embeddings::properties *prop,
    unsigned int current_frame, unsigned int total_frames,
    std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> &map,
    const AxDataInterface &video_interface, Ax::Logger &logger)
{
  auto start_time = std::chrono::high_resolution_clock::now();
  if (!prop) {
    logger(AX_ERROR) << "decode_to_meta : properties not set" << std::endl;
    throw std::runtime_error("decode_to_meta : properties not set");
  }
  auto tensors = in_tensors;
  if (tensors.size() != 1) {
    throw std::runtime_error("embeddings : Number of input tensors must be 1");
  }
  auto *data = static_cast<float *>(tensors[0].data);
  const auto total_size = tensors[0].total();

  std::vector<float> current_embedding(data, data + total_size);

  ax_utils::insert_and_associate_meta<AxMetaEmbeddings>(map, prop->meta_name,
      prop->master_meta, current_frame, total_frames, prop->association_meta,
      std::vector<std::vector<float>>{ current_embedding }, prop->decoder_name);
  auto end_time = std::chrono::high_resolution_clock::now();
  auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time);
  logger(AX_INFO) << "decode_to_meta : Decoding embeddings: " << duration.count()
                  << " microseconds" << std::endl;
}

extern "C" const std::unordered_set<std::string> &
allowed_properties()
{
  static const std::unordered_set<std::string> allowed_properties{ "meta_key",
    "master_meta", "decoder_name", "association_meta" };
  return allowed_properties;
}

extern "C" std::shared_ptr<void>
init_and_set_static_properties(
    const std::unordered_map<std::string, std::string> &input, Ax::Logger &logger)
{
  auto props = std::make_shared<embeddings::properties>();
  props->meta_name = Ax::get_property(
      input, "meta_key", "recog_static_properties", props->meta_name);
  props->master_meta = Ax::get_property(
      input, "master_meta", "recog_static_properties", props->master_meta);
  props->decoder_name = Ax::get_property(
      input, "decoder_name", "recog_static_properties", props->decoder_name);
  props->association_meta = Ax::get_property(input, "association_meta",
      "recog_static_properties", props->association_meta);
  return props;
}

extern "C" void
set_dynamic_properties(const std::unordered_map<std::string, std::string> &input,
    embeddings::properties *prop, Ax::Logger &logger)
{
}
