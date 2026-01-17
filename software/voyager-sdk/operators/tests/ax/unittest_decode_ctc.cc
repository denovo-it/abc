// Copyright Axelera AI, 2025
#include "gtest/gtest.h"
#include <gmodule.h>
#include "gmock/gmock.h"
#include "unittest_ax_common.h"

#include <algorithm> // for std::find
#include <cstdlib> // For rand()
#include <fstream>
#include <iterator> // for std::distance
#include <memory>
#include <numeric>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

#include <filesystem>
#include "AxDataInterface.h"
#include "AxLog.hpp"
#include "AxMeta.hpp"
#include "AxMetaLicensePlate.hpp"

namespace fs = std::filesystem;

namespace
{

// Helper function to get label from AxLicensePlateMeta
std::string
get_license_plate_text(const AxLicensePlateMeta *meta)
{
  auto extern_meta_list = meta->get_extern_meta();
  for (const auto &meta_item : extern_meta_list) {
    if (std::string(meta_item.subtype) == "label") {
      // Directly create string from potentially multi-byte char data
      return std::string(meta_item.meta, meta_item.meta_size);
    }
  }
  return "";
}

// Helper function to check if a meta object exists and is of the expected type
bool
check_meta_exists(const std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> &map,
    const std::string &meta_key, const std::string &expected_text = "")
{
  auto position = map.find(meta_key);
  if (position == map.end()) {
    return false;
  }

  auto *meta = position->second.get();
  if (meta == nullptr) {
    return false;
  }

  auto *license_plate_meta = dynamic_cast<AxLicensePlateMeta *>(meta);
  if (license_plate_meta == nullptr) {
    // Check if it's the expected type
    return false;
  }

  // If expected_text is provided, check if the license plate text matches
  if (!expected_text.empty()) {
    return get_license_plate_text(license_plate_meta) == expected_text;
  }

  return true; // Type matches, no text check needed
}

// Helper to create tensor with float data
template <typename T>
AxTensorsInterface
tensors_from_vector(std::vector<T> &data, std::vector<int> sizes)
{
  return {
    { std::move(sizes), sizeof(data[0]), data.data() },
  };
}

// Helper to create sample NHWC tensor (do_reduce_mean=true case)
// Now requires the actual blank_index used in the char list
std::vector<float>
create_nhwc_tensor(int batch_size, int height, int width, int channels,
    const std::vector<int> &max_indices, int blank_index)
{
  size_t total_elements = static_cast<size_t>(batch_size) * height * width * channels;
  if (total_elements == 0)
    return {}; // Handle zero size case
  std::vector<float> data(total_elements, 0.0f);

  for (int h = 0; h < height; h++) {
    for (int w = 0; w < width; w++) {
      int max_index = (w < max_indices.size()) ? max_indices[w] : blank_index;
      // Ensure blank_index is valid within the context of the loop
      if (blank_index < 0 || blank_index >= channels) {
        // If blank index is invalid, default to index 0 or handle error
        max_index = (w < max_indices.size()) ? max_indices[w] : 0;
      }

      for (int c = 0; c < channels; c++) {
        float value = (c == max_index) ? 10.0f : 0.1f;
        // Calculate flat index for NHWC layout
        size_t idx = static_cast<size_t>(h) * width * channels
                     + static_cast<size_t>(w) * channels + c;
        if (idx < data.size()) { // Bounds check
          data[idx] = value;
        } else {
          // This should not happen if total_elements calculation is correct
          // Add error handling or logging if needed
        }
      }
    }
  }
  return data;
}

// Struct to hold result of creating chars file
struct CharsFileInfo {
  std::string filename;
  int expected_blank_index = -1;
  int num_chars = 0; // Total number of labels including blank
};

// Test fixture for decode_ctc tests
class DecodeCTCTest : public ::testing::Test
{
  protected:
  std::string m_meta_key = "license_plate";
  std::vector<fs::path> m_temp_files; // Keep track of created files

  // Default characters and expected text for basic tests
  std::vector<std::string> m_default_chars = { "A", "B", "C", "1", "2", "3" };
  std::string m_default_expected_text = "ABC123";
  std::vector<int> m_default_max_indices = { 0, 1, 2, 3, 4, 5 };

  // Test data (will be filled by setup methods)
  std::vector<float> m_tensor_data;
  std::vector<int> m_tensor_shape;
  AxTensorsInterface m_tensors;
  AxVideoInterface m_video_info{ { 640, 480, 640, 0, AxVideoFormat::RGB }, nullptr };

  void SetUp() override
  {
    // Seed random generator for unique filenames
    srand(time(nullptr));
  }

