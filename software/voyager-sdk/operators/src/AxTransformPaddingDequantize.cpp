// Copyright Axelera AI, 2025
#include <optional>
#include <unordered_map>
#include <unordered_set>
#include "AxDataInterface.h"
#include "AxLog.hpp"
#include "AxMeta.hpp"
#include "AxOpUtils.hpp"

namespace
{
using lookups = std::array<float, 256>;
struct padding_dequant_properties {
  std::vector<std::vector<int>> paddings;
  std::vector<int> in_shape{};
  std::vector<int> out_shape{};
  std::vector<bool> transpose{};
  bool dequant_lut{ true };
  std::vector<float> dequant_scale{};
  std::vector<float> dequant_zeropoint{};
  std::vector<lookups> dequantize_tables{};
};

float
dequantize(int8_t value, const float *the_table)
{
  int index = value + 128;
  return the_table[index];
}

std::vector<int>
to_4d_shape(const std::vector<int> &shape)
{
  std::vector<int> result = shape;
  while (result.size() < 4) {
    result.insert(result.begin(), 1);
  }
  return result;
}

} // namespace

extern "C" const std::unordered_set<std::string> &
allowed_properties()
{
  static const std::unordered_set<std::string> allowed_properties{ "padding", "input_shape",
    "output_shape", "dequant_scale", "dequant_zeropoint", "transpose", "dequant_lut" };
  return allowed_properties;
}

extern "C" std::shared_ptr<void>
init_and_set_static_properties(
    const std::unordered_map<std::string, std::string> &input, Ax::Logger &logger)
{
  std::shared_ptr<padding_dequant_properties> prop
      = std::make_shared<padding_dequant_properties>();
  prop->paddings = Ax::get_property(input, "padding",
      "padding_dequant_properties", std::vector<std::vector<int>>{});
  // For backward compatibility - if no paddings were specified but there's a single padding vector, convert it
  if (prop->paddings.empty()) {
    std::vector<int> single_padding = Ax::get_property(
        input, "padding", "padding_dequant_properties", std::vector<int>{});
    if (!single_padding.empty()) {
      prop->paddings.push_back(single_padding);
    }
  }
  prop->in_shape = Ax::get_property(
      input, "input_shape", "padding_dequant_properties", prop->in_shape);
  prop->out_shape = Ax::get_property(
      input, "output_shape", "padding_dequant_properties", prop->out_shape);

  prop->dequant_scale = Ax::get_property(
      input, "dequant_scale", "transform_dequantize", std::vector<float>{});
  prop->dequant_zeropoint = Ax::get_property(
      input, "dequant_zeropoint", "transform_dequantize", std::vector<float>{});
  if (prop->dequant_scale.empty() && prop->dequant_zeropoint.empty()) {
    throw std::runtime_error(
        "Either dequant_scale, dequant_zeropoint or both must be specified in transform_dequantize");
  }
  if (!prop->dequant_scale.empty() && !prop->dequant_zeropoint.empty()
      && prop->dequant_scale.size() != prop->dequant_zeropoint.size()) {
    throw std::logic_error(
        "dequant_scale and dequant_zeropoint must be the same size in transform_dequantize");
  }
  if (prop->dequant_scale.empty()) {
    prop->dequant_scale = std::vector<float>(prop->dequant_zeropoint.size(), 1.0);
  }
  if (prop->dequant_zeropoint.empty()) {
    prop->dequant_zeropoint = std::vector<float>(prop->dequant_scale.size(), 0.0);
  }
  prop->dequantize_tables = ax_utils::build_dequantization_tables(
      prop->dequant_zeropoint, prop->dequant_scale);

  std::string transpose_str
      = Ax::get_property(input, "transpose", "transform_dequantize", std::string{});
  if (!transpose_str.empty()) {
    auto transpose_string_views = Ax::Internal::split(transpose_str, ',');
    prop->transpose.reserve(transpose_string_views.size());
    for (const auto &val_view : transpose_string_views) {
      prop->transpose.push_back(std::stoi(std::string(val_view)) != 0);
    }
  }

  prop->dequant_lut = Ax::get_property(
      input, "dequant_lut", "transform_postamble", prop->dequant_lut);
  return prop;
}


