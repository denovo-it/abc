// Copyright Axelera AI, 2025
// Optimized anchor-free YOLO(v8) decoder

#include "AxDataInterface.h"
#include "AxLog.hpp"
#include "AxMetaKptsDetection.hpp"
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

namespace yolov8_decode
{
using lookups = std::array<float, 256>;
using inferences = ax_utils::inferences;

constexpr auto weights_size = 16;
struct properties {
  std::vector<lookups> sigmoid_tables{};
  std::vector<lookups> softmax_tables{};
  std::vector<lookups> dequantize_tables{};
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
  std::vector<int> kpts_shape{ 0, 0 };
  std::string meta_name{};
  std::string master_meta{};
  std::string association_meta{};
  std::string decoder_name{};
  bool scale_up{ true };
  bool letterbox{ true };
  int model_width{};
  int model_height{};
};


/// @brief Sort the tensors into the order that they are expected to be in and
///        pairs the box prediction with the correspong confidence predictions.
///        We determine which is which from the channel size.
/// @param tensors - The tensors to sort
/// @param num_classes - The number of classes
/// @param kpts_per_box - The number of kpts per box
/// @param logger - The logger to use for logging
/// @return The sorted tensors

struct tensor_pair {
  int conf_idx;
  int box_idx;
  int kpt_idx;
};

float
dequantize(int8_t value, const float *the_table)
{
  int index = value + 128;
  return the_table[index];
}

std::vector<tensor_pair>
sort_tensors(const AxTensorsInterface &tensors, int num_classes,
    int kpts_per_box, Ax::Logger &logger)
{
  if (tensors.size() % 2 != 0 && kpts_per_box == 0) {
    logger.throw_error("libdecode_yolov8: The number of tensors must be even, but got "
                       + Ax::to_string(tensors) + " when num_kpts=0");
  }
  if (tensors.size() % 3 != 0 && kpts_per_box > 0) {
    logger.throw_error("libdecode_yolov8: The number of tensors must be multiple of 3, but got "
                       + Ax::to_string(tensors) + " when num_kpts>0 ("
                       + std::to_string(kpts_per_box) + ")");
  }
  std::vector<int> indices(tensors.size());
  std::iota(std::begin(indices), std::end(indices), 0);
  std::sort(std::begin(indices), std::end(indices), [&tensors](auto a, auto b) {
    const int width_or_height_idx = 2;
    const int channels_idx = 3;
    return std::tie(tensors[a].sizes[width_or_height_idx], tensors[a].sizes[channels_idx])
           > std::tie(tensors[b].sizes[width_or_height_idx], tensors[b].sizes[channels_idx]);
  });

  auto swap = num_classes < 64;
  std::vector<tensor_pair> tensor_pairs;
  for (auto i = size_t{}; i != indices.size(); i += kpts_per_box == 0 ? 2 : 3) {
    if (kpts_per_box == 0) {
      tensor_pairs.push_back(swap ? tensor_pair{ indices[i + 1], indices[i], -1 } :
                                    tensor_pair{ indices[i], indices[i + 1], -1 });
    } else {
      tensor_pairs.push_back(tensor_pair{ indices[i + 2], indices[i], indices[i + 1] });
    }
  }

  return tensor_pairs;
}

/// @brief Decode a single cell of the tensor
/// @param box_data - pointer to the raw tensor box data
/// @param score_data - pointer to the raw tensor score
/// @param props - properties of the model
/// @param score_level - index of score tensor
/// @param box_level - index of box tensor
/// @param recip_width - scale facror
/// @param xpos - x position of the cell
/// @param ypos - y position of the cell
/// @param outputs - output inferences
/// @return - The number of predictions added
int
decode_cell(const int8_t *box_data, const int8_t *score_data, const int8_t *kpts_data,
    const properties &props, int score_level, int box_level, int kpt_level,
    float recip_width, int xpos, int ypos, bool focal_loss, inferences &outputs)
{
  const auto dummy = float{};
  const auto &lookups = props.sigmoid_tables.empty() ?
                            &dummy :
                            props.sigmoid_tables[score_level].data();

  const auto &box_lookups = props.dequantize_tables.empty() ?
                                &dummy :
                                props.dequantize_tables[box_level].data();
  const auto confidence = props.confidence;
  const auto num_predictions = ax_utils::decode_scores(score_data, lookups, 1,
      props.filter, props.confidence, props.multiclass, outputs);
  if (num_predictions != 0) {
    const auto &softmax_lookups = props.softmax_tables[box_level].data();
    //  Here we need to decode the box
    constexpr auto box_size = 4;
    std::array<float, box_size> box;
    std::array<float, weights_size> softmaxed;
    auto *box_ptr = box_data;
    auto next_box = softmaxed.size();
    for (auto &b : box) {
      if (!focal_loss) {
        b = yolov8_decode::dequantize(*box_ptr++, box_lookups);
      } else {
        ax_utils::softmax(
            box_ptr, softmaxed.size(), 1, softmax_lookups, softmaxed.data());
        b = std::transform_reduce(
            props.weights.begin(), props.weights.end(), softmaxed.begin(), 0.0F);
        box_ptr = std::next(box_ptr, next_box);
      }
    }

    const auto x1 = (xpos + 0.5F - box[0]) * recip_width;
    const auto y1 = (ypos + 0.5F - box[1]) * recip_width;
    const auto x2 = (xpos + 0.5F + box[2]) * recip_width;
    const auto y2 = (ypos + 0.5F + box[3]) * recip_width;

    outputs.boxes.insert(outputs.boxes.end(), num_predictions,
        {
            std::clamp(x1, 0.0F, 1.0F),
            std::clamp(y1, 0.0F, 1.0F),
            std::clamp(x2, 0.0F, 1.0F),
            std::clamp(y2, 0.0F, 1.0F),
        });

    if (kpt_level != -1) {
      // constexpr auto kpt_size = 3;
      const auto &dequantize_lookups = props.dequantize_tables[kpt_level].data();
      const auto &sigmoid_lookups = props.sigmoid_tables[kpt_level].data();
      auto *kpts_ptr = kpts_data;

      for (auto i = 0; i < props.kpts_shape[0]; ++i) {
        const auto x = (xpos + 2.0F * yolov8_decode::dequantize(kpts_ptr[0], dequantize_lookups))
                       * recip_width;
        const auto y = (ypos + 2.0F * yolov8_decode::dequantize(kpts_ptr[1], dequantize_lookups))
                       * recip_width;
        const auto v = props.kpts_shape[1] == 3 ?
                           ax_utils::sigmoid(kpts_ptr[2], sigmoid_lookups) :
                           1.0F;

        outputs.kpts.insert(outputs.kpts.end(), {
                                                    std::clamp(x, 0.0F, 1.0F),
                                                    std::clamp(y, 0.0F, 1.0F),
                                                    v,
                                                });
        kpts_ptr = std::next(kpts_ptr, props.kpts_shape[1]);
      }
    }
  }

  return num_predictions;
}

///
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
decode_tensor(const AxTensorsInterface &tensors, int score_idx, int box_idx,
    int kpt_idx, const properties &props, int level, inferences &outputs,
    bool focal_loss, Ax::Logger &logger)
{
  auto [box_width, box_height, box_depth] = ax_utils::get_dims(tensors, box_idx, true);
  auto [score_width, score_height, score_depth]
      = ax_utils::get_dims(tensors, score_idx, true);
  auto [kpts_width, kpts_height, kpts_depth] = ax_utils::get_dims(tensors, kpt_idx, true);

  if (box_width != score_width || box_height != score_height) {
    logger(AX_ERROR) << "decode_tensor : box and score tensors must be the same size"
                     << std::endl;
    return 0;
  }
  const auto box_x_stride = box_depth;
  const auto box_y_stride = box_x_stride * box_width;

  const auto score_x_stride = score_depth;
  const auto score_y_stride = score_x_stride * score_width;

  const auto kpts_x_stride = kpts_depth;
  const auto kpts_y_stride = kpts_x_stride * kpts_width;

  const auto box_tensor = tensors[box_idx];
  const auto score_tensor = tensors[score_idx];
  const auto kpts_tensor = kpt_idx == -1 ? nullptr : tensors[kpt_idx].data;
  const auto *box_data = static_cast<const int8_t *>(box_tensor.data);
  const auto *score_data = static_cast<const int8_t *>(score_tensor.data);
  const auto *kpts_data = static_cast<const int8_t *>(kpts_tensor);

  auto total = 0;
  const auto recip_width = 1.0F / std::max(box_width, box_height);

  for (auto y = 0; y != box_height; ++y) {
    auto *box_ptr = std::next(box_data, box_y_stride * y);
    auto *score_ptr = std::next(score_data, score_y_stride * y);
    auto *kpts_ptr = kpts_data != nullptr ? std::next(kpts_data, kpts_y_stride * y) : nullptr;

    for (auto x = 0; x != box_width; ++x) {
      total += decode_cell(box_ptr, score_ptr, kpts_ptr, props, score_idx,
          box_idx, kpt_idx, recip_width, x, y, focal_loss, outputs);
      box_ptr = std::next(box_ptr, box_x_stride);
      score_ptr = std::next(score_ptr, score_x_stride);
      kpts_ptr = kpts_data != nullptr ? std::next(kpts_ptr, kpts_x_stride) : nullptr;
    }
  }
  return total;
}

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
/// @param padding - The padding for each tensor
/// @param logger - The logger to use for logging
/// @return The resulting inferences

inferences
decode_tensors(const AxTensorsInterface &tensors, const properties &prop,
    const std::vector<std::vector<int>> &padding, Ax::Logger &logger)
{
  auto depadded = depad_tensors(tensors, padding);
  auto tensor_order = sort_tensors(depadded, prop.num_classes, prop.kpts_shape[0], logger);

  inferences predictions(1000, 1000 * prop.kpts_shape[0]);
  predictions.kpts_shape = prop.kpts_shape;

  for (int level = 0; level != tensor_order.size(); ++level) {
    const auto [conf_tensor, loc_tensor, kpt_tensor] = tensor_order[level];

    auto [box_width, box_height, box_depth]
        = ax_utils::get_dims(depad_tensors(tensors, padding), loc_tensor, true);
    bool focal_loss;
    if (box_depth == weights_size * 4) {
      focal_loss = true;
    } else if (box_depth == 4) {
      focal_loss = false;
    } else {
      logger.throw_error(
          "decode_tensors :  invalid tensor shape, expect ["
          + std::to_string(box_width) + ", " + std::to_string(box_height) + ", 4] or ["
          + std::to_string(box_width) + ", " + std::to_string(box_height) + ", "
          + std::to_string(weights_size * 4) + "] but got: [" + std::to_string(box_width)
          + ", " + std::to_string(box_height) + ", " + std::to_string(box_depth) + "] ");
    }
    auto num = decode_tensor(tensors, conf_tensor, loc_tensor, kpt_tensor, prop,
        level, predictions, focal_loss, logger);
  }
  return predictions;
}

} // namespace yolov8_decode

