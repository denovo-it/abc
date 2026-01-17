// Copyright Axelera AI, 2025
#include <algorithm>
#include <gmock/gmock.h>
#include <numeric>
#include "unittest_ax_common.h"

/**
 * Unit tests for AxTransformPaddingDequantize operator
 *
 * This operator has the following key features:
 * 1. Input padding/cropping functionality
 * 2. Dequantization of int8 to float values
 * 3. Optional transposition from NHWC to NCHW format
 * 4. Optional LUT-based vs. direct dequantization
 */
class TransformPaddingDequantizeTest : public ::testing::Test
{
  protected:
  int calculateSize(const std::vector<int> &dims)
  {
    return std::accumulate(dims.begin(), dims.end(), 1, std::multiplies<int>());
  }
};

// =============================================================================
// Basic Initialization and Error Handling Tests
// =============================================================================

TEST_F(TransformPaddingDequantizeTest, non_tensor_input)
{
  auto xform = Ax::LoadTransform("paddingdequantize", { { "dequant_scale", "0" } });

  // Test with empty input
  AxDataInterface inp_empty;
  EXPECT_THROW(xform->set_output_interface(inp_empty), std::runtime_error);

  // Test with video input
  AxVideoInterface inp_video{ {}, nullptr };
  EXPECT_THROW(xform->set_output_interface(inp_video), std::runtime_error);
}

TEST_F(TransformPaddingDequantizeTest, invalid_configurations)
{
  // Missing required parameters should throw
  EXPECT_THROW(Ax::LoadTransform("paddingdequantize", {}), std::runtime_error);

  // Test mismatch between dequant_scale and dequant_zeropoint sizes
  std::unordered_map<std::string, std::string> input_mismatch
      = { { "dequant_scale", "0.5,0.25" }, { "dequant_zeropoint", "1" } };
  EXPECT_THROW(Ax::LoadTransform("paddingdequantize", input_mismatch), std::logic_error);
}

// =============================================================================
// Dequantization Tests
// =============================================================================

TEST_F(TransformPaddingDequantizeTest, basic_dequantization)
{
  std::unordered_map<std::string, std::string> input = {
    { "dequant_scale", "0.5" },
    { "dequant_zeropoint", "0" },
    { "transpose", "0" },
    { "padding", "0,0,0,0,0,0,0,0" },
  };

  auto xform = Ax::LoadTransform("paddingdequantize", input);

  // Create a simple 2x2x2 tensor filled with values 0-7
  std::vector<int> dims = { 1, 2, 2, 2 };
  int size = calculateSize(dims);
  auto inp_data = std::vector<int8_t>(size);
  std::iota(inp_data.begin(), inp_data.end(), 0);

  auto out_data = std::vector<float>(size);
  AxTensorsInterface inp{ { dims, 1, inp_data.data() } };

  auto out = std::get<AxTensorsInterface>(xform->set_output_interface(inp));
  ASSERT_EQ(out.size(), 1);
  EXPECT_EQ(out[0].sizes, dims);
  EXPECT_EQ(out[0].bytes, 4); // float output

  out[0].data = out_data.data();
  Ax::MetaMap metadata;
  xform->transform(inp, out, 0, 1, metadata);

  // Expected output: scale * input_value
  for (int i = 0; i < size; ++i) {
    EXPECT_FLOAT_EQ(out_data[i], 0.5f * inp_data[i]);
  }
}

TEST_F(TransformPaddingDequantizeTest, multi_tensor_dequantization)
{
  std::unordered_map<std::string, std::string> input = {
    { "dequant_scale", "0.5,0.25" },
    { "dequant_zeropoint", "1,2" },
    { "transpose", "0" },
    { "padding", "0,0,0,0,0,0,0,0|0,0,0,0,0,0,0,0" },
  };

  auto xform = Ax::LoadTransform("paddingdequantize", input);

  std::vector<int> dims = { 1, 2, 3, 4 };
  int tensor_size = calculateSize(dims);
  int total_size = tensor_size * 2; // Two tensors

  auto inp_data = std::vector<int8_t>(total_size);
  std::iota(inp_data.begin(), inp_data.begin() + tensor_size, 0);
  std::iota(inp_data.begin() + tensor_size, inp_data.end(), 0);

  auto out_data = std::vector<float>(total_size);
  AxTensorsInterface inp{ { dims, 1, inp_data.data() },
    { dims, 1, inp_data.data() + tensor_size } };

  auto out = std::get<AxTensorsInterface>(xform->set_output_interface(inp));
  ASSERT_EQ(out.size(), 2);
  EXPECT_EQ(out[0].sizes, dims);
  EXPECT_EQ(out[1].sizes, dims);
  EXPECT_EQ(out[0].bytes, 4);
  EXPECT_EQ(out[1].bytes, 4);

  out[0].data = out_data.data();
  out[1].data = out_data.data() + tensor_size;
  Ax::MetaMap metadata;
  xform->transform(inp, out, 0, 1, metadata);

  // Create expected output and verify
  auto expected = std::vector<float>(total_size);
  std::iota(expected.begin(), expected.begin() + tensor_size, 0);
  std::iota(expected.begin() + tensor_size, expected.end(), 0);

  // Apply dequantization formulas: scale * (value - zeropoint)
  std::transform(expected.begin(), expected.begin() + tensor_size,
      expected.begin(), [](auto x) { return 0.5f * (x - 1.0f); });
  std::transform(expected.begin() + tensor_size, expected.end(),
      expected.begin() + tensor_size, [](auto x) { return 0.25f * (x - 2.0f); });

  EXPECT_EQ(expected, out_data);
}

