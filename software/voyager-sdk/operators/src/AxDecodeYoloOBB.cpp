// Copyright Axelera AI, 2025
// Optimized anchor-free OBB decoder

#include "AxDataInterface.h"
#include "AxLog.hpp"
#include "AxMetaObjectDetection.hpp"
#include "AxOpUtils.hpp"
#include "AxUtils.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <fstream>
#include <numeric>
#include <unordered_set>
#include <vector>

namespace yolo_obb_decode
{
using lookups = std::array<float, 256>;
using inferences = ax_utils::inferences;

constexpr auto weights_size = 16;
struct properties {
  std::vector<lookups> sigmoid_tables{};
  std::vector<lookups> softmax_tables{};
  std::vector<lookups> dequantize_tables{};
  std::vector<ax_utils::sin_cos_lookups> sin_cos_tables{};
  std::vector<std::vector<int>> padding{};
  std::vector<float> zero_points{};
  std::vector<float> scales{};
  std::vector<std::string> class_labels{};
  std::vector<int> filter{};
  std::array<float, weights_size> weights;

  float confidence{ 0.25F };
  int num_classes{ 0 };
  int topk{ 2000 };
  bool multiclass{ true };
  std::string meta_name{};
  std::string master_meta{};
  std::string association_meta{};
  std::string decoder_name{};
  bool scale_up{ true };
  bool letterbox{ true };
  int model_width{};
  int model_height{};
};

struct tensor_pair {
  int conf_idx;
  int box_idx;
  int theta_idx;
};

/// @brief Dequantize a single int8 value using the provided lookup table
/// @param value - The int8 value to dequantize
/// @param the_table - The lookup table to use for dequantization
/// @return - The dequantized float value
float
dequantize(int value, const float *the_table)
{
  int index = value + 128;
  return the_table[index];
}

/// @brief Sort the tensors into the order that they are expected to be in and
///        pairs the box prediction with the correspong confidence predictions.
///        We determine which is which from the channel size.
/// @param tensors - The tensors to sort
/// @param num_classes - The number of classes
/// @param logger - The logger to use for logging
/// @return - The sorted tensors
std::vector<tensor_pair>
sort_tensors(const AxTensorsInterface &tensors, int num_classes, Ax::Logger &logger)
{
  if (tensors.size() % 3 != 0) {
    logger(AX_ERROR) << "The number of tensors must be multiple of 3" << std::endl;
    throw std::runtime_error(
        "The number of tensors must be even" + std::to_string(tensors.size()));
  }
  std::vector<int> indices(tensors.size());
  std::iota(std::begin(indices), std::end(indices), 0);
  std::sort(std::begin(indices), std::end(indices), [&tensors](auto a, auto b) {
    const int width_or_height_idx = 2;
    const int channels_idx = 3;
    return std::tie(tensors[a].sizes[width_or_height_idx], tensors[a].sizes[channels_idx])
           > std::tie(tensors[b].sizes[width_or_height_idx], tensors[b].sizes[channels_idx]);
  });

  std::vector<tensor_pair> tensor_pairs;
  for (auto i = size_t{}; i != indices.size(); i += 3) {
    tensor_pairs.push_back(tensor_pair{ indices[i + 1], indices[i], indices[i + 2] });
  }

  return tensor_pairs;
}
struct fpoint {
  float x;
  float y;
};

/// @brief Decode the scores and add to the outputs of a grid cell
/// @param box_data - The box data for this cell
/// @param score_data - The score data for this cell
/// @param theta_data - The theta orientation angle data for this cell
/// @param props - The properties of the model
/// @param score_level - The index of the score tensor
/// @param box_level - The index of the box tensor
/// @param theta_level - The index of the theta tensor
/// @param recip_width - The reciprocal of the width of the tensor
/// @param xpos - The x position of this cell
/// @param ypos - The y position of this cell
/// @param outputs - The output inferences
int
decode_cell(const int8_t *box_data, const int8_t *score_data,
    const int8_t *theta_data, const properties &props, int score_level, int box_level,
    int theta_level, float recip_width, int xpos, int ypos, inferences &outputs)
{
  const auto &lookups = props.sigmoid_tables[score_level].data();
  const auto confidence = props.confidence;
  const auto num_predictions = ax_utils::decode_scores(score_data, lookups, 1,
      props.filter, props.confidence, props.multiclass, outputs);
  if (num_predictions != 0) {
    const auto &softmax_lookups = props.softmax_tables[box_level].data();
    const auto &theta_lookups = props.sigmoid_tables[theta_level].data();
    const auto &sin_cos_lookups = props.sin_cos_tables[theta_level].data();
    const float angle
        = (yolo_obb_decode::dequantize(*theta_data, theta_lookups) - 0.25) * M_PI;

    constexpr auto box_size = 4;
    std::array<float, box_size> box;
    std::array<float, weights_size> softmaxed;
    auto *box_ptr = box_data;
    auto next_box = softmaxed.size();
    for (auto &b : box) {
      ax_utils::softmax(box_ptr, softmaxed.size(), 1, softmax_lookups, softmaxed.data());
      b = std::transform_reduce(
          props.weights.begin(), props.weights.end(), softmaxed.begin(), 0.0F);
      box_ptr = std::next(box_ptr, next_box);
    }
    const auto xf = (box[2] - box[0]) * 0.5F;
    const auto yf = (box[3] - box[1]) * 0.5F;

    float sin_a = yolo_obb_decode::dequantize(*theta_data, sin_cos_lookups);
    float cos_a = yolo_obb_decode::dequantize(*theta_data, sin_cos_lookups + 256);

    const float cx = xf * cos_a - yf * sin_a;
    const float cy = xf * sin_a + yf * cos_a;
    const float w = (box[0] + box[2]);
    const float h = (box[1] + box[3]);
    outputs.obb.insert(outputs.obb.end(), num_predictions,
        {
            std::clamp((cx + xpos + 0.5F) * recip_width, 0.0f, 1.0f),
            std::clamp((cy + ypos + 0.5F) * recip_width, 0.0f, 1.0f),
            std::clamp(w * recip_width, 0.0f, 1.0f),
            std::clamp(h * recip_width, 0.0f, 1.0f),
            angle,
        });
  }
  return num_predictions;
}


/// @brief Decode a single feature map tensor
/// @param tensors - The tensor data
/// @param score_idx - The index of the score tensor
/// @param box_idx - The index of the box tensor
/// @param props - The properties of the model
/// @param level - which of features maps this tensor is
/// @param outputs - output inferences
/// @param logger - The logger to use for logging
/// @return - The number of predictions added
int
decode_tensor(const AxTensorsInterface &tensors, int score_idx, int box_idx, int theta_idx,
    const properties &props, int level, inferences &outputs, Ax::Logger &logger)
{
  auto [box_width, box_height, box_depth] = ax_utils::get_dims(tensors, box_idx, true);
  auto [score_width, score_height, score_depth]
      = ax_utils::get_dims(tensors, score_idx, true);
  auto [theta_width, theta_height, theta_depth]
      = ax_utils::get_dims(tensors, theta_idx, true);

  if (box_width != score_width || box_height != score_height) {
    logger(AX_ERROR) << "decode_tensor : box and score tensors must be the same size"
                     << std::endl;
    return 0;
  }
  const auto box_x_stride = box_depth;
  const auto box_y_stride = box_x_stride * box_width;

  const auto score_x_stride = score_depth;
  const auto score_y_stride = score_x_stride * score_width;

  const auto theta_x_stride = theta_depth;
  const auto theta_y_stride = theta_x_stride * theta_width;

  const auto box_tensor = tensors[box_idx];
  const auto score_tensor = tensors[score_idx];
  const auto theta_tensor = tensors[theta_idx];
  const auto *box_data = static_cast<const int8_t *>(box_tensor.data);
  const auto *score_data = static_cast<const int8_t *>(score_tensor.data);
  const auto *theta_data = static_cast<const int8_t *>(theta_tensor.data);

  auto total = 0;
  const auto recip_width = 1.0F / std::max(box_width, box_height);

  for (auto y = 0; y != box_height; ++y) {
    auto *box_ptr = std::next(box_data, box_y_stride * y);
    auto *score_ptr = std::next(score_data, score_y_stride * y);
    auto *theta_ptr = std::next(theta_data, theta_y_stride * y);

    for (auto x = 0; x != box_width; ++x) {
      total += decode_cell(box_ptr, score_ptr, theta_ptr, props, score_idx,
          box_idx, theta_idx, recip_width, x, y, outputs);
      box_ptr = std::next(box_ptr, box_x_stride);
      score_ptr = std::next(score_ptr, score_x_stride);
      theta_ptr = std::next(theta_ptr, theta_x_stride);
    }
  }
  return total;
}
/// @brief Remove padding from the tensors
/// @param tensors - The input tensors
/// @param padding - The padding for each tensor
/// @return - The depadded tensors
AxTensorsInterface
depad_tensors(const AxTensorsInterface &tensors, const std::vector<std::vector<int>> &padding)
{
  auto depadded = tensors;
  for (auto i = 0; i != padding.size(); ++i) {
    depadded[i].sizes[3] = tensors[i].sizes[3] - padding[i][7] - padding[i][6];
  }
  return depadded;
}

/// @brief Decode the tensors into a set of inferences
/// @param tensors - The input tensors
/// @param prop - The properties of the model
/// @param padding - The padding to remove from the tensors
/// @return - The decoded inferences
inferences
decode_tensors(const AxTensorsInterface &tensors, const properties &prop,
    const std::vector<std::vector<int>> &padding, Ax::Logger &logger)
{
  auto depadded = depad_tensors(tensors, padding);
  auto tensor_order = sort_tensors(depadded, prop.num_classes, logger);

  inferences predictions(1000);
  for (int level = 0; level != tensor_order.size(); ++level) {
    const auto [conf_tensor, loc_tensor, theta_tensor] = tensor_order[level];
    auto num = decode_tensor(tensors, conf_tensor, loc_tensor, theta_tensor,
        prop, level, predictions, logger);
  }
  return predictions;
}

} // namespace yolo_obb_decode

