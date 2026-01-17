// Copyright Axelera AI, 2025
#include "gtest/gtest.h"
#include <gmodule.h>
#include "gmock/gmock.h"
#include "unittest_ax_common.h"

#include <cstring>
#include <memory>
#include <numeric>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

#include "AxDataInterface.h"
#include "AxLog.hpp"
#include "AxMeta.hpp"
#include "AxMetaRawTensor.hpp"

namespace
{

// Helper function to check if a meta object exists and is of the expected type
bool
check_meta_exists(const std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> &map,
    const std::string &meta_key)
{
  auto position = map.find(meta_key);
  if (position == map.end()) {
    return false;
  }
  // Also check if the pointer is valid and if it can be cast to the expected type
  auto *base_ptr = position->second.get();
  if (base_ptr == nullptr) {
    return false;
  }
  auto *derived_ptr = dynamic_cast<AxMetaRawTensor *>(base_ptr);
  return derived_ptr != nullptr;
}

template <typename T>
AxTensorsInterface
tensors_from_vector(std::vector<T> &tensor_data, std::vector<int> sizes)
{
  return {
    { sizes, static_cast<int>(sizeof(T)), tensor_data.data() },
  };
}

AxTensorsInterface
tensors_from_int8_vector(std::vector<int8_t> &tensor_data, std::vector<int> sizes)
{
  return {
    { sizes, static_cast<int>(sizeof(int8_t)), tensor_data.data() },
  };
}

AxTensorsInterface
tensors_from_int16_vector(std::vector<int16_t> &tensor_data, std::vector<int> sizes)
{
  return {
    { sizes, static_cast<int>(sizeof(int16_t)), tensor_data.data() },
  };
}

AxTensorsInterface
tensors_from_float64_vector(std::vector<double> &tensor_data, std::vector<int> sizes)
{
  return {
    { sizes, static_cast<int>(sizeof(double)), tensor_data.data() },
  };
}

class DecodeToRawTensorTest : public ::testing::Test
{
  protected:
  std::vector<float> m_tensor_data1;
  std::vector<float> m_tensor_data2;
  std::vector<int> m_tensor_shape1 = { 1, 2, 3, 4 }; // Example shape 1*2*3*4 = 24 elements
  std::vector<int> m_tensor_shape2 = { 1, 5, 5 }; // Example shape 1*5*5 = 25 elements
  std::string m_meta_key = "TensorMeta"; // Default key

  // Keep video info as it's part of the API call signature
  AxVideoInterface m_video_info{ { 640, 480, 640, 0, AxVideoFormat::RGB }, nullptr };
  AxTensorsInterface m_tensors;

  // Expected dimensions converted to int64_t for comparison
  std::vector<int64_t> m_dims1;
  std::vector<int64_t> m_dims2;

  void SetUp() override
  {
    // Initialize tensor data 1
    m_tensor_data1.resize(1 * 2 * 3 * 4);
    std::iota(m_tensor_data1.begin(), m_tensor_data1.end(), 0.0f); // Fill with 0.0, 1.0, ...
    for (int size : m_tensor_shape1) {
      m_dims1.push_back(static_cast<int64_t>(size));
    }

    // Initialize tensor data 2
    m_tensor_data2.resize(1 * 5 * 5);
    std::iota(m_tensor_data2.begin(), m_tensor_data2.end(), 100.0f); // Fill with 100.0, 101.0, ...
    for (int size : m_tensor_shape2) {
      m_dims2.push_back(static_cast<int64_t>(size));
    }

    // By default, setup with one tensor
    m_tensors = tensors_from_vector(m_tensor_data1, m_tensor_shape1);
  }

  void SetupMultipleTensors()
  {
    m_tensors = tensors_from_vector(m_tensor_data1, m_tensor_shape1);
    auto tensor2_interface = tensors_from_vector(m_tensor_data2, m_tensor_shape2);
    m_tensors.push_back(std::move(tensor2_interface[0]));
  }