extern "C" void
decode_to_meta(const AxTensorsInterface &in_tensors, const yolov8_decode::properties *prop,
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
  if (tensors.size() != prop->sigmoid_tables.size() && tensors[0].bytes == 1) {
    throw std::runtime_error(
        "ssd_decode_to_meta : Number of input tensors or dequantize parameters is incorrect");
  }

  if (tensors.size() == 1) {
    throw std::runtime_error(
        "depadd_tensors : padding cannot be applied when there is only one tensor, consider removing handle_all: True from pipeline");
  }

  if (tensors.size() != padding.size()) {
    throw std::runtime_error(
        "depadd_tensors : number of tensors: " + std::to_string(tensors.size())
        + " and padding size " + std::to_string(padding.size()) + " do not match");
  }

  auto predictions = yolov8_decode::decode_tensors(tensors, *prop, padding, logger);
  predictions = ax_utils::topk(predictions, prop->topk);

  std::vector<BboxXyxy> pixel_boxes;
  AxMetaBbox *master_meta = nullptr;
  if (prop->master_meta.empty()) {
    pixel_boxes = ax_utils::scale_boxes(predictions.boxes,
        std::get<AxVideoInterface>(video_interface), prop->model_width,
        prop->model_height, prop->scale_up, prop->letterbox);
  } else {
    const auto &box_key = prop->association_meta.empty() ? prop->master_meta :
                                                           prop->association_meta;
    master_meta = ax_utils::get_meta<AxMetaBbox>(box_key, map, "yolov8_decode");
    auto master_box = master_meta->get_box_xyxy(subframe_index);
    pixel_boxes = ax_utils::scale_shift_boxes(predictions.boxes, master_box,
        prop->model_width, prop->model_height, prop->scale_up, prop->letterbox);
  }

  std::vector<KptXyv> pixel_kpts;
  std::vector<int> ids;
  if (prop->kpts_shape[0] > 0) {
    if (prop->master_meta.empty()) {
      auto &vinfo = std::get<AxVideoInterface>(video_interface);
      pixel_kpts = ax_utils::scale_kpts(predictions.kpts, vinfo.info.width,
          vinfo.info.height, prop->model_width, prop->model_height,
          prop->scale_up, prop->letterbox);
    } else {
      auto master_box = master_meta->get_box_xyxy(subframe_index);
      pixel_kpts = ax_utils::scale_shift_kpts(predictions.kpts, master_box,
          prop->model_width, prop->model_height, prop->scale_up, prop->letterbox);
    }
    ax_utils::insert_and_associate_meta<AxMetaKptsDetection>(map,
        prop->meta_name, prop->master_meta, subframe_index, number_of_subframes,
        prop->association_meta, std::move(pixel_boxes), std::move(pixel_kpts),
        std::move(predictions.scores), ids, prop->kpts_shape, prop->decoder_name);
  } else {
    ax_utils::insert_and_associate_meta<AxMetaObjDetection>(map,
        prop->meta_name, prop->master_meta, subframe_index, number_of_subframes,
        prop->association_meta, std::move(pixel_boxes),
        std::move(predictions.scores), std::move(predictions.class_ids), ids);
  }

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
    "kpts_shape",
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
  auto props = std::make_shared<yolov8_decode::properties>();
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
  props->kpts_shape = Ax::get_property(
      input, "kpts_shape", "detection_static_properties", props->kpts_shape);
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
    yolov8_decode::properties *prop, Ax::Logger &logger)
{
  prop->confidence = Ax::get_property(input, "confidence_threshold",
      "detection_dynamic_properties", prop->confidence);
  logger(AX_DEBUG) << "prop->confidence_threshold is " << prop->confidence << std::endl;
}
