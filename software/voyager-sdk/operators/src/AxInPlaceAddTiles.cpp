// Copyright Axelera AI, 2023
#include <unordered_set>
#include "AxDataInterface.h"
#include "AxLog.hpp"
#include "AxMetaObjectDetection.hpp"
#include "AxMetaStreamId.hpp"
#include "AxOpUtils.hpp"
#include "AxStreamerUtils.hpp"
#include "AxUtils.hpp"

struct addtiles_properties {
  std::string meta_key{ "" };
  std::string tile_size{};
  std::string tile_position{};
  size_t slice_size{ 1080 };
  size_t tile_overlap{ 0 };
  size_t model_width{ 0 };
  size_t model_height{ 0 };
  size_t tile_width{ 0 };
  size_t tile_height{ 0 };
};

extern "C" const std::unordered_set<std::string> &
allowed_properties()
{
  static const std::unordered_set<std::string> allowed_properties{
    "meta_key",
    "tile_size",
    "tile_overlap",
    "tile_position",
    "model_width",
    "model_height",
  };
  return allowed_properties;
}

void
determine_slice_sizes(addtiles_properties &properties, Ax::Logger &logger)
{
  if (properties.tile_size == "default") {
    properties.tile_width = properties.model_width;
    properties.tile_height = properties.model_height;
    return;
  }
  auto parts = Ax::Internal::split(properties.tile_size, 'x');
  if (parts.size() == 1) {
    auto slice_size = std::stoi(std::string(parts[0]));

    auto longest = std::max(properties.model_width, properties.model_height);
    if (slice_size < longest) {
      logger(AX_WARN)
          << "inplace_addtiles: slice_size (" << slice_size
          << ") is less than the model's longest side (" << longest << ")."
          << " Using the model's longest side as slice_size." << std::endl;
      slice_size = longest;
    }
    auto model_ratio = static_cast<float>(properties.model_width) / properties.model_height;
    auto slice_width = model_ratio > 1 ? slice_size : slice_size * model_ratio;
    auto slice_height = model_ratio > 1 ? slice_size / model_ratio : slice_size;
    properties.tile_width = slice_width;
    properties.tile_height = slice_height;
    return;
  } else {
    properties.tile_width = std::stoi(std::string(parts[0]));
    properties.tile_height = std::stoi(std::string(parts[1]));
  }
}

extern "C" std::shared_ptr<void>
init_and_set_static_properties(
    const std::unordered_map<std::string, std::string> &input, Ax::Logger &logger)
{
  auto prop = std::make_shared<addtiles_properties>();
  prop->meta_key = Ax::get_property(
      input, "meta_key", "addtiles_static_properties", prop->meta_key);
  prop->tile_size = Ax::get_property(
      input, "tile_size", "addtiles_static_properties", prop->tile_size);
  prop->tile_overlap = Ax::get_property(
      input, "tile_overlap", "addtiles_static_properties", prop->tile_overlap);
  prop->tile_position = Ax::get_property(
      input, "tile_position", "addtiles_static_properties", prop->tile_position);
  prop->model_width = Ax::get_property(
      input, "model_width", "addtiles_static_properties", prop->model_width);
  prop->model_height = Ax::get_property(
      input, "model_height", "addtiles_static_properties", prop->model_height);
  determine_slice_sizes(*prop, logger);
  return prop;
}

struct tiling_params {
  int tile_region_width;
  int tile_region_height;
  int col_start;
  int row_start;
};

tiling_params
determine_tile_params(int width, int height, const std::string &position)
{
  int col_start = 0;
  int row_start = 0;
  int tile_region_width = width;
  int tile_region_height = height;
  if (position == "none") {
    //  Nothing to do
  } else if (position == "left") {
    tile_region_width = width / 2;
  } else if (position == "right") {
    col_start = tile_region_width / 2;
    tile_region_width = width / 2;
  } else if (position == "top") {
    tile_region_height = height / 2;
  } else if (position == "bottom") {
    tile_region_height = height / 2;
    row_start = height / 2;
  } else {
    throw std::runtime_error("Invalid tile position");
  }
  return { tile_region_width, tile_region_height, col_start, row_start };
}

extern "C" void
inplace(const AxDataInterface &interface, const addtiles_properties *details,
    unsigned int, unsigned int,
    std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> &map, Ax::Logger &logger)
{
  if (details->meta_key.empty()) {
    logger(AX_ERROR) << "inplace_addtiles: meta_key is empty" << std::endl;
    throw std::runtime_error("inplace_addtiles: meta_key is empty");
  }
  if (map.count(details->meta_key)) {
    logger(AX_ERROR) << "inplace_addtiles: meta_key (" << details->meta_key
                     << ") already exists" << std::endl;
    throw std::runtime_error("inplace_addtiles: meta_key already exists");
  }

  if (!std::holds_alternative<AxVideoInterface>(interface)) {
    throw std::runtime_error("addtiles works on video input only");
  }

  auto &video = std::get<AxVideoInterface>(interface);

  auto [tile_region_width, tile_region_height, col_start, row_start]
      = determine_tile_params(video.info.width, video.info.height, details->tile_position);

  int slice_width = details->tile_width;
  int slice_height = details->tile_height;

  auto [x_slices, x_overlap]
      = Ax::determine_overlap(tile_region_width, slice_width, details->tile_overlap);
  auto [y_slices, y_overlap]
      = Ax::determine_overlap(tile_region_height, slice_height, details->tile_overlap);

  std::vector<box_xyxy> boxes{ { 0, 0, video.info.width - 1, video.info.height - 1 } };
  for (auto row = 0; row != y_slices; ++row) {
    for (auto col = 0; col != x_slices; ++col) {
      int x = col * (slice_width - x_overlap);
      int y = row * (slice_height - y_overlap);
      if (x + slice_width > tile_region_width) {
        x = std::max(tile_region_width - slice_width, 0);
      }
      if (y + slice_height > tile_region_height) {
        y = std::max(tile_region_height - slice_height, 0);
      }
      auto box = box_xyxy{
        .x1 = x + col_start,
        .y1 = y + row_start,
        //  Remember this is a fully closed range
        .x2 = std::min(static_cast<int>(x + slice_width) + col_start - 1,
            col_start + tile_region_width - 1),
        .y2 = std::min(static_cast<int>(y + slice_height) + row_start - 1,
            row_start + tile_region_height - 1),
      };
      boxes.push_back(box);
    }
  }
  std::vector<float> scores(boxes.size(), 1.0);
  std::vector<int> class_ids(boxes.size(), -1);
  ax_utils::insert_meta<AxMetaObjDetection>(map, details->meta_key, "", 0, 1,
      std::move(boxes), std::move(scores), std::move(class_ids));
}
