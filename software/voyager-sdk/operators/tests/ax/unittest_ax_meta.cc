// Copyright Axelera AI, 2023
#include "gtest/gtest.h"
#include <gmodule.h>
#include "gmock/gmock.h"

#include <memory>
#include <stdexcept>
#include <string>
#include <unordered_map>

#include "AxMeta.hpp"
#include "AxMetaClassification.hpp"
#include "AxMetaObjectDetection.hpp"

TEST(ax_meta_base, insert_submeta)
{
  auto meta = AxMetaBase();
  auto submeta1 = std::make_shared<AxMetaBase>();
  auto submeta2 = std::make_shared<AxMetaBase>();
  auto submeta3 = std::make_shared<AxMetaBase>();

  EXPECT_NO_THROW(meta.insert_submeta("submeta", 1, 2, submeta1));
  EXPECT_NO_THROW(meta.insert_submeta("submeta", 0, 2, submeta2));
}

TEST(ax_meta_base, get_submeta)
{
  auto meta = AxMetaBase();
  auto submeta = std::make_shared<AxMetaObjDetection>();

  meta.insert_submeta("submeta", 0, 2, submeta);

  EXPECT_THROW(meta.get_submeta<AxMetaObjDetection>("submeta", 0, 1), std::runtime_error);
  EXPECT_THROW(meta.get_submeta<AxMetaObjDetection>("submeta", 1, 2), std::runtime_error);
  EXPECT_THROW(meta.get_submeta<AxMetaObjDetection>("non_existent", 0, 2), std::runtime_error);
  EXPECT_THROW(meta.get_submeta<AxMetaClassification>("submeta", 0, 2), std::runtime_error);
  EXPECT_NO_THROW(meta.get_submeta<AxMetaObjDetection>("submeta", 0, 2));
}

TEST(ax_meta_base, get_submetas)
{
  auto meta = AxMetaBase();
  auto submeta = std::make_shared<AxMetaObjDetection>();
  meta.insert_submeta("submeta", 1, 3, submeta);

  EXPECT_THROW(meta.get_submetas<AxMetaClassification>("submeta"), std::runtime_error);
  EXPECT_EQ(meta.get_submetas<AxMetaObjDetection>("submeta").size(), 3);
  EXPECT_EQ(meta.get_submetas<AxMetaObjDetection>("non_existent").size(), 0);
  EXPECT_EQ(meta.get_submetas<AxMetaObjDetection>("submeta")[0], nullptr);
  EXPECT_EQ(meta.get_submetas<AxMetaObjDetection>("submeta")[1], submeta.get());
  EXPECT_EQ(meta.get_submetas<AxMetaObjDetection>("submeta")[2], nullptr);
}