  void TearDown() override
  {
    // Remove all created temp files
    for (const auto &path : m_temp_files) {
      if (fs::exists(path)) {
        try {
          fs::remove(path);
        } catch (...) { /* Ignore cleanup errors */
        }
      }
    }
    m_temp_files.clear();
  }

  // Creates a temporary character file.
  // blank_representation: "", "-", or "NONE" (or any other string not matching "" or "-")
  CharsFileInfo create_chars_file(const std::vector<std::string> &chars,
      const std::string &blank_representation = "",
      const std::string &filename_prefix = "test_ctc_chars_")
  {
    fs::path temp_dir = fs::temp_directory_path();
    fs::path unique_path = temp_dir
                           / (filename_prefix + std::to_string(time(0)) + "_"
                               + std::to_string(rand()) + ".txt");
    m_temp_files.push_back(unique_path);

    std::ofstream file(unique_path);
    if (!file.is_open()) {
      throw std::runtime_error("Failed to open file for writing: " + unique_path.string());
    }

    std::vector<std::string> final_chars = chars;
    int blank_idx = -1;

    // Add the blank token representation if specified as "" or "-"
    if (blank_representation == "" || blank_representation == "-") {
      final_chars.push_back(blank_representation);
      blank_idx = final_chars.size() - 1; // It's now the last element
    }

    // Write characters to file
    for (const auto &s : final_chars) {
      file << s << std::endl;
    }
    file.close();

    return { unique_path.string(), blank_idx, (int) final_chars.size() };
  }

  // Setup for NHWC (4D) - used for do_reduce_mean=true
  void setup_nhwc_tensor(const std::vector<int> &max_indices,
      int channels, // Total number of labels including blank
      int blank_index, // The actual blank index
      int num_heads = 1)
  {
    int batch_size = 1;
    int height = num_heads;
    int width = 20; // Sequence length (positions)

    // Ensure channels is positive
    ASSERT_GT(channels, 0) << "Number of channels must be positive.";

    m_tensor_data = create_nhwc_tensor(
        batch_size, height, width, channels, max_indices, blank_index);
    m_tensor_shape = { batch_size, height, width, channels };

    m_tensors = tensors_from_vector(m_tensor_data, m_tensor_shape);
  }

  // Setup for 3D ([Slice, C, W]) - used for do_reduce_mean=false
  void setup_3d_tensor(const std::vector<int> &max_indices,
      int channels, // Total number of labels including blank
      int blank_index // The actual blank index
  )
  {
    int num_slices = 1;
    int chars_count = channels; // C dimension (index 1)
    int positions = 20; // W dimension (index 2)

    // Ensure channels is positive
    ASSERT_GT(chars_count, 0) << "Number of channels must be positive.";

    std::vector<float> data(num_slices * chars_count * positions, 0.0f);

    for (int ch = 0; ch < chars_count; ++ch) {
      for (int pos = 0; pos < positions; ++pos) {
        int max_char_for_this_pos = (pos < max_indices.size()) ? max_indices[pos] : blank_index;
        // Ensure blank_index is valid
        if (blank_index < 0 || blank_index >= chars_count) {
          max_char_for_this_pos = (pos < max_indices.size()) ? max_indices[pos] : 0;
        }

        float value = (ch == max_char_for_this_pos) ? 10.0f : 0.1f;

        size_t idx = static_cast<size_t>(ch) * positions + pos; // Flat index for slice 0
        if (idx < data.size()) { // Bounds check
          data[idx] = value;
        }
      }
    }

    m_tensor_data = data;
    m_tensor_shape = { 1, num_slices, chars_count, positions };
    m_tensors = tensors_from_vector(m_tensor_data, m_tensor_shape);
  }

