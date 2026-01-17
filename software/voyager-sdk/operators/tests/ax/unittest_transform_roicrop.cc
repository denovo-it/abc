// Copyright Axelera AI, 2025
#include "unittest_ax_common.h"

namespace
{
const auto crop_lib = "roicrop";

TEST(roicrop, meta_and_cropping_x_fails)
{
  std::unordered_map<std::string, std::string> input = {
    { "meta_key", "anything" },
    { "left", "224" },
  };
  EXPECT_THROW(Ax::LoadTransform(crop_lib, input), std::runtime_error);
}

TEST(roicrop, meta_and_cropping_y_fails)
{
  std::unordered_map<std::string, std::string> input = {
    { "meta_key", "anything" },
    { "top", "224" },
  };
  EXPECT_THROW(Ax::LoadTransform(crop_lib, input), std::runtime_error);
}

TEST(roicrop, meta_and_cropping_width_fails)
{
  std::unordered_map<std::string, std::string> input = {
    { "meta_key", "anything" },
    { "width", "224" },
  };
  EXPECT_THROW(Ax::LoadTransform(crop_lib, input), std::runtime_error);
}

TEST(roicrop, meta_and_cropping_height_fails)
{
  std::unordered_map<std::string, std::string> input = {
    { "meta_key", "anything" },
    { "height", "224" },
  };
  EXPECT_THROW(Ax::LoadTransform(crop_lib, input), std::runtime_error);
}

TEST(roicrop, crop_box)
{
  std::unordered_map<std::string, std::string> input = {
    { "left", "200" },
    { "top", "100" },
    { "width", "224" },
    { "height", "224" },
  };
  auto xform = Ax::LoadTransform(crop_lib, input);
  AxVideoInterface video_info{ { 640, 480, 640 * 4, 0, AxVideoFormat::RGBA }, nullptr };
  Ax::MetaMap metadata;

  auto out_interface = xform->set_output_interface_from_meta(video_info, 0, 1, metadata);
  auto info = std::get<AxVideoInterface>(out_interface).info;
  EXPECT_EQ(info.width, 224);
  EXPECT_EQ(info.height, 224);
  EXPECT_EQ(info.x_offset, 200);
  EXPECT_EQ(info.y_offset, 100);
  EXPECT_EQ(info.cropped, true);
}

TEST(roicrop, x_bounds)
{
  std::unordered_map<std::string, std::string> input = {
    { "left", "650" },
    { "top", "100" },
    { "width", "224" },
    { "height", "224" },
  };
  auto xform = Ax::LoadTransform(crop_lib, input);
  AxVideoInterface video_info{ { 640, 480, 640 * 4, 0, AxVideoFormat::RGBA }, nullptr };
  Ax::MetaMap metadata;

  EXPECT_THROW(xform->set_output_interface_from_meta(video_info, 0, 1, metadata),
      std::runtime_error);
}

TEST(roicrop, y_bounds)
{
  std::unordered_map<std::string, std::string> input = {
    { "left", "0" },
    { "top", "480" },
    { "width", "224" },
    { "height", "224" },
  };
  auto xform = Ax::LoadTransform(crop_lib, input);
  AxVideoInterface video_info{ { 640, 480, 640 * 4, 0, AxVideoFormat::RGBA }, nullptr };
  Ax::MetaMap metadata;

  EXPECT_THROW(xform->set_output_interface_from_meta(video_info, 0, 1, metadata),
      std::runtime_error);
}

TEST(roicrop, width_bounds)
{
  std::unordered_map<std::string, std::string> input = {
    { "left", "460" },
    { "top", "0" },
    { "width", "224" },
    { "height", "224" },
  };
  auto xform = Ax::LoadTransform(crop_lib, input);
  AxVideoInterface video_info{ { 640, 480, 640 * 4, 0, AxVideoFormat::RGBA }, nullptr };
  Ax::MetaMap metadata;

  auto out_interface = xform->set_output_interface_from_meta(video_info, 0, 1, metadata);
  auto info = std::get<AxVideoInterface>(out_interface).info;
  EXPECT_EQ(info.width, 180);
  EXPECT_EQ(info.height, 224);
  EXPECT_EQ(info.x_offset, 460);
  EXPECT_EQ(info.y_offset, 0);
  EXPECT_EQ(info.cropped, true);
}

TEST(roicrop, height_bounds)
{
  std::unordered_map<std::string, std::string> input = {
    { "left", "400" },
    { "top", "300" },
    { "width", "224" },
    { "height", "224" },
  };
  auto xform = Ax::LoadTransform(crop_lib, input);
  AxVideoInterface video_info{ { 640, 480, 640 * 4, 0, AxVideoFormat::RGBA }, nullptr };
  Ax::MetaMap metadata;

  auto out_interface = xform->set_output_interface_from_meta(video_info, 0, 1, metadata);
  auto info = std::get<AxVideoInterface>(out_interface).info;
  EXPECT_EQ(info.width, 224);
  EXPECT_EQ(info.height, 180);
  EXPECT_EQ(info.x_offset, 400);
  EXPECT_EQ(info.y_offset, 300);
  EXPECT_EQ(info.cropped, true);
}

} // namespace
