// Copyright Axelera AI, 2023
#include <fstream>
#include <numeric>
#include <unordered_set>

#include "AxDataInterface.h"
#include "AxLog.hpp"
#include "AxMetaClassification.hpp"
#include "AxOpUtils.hpp"
#include "AxUtils.hpp"

extern "C" const std::unordered_set<std::string> &
allowed_properties()
{
  static const std::unordered_set<std::string> allowed_properties{
    "meta_key",
    "master_meta",
    "association_meta",
    "classlabels_file",
    "top_k",
    "sorted",
    "largest",
    "softmax",
  };
  return allowed_properties;
}

struct classification_properties {
  std::string meta_key
      = "meta_" + std::to_string(reinterpret_cast<long long unsigned int>(this));
  std::string master_meta{};
  std::string association_meta{};
  std::vector<std::string> classlabels;
  int top_k;
  int sorted;
  int largest;
  int softmax;
};

extern "C" std::shared_ptr<void>
init_and_set_static_properties(
    const std::unordered_map<std::string, std::string> &input, Ax::Logger &logger)
{
  std::shared_ptr<classification_properties> prop
      = std::make_shared<classification_properties>();

  auto classlabels = Ax::get_property(input, "classlabels_file",
      "classification_static_properties", std::string{});
  if (!classlabels.empty()) {
    prop->classlabels = ax_utils::read_class_labels(
        classlabels, "classification_static_properties", logger);
  }

  prop->meta_key = Ax::get_property(
      input, "meta_key", "classification_static_properties", prop->meta_key);
  prop->master_meta = Ax::get_property(input, "master_meta",
      "classification_static_properties", prop->master_meta);
  prop->association_meta = Ax::get_property(input, "association_meta",
      "classification_static_properties", prop->association_meta);
  return prop;
}

extern "C" void
set_dynamic_properties(const std::unordered_map<std::string, std::string> &input,
    classification_properties *prop, Ax::Logger &logger)
{
  prop->top_k = Ax::get_property(input, "top_k", "classification_dynamic_properties", 1);
  //  Currently this property is ignored as the output is always sorted.
  //  Added purely for completeness
  prop->sorted
      = Ax::get_property(input, "sorted", "classification_dynamic_properties", false);
  prop->largest
      = Ax::get_property(input, "largest", "classification_dynamic_properties", true);
  prop->softmax
      = Ax::get_property(input, "softmax", "classification_dynamic_properties", true);
}

extern "C" void
decode_to_meta(const AxTensorsInterface &tensors, const classification_properties *prop,
    unsigned int current_frame, unsigned int total_frames,
    std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> &map,
    const AxDataInterface &, Ax::Logger &logger)
{
  if (total_frames <= current_frame) {
    throw std::runtime_error("classification_decode_to_meta: Current frame is out of bounds");
  }
  if (1 != tensors.size()) {
    throw std::runtime_error("classification_decode_to_meta: Number of tensors must be 1");
  }
  auto &tensor = tensors[0];
  size_t total = tensor.total();
  if (!prop->classlabels.empty() && prop->classlabels.size() != total) {
    logger(AX_WARN) << "classification_decode_to_meta: Number of classes from NN ("
                    << total << ") must match that of classes file ("
                    << prop->classlabels.size() << ")" << std::endl;
  }
  if (4 != tensor.bytes) {
    throw std::runtime_error("classification_decode_to_meta: NN must return float");
  }

  std::vector<int> indices(total);

  auto *mat_data = static_cast<const float *>(tensor.data);
  std::vector<float> mat_copy{};

  if (prop->softmax) {
    mat_copy.resize(total);
    float max_for_shift = *std::max_element(mat_data, mat_data + total);
    std::transform(mat_data, mat_data + total, mat_copy.begin(),
        [max_for_shift](float a) { return std::exp(a - max_for_shift); });
    float denominator = std::accumulate(mat_copy.begin(), mat_copy.end(), 0.0);
    std::transform(mat_copy.begin(), mat_copy.end(), mat_copy.begin(),
        [denominator](float a) { return a / denominator; });
    mat_data = mat_copy.data();
  }

  std::iota(indices.begin(), indices.end(), 0);

  auto top_k = std::min(std::size_t(prop->top_k), total);
  if (prop->largest) {
    std::partial_sort(indices.begin(), std::next(indices.begin(), top_k),
        indices.end(),
        [mat_data](int i, int j) { return mat_data[i] > mat_data[j]; });
  } else {
    std::partial_sort(indices.begin(), std::next(indices.begin(), top_k),
        indices.end(),
        [mat_data](int i, int j) { return mat_data[i] < mat_data[j]; });
  }

  std::vector<float> scores;
  std::vector<std::string> labels;
  scores.reserve(top_k);
  labels.reserve(top_k);
  indices.resize(top_k);

  for (auto idx : indices) {
    scores.push_back(mat_data[idx]);
    if (prop->classlabels.empty()) {
      labels.push_back("Class: " + std::to_string(idx));
    } else {
      labels.push_back(prop->classlabels[idx]);
    }
  }

  ax_utils::insert_and_associate_meta<AxMetaClassification>(map, prop->meta_key,
      prop->master_meta, current_frame, total_frames, prop->association_meta,
      AxMetaClassification::scores_vec{ scores },
      AxMetaClassification::classes_vec{ indices },
      AxMetaClassification::labels_vec{ labels });
}
