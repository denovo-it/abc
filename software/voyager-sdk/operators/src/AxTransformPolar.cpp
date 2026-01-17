// Copyright Axelera AI, 2025
#include <unordered_map>
#include <unordered_set>
#include "AxDataInterface.h"
#include "AxLog.hpp"
#include "AxMeta.hpp"
#include "AxStreamerUtils.hpp"
#include "AxUtils.hpp"

#include <opencv2/opencv.hpp>

struct polar_properties {
  int width{};
  int height{};
  int size{};
  float center_x{ 0.5f };
  float center_y{ 0.5f };
  bool rotate180{ true };
  float max_radius{};
  bool inverse{ false };
  bool linear_polar{ true };
  std::string format{};
};

extern "C" const std::unordered_set<std::string> &
allowed_properties()
{
  static const std::unordered_set<std::string> allowed_properties{ "center_x",
    "center_y", "max_radius", "inverse", "linear_polar", "format", "width",
    "height", "size", "start_angle", "rotate180" };
  return allowed_properties;
}

extern "C" std::shared_ptr<void>
init_and_set_static_properties(
    const std::unordered_map<std::string, std::string> &input, Ax::Logger &logger)
{
  auto prop = std::make_shared<polar_properties>();

  prop->center_x
      = Ax::get_property(input, "center_x", "polar_static_properties", prop->center_x);
  prop->center_y
      = Ax::get_property(input, "center_y", "polar_static_properties", prop->center_y);
  prop->max_radius = Ax::get_property(
      input, "max_radius", "polar_static_properties", prop->max_radius);
  prop->inverse
      = Ax::get_property(input, "inverse", "polar_static_properties", prop->inverse);
  prop->linear_polar = Ax::get_property(
      input, "linear_polar", "polar_static_properties", prop->linear_polar);
  prop->format = Ax::get_property(input, "format", "polar_dynamic_properties", prop->format);
  prop->size = Ax::get_property(input, "size", "polar_static_properties", prop->size);
  prop->width = Ax::get_property(input, "width", "polar_static_properties", prop->width);
  prop->height = Ax::get_property(input, "height", "polar_static_properties", prop->height);
  prop->rotate180 = Ax::get_property(
      input, "rotate180", "polar_static_properties", prop->rotate180);

  if (prop->size > 0 && (prop->width > 0 || prop->height > 0)) {
    throw std::runtime_error("You must provide only one of width/height or size");
  }

  return prop;
}

extern "C" void
set_dynamic_properties(const std::unordered_map<std::string, std::string> & /*input*/,
    polar_properties * /*prop*/, Ax::Logger & /*logger*/)
{
}

std::pair<int, int>
determine_width_height(const AxVideoInterface &in_info, int size)
{
  auto width = in_info.info.width;
  auto height = in_info.info.height;
  auto height_is_shortest = height < width;
  auto scale = height_is_shortest ? static_cast<double>(size) / height :
                                    static_cast<double>(size) / width;
  return { static_cast<int>(std::round(width * scale)),
    static_cast<int>(std::round(height * scale)) };
}


const char *name = "Polar Transform";

extern "C" AxDataInterface
set_output_interface(const AxDataInterface &interface,
    const polar_properties *prop, Ax::Logger &logger)
{
  AxDataInterface output{};
  if (std::holds_alternative<AxVideoInterface>(interface)) {
    auto in_info = std::get<AxVideoInterface>(interface);
    auto out_info = in_info;
    auto width = in_info.info.width;
    int height = in_info.info.height;
    if (prop->size) {
      std::tie(width, height) = determine_width_height(in_info, prop->size);
    } else if (prop->width != 0 && prop->height != 0) {
      width = prop->width;
      height = prop->height;
    }
    out_info.info.width = width;
    out_info.info.height = height;
    out_info.info.actual_height = height;

    auto format = prop->format.empty() ? out_info.info.format :
                                         AxVideoFormatFromString(prop->format);
    out_info.info.format = format;

    // Valid output formats are RGB, BGR, and GRAY8
    std::array valid_output_formats = {
      AxVideoFormat::RGB,
      AxVideoFormat::BGR,
      AxVideoFormat::GRAY8,
    };
    Ax::validate_output_format(out_info.info.format, prop->format, name, valid_output_formats);
    output = out_info;
  }
  return output;
}

float
calculate_max_radius(const AxVideoInterface &in_info, float center_x, float center_y)
{
  float cx = center_x * in_info.info.width;
  float cy = center_y * in_info.info.height;

  // Calculate distance to corners
  float d1 = sqrt(cx * cx + cy * cy);
  float d2 = sqrt((in_info.info.width - cx) * (in_info.info.width - cx) + cy * cy);
  float d3 = sqrt(cx * cx + (in_info.info.height - cy) * (in_info.info.height - cy));
  float d4 = sqrt((in_info.info.width - cx) * (in_info.info.width - cx)
                  + (in_info.info.height - cy) * (in_info.info.height - cy));

  return fmax(fmax(d1, d2), fmax(d3, d4));
}