// =============================================================================
// Transpose Tests
// =============================================================================

TEST_F(TransformPaddingDequantizeTest, basic_transpose)
{
  std::unordered_map<std::string, std::string> input = {
    { "dequant_scale", "1" },
    { "dequant_zeropoint", "0" },
    { "transpose", "1" },
    { "padding", "0,0,0,0,0,0,0,0" },
  };

  auto xform = Ax::LoadTransform("paddingdequantize", input);

  std::vector<int> dims = { 1, 2, 3, 4 };
  int size = calculateSize(dims);

  auto inp_data = std::vector<int8_t>(size);
  std::iota(inp_data.begin(), inp_data.end(), 0);

  auto out_data = std::vector<float>(size);
  AxTensorsInterface inp{ { dims, 1, inp_data.data() } };

  auto out = std::get<AxTensorsInterface>(xform->set_output_interface(inp));
  ASSERT_EQ(out.size(), 1);

  // Check that output shape is transposed from NHWC to NCHW
  EXPECT_EQ(out[0].sizes, std::vector<int>({ 1, 4, 2, 3 }));
  EXPECT_EQ(out[0].bytes, 4);

  out[0].data = out_data.data();
  Ax::MetaMap metadata;
  xform->transform(inp, out, 0, 1, metadata);

  // Expected transposed values - verified against the operator's implementation
  auto expected = std::vector<float>({ 0, 4, 8, 12, 16, 20, 1, 5, 9, 13, 17, 21,
      2, 6, 10, 14, 18, 22, 3, 7, 11, 15, 19, 23 });

  EXPECT_EQ(expected, out_data);
}

TEST_F(TransformPaddingDequantizeTest, selective_transpose)
{
  // Test with different transpose settings for multiple tensors
  std::unordered_map<std::string, std::string> input = {
    { "dequant_scale", "1,1" },
    { "dequant_zeropoint", "0,0" },
    { "transpose", "1,0" }, // First tensor transposed, second not
    { "padding", "0,0,0,0,0,0,0,0|0,0,0,0,0,0,0,0" },
  };

  auto xform = Ax::LoadTransform("paddingdequantize", input);

  // Create two tensors with the same dimensions
  std::vector<int> dims = { 1, 2, 2, 2 };
  int tensor_size = calculateSize(dims);
  int total_size = tensor_size * 2;

  auto inp_data = std::vector<int8_t>(total_size);
  std::iota(inp_data.begin(), inp_data.end(), 0);

  AxTensorsInterface inp{ { dims, 1, inp_data.data() },
    { dims, 1, inp_data.data() + tensor_size } };

  auto out = std::get<AxTensorsInterface>(xform->set_output_interface(inp));
  ASSERT_EQ(out.size(), 2);

  // First tensor should be transposed, second should not
  EXPECT_EQ(out[0].sizes, std::vector<int>({ 1, 2, 2, 2 }));
  EXPECT_EQ(out[1].sizes, std::vector<int>({ 1, 2, 2, 2 }));

  auto out_data = std::vector<float>(total_size);
  out[0].data = out_data.data();
  out[1].data = out_data.data() + tensor_size;

  Ax::MetaMap metadata;
  xform->transform(inp, out, 0, 1, metadata);

  // Verify first tensor (transposed) values
  // For a 1x2x2x2 tensor with data [0,1,2,3,4,5,6,7], after NHWC->NCHW
  // transpose. The NHWC to NCHW transformation swaps dimensions: H and C, then
  // W and C This results in: [0,2,4,6,1,3,5,7]
  auto expected1 = std::vector<float>({ 0, 2, 4, 6, 1, 3, 5, 7 });
  for (size_t i = 0; i < expected1.size(); ++i) {
    EXPECT_FLOAT_EQ(out_data[i], expected1[i]);
  }

  // Verify second tensor (not transposed) values
  for (int i = 0; i < tensor_size; ++i) {
    EXPECT_FLOAT_EQ(out_data[i + tensor_size], static_cast<float>(i + tensor_size));
  }
}

// =============================================================================
// Padding Tests
// =============================================================================