extern "C" void
decode_to_meta(const AxTensorsInterface &in_tensors, const yolo_obb_decode::properties *prop,
    unsigned int subframe_index, unsigned int number_of_subframes,
    std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> &map,
    const AxDataInterface &video_interface, Ax::Logger &logger)
{
  auto start_time = std::chrono::high_resolution_clock::now();
  if (!prop) {
    logger(AX_ERROR) << "decode_to_meta : properties not set" << std::endl;
    throw std::runtime_error("decode_to_meta : properties not set");
  }
  auto tensors = in_tensors;
  auto padding = prop->padding;

  if (tensors.size() == 1) {
    throw std::runtime_error(
        "decode_to_meta : Badly constructed pipeline, possible reason is setting handle_postamble or handle_all to true, please refer to docs/tutorials/application.md");
  }

  if (tensors.size() != padding.size()) {
    throw std::runtime_error(
        "decode_to_meta : number of tensors: " + std::to_string(tensors.size())
        + " and padding size " + std::to_string(padding.size()) + " do not match");
  }

  if (tensors.size() != prop->sigmoid_tables.size() && tensors[0].bytes == 1) {
    throw std::runtime_error(
        "ssd_decode_to_meta : Number of input tensors or dequantize parameters is incorrect");
  }
  auto predictions = yolo_obb_decode::decode_tensors(tensors, *prop, padding, logger);
  predictions = ax_utils::topk(predictions, prop->topk);

  std::vector<BboxXywhr> pixel_boxes;
  AxMetaBbox *master_meta = nullptr;
  if (prop->master_meta.empty()) {

    pixel_boxes = ax_utils::scale_boxes(predictions.obb,
        std::get<AxVideoInterface>(video_interface), prop->model_width,
        prop->model_height, prop->scale_up, prop->letterbox);
  } else {
    const auto &box_key = prop->association_meta.empty() ? prop->master_meta :
                                                           prop->association_meta;
    master_meta = ax_utils::get_meta<AxMetaBbox>(box_key, map, "yolo_obb_decode");
    auto master_box = master_meta->get_box_xyxy(subframe_index);

    pixel_boxes = ax_utils::scale_shift_boxes(predictions.obb, master_box,
        prop->model_width, prop->model_height, prop->scale_up, prop->letterbox);
  }

  std::vector<int> ids;
  ax_utils::insert_and_associate_meta<AxMetaObjDetectionOBB>(map,
      prop->meta_name, prop->master_meta, subframe_index, number_of_subframes,
      prop->association_meta, std::move(pixel_boxes),
      std::move(predictions.scores), std::move(predictions.class_ids), ids);

  auto end_time = std::chrono::high_resolution_clock::now();
  auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time);
  logger(AX_DEBUG) << "decode_to_meta : Decoding took " << duration.count()
                   << " microseconds" << std::endl;
}

