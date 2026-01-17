// Copyright Axelera AI, 2025
#include <unordered_map>
#include <unordered_set>
#include "AxDataInterface.h"
#include "AxLog.hpp"
#include "AxMetaBBox.hpp"
#include "AxStreamerUtils.hpp"
#include "AxUtils.hpp"

#include "AxStreamerUtils.hpp"

#include <opencv2/core/ocl.hpp>

struct roicrop_properties {
  std::string meta_key{};
  int left{ -1 };
  int top{ -1 };
  int width{ -1 };
  int height{ -1 };
  bool downstream_supports_opencl{ false };
};

extern "C" const std::unordered_set<std::string> &
allowed_properties()
{
  static const std::unordered_set<std::string> allowed_properties{
    "meta_key",
    "top",
    "left",
    "width",
    "height",
  };
  return allowed_properties;
}

extern "C" std::shared_ptr<void>
init_and_set_static_properties(
    const std::unordered_map<std::string, std::string> &input, Ax::Logger &logger)
{
  auto prop = std::make_shared<roicrop_properties>();
  prop->meta_key = Ax::get_property(input, "meta_key", "roicrop_properties", prop->meta_key);
  prop->top = Ax::get_property(input, "top", "roicrop_properties", prop->top);
  prop->left = Ax::get_property(input, "left", "roicrop_properties", prop->left);
  prop->width = Ax::get_property(input, "width", "roicrop_properties", prop->width);
  prop->height = Ax::get_property(input, "height", "roicrop_properties", prop->height);

  if (prop->meta_key.empty()) {
    if (prop->top == -1 || prop->left == -1 || prop->width == -1 || prop->height == -1) {
      logger.throw_error("roicrop: if meta_key is not provided, x, y, width and height must be provided");
    }
  } else {
    if (prop->top != -1 || prop->left != -1 || prop->width != -1 || prop->height != -1) {
      logger.throw_error("roicrop: if meta_key is provided, x, y, width and height must not be provided");
    }
  }
  return prop;
}

extern "C" void
set_dynamic_properties(const std::unordered_map<std::string, std::string> &input,
    roicrop_properties *prop, Ax::Logger & /*logger*/)
{
  prop->downstream_supports_opencl = Ax::get_property(input, "downstream_supports_opencl",
      "roicrop_static_properties", prop->downstream_supports_opencl);
}


BboxXyxy
get_roi(const roicrop_properties *prop, unsigned int subframe_index,
    unsigned int number_of_subframes,
    std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> &meta_map,
    Ax::Logger &logger)
{
  if (!prop->meta_key.empty()) {
    if (number_of_subframes == 0) {
      return { 0, 0, 15, 15 };
    }
    auto meta = meta_map.find(prop->meta_key);
    if (meta == meta_map.end()) {
      logger.throw_error("roicrop: meta_key " + prop->meta_key + " not found in meta map");
    }
    AxMetaBbox *box_meta
        = dynamic_cast<AxMetaBbox *>(meta_map.at(prop->meta_key).get());
    if (!box_meta) {
      logger.throw_error("roicrop has not been provided with AxMetaBbox");
    }
    if (number_of_subframes <= subframe_index) {
      logger.throw_error("roicrop subframe index must be less than number of subframes");
    }
    return box_meta->get_box_xyxy(subframe_index);
  }
  return { prop->left, prop->top, prop->left + prop->width - 1,
    prop->top + prop->height - 1 };
}

extern "C" AxDataInterface
set_output_interface_from_meta(const AxDataInterface &interface,
    const roicrop_properties *prop, unsigned int subframe_index, unsigned int number_of_subframes,
    std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> &meta_map,
    Ax::Logger &logger)
{
  if (!std::holds_alternative<AxVideoInterface>(interface)) {
    throw std::runtime_error("roicrop works on video input only");
  }
  AxDataInterface output = interface;
  auto &out_info = std::get<AxVideoInterface>(output).info;

  auto input = std::get<AxVideoInterface>(interface);

  auto [x1, y1, x2, y2]
      = get_roi(prop, subframe_index, number_of_subframes, meta_map, logger);
  if (out_info.width <= x1) {
    logger.throw_error("roicrop: x1 is out of bounds");
  }
  if (out_info.height <= y1) {
    logger.throw_error("roicrop: x1 is out of bounds");
  }
  if (out_info.width <= x2) {
    logger(AX_WARN) << "roicrop: box exceeds image width, clipping to image width"
                    << std::endl;
    x2 = out_info.width - 1;
  }
  if (out_info.height <= y2) {
    logger(AX_WARN) << "roicrop: box exceeds image height, clipping to image height"
                    << std::endl;
    y2 = out_info.height - 1;
  }
  out_info.width = 1 + x2 - x1;
  out_info.height = 1 + y2 - y1;
  out_info.x_offset = x1;
  out_info.y_offset = y1;
  out_info.cropped = true;
  return output;
}

extern "C" void
transform(const AxDataInterface &input, const AxDataInterface &output,
    const roicrop_properties *prop, unsigned int subframe_index, unsigned int subframe_number,
    std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> &map, Ax::Logger &logger)
{
  cv::ocl::setUseOpenCL(false);

  auto &input_video = std::get<AxVideoInterface>(input);
  cv::Mat input_mat(cv::Size(input_video.info.width, input_video.info.height),
      Ax::opencv_type_u8(input_video.info.format), input_video.data,
      input_video.info.stride);

  cv::Mat input_cropped;
  auto out = set_output_interface_from_meta(
      input, prop, subframe_index, subframe_number, map, logger);
  auto &out_info = std::get<AxVideoInterface>(out).info;

  cv::Rect crop_rect(
      out_info.x_offset, out_info.y_offset, out_info.width, out_info.height);
  input_cropped = input_mat(crop_rect);

  auto &output_video = std::get<AxVideoInterface>(output);
  if (input_video.info.format != output_video.info.format)
    throw std::runtime_error("roicrop cannot do video format conversions");

  cv::Mat output_mat(cv::Size(output_video.info.width, output_video.info.height),
      Ax::opencv_type_u8(output_video.info.format), output_video.data,
      output_video.info.stride);

  input_cropped.copyTo(output_mat);
}

extern "C" bool
query_supports(Ax::PluginFeature feature,
    const roicrop_properties *resize_properties, Ax::Logger &logger)
{
  if (feature == Ax::PluginFeature::opencl_buffers) {
    return resize_properties && resize_properties->downstream_supports_opencl;
  }
  return false;
}