  // Helper to create properties map, optionally adding blank_index
  std::unordered_map<std::string, std::string> create_properties(
      const std::string &chars_file, bool use_reduce_mean,
      int configured_blank_index = -1 // Optional: set to configure blank_index
  )
  {
    std::unordered_map<std::string, std::string> props = { { "meta_key", m_meta_key },
      { "task_category", "LicensePlateRecognition" }, { "chars_file", chars_file },
      { "do_reduce_mean", use_reduce_mean ? "1" : "0" } };
    if (configured_blank_index >= 0) {
      props["blank_index"] = std::to_string(configured_blank_index);
    }
    return props;
  }
};

//======== Basic Tests (Adapted) ========

TEST_F(DecodeCTCTest, nhwc_layout_with_reduce_mean)
{
  auto chars_info = create_chars_file(m_default_chars, ""); // Use "" as blank
  setup_nhwc_tensor(m_default_max_indices, chars_info.num_chars, chars_info.expected_blank_index);
  auto properties = create_properties(chars_info.filename, true);

  auto decoder = Ax::LoadDecode("ctc", properties);
  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> meta_map{};
  decoder->decode_to_meta(m_tensors, 0, 1, meta_map, m_video_info);

  ASSERT_TRUE(check_meta_exists(meta_map, m_meta_key, m_default_expected_text));
}

TEST_F(DecodeCTCTest, nhwc_layout_multi_heads_with_reduce_mean)
{
  auto chars_info = create_chars_file(m_default_chars, ""); // Use "" as blank
  setup_nhwc_tensor(m_default_max_indices, chars_info.num_chars,
      chars_info.expected_blank_index, 3);
  auto properties = create_properties(chars_info.filename, true);

  auto decoder = Ax::LoadDecode("ctc", properties);
  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> meta_map{};
  decoder->decode_to_meta(m_tensors, 0, 1, meta_map, m_video_info);

  ASSERT_TRUE(check_meta_exists(meta_map, m_meta_key, m_default_expected_text));
}
#if 1
TEST_F(DecodeCTCTest, three_dimensional_tensor_without_reduce_mean)
{
  auto chars_info = create_chars_file(m_default_chars, ""); // Use "" as blank
  setup_3d_tensor(m_default_max_indices, chars_info.num_chars, chars_info.expected_blank_index);
  auto properties = create_properties(chars_info.filename, false);

  auto decoder = Ax::LoadDecode("ctc", properties);
  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> meta_map{};
  decoder->decode_to_meta(m_tensors, 0, 1, meta_map, m_video_info);

  ASSERT_TRUE(check_meta_exists(meta_map, m_meta_key, m_default_expected_text));
}
#endif

//======== Blank Index Tests (New) ========

TEST_F(DecodeCTCTest, BlankIndexDetectEmptyString)
{
  auto chars_info = create_chars_file(m_default_chars, ""); // Blank is ""
  ASSERT_NE(chars_info.expected_blank_index, -1);
  setup_nhwc_tensor(m_default_max_indices, chars_info.num_chars, chars_info.expected_blank_index);
  auto properties = create_properties(chars_info.filename, true); // Don't configure blank_index

  auto decoder = Ax::LoadDecode("ctc", properties);
  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> meta_map{};
  // Should decode correctly by detecting ""
  ASSERT_NO_THROW(decoder->decode_to_meta(m_tensors, 0, 1, meta_map, m_video_info));
  ASSERT_TRUE(check_meta_exists(meta_map, m_meta_key, m_default_expected_text));
}

TEST_F(DecodeCTCTest, BlankIndexDetectHyphenFallback)
{
  auto chars_info = create_chars_file(m_default_chars, "-"); // Blank is "-", no ""
  ASSERT_NE(chars_info.expected_blank_index, -1);
  setup_nhwc_tensor(m_default_max_indices, chars_info.num_chars, chars_info.expected_blank_index);
  auto properties = create_properties(chars_info.filename, true); // Don't configure blank_index

  auto decoder = Ax::LoadDecode("ctc", properties);
  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> meta_map{};
  // Should decode correctly by falling back to detecting "-"
  ASSERT_NO_THROW(decoder->decode_to_meta(m_tensors, 0, 1, meta_map, m_video_info));
  ASSERT_TRUE(check_meta_exists(meta_map, m_meta_key, m_default_expected_text));
}

TEST_F(DecodeCTCTest, BlankIndexConfiguredOverride)
{
  // Create file with BOTH "" and "-"
  std::vector<std::string> chars_with_both = m_default_chars;
  chars_with_both.push_back(""); // Add "" first
  chars_with_both.push_back("-"); // Add "-" second
  int hyphen_idx = static_cast<int>(chars_with_both.size()) - 1; // Index of "-"

  auto chars_info = create_chars_file(chars_with_both, "NONE", "test_chars_both_"); // Write as is
  ASSERT_EQ(chars_info.expected_blank_index, -1); // No blank added by helper
  ASSERT_EQ(chars_info.num_chars, m_default_chars.size() + 2);

  // Setup tensor to use HYPHEN as the intended blank
  setup_nhwc_tensor(m_default_max_indices, chars_info.num_chars, hyphen_idx);
  // Configure blank_index explicitly to the HYPHEN index
  auto properties = create_properties(chars_info.filename, true, hyphen_idx);

  auto decoder = Ax::LoadDecode("ctc", properties);
  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> meta_map{};
  // Should decode correctly using the CONFIGURED hyphen index, ignoring the empty string
  ASSERT_NO_THROW(decoder->decode_to_meta(m_tensors, 0, 1, meta_map, m_video_info));
  ASSERT_TRUE(check_meta_exists(meta_map, m_meta_key, m_default_expected_text));
}

TEST_F(DecodeCTCTest, BlankIndexConfiguredInvalid)
{
  auto chars_info = create_chars_file(m_default_chars, ""); // File is valid
  auto properties = create_properties(chars_info.filename, true,
      chars_info.num_chars + 5); // Out of bounds index

  // Expect init to throw because configured index is invalid
  ASSERT_THROW(Ax::LoadDecode("ctc", properties), std::runtime_error);
}

TEST_F(DecodeCTCTest, BlankIndexNotFound)
{
  // Create file with neither "" nor "-"
  auto chars_info = create_chars_file(m_default_chars, "NONE");
  auto properties = create_properties(chars_info.filename, true); // Don't configure

  // Expect init to throw because blank cannot be determined
  ASSERT_THROW(Ax::LoadDecode("ctc", properties), std::runtime_error);
}

TEST_F(DecodeCTCTest, BlankIndexMultipleHyphens)
{
  // Create file with multiple "-" but no ""
  std::vector<std::string> chars_multi_hyphen = m_default_chars;
  chars_multi_hyphen.push_back("-"); // First hyphen
  int first_hyphen_idx = static_cast<int>(chars_multi_hyphen.size()) - 1;
  chars_multi_hyphen.push_back("X"); // Separator
  chars_multi_hyphen.push_back("-"); // Second hyphen

  auto chars_info = create_chars_file(chars_multi_hyphen, "NONE", "test_chars_multi_hyphen_");
  ASSERT_EQ(chars_info.num_chars, m_default_chars.size() + 3);

  // Setup tensor to use the FIRST hyphen as the intended blank
  setup_nhwc_tensor(m_default_max_indices, chars_info.num_chars, first_hyphen_idx);
  auto properties = create_properties(chars_info.filename, true); // Don't configure blank_index

  auto decoder = Ax::LoadDecode("ctc", properties); // Warning expected in logs here
  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> meta_map{};
  // Should decode correctly using the FIRST hyphen index
  ASSERT_NO_THROW(decoder->decode_to_meta(m_tensors, 0, 1, meta_map, m_video_info));
  ASSERT_TRUE(check_meta_exists(meta_map, m_meta_key, m_default_expected_text));
}

//======== UTF-8 Test (New) ========

TEST_F(DecodeCTCTest, DecodeUTF8)
{
  // Use Chinese characters + alphanumeric
  std::vector<std::string> utf8_chars = { "京", "A", "B", "1", "2" };
  std::string expected_utf8_text = "京AB12";
  std::vector<int> utf8_max_indices = { 0, 1, 2, 3, 4 };

  auto chars_info = create_chars_file(utf8_chars, "-", "test_chars_utf8_"); // Use "-" as blank
  ASSERT_NE(chars_info.expected_blank_index, -1);

  setup_nhwc_tensor(utf8_max_indices, chars_info.num_chars, chars_info.expected_blank_index);
  auto properties = create_properties(chars_info.filename, true); // Don't configure, let it find "-"

  auto decoder = Ax::LoadDecode("ctc", properties);
  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> meta_map{};
  ASSERT_NO_THROW(decoder->decode_to_meta(m_tensors, 0, 1, meta_map, m_video_info));

  // Verify the decoded string matches the expected multi-byte string
  ASSERT_TRUE(check_meta_exists(meta_map, m_meta_key, expected_utf8_text));
}

//======== Error Handling Tests (Adapted) ========

TEST_F(DecodeCTCTest, invalid_current_frame)
{
  auto chars_info = create_chars_file(m_default_chars, "");
  setup_nhwc_tensor(m_default_max_indices, chars_info.num_chars, chars_info.expected_blank_index);
  auto properties = create_properties(chars_info.filename, true);
  auto decoder = Ax::LoadDecode("ctc", properties);
  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> meta_map{};
  ASSERT_THROW(decoder->decode_to_meta(m_tensors, 1, 1, meta_map, m_video_info),
      std::runtime_error);
}

TEST_F(DecodeCTCTest, empty_tensor_list)
{
  auto chars_info = create_chars_file(m_default_chars, "");
  auto properties = create_properties(chars_info.filename, true);
  auto decoder = Ax::LoadDecode("ctc", properties);
  AxTensorsInterface empty_tensors{};
  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> meta_map{};
  ASSERT_THROW(decoder->decode_to_meta(empty_tensors, 0, 1, meta_map, m_video_info),
      std::runtime_error);
}

TEST_F(DecodeCTCTest, non_float_tensor)
{
  auto chars_info = create_chars_file(m_default_chars, "");
  std::vector<int8_t> int_data(1 * 1 * 20 * chars_info.num_chars, 1);
  std::vector<int> shape = { 1, 1, 20, chars_info.num_chars }; // NHWC
  auto int_tensors = tensors_from_vector(int_data, shape);
  auto properties = create_properties(chars_info.filename, true);
  auto decoder = Ax::LoadDecode("ctc", properties);
  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> meta_map{};
  ASSERT_THROW(decoder->decode_to_meta(int_tensors, 0, 1, meta_map, m_video_info),
      std::runtime_error);
}

//======== Edge Case Tests (Adapted) ========

TEST_F(DecodeCTCTest, null_tensor_data)
{
  auto chars_info = create_chars_file(m_default_chars, "");
  setup_nhwc_tensor(m_default_max_indices, chars_info.num_chars, chars_info.expected_blank_index);
  m_tensors[0].data = nullptr; // Manually set data to null
  auto properties = create_properties(chars_info.filename, true);
  auto decoder = Ax::LoadDecode("ctc", properties);
  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> meta_map{};
  ASSERT_THROW(decoder->decode_to_meta(m_tensors, 0, 1, meta_map, m_video_info),
      std::runtime_error);
}

TEST_F(DecodeCTCTest, zero_positions_dimension) // W=0
{
  auto chars_info = create_chars_file(m_default_chars, "");
  int batch_size = 1;
  int height = 1;
  int width = 0; // Zero positions
  int channels = chars_info.num_chars;

  m_tensor_data = create_nhwc_tensor(
      batch_size, height, width, channels, {}, chars_info.expected_blank_index);
  m_tensor_shape = { batch_size, height, width, channels };
  m_tensors = tensors_from_vector(m_tensor_data, m_tensor_shape);

  auto properties = create_properties(chars_info.filename, true);
  auto decoder = Ax::LoadDecode("ctc", properties);
  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> meta_map{};
  ASSERT_THROW(decoder->decode_to_meta(m_tensors, 0, 1, meta_map, m_video_info),
      std::runtime_error);
}

TEST_F(DecodeCTCTest, zero_chars_dimension_3d) // C=0
{
  // Note: create_chars_file helper adds blank if specified, so need manual setup
  auto chars_info = create_chars_file({}, "NONE"); // Empty chars list
  ASSERT_EQ(chars_info.num_chars, 0);

  int num_slices = 1;
  int chars_count = 0; // Zero characters
  int positions = 20;

  std::vector<float> data; // Empty data
  m_tensor_shape = { num_slices, chars_count, positions };
  m_tensors = tensors_from_vector(data, m_tensor_shape);

  auto properties = create_properties(chars_info.filename, false);
  // Init should fail because chars list loaded from file is empty
  ASSERT_THROW(Ax::LoadDecode("ctc", properties), std::runtime_error);
}
//======== Configuration Tests (Adapted) ========

TEST_F(DecodeCTCTest, custom_meta_key)
{
  auto chars_info = create_chars_file(m_default_chars, "");
  setup_nhwc_tensor(m_default_max_indices, chars_info.num_chars, chars_info.expected_blank_index);
  std::string custom_meta_key = "custom_lpr";
  auto properties = create_properties(chars_info.filename, true);
  properties["meta_key"] = custom_meta_key;

  auto decoder = Ax::LoadDecode("ctc", properties);
  std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> meta_map{};
  decoder->decode_to_meta(m_tensors, 0, 1, meta_map, m_video_info);
  ASSERT_TRUE(check_meta_exists(meta_map, custom_meta_key, m_default_expected_text));
}

TEST_F(DecodeCTCTest, replace_existing_meta)
{
  auto chars_info = create_chars_file(m_default_chars, "");
  setup_nhwc_tensor(m_default_max_indices, chars_info.num_chars, chars_info.expected_blank_index);

  std::string meta_key = m_meta_key;
  Ax::MetaMap meta_map;
  std::string initial_text = "INITIAL";
  meta_map[meta_key] = std::make_unique<AxLicensePlateMeta>(initial_text);
  ASSERT_TRUE(check_meta_exists(meta_map, meta_key, initial_text));

  auto properties = create_properties(chars_info.filename, true);
  auto decoder = Ax::LoadDecode("ctc", properties);
  decoder->decode_to_meta(m_tensors, 0, 1, meta_map, m_video_info);
  ASSERT_TRUE(check_meta_exists(meta_map, meta_key, m_default_expected_text));
}

} // namespace