extern "C" AxDataInterface
set_output_interface(const AxDataInterface &interface,
    const padding_dequant_properties *prop, Ax::Logger &logger)
{
  if (!std::holds_alternative<AxTensorsInterface>(interface)) {
    throw std::runtime_error("transform_padding requires tensor input");
  }
  auto input = std::get<AxTensorsInterface>(interface);

  // Make sure we have at least one tensor
  if (input.empty() || input[0].bytes != 1) {
    throw std::runtime_error("transform_padding requires at least one int8 tensor input");
  }

  // Make sure we have paddings for each tensor or at least one default padding
  if (prop->paddings.empty()) {
    throw std::runtime_error("transform_padding: no padding configurations provided");
  }

  if (prop->paddings.size() < input.size()) {
    throw std::runtime_error("transform_padding: fewer padding configurations than tensors, expected "
                             + std::to_string(input.size()) + " but got "
                             + std::to_string(prop->paddings.size()));
  }

  // Validate each padding configuration
  for (size_t i = 0; i < std::min(prop->paddings.size(), input.size()); ++i) {
    const auto &padding = prop->paddings[i];
    if ((padding.size() % 2) != 0) {
      throw std::runtime_error("transform_padding: padding must be a multiple of 2:"
                               + ax_utils::sizes_to_string(padding));
    }
    if (padding.size() / 2 > input[i].sizes.size()) {
      throw std::runtime_error("transform_padding: padding "
                               + ax_utils::sizes_to_string(padding) + " too long for input tensor "
                               + ax_utils::sizes_to_string(input[i].sizes));
    }
  }

  if (!ax_utils::validate_shape(prop->in_shape, input[0].sizes)) {
    throw std::runtime_error("transform_padding: input_shape "
                             + ax_utils::sizes_to_string(prop->in_shape) + " does not match input tensor "
                             + ax_utils::sizes_to_string(input[0].sizes));
  }

  auto output = input;

  // Calculate output sizes for each tensor based on its padding
  for (size_t i = 0; i < input.size(); ++i) {
    // Use the appropriate padding for this tensor (or the last one if we have fewer paddings than tensors)
    const auto &padding
        = i < prop->paddings.size() ? prop->paddings[i] : prop->paddings.back();

    auto in_sizes = prop->in_shape.empty() ? input[i].sizes : prop->in_shape;
    const auto info = ax_utils::get_transfer_info(in_sizes, padding);

    if (i == 0 && !ax_utils::validate_shape(prop->out_shape, info.out_sizes)) {
      throw std::runtime_error("transform_padding: output_shape "
                               + ax_utils::sizes_to_string(prop->out_shape) + " does not match calculated output tensor "
                               + ax_utils::sizes_to_string(info.out_sizes));
    }

    auto &tensor = output[i];
    tensor.sizes = prop->out_shape.empty() ? info.out_sizes : prop->out_shape;
    tensor.bytes = 4;
    bool should_transpose = i < prop->transpose.size() ? prop->transpose[i] : false;
    if (should_transpose) {
      if (tensor.sizes.size() != 4) {
        throw std::runtime_error("dequantize with transpose must tranform 4 dimensional tensor");
      }
      std::swap(tensor.sizes[3], tensor.sizes[2]); // NHWC -> NHCW
      std::swap(tensor.sizes[2], tensor.sizes[1]); // NHCW -> NCHW
    }
  }

  return { output };
}

extern "C" void
transform(const AxDataInterface &input, const AxDataInterface &output,
    const padding_dequant_properties *prop, unsigned int, unsigned int,
    std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> &, Ax::Logger &logger)
{
  auto input_tensors = std::get<AxTensorsInterface>(input);
  auto output_tensors = std::get<AxTensorsInterface>(output);

  for (size_t i = 0; i < input_tensors.size(); ++i) {
    const auto out_shape = to_4d_shape(output_tensors[i].sizes);
    auto in_shape = to_4d_shape(
        prop->in_shape.empty() ? input_tensors[i].sizes : prop->in_shape);
    const int N = out_shape[0], C = out_shape[1], H = out_shape[2], W = out_shape[3];
    const int in0 = in_shape[0], in1 = in_shape[1], in2 = in_shape[2], in3 = in_shape[3];

    bool should_transpose = i < prop->transpose.size() ? prop->transpose[i] : false;

    if ((!should_transpose && (N > in0 || C > in1 || H > in2 || W > in3))
        || (should_transpose && (N > in0 || C > in3 || H > in1 || W > in2))) {
      throw std::runtime_error(
          "dequantize input and output sizes do not correspond. Output shape must be smaller");
    }
    const auto &padding
        = i < prop->paddings.size() ? prop->paddings[i] : prop->paddings.back();

    const auto info = ax_utils::get_transfer_info(in_shape, padding);

    cv::Mat input_mat(info.in_sizes, CV_8SC1, input_tensors[i].data);
    cv::Mat output_mat(info.out_sizes, CV_32FC1, output_tensors[i].data);
    const auto &dequantize_lookups = prop->dequantize_tables[i].data();
    auto cropped = std::all_of(padding.begin(), padding.end(),
                       [](int val) { return val == 0; }) ?
                       input_mat :
                       input_mat(info.ranges).clone();

    int8_t *inptr = cropped.ptr<int8_t>();
    float *outptr = output_mat.ptr<float>();

    if (!should_transpose) {
      std::transform(inptr, inptr + cropped.total(), outptr,
          [&dequantize_lookups](
              int8_t val) { return dequantize(val, dequantize_lookups); });
    } else {
      const int sh = W * C;
      const int sn = H * sh;
      for (int iN = 0; iN < N; ++iN) {
        for (int iC = 0; iC < C; ++iC) {
          for (int iH = 0; iH < H; ++iH) {
            for (int iW = 0; iW < W; ++iW) {
              int input_index = iN * sn + iH * sh + iW * C + iC;
              *outptr++ = prop->dequant_lut ?
                              dequantize(inptr[input_index], dequantize_lookups) :
                              prop->dequant_scale[i]
                                  * (static_cast<float>(inptr[input_index])
                                      - prop->dequant_zeropoint[i]);
            }
          }
        }
      }
    }
  }
}