extern "C" const std::unordered_set<std::string> &
allowed_properties()
{
  static const std::unordered_set<std::string> allowed_properties{
    "meta_key",
    "master_meta",
    "association_meta",
    "classlabels_file",
    "confidence_threshold",
    "max_boxes",
    "label_filter",
    "topk",
    "zero_points",
    "scales",
    "multiclass",
    "classes",
    "padding",
    "decoder_name",
    "scale_up",
    "letterbox",
    "model_width",
    "model_height",
  };
  return allowed_properties;
}

extern "C" std::shared_ptr<void>
init_and_set_static_properties(
    const std::unordered_map<std::string, std::string> &input, Ax::Logger &logger)
{
  auto props = std::make_shared<yolo_obb_decode::properties>();
  props->meta_name = Ax::get_property(
      input, "meta_key", "detection_static_properties", props->meta_name);
  props->master_meta = Ax::get_property(
      input, "master_meta", "detection_static_properties", props->master_meta);
  props->association_meta = Ax::get_property(input, "association_meta",
      "detection_static_properties", props->association_meta);
  props->zero_points = Ax::get_property(
      input, "zero_points", "detection_static_properties", props->zero_points);
  props->scales = Ax::get_property<float>(
      input, "scales", "detection_static_properties", props->scales);
  props->num_classes = Ax::get_property(
      input, "classes", "detection_static_properties", props->num_classes);
  props->decoder_name = Ax::get_property(
      input, "decoder_name", "detection_static_properties", props->decoder_name);
  auto topk
      = Ax::get_property(input, "topk", "detection_static_properties", props->topk);
  if (topk > 0) {
    props->topk = topk;
  }
  props->scale_up = Ax::get_property(
      input, "scale_up", "detection_static_properties", props->scale_up);

  props->model_width = Ax::get_property(
      input, "model_width", "detection_static_properties", props->model_width);
  props->model_height = Ax::get_property(
      input, "model_height", "detection_static_properties", props->model_height);
  if (props->model_height == 0 || props->model_width == 0) {
    logger(AX_ERROR) << "detection_static_properties : model_width and model_height must be "
                        "provided"
                     << std::endl;
    throw std::runtime_error(
        "detection_static_properties : model_width and model_height must be provided");
  }

  auto filename = Ax::get_property(
      input, "classlabels_file", "yolo_decode_static_properties", std::string{});
  if (!filename.empty()) {
    props->class_labels = ax_utils::read_class_labels(
        filename, "yolo_decode_static_properties", logger);
  }
  if (props->num_classes == 0) {
    props->num_classes = props->class_labels.size();
  }

  props->multiclass = Ax::get_property(
      input, "multiclass", "detection_static_properties", props->multiclass);

  //  Build the lookup tables
  if (props->zero_points.size() != props->scales.size()) {
    logger(AX_ERROR) << "detection_static_properties : zero_points and scales must have the same "
                        "number of elements."
                     << std::endl;
    throw std::runtime_error(
        "detection_static_properties : zero_points and scales must be the same size");
  }

  if (props->num_classes == 0) {
    if (!props->class_labels.empty()) {
      props->num_classes = props->class_labels.size();
    }
  }
  if (props->num_classes != 0) {
    ax_utils::validate_classes(props->class_labels, props->num_classes,
        "yolo_decode_static_properties", logger);
  }

  props->sigmoid_tables
      = ax_utils::build_sigmoid_tables(props->zero_points, props->scales);
  props->softmax_tables
      = ax_utils::build_exponential_tables(props->zero_points, props->scales);
  props->dequantize_tables
      = ax_utils::build_dequantization_tables(props->zero_points, props->scales);
  props->sin_cos_tables = ax_utils::build_trigonometric_tables(
      props->zero_points, props->scales, -0.25F, M_PI);
  props->filter = Ax::get_property(
      input, "label_filter", "detection_static_properties", props->filter);
  if (props->filter.empty()) {
    auto size = props->num_classes;
    props->filter.resize(size);
    std::iota(props->filter.begin(), props->filter.end(), 0);
  }
  props->letterbox = Ax::get_property(
      input, "letterbox", "detection_static_properties", props->letterbox);
  props->padding = Ax::get_property(
      input, "padding", "detection_static_properties", props->padding);
  std::sort(props->filter.begin(), props->filter.end());
  props->filter.erase(std::unique(props->filter.begin(), props->filter.end()),
      props->filter.end());
  std::iota(props->weights.begin(), props->weights.end(), 0);

  return props;
}

extern "C" void
set_dynamic_properties(const std::unordered_map<std::string, std::string> &input,
    yolo_obb_decode::properties *prop, Ax::Logger &logger)
{
  prop->confidence = Ax::get_property(input, "confidence_threshold",
      "detection_dynamic_properties", prop->confidence);
  logger(AX_DEBUG) << "prop->confidence_threshold is " << prop->confidence << std::endl;
}