extern "C" void
transform(const AxDataInterface &input, const AxDataInterface &output,
    const polar_properties *prop, unsigned int, unsigned int,
    std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> &, Ax::Logger &logger)
{
  auto in_info = std::get<AxVideoInterface>(input);
  auto out_info = std::get<AxVideoInterface>(output);

  // Create input Mat and ensure contiguous memory
  cv::Mat input_mat;

  auto valid_formats = {
    AxVideoFormat::RGB,
    AxVideoFormat::BGR,
    AxVideoFormat::GRAY8,
    AxVideoFormat::RGBA,
    AxVideoFormat::YUY2,
    AxVideoFormat::NV12,
    AxVideoFormat::I420,
  };

  if (std::none_of(valid_formats.begin(), valid_formats.end(),
          [&in_info](auto format) { return format == in_info.info.format; })) {
    throw std::runtime_error("Polar Transform does not work with the input format: "
                             + AxVideoFormatToString(in_info.info.format));
  }

  // Transfer in_info.data into conteguous buffer


  // TODO: fix AX_VIDEO_FORMAT_REGISTER where the second param should represent number of channels not planes for planar formats
  // This works only with contiguous memory
  if (in_info.info.format == AxVideoFormat::I420
      || in_info.info.format == AxVideoFormat::NV12) {
    // I420 is planar format, create Mat with single channel for Y plane
    input_mat = cv::Mat(in_info.info.height * 1.5, in_info.info.width, CV_8UC1,
        in_info.data, in_info.info.stride);
  } else if (in_info.info.format == AxVideoFormat::YUY2) {
    // YUY2 is packed format, 2 bytes per pixel horizontally
    input_mat = cv::Mat(in_info.info.height, in_info.info.width, CV_8UC2,
        in_info.data, in_info.info.stride);
  } else if (in_info.info.format == AxVideoFormat::RGBA) {
    input_mat = cv::Mat(in_info.info.height, in_info.info.width, CV_8UC4,
        in_info.data, in_info.info.stride);
  }

  else {
    input_mat = cv::Mat(in_info.info.height, in_info.info.width,
        Ax::opencv_type_u8(in_info.info.format), in_info.data, in_info.info.stride);
  }

  cv::Mat processed_input;
  bool needs_conversion = (in_info.info.format == AxVideoFormat::YUY2
                           || in_info.info.format == AxVideoFormat::RGBA
                           || in_info.info.format == AxVideoFormat::NV12
                           || in_info.info.format == AxVideoFormat::I420);

  if (needs_conversion) {

    cv::cvtColor(input_mat, processed_input,
        Ax::Internal::format2format(in_info.info.format, out_info.info.format));

  } else {
    processed_input = input_mat;
  }

  // Ensure input is row major by transposing, as this is expected by warpPolar
  cv::transpose(processed_input, processed_input);

  // Calculate parameters
  float max_radius = prop->max_radius;
  if (max_radius == 0.0f) {
    max_radius = calculate_max_radius(in_info, prop->center_x, prop->center_y);
  }
  // After transpose, width and height are swapped
  cv::Point2f center(
      prop->center_y * in_info.info.height, prop->center_x * in_info.info.width);

  int flags = cv::INTER_LINEAR;
  if (prop->inverse) {
    flags |= cv::WARP_INVERSE_MAP;
  }
  if (prop->linear_polar) {
    flags |= cv::WARP_POLAR_LINEAR;
  } else {
    flags |= cv::WARP_POLAR_LOG;
  }

  // Apply polar transformation to temporary Mat
  cv::Mat temp_output;
  // After transpose, output dimensions should also be swapped
  cv::warpPolar(processed_input, temp_output,
      cv::Size(out_info.info.height, out_info.info.width), center, max_radius, flags);

  // Handle rotation if needed
  if (prop->rotate180) {
    cv::rotate(temp_output, temp_output, cv::ROTATE_180);
  }

  // Transpose back to original orientation
  cv::transpose(temp_output, temp_output);

  // Create output Mat with custom stride and copy result
  cv::Mat output_mat(out_info.info.height, out_info.info.width,
      Ax::opencv_type_u8(out_info.info.format), out_info.data, out_info.info.stride);

  temp_output.copyTo(output_mat);
}

extern "C" bool
query_supports(Ax::PluginFeature feature, const polar_properties *prop, Ax::Logger &logger)
{
  if (feature == Ax::PluginFeature::opencl_buffers) {
    return false; // OpenCV version doesn't support OpenCL buffers directly
  }
  return false;
}