  template <typename T>
  void VerifyExternMeta(const std::vector<extern_meta> &metas,
      size_t tensor_index, const std::vector<T> &expected_data,
      const std::vector<int64_t> &expected_dims, const std::string &expected_dtype)
  {
    ASSERT_GE(metas.size(), (tensor_index + 1) * 3) << "Not enough entries in extern_meta vector";

    // Data
    const auto &data_meta = metas[tensor_index * 3];
    std::string expected_data_name = "data_" + std::to_string(tensor_index);
    ASSERT_STREQ(data_meta.type, "TensorMeta") << "Incorrect data meta type";
    ASSERT_STREQ(data_meta.subtype, expected_data_name.c_str())
        << "Incorrect data meta subtype (name)";
    ASSERT_EQ(data_meta.meta_size, expected_data.size() * sizeof(T))
        << "Incorrect data meta size";
    ASSERT_EQ(data_meta.meta_size % sizeof(T), 0) << "Data size not multiple of element size";
    size_t num_data_elements = data_meta.meta_size / sizeof(T);
    ASSERT_EQ(num_data_elements, expected_data.size()) << "Incorrect number of data elements";
    const T *data_ptr = reinterpret_cast<const T *>(data_meta.meta);
    for (size_t i = 0; i < num_data_elements; ++i) {
      ASSERT_EQ(data_ptr[i], expected_data[i]) << "Data mismatch at index " << i;
    }

    // Dims
    const auto &dims_meta = metas[tensor_index * 3 + 1];
    std::string expected_dims_name = "dims_" + std::to_string(tensor_index);
    ASSERT_STREQ(dims_meta.type, "TensorMeta") << "Incorrect dims meta type";
    ASSERT_STREQ(dims_meta.subtype, expected_dims_name.c_str())
        << "Incorrect dims meta subtype (name)";
    ASSERT_EQ(dims_meta.meta_size, expected_dims.size() * sizeof(int64_t))
        << "Incorrect dims meta size";
    ASSERT_EQ(dims_meta.meta_size % sizeof(int64_t), 0) << "Dims size not multiple of int64_t";
    size_t num_dims = dims_meta.meta_size / sizeof(int64_t);
    ASSERT_EQ(num_dims, expected_dims.size()) << "Incorrect number of dimensions";
    const int64_t *dims_ptr = reinterpret_cast<const int64_t *>(dims_meta.meta);
    for (size_t i = 0; i < num_dims; ++i) {
      ASSERT_EQ(dims_ptr[i], expected_dims[i]) << "Dimension mismatch at index " << i;
    }

    // Dtype
    const auto &dtype_meta = metas[tensor_index * 3 + 2];
    std::string expected_dtype_name = "dtype_" + std::to_string(tensor_index);
    ASSERT_STREQ(dtype_meta.type, "TensorMeta") << "Incorrect dtype meta type";
    ASSERT_STREQ(dtype_meta.subtype, expected_dtype_name.c_str())
        << "Incorrect dtype meta subtype (name)";
    ASSERT_EQ(dtype_meta.meta_size, expected_dtype.size()) << "Incorrect dtype meta size";
    std::string dtype_str(dtype_meta.meta, dtype_meta.meta + dtype_meta.meta_size);
    ASSERT_EQ(dtype_str, expected_dtype) << "Incorrect dtype string";
  }
};

TEST_F(DecodeToRawTensorTest, SingleFloatTensor)
{
  std::unordered_map<std::string, std::string> properties = { { "meta_key", m_meta_key } };
  auto decoder = Ax::LoadDecode("to_raw_tensor", properties);

  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> map{};
  decoder->decode_to_meta(m_tensors, 0, 1, map, m_video_info);

  ASSERT_TRUE(check_meta_exists(map, m_meta_key));

  auto *wrapper = dynamic_cast<AxMetaRawTensor *>(map[m_meta_key].get());
  ASSERT_NE(wrapper, nullptr);

  auto extern_metas = wrapper->get_extern_meta();
  ASSERT_EQ(extern_metas.size(), 3) << "Expected 3 meta entries (data, dims, dtype)";
  VerifyExternMeta<float>(extern_metas, 0, m_tensor_data1, m_dims1, "f4");
}

TEST_F(DecodeToRawTensorTest, MultipleFloatTensors)
{
  SetupMultipleTensors();

  std::unordered_map<std::string, std::string> properties = { { "meta_key", m_meta_key } };
  auto decoder = Ax::LoadDecode("to_raw_tensor", properties);

  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> map{};
  decoder->decode_to_meta(m_tensors, 0, 1, map, m_video_info);

  ASSERT_TRUE(check_meta_exists(map, m_meta_key));
  auto *wrapper = dynamic_cast<AxMetaRawTensor *>(map[m_meta_key].get());
  ASSERT_NE(wrapper, nullptr);

  auto extern_metas = wrapper->get_extern_meta();
  ASSERT_EQ(extern_metas.size(), 6)
      << "Expected 6 meta entries (data, dims, dtype for each tensor)";
  VerifyExternMeta<float>(extern_metas, 0, m_tensor_data1, m_dims1, "f4");
  VerifyExternMeta<float>(extern_metas, 1, m_tensor_data2, m_dims2, "f4");
}

TEST_F(DecodeToRawTensorTest, CustomMetaKey)
{
  std::string custom_key = "MyRawTensors";
  std::unordered_map<std::string, std::string> properties = { { "meta_key", custom_key } };
  auto decoder = Ax::LoadDecode("to_raw_tensor", properties);

  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> map{};
  decoder->decode_to_meta(m_tensors, 0, 1, map, m_video_info); // Uses single tensor from SetUp

  // Check using the custom key
  ASSERT_TRUE(check_meta_exists(map, custom_key));
  ASSERT_FALSE(check_meta_exists(map, m_meta_key)) << "Should not use default key";

  auto *wrapper = dynamic_cast<AxMetaRawTensor *>(map[custom_key].get());
  ASSERT_NE(wrapper, nullptr);

  auto extern_metas = wrapper->get_extern_meta();
  ASSERT_EQ(extern_metas.size(), 3);
  VerifyExternMeta<float>(extern_metas, 0, m_tensor_data1, m_dims1, "f4");
}

TEST_F(DecodeToRawTensorTest, EmptyInput)
{
  m_tensors.clear(); // No input tensors

  std::unordered_map<std::string, std::string> properties = { { "meta_key", m_meta_key } };
  auto decoder = Ax::LoadDecode("to_raw_tensor", properties);

  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> map{};
  decoder->decode_to_meta(m_tensors, 0, 1, map, m_video_info);

  // Meta should still be created, but empty
  ASSERT_TRUE(check_meta_exists(map, m_meta_key));
  auto *wrapper = dynamic_cast<AxMetaRawTensor *>(map[m_meta_key].get());
  ASSERT_NE(wrapper, nullptr);

  auto extern_metas = wrapper->get_extern_meta();
  ASSERT_TRUE(extern_metas.empty()) << "Extern meta should be empty for empty input";
}

TEST_F(DecodeToRawTensorTest, Int8Tensor)
{
  std::vector<int8_t> int8_data(20);
  std::iota(int8_data.begin(), int8_data.end(), 0);
  std::vector<int> int8_shape = { 1, 4, 5 };
  m_tensors = tensors_from_int8_vector(int8_data, int8_shape);
  std::vector<int64_t> int8_dims(int8_shape.begin(), int8_shape.end());

  std::unordered_map<std::string, std::string> properties = { { "meta_key", m_meta_key } };
  auto decoder = Ax::LoadDecode("to_raw_tensor", properties);

  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> map{};
  decoder->decode_to_meta(m_tensors, 0, 1, map, m_video_info);

  ASSERT_TRUE(check_meta_exists(map, m_meta_key));
  auto *wrapper = dynamic_cast<AxMetaRawTensor *>(map[m_meta_key].get());
  ASSERT_NE(wrapper, nullptr);

  auto extern_metas = wrapper->get_extern_meta();
  ASSERT_EQ(extern_metas.size(), 3);
  VerifyExternMeta<int8_t>(extern_metas, 0, int8_data, int8_dims, "i1");
}

TEST_F(DecodeToRawTensorTest, Int16Tensor)
{
  std::vector<int16_t> int16_data(12);
  std::iota(int16_data.begin(), int16_data.end(), 0);
  std::vector<int> int16_shape = { 2, 2, 3 };
  m_tensors = tensors_from_int16_vector(int16_data, int16_shape);
  std::vector<int64_t> int16_dims(int16_shape.begin(), int16_shape.end());

  std::unordered_map<std::string, std::string> properties = { { "meta_key", m_meta_key } };
  auto decoder = Ax::LoadDecode("to_raw_tensor", properties);

  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> map{};
  decoder->decode_to_meta(m_tensors, 0, 1, map, m_video_info);

  ASSERT_TRUE(check_meta_exists(map, m_meta_key));
  auto *wrapper = dynamic_cast<AxMetaRawTensor *>(map[m_meta_key].get());
  ASSERT_NE(wrapper, nullptr);

  auto extern_metas = wrapper->get_extern_meta();
  ASSERT_EQ(extern_metas.size(), 3);
  VerifyExternMeta<int16_t>(extern_metas, 0, int16_data, int16_dims, "i2");
}

TEST_F(DecodeToRawTensorTest, Float64Tensor)
{
  std::vector<double> float64_data(7);
  std::iota(float64_data.begin(), float64_data.end(), 0.0);
  std::vector<int> float64_shape = { 7 };
  m_tensors = tensors_from_float64_vector(float64_data, float64_shape);
  std::vector<int64_t> float64_dims(float64_shape.begin(), float64_shape.end());

  std::unordered_map<std::string, std::string> properties = { { "meta_key", m_meta_key } };
  auto decoder = Ax::LoadDecode("to_raw_tensor", properties);

  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> map{};
  decoder->decode_to_meta(m_tensors, 0, 1, map, m_video_info);

  ASSERT_TRUE(check_meta_exists(map, m_meta_key));
  auto *wrapper = dynamic_cast<AxMetaRawTensor *>(map[m_meta_key].get());
  ASSERT_NE(wrapper, nullptr);

  auto extern_metas = wrapper->get_extern_meta();
  ASSERT_EQ(extern_metas.size(), 3);
  VerifyExternMeta<double>(extern_metas, 0, float64_data, float64_dims, "f8");
}

TEST_F(DecodeToRawTensorTest, MixedTensors)
{
  // One float32, one int16, one int8
  std::vector<float> float_data(4, 1.5f);
  std::vector<int16_t> int16_data(4, 42);
  std::vector<int8_t> int8_data(4, -7);
  std::vector<int> shape = { 2, 2 };
  m_tensors.clear();
  m_tensors.push_back({ shape, static_cast<int>(sizeof(float)), float_data.data() });
  m_tensors.push_back({ shape, static_cast<int>(sizeof(int16_t)), int16_data.data() });
  m_tensors.push_back({ shape, static_cast<int>(sizeof(int8_t)), int8_data.data() });
  std::vector<int64_t> dims(shape.begin(), shape.end());

  std::unordered_map<std::string, std::string> properties = { { "meta_key", m_meta_key } };
  auto decoder = Ax::LoadDecode("to_raw_tensor", properties);

  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> map{};
  decoder->decode_to_meta(m_tensors, 0, 1, map, m_video_info);

  ASSERT_TRUE(check_meta_exists(map, m_meta_key));
  auto *wrapper = dynamic_cast<AxMetaRawTensor *>(map[m_meta_key].get());
  ASSERT_NE(wrapper, nullptr);

  auto extern_metas = wrapper->get_extern_meta();
  ASSERT_EQ(extern_metas.size(), 9);
  VerifyExternMeta<float>(extern_metas, 0, float_data, dims, "f4");
  VerifyExternMeta<int16_t>(extern_metas, 1, int16_data, dims, "i2");
  VerifyExternMeta<int8_t>(extern_metas, 2, int8_data, dims, "i1");
}

TEST_F(DecodeToRawTensorTest, SkipEmptyTensorData)
{
  // Create one valid tensor and one empty tensor
  m_tensors = tensors_from_vector(m_tensor_data1, m_tensor_shape1);
  std::vector<float> empty_data;
  std::vector<int> empty_shape = { 1, 0, 5 }; // Shape with a zero dimension
  auto empty_tensor_interface = tensors_from_vector(empty_data, empty_shape);
  m_tensors.push_back(std::move(empty_tensor_interface[0]));

  std::unordered_map<std::string, std::string> properties = { { "meta_key", m_meta_key } };
  auto decoder = Ax::LoadDecode("to_raw_tensor", properties);

  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> map{};
  decoder->decode_to_meta(m_tensors, 0, 1, map, m_video_info);

  ASSERT_TRUE(check_meta_exists(map, m_meta_key));
  auto *wrapper = dynamic_cast<AxMetaRawTensor *>(map[m_meta_key].get());
  ASSERT_NE(wrapper, nullptr);

  auto extern_metas = wrapper->get_extern_meta();
  // Only the first, valid tensor should be present
  ASSERT_EQ(extern_metas.size(), 3)
      << "Expected 3 meta entries (data0, dims0, dtype0) for the valid tensor";
  VerifyExternMeta<float>(extern_metas, 0, m_tensor_data1, m_dims1, "f4");
}

} // namespace