TEST_F(TransformPaddingDequantizeTest, padding_and_dequant)
{
  std::unordered_map<std::string, std::string> input = {
    { "dequant_scale", "0.5" }, { "dequant_zeropoint", "1" }, { "transpose", "1" },
    { "padding", "0,0,0,0,0,0,0,-1" }, // Crop last element of width
  };

  auto xform = Ax::LoadTransform("paddingdequantize", input);

  std::vector<int> dims = { 1, 2, 3, 4 };
  int size = calculateSize(dims);

  auto inp_data = std::vector<int8_t>(size);
  std::iota(inp_data.begin(), inp_data.end(), 0);

  std::vector<int> out_dims = { 1, 3, 2, 3 }; // After transpose and cropping
  int out_size = calculateSize(out_dims);

  auto out_data = std::vector<float>(out_size);
  AxTensorsInterface inp{ { dims, 1, inp_data.data() } };

  auto out = std::get<AxTensorsInterface>(xform->set_output_interface(inp));
  ASSERT_EQ(out.size(), 1);
  EXPECT_EQ(out[0].sizes, out_dims);
  EXPECT_EQ(out[0].bytes, 4);

  out[0].data = out_data.data();
  Ax::MetaMap metadata;
  xform->transform(inp, out, 0, 1, metadata);

  // Expected cropped and transposed values with dequantization
  auto expected = std::vector<float>({ -0.5, 1.5, 3.5, 5.5, 7.5, 9.5, 0, 2, 4,
      6, 8, 10, 0.5, 2.5, 4.5, 6.5, 8.5, 10.5 });

  EXPECT_EQ(expected, out_data);
}

// =============================================================================
// LUT vs Direct Dequantization Tests
// =============================================================================

TEST_F(TransformPaddingDequantizeTest, dequantize_without_lut)
{
  std::unordered_map<std::string, std::string> input = {
    { "dequant_scale", "0.5" }, { "dequant_zeropoint", "1" }, { "transpose", "1" },
    { "padding", "0,0,0,0,0,0,0,-1" }, { "dequant_lut", "0" }, // Don't use LUT
  };

  auto xform = Ax::LoadTransform("paddingdequantize", input);

  std::vector<int> dims = { 1, 2, 3, 4 };
  int size = calculateSize(dims);

  auto inp_data = std::vector<int8_t>(size);
  std::iota(inp_data.begin(), inp_data.end(), 0);

  auto out_data = std::vector<float>(1 * 3 * 2 * 3);
  AxTensorsInterface inp{ { dims, 1, inp_data.data() } };

  auto out = std::get<AxTensorsInterface>(xform->set_output_interface(inp));
  ASSERT_EQ(out.size(), 1);
  EXPECT_EQ(out[0].sizes, std::vector<int>({ 1, 3, 2, 3 }));
  EXPECT_EQ(out[0].bytes, 4);

  out[0].data = out_data.data();
  Ax::MetaMap metadata;
  xform->transform(inp, out, 0, 1, metadata);

  // Expected: should match test_padding_transform_dequantize
  auto expected = std::vector<float>({ -0.5, 1.5, 3.5, 5.5, 7.5, 9.5, 0, 2, 4,
      6, 8, 10, 0.5, 2.5, 4.5, 6.5, 8.5, 10.5 });

  EXPECT_EQ(expected, out_data);
}

// =============================================================================
// Edge Cases
// =============================================================================

TEST_F(TransformPaddingDequantizeTest, extreme_values)
{
  std::unordered_map<std::string, std::string> input = {
    { "dequant_scale", "0.5" },
    { "dequant_zeropoint", "0" },
    { "transpose", "0" },
    { "padding", "0,0,0,0,0,0,0,0" },
  };

  auto xform = Ax::LoadTransform("paddingdequantize", input);

  std::vector<int> dims = { 1, 1, 2, 2 };
  int size = calculateSize(dims);

  auto inp_data = std::vector<int8_t>{ INT8_MIN, INT8_MAX, 0, -1 };
  auto out_data = std::vector<float>(size);

  AxTensorsInterface inp{ { dims, 1, inp_data.data() } };
  auto out = std::get<AxTensorsInterface>(xform->set_output_interface(inp));
  out[0].data = out_data.data();

  Ax::MetaMap metadata;
  xform->transform(inp, out, 0, 1, metadata);

  // Expected: scale * value
  auto expected = std::vector<float>{ 0.5f * INT8_MIN, 0.5f * INT8_MAX, 0.0f, -0.5f };

  EXPECT_THAT(out_data, testing::Pointwise(testing::FloatEq(), expected));
}

TEST_F(TransformPaddingDequantizeTest, empty_padding_vector)
{
  std::unordered_map<std::string, std::string> input = {
    { "dequant_scale", "1.0" }, { "dequant_zeropoint", "0" },
    // No padding specified - should cause error
  };

  auto xform = Ax::LoadTransform("paddingdequantize", input);

  std::vector<int> dims = { 1, 2, 2, 2 };
  int size = calculateSize(dims);

  auto inp_data = std::vector<int8_t>(size);
  std::iota(inp_data.begin(), inp_data.end(), 0);

  AxTensorsInterface inp{ { dims, 1, inp_data.data() } };

  // Should fail with runtime error about missing padding
  EXPECT_THROW(xform->set_output_interface(inp), std::runtime_error);
}
