// Copyright Axelera AI, 2025
#include "gtest/gtest.h"
#include <gmodule.h>
#include "gmock/gmock.h"
#include "unittest_ax_common.h"

#include <memory>
#include <stdexcept>
#include <string>
#include <unordered_map>

#include <filesystem>
#include "AxLog.hpp"
#include "AxMeta.hpp"
#include "AxMetaObjectDetection.hpp"

#include "AxDataInterface.h"

namespace fs = std::filesystem;

namespace
{

struct object_meta {
  std::vector<int32_t> boxes;
  std::vector<float> scores;
  std::vector<int32_t> classes;
};

object_meta
get_object_meta(const std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> &map,
    std::string meta_identifier)
{
  auto position = map.find(meta_identifier);
  if (position == map.end()) {
    return { {}, {} };
  }
  auto *meta = position->second.get();
  EXPECT_NE(meta, nullptr);
  EXPECT_EQ(typeid(*meta), typeid(AxMetaObjDetection));

  auto actual_metadata = meta->get_extern_meta();
  EXPECT_EQ(actual_metadata.size(), 3);

  auto p_boxes = reinterpret_cast<const int32_t *>(actual_metadata[0].meta);
  auto p_scores = reinterpret_cast<const float *>(actual_metadata[1].meta);
  auto p_classes = reinterpret_cast<const int32_t *>(actual_metadata[2].meta);
  auto actual_boxes = std::vector<int32_t>{ p_boxes,
    p_boxes + actual_metadata[0].meta_size / sizeof(int32_t) };
  auto actual_scores = std::vector<float>{ p_scores,
    p_scores + actual_metadata[1].meta_size / sizeof(float) };
  auto actual_classes = std::vector<int32_t>{ p_classes,
    p_classes + actual_metadata[2].meta_size / sizeof(int32_t) };

  return { actual_boxes, actual_scores, actual_classes };
}

template <typename T>
AxTensorsInterface
tensors_from_vector(std::vector<T> &tensors, std::vector<int> sizes)
{
  return {
    { sizes, sizeof tensors[0], tensors.data() },
  };
}

TEST(yolo10_simple_errors, no_meta_key_throws)
{
  std::unordered_map<std::string, std::string> properties = {};
  EXPECT_THROW(Ax::LoadDecode("yolov10_simple", properties), std::runtime_error);
}

TEST(yolo10_simple_basic, no_detections_with_high_confidence)
{
  // Create a tensor with a simple detection but set high confidence threshold to filter it
  std::vector<float> output_tensor = { // Box coordinates (x1, y1, x2, y2)
    100.0f, 100.0f, 200.0f, 200.0f,
    // Confidence score and class ID
    0.75f, 1.0f
  };

  std::string meta_identifier = "yolo10_test";

  std::unordered_map<std::string, std::string> properties = {
    { "meta_key", meta_identifier },
    { "confidence_threshold", "0.9" }, // Set high threshold to filter detection
    { "classes", "80" },
    { "model_width", "640" },
    { "model_height", "640" },
    { "scale_up", "1" },
    { "letterbox", "1" },
  };
  auto decoder = Ax::LoadDecode("yolov10_simple", properties);

  AxVideoInterface video_info{ { 640, 480, 640, 0, AxVideoFormat::RGB }, nullptr };
  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> map{};

  auto tensors = tensors_from_vector(output_tensor, { 1, 1, 1, 6 });
  decoder->decode_to_meta(tensors, 0, 1, map, video_info);

  auto [actual_boxes, actual_scores, actual_classes] = get_object_meta(map, meta_identifier);
  EXPECT_EQ(actual_classes, std::vector<int32_t>{});
  EXPECT_EQ(actual_scores, std::vector<float>{});
}

TEST(yolo10_simple_basic, single_detection_with_low_confidence)
{
  // Create a tensor with a simple detection
  std::vector<float> output_tensor = { // Box coordinates (x1, y1, x2, y2)
    100.0f, 100.0f, 200.0f, 200.0f,
    // Confidence score and class ID
    0.75f, 1.0f
  };

  std::string meta_identifier = "yolo10_test";

  std::unordered_map<std::string, std::string> properties = {
    { "meta_key", meta_identifier },
    { "confidence_threshold", "0.5" },
    { "classes", "80" },
    { "model_width", "640" },
    { "model_height", "640" },
    { "scale_up", "1" },
    { "letterbox", "1" },
  };
  auto decoder = Ax::LoadDecode("yolov10_simple", properties);

  AxVideoInterface video_info{ { 640, 480, 640, 0, AxVideoFormat::RGB }, nullptr };
  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> map{};

  auto tensors = tensors_from_vector(output_tensor, { 1, 1, 1, 6 });
  decoder->decode_to_meta(tensors, 0, 1, map, video_info);

  auto [actual_boxes, actual_scores, actual_classes] = get_object_meta(map, meta_identifier);

  // Should have one detection
  EXPECT_EQ(actual_classes.size(), 1);
  EXPECT_EQ(actual_scores.size(), 1);
  EXPECT_EQ(actual_boxes.size(), 4); // 4 coordinates for one box

  // Check detection details
  EXPECT_EQ(actual_classes[0], 1);
  EXPECT_FLOAT_EQ(actual_scores[0], 0.75f);

  // Verify box coordinates were scaled correctly
  // Note: The exact box coordinates will depend on the scaling implementation
  // This test just verifies we have valid coordinates
  EXPECT_GT(actual_boxes[0], 0);
  EXPECT_GT(actual_boxes[1], 0);
  EXPECT_GT(actual_boxes[2], actual_boxes[0]);
  EXPECT_GT(actual_boxes[3], actual_boxes[1]);
}

TEST(yolo10_simple_basic, multiple_detections)
{
  // Create a tensor with multiple detections
  std::vector<float> output_tensor = { // Box 1
    100.0f, 100.0f, 200.0f, 200.0f, 0.9f, 1.0f,
    // Box 2
    300.0f, 300.0f, 400.0f, 400.0f, 0.8f, 2.0f,
    // Box 3 (will be filtered out by confidence threshold)
    50.0f, 50.0f, 150.0f, 150.0f, 0.3f, 3.0f
  };

  std::string meta_identifier = "yolo10_test";

  std::unordered_map<std::string, std::string> properties = {
    { "meta_key", meta_identifier },
    { "confidence_threshold", "0.5" },
    { "classes", "80" },
    { "model_width", "640" },
    { "model_height", "640" },
    { "scale_up", "1" },
    { "letterbox", "1" },
  };
  auto decoder = Ax::LoadDecode("yolov10_simple", properties);

  AxVideoInterface video_info{ { 640, 480, 640, 0, AxVideoFormat::RGB }, nullptr };
  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> map{};

  auto tensors = tensors_from_vector(output_tensor, { 1, 1, 3, 6 });
  decoder->decode_to_meta(tensors, 0, 1, map, video_info);

  auto [actual_boxes, actual_scores, actual_classes] = get_object_meta(map, meta_identifier);

  // Should have two detections (third one filtered by confidence)
  EXPECT_EQ(actual_classes.size(), 2);
  EXPECT_EQ(actual_scores.size(), 2);
  EXPECT_EQ(actual_boxes.size(), 8); // 4 coordinates for each box

  // Verify classes and scores
  std::vector<int> expected_classes = { 1, 2 };
  EXPECT_THAT(actual_classes, testing::UnorderedElementsAreArray(expected_classes));

  // Check scores are in expected range
  for (auto score : actual_scores) {
    EXPECT_GE(score, 0.5f);
    EXPECT_LE(score, 1.0f);
  }
}

TEST(yolo10_simple_basic, class_filtering)
{
  // Create a tensor with multiple detections of different classes
  std::vector<float> output_tensor = { // Box class 1
    100.0f, 100.0f, 200.0f, 200.0f, 0.9f, 1.0f,
    // Box class 2
    300.0f, 300.0f, 400.0f, 400.0f, 0.8f, 2.0f,
    // Box class 3
    50.0f, 50.0f, 150.0f, 150.0f, 0.7f, 3.0f
  };

  std::string meta_identifier = "yolo10_test";

  std::unordered_map<std::string, std::string> properties = {
    { "meta_key", meta_identifier },
    { "confidence_threshold", "0.5" },
    { "classes", "80" },
    { "label_filter", "1,3" }, // Only allow classes 1 and 3
    { "model_width", "640" },
    { "model_height", "640" },
    { "scale_up", "1" },
    { "letterbox", "1" },
  };
  auto decoder = Ax::LoadDecode("yolov10_simple", properties);

  AxVideoInterface video_info{ { 640, 480, 640, 0, AxVideoFormat::RGB }, nullptr };
  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> map{};

  auto tensors = tensors_from_vector(output_tensor, { 1, 1, 3, 6 });
  decoder->decode_to_meta(tensors, 0, 1, map, video_info);

  auto [actual_boxes, actual_scores, actual_classes] = get_object_meta(map, meta_identifier);

  // Should have only two detections (class 2 filtered out)
  EXPECT_EQ(actual_classes.size(), 2);
  EXPECT_EQ(actual_scores.size(), 2);

  // Verify only classes 1 and 3 are present
  std::vector<int> expected_classes = { 1, 3 };
  EXPECT_THAT(actual_classes, testing::UnorderedElementsAreArray(expected_classes));
}

} // namespace
