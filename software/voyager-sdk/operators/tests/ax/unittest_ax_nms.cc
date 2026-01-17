// Copyright Axelera AI, 2025
#include <gtest/gtest.h>

#include "AxNms.hpp"

namespace
{
TEST(nms, empty_list_returns_empty_list)
{
  auto boxes = std::vector<box_xyxy>{};
  auto scores = std::vector<float>{};
  auto classes = std::vector<int>{};
  auto meta = AxMetaObjDetection(boxes, scores, classes);
  auto actual = non_max_suppression(meta, 0.5f, true, 300, false);
  EXPECT_EQ(actual.num_elements(), 0);
}

TEST(nms, overlapping_boxes_different_classes_do_not_suppress_if_class_aware)
{
  auto boxes = std::vector<box_xyxy>{ { 0, 0, 10, 10 }, { 1, 1, 11, 11 } };
  auto scores = std::vector<float>{ 0.5f, 0.6f };
  auto classes = std::vector<int>{ 1, 2 };
  auto meta = AxMetaObjDetection(boxes, scores, classes);
  auto actual = non_max_suppression(meta, 0.5f, false, 300, false);
  EXPECT_EQ(actual.num_elements(), 2);
}

TEST(nms, overlapping_boxes_different_classes_suppress_if_class_agnostic)
{
  auto boxes = std::vector<box_xyxy>{ { 0, 0, 10, 10 }, { 1, 1, 11, 11 } };
  auto scores = std::vector<float>{ 0.5f, 0.6f };
  auto classes = std::vector<int>{ 1, 2 };
  auto meta = AxMetaObjDetection(boxes, scores, classes);
  auto actual = non_max_suppression(meta, 0.5f, true, 300, false);
  EXPECT_EQ(actual.num_elements(), 1);
}

TEST(nms, non_overlapping_boxes_do_not_suppress)
{
  auto boxes = std::vector<box_xyxy>{ { 0, 0, 10, 10 }, { 10, 10, 21, 21 } };
  auto scores = std::vector<float>{ 0.5f, 0.6f };
  auto classes = std::vector<int>{ 1, 2 };
  auto meta = AxMetaObjDetection(boxes, scores, classes);
  auto actual = non_max_suppression(meta, 0.5f, true, 300, false);
  EXPECT_EQ(actual.num_elements(), 2);
}

TEST(nms, only_topk_is_returned)
{
  auto boxes = std::vector<box_xyxy>{ { 0, 0, 10, 10 }, { 10, 10, 21, 21 } };
  auto scores = std::vector<float>{ 0.5f, 0.6f };
  auto classes = std::vector<int>{ 1, 2 };
  auto meta = AxMetaObjDetection(boxes, scores, classes);
  auto actual = non_max_suppression(meta, 0.5f, true, 1, false);
  EXPECT_EQ(actual.num_elements(), 1);
  auto box_xyxy = actual.get_box_xyxy(0);
  EXPECT_EQ(box_xyxy.x1, 10);
  EXPECT_EQ(box_xyxy.y1, 10);
  EXPECT_EQ(box_xyxy.x2, 21);
  EXPECT_EQ(box_xyxy.y2, 21);
}

TEST(nms, kpts_input)
{
  auto boxes = std::vector<box_xyxy>{ { 0, 0, 10, 10 }, { 10, 10, 21, 21 } };
  auto kpts = std::vector<kpt_xyv>();
  kpts.insert(kpts.end(), 17, { 0, 0, 0.0 });
  kpts.insert(kpts.end(), 17, { 10, 10, 1.0 });

  auto scores = std::vector<float>{ 0.5f, 0.6f };
  auto ids = std::vector<int>{};
  auto meta = AxMetaKptsDetection(boxes, kpts, scores, ids, { 17, 3 });
  auto actual = non_max_suppression(meta, 0.5f, true, 1, false);

  EXPECT_EQ(actual.num_elements(), 1);
  auto box_xyxy = actual.get_box_xyxy(0);
  EXPECT_EQ(box_xyxy.x1, 10);
  EXPECT_EQ(box_xyxy.y1, 10);
  EXPECT_EQ(box_xyxy.x2, 21);
  EXPECT_EQ(box_xyxy.y2, 21);
  auto actual_kpts = actual.get_kpts();
  EXPECT_EQ(actual_kpts.size(), 17);
  EXPECT_TRUE(std::all_of(actual_kpts.begin(), actual_kpts.end(),
      [](const auto &kpt) { return kpt.x == 10; }));
}

TEST(nms, highest_scoring_overlapping_boxes_remains)
{
  auto boxes
      = std::vector<box_xyxy>{ { 0, 0, 10, 10 }, { 1, 1, 11, 11 }, { 1, 1, 10, 10 } };
  auto scores = std::vector<float>{ 0.5F, 0.6F, 0.4F };
  auto classes = std::vector<int>{ 1, 1, 1 };
  auto meta = AxMetaObjDetection(boxes, scores, classes);
  auto actual = non_max_suppression(meta, 0.5F, false, 300, false);
  EXPECT_EQ(actual.num_elements(), 1);
  EXPECT_FLOAT_EQ(actual.score(0), 0.6F);
  auto box_xyxy = actual.get_box_xyxy(0);
  EXPECT_EQ(box_xyxy.x1, 1);
  EXPECT_EQ(box_xyxy.y1, 1);
  EXPECT_EQ(box_xyxy.x2, 11);
  EXPECT_EQ(box_xyxy.y2, 11);
}
} // namespace
