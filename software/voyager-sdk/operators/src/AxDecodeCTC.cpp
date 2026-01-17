// Copyright Axelera AI, 2025
#include <unordered_set>

#include "AxMetaLicensePlate.hpp"
#include "AxOpUtils.hpp"

extern "C" const std::unordered_set<std::string> &
allowed_properties()
{
  static const std::unordered_set<std::string> allowed_properties{ "meta_key",
    "master_meta", "chars_file", "do_reduce_mean", "task_category", "blank_index" };
  return allowed_properties;
}

struct ctc_properties {
  std::string meta_key{};
  std::string master_meta{};
  std::vector<std::string> chars;
  bool do_reduce_mean = false;
  std::string task_category{};
  int blank_index = -1; // Added to store the detected blank token index
};

extern "C" std::shared_ptr<void>
init_and_set_static_properties(
    const std::unordered_map<std::string, std::string> &input, Ax::Logger &logger)
{
  std::shared_ptr<ctc_properties> prop = std::make_shared<ctc_properties>();

  prop->meta_key
      = Ax::get_property(input, "meta_key", "ctc_static_properties", prop->meta_key);

  auto chars_file_path = Ax::get_property(
      input, "chars_file", "ctc_static_properties", std::string{});

  // Ensure chars_file is provided
  if (chars_file_path.empty()) {
    logger(AX_ERROR) << "Required property 'chars_file' is missing.";
    throw std::runtime_error("'chars_file' must be provided for CTC decoding.");
  }

  // For LPR CTC, labels should NOT be trimmed, as the blank is typically empty.
  // Always call read_class_labels with trimmed = false.
  logger(AX_DEBUG) << "Reading class labels from: " << chars_file_path << " (trimmed=false)";
  auto charstrings = ax_utils::read_class_labels(
      chars_file_path, "ctc_static_properties", logger, /*trimmed=*/false);

  if (charstrings.empty()) {
    logger(AX_ERROR) << "Failed to read class labels or file is empty: " << chars_file_path;
    throw std::runtime_error("Could not load class labels from chars_file.");
  }

  // Debug: Log the size and first element read
  logger(AX_DEBUG)
      << "Read " << charstrings.size() << " labels. First label: \""
      << (charstrings.empty() ? "[EMPTY VECTOR]" : charstrings[0])
      << "\" (length: " << (charstrings.empty() ? 0 : charstrings[0].length()) << ")";

  prop->chars = std::move(charstrings);

  // --- Blank Index Handling ---
  prop->blank_index = -1; // Initialize

  // 1. Try to get blank_index from properties first.
  int configured_blank_index
      = Ax::get_property(input, "blank_index", "ctc_static_properties", -1);

  if (configured_blank_index >= 0) {
    logger(AX_INFO) << "Using configured blank_index: " << configured_blank_index;
    if (static_cast<size_t>(configured_blank_index) >= prop->chars.size()) {
      logger(AX_ERROR)
          << "Configured blank_index " << configured_blank_index
          << " is out of bounds for loaded labels (size: " << prop->chars.size() << ")";
      throw std::runtime_error("Configured blank_index is out of bounds.");
    }
    prop->blank_index = configured_blank_index;
  } else {
    // 2. If not configured, try to detect empty string "".
    logger(AX_INFO) << "blank_index not configured, attempting to detect empty string \"\".";
    auto it_empty = std::find(prop->chars.begin(), prop->chars.end(), "");
    if (it_empty != prop->chars.end()) {
      prop->blank_index = std::distance(prop->chars.begin(), it_empty);
      logger(AX_INFO) << "Detected empty string \"\" blank token at index: "
                      << prop->blank_index;
    } else {
      // 3. If "" not found, fall back to searching for "-".
      logger(AX_INFO) << "Empty string blank token not found, falling back to search for hyphen '-'.";
      auto it_hyphen = std::find(prop->chars.begin(), prop->chars.end(), "-");
      if (it_hyphen != prop->chars.end()) {
        prop->blank_index = std::distance(prop->chars.begin(), it_hyphen);
        logger(AX_INFO) << "Detected hyphen '-' blank token fallback at index: "
                        << prop->blank_index;
        // Check for multiple hyphens
        auto it_hyphen_next = std::find(it_hyphen + 1, prop->chars.end(), "-");
        if (it_hyphen_next != prop->chars.end()) {
          logger(AX_WARN) << "Multiple hyphen '-' entries found in label file. Using the first one at index "
                          << prop->blank_index
                          << ". This might indicate an issue with the label file.";
        }
      }
    }
  }

  // 4. Final check: If no blank index found by any method, error out.
  if (prop->blank_index < 0) {
    std::string first_few_labels = "[";
    for (size_t i = 0; i < std::min((size_t) 5, prop->chars.size()); ++i) {
      first_few_labels += "\"" + prop->chars[i] + "\"(len="
                          + std::to_string(prop->chars[i].length()) + "), ";
    }
    first_few_labels += "...]";
    logger(AX_ERROR) << "Could not determine CTC blank index.";
    logger(AX_ERROR) << "Tried configured 'blank_index', detection of empty string \"\", and fallback detection of hyphen '-'.";
    logger(AX_ERROR) << "Label file used: " << chars_file_path;
    logger(AX_ERROR) << "First few labels read: " << first_few_labels;
    logger(AX_ERROR) << "Please ensure the label file is correct and contains either \"\" or '-', or configure 'blank_index'.";
    throw std::runtime_error("Failed to determine CTC blank index.");
  }
  // --- End Blank Index Handling ---

  prop->master_meta = Ax::get_property(
      input, "master_meta", "ctc_static_properties", prop->master_meta);
  prop->do_reduce_mean = Ax::get_property(
      input, "do_reduce_mean", "ctc_static_properties", prop->do_reduce_mean);
  prop->task_category = Ax::get_property(
      input, "task_category", "ctc_static_properties", std::string{});

  if (prop->task_category != "LicensePlateRecognition") {
    throw std::runtime_error("Please support task category: " + prop->task_category);
  }

  return prop;
}

extern "C" void
set_dynamic_properties(const std::unordered_map<std::string, std::string> &input,
    ctc_properties *prop, Ax::Logger &logger)
{
}

/**
 * @brief Performs CTC (Connectionist Temporal Classification) greedy decoding.
 *
 * This function decodes a sequence of character indices by applying a greedy
 * decoding algorithm. It removes duplicate consecutive characters and ignores
 * the blank token.
 *
 * @param prop Pointer to the `ctc_properties` structure, which contains character mappings.
 * @param data Vector of integer indices representing the predicted character sequence.
 * @param blank_token (Optional) Integer representing the blank token.
 * @return Decoded text as a `std::string`.
 */
static std::string
ctc_greedy_decode(const ctc_properties *prop, const std::vector<int> &data, int blank_token)
{
  std::string decoded_text;
  int prev_char = blank_token; // Track previous character to remove duplicates
  for (int c : data) {
    if (c != blank_token && c != prev_char) {
      // Ensure index 'c' is within bounds before accessing prop->chars
      if (c >= 0 && static_cast<size_t>(c) < prop->chars.size()) {
        decoded_text += prop->chars[c]; // Append the whole string
      } else {
        // Handle invalid index if necessary, e.g., log an error or skip
        // logger(AX_WARN) << "ctc_greedy_decode: Invalid character index " << c;
      }
    }
    prev_char = c; // Update previous character
  }
  return decoded_text;
}

// Helper function to format vector elements for debugging
std::string
format_vector(const std::vector<float> &vec, size_t limit)
{
  std::ostringstream oss;
  oss << "[";
  for (size_t i = 0; i < std::min(limit, vec.size()); ++i) {
    if (i > 0)
      oss << ", ";
    oss << vec[i];
  }
  oss << "]";
  return oss.str();
}

extern "C" void
decode_to_meta(const AxTensorsInterface &tensors, const ctc_properties *prop,
    unsigned int current_frame, unsigned int total_frames,
    std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> &map,
    const AxDataInterface &, Ax::Logger &logger)
{
  if (total_frames <= current_frame) {
    throw std::runtime_error("ctc_decode_to_meta: Current frame is out of bounds");
  }

  if (1 != tensors.size()) {
    throw std::runtime_error("ctc_decode_to_meta: Number of tensors must be 1, but got "
                             + std::to_string(tensors.size()));
  }

  auto &tensor = tensors[0];

  if (4 != tensor.bytes) {
    throw std::runtime_error("ctc_decode_to_meta: NN must return float");
  }

  // Log tensor information for debugging
  logger(AX_TRACE) << "Processing tensor with " << tensor.sizes.size()
                   << " dimensions, reduce_mean=" << prop->do_reduce_mean;

  size_t num_chunks_to_reduce = 1;
  size_t positions;
  size_t chars_count;

  // Simplified dimension handling based on do_reduce_mean
  if (prop->do_reduce_mean) {
    // Expect exactly 4D tensor: NHWC layout [B, H, W, C]
    if (tensor.sizes.size() != 4) {
      logger(AX_ERROR) << "When do_reduce_mean=true, tensor must have exactly 4 dimensions (NHWC)";
      throw std::runtime_error("ctc_decode_to_meta: Expected 4D tensor for do_reduce_mean=true");
    }
    num_chunks_to_reduce = tensor.sizes[1]; // H (number of heads to average over)
    positions = tensor.sizes[2]; // W
    chars_count = tensor.sizes[3]; // C
    logger(AX_TRACE) << "Using NHWC layout: B=" << tensor.sizes[0] << ", H=" << num_chunks_to_reduce
                     << ", W=" << positions << ", C=" << chars_count;
  } else {
    size_t num_slices = tensor.sizes[1]; // Slice dimension (e.g., Batch or Head if not reduced)
    chars_count = tensor.sizes[2]; // C (Number of characters)
    positions = tensor.sizes[3]; // W (Number of sequence positions)
    num_chunks_to_reduce = 1; // No reduction happens here
    logger(AX_TRACE) << "Using 3D layout [Slice, C, W]: Slice=" << num_slices
                     << ", C=" << chars_count << ", W=" << positions;
    if (num_slices > 1) {
      logger(AX_WARN)
          << "Tensor has " << num_slices
          << " slices, but only the first slice (index 0) will be used when do_reduce_mean=false.";
    }
  }

  const auto *input_data_start = static_cast<const float *>(tensor.data);
  if (!input_data_start) {
    throw std::runtime_error("ctc_decode_to_meta: Tensor data pointer is null");
  }

  // Calculate chunk size (used differently depending on layout)
  const size_t chunk_size = positions * chars_count;

  if (chunk_size == 0) { // Simplified check as num_chunks_to_reduce depends on path
    throw std::runtime_error(
        "ctc_decode_to_meta: Calculated chunk_size (positions * chars_count) is zero");
  }

  std::vector<float> averaged_output; // Will hold the result if reduction is done
  const float *data_for_argmax = nullptr; // Pointer to the data argmax will use

  if (prop->do_reduce_mean) {
    // Perform the averaging (ReduceMean over dimension 1 - H in NHWC)
    averaged_output.resize(chunk_size); // chunk_size is W*C here
    // Copy the first head (H=0)
    std::copy(input_data_start, input_data_start + chunk_size, averaged_output.begin());

    // Accumulate sums from the remaining heads (if any)
    for (size_t i = 1; i < num_chunks_to_reduce; ++i) {
      // Offset needs to account for Batch dim 0 as well, but we assume B=1 for
      // now Proper offset would be complex if B > 1. Current offset assumes
      // B=1. Offset = i * H * W * C = i * chunk_size (because H is dim 1)
      const float *current_chunk_data = input_data_start + (i * chunk_size);
      std::transform(averaged_output.begin(), averaged_output.end(),
          current_chunk_data, averaged_output.begin(), std::plus<float>());
    }

    // Divide all elements by the number of chunks to get the mean
    if (num_chunks_to_reduce > 1) {
      float inv_chunks = 1.0f / static_cast<float>(num_chunks_to_reduce);
      std::transform(averaged_output.begin(), averaged_output.end(),
          averaged_output.begin(),
          [inv_chunks](float val) { return val * inv_chunks; });
    }
    data_for_argmax = averaged_output.data();
  } else {
    // Skip ReduceMean: Use the 3D tensor directly [C, H, W]
    data_for_argmax = input_data_start;
    // No need for byte check here as we use the whole tensor
  }

  if (!data_for_argmax) {
    throw std::runtime_error("ctc_decode_to_meta: Internal error - data for argmax not set");
  }

  std::vector<int> maxs;
  maxs.reserve(positions);

  if (prop->do_reduce_mean) {
    // NHWC case (effectively operating on averaged [W, C] data)
    const float *current_pos_ptr = data_for_argmax;
    for (size_t i = 0; i < positions; ++i) {
      // Find max element across the C dimension for this position W
      auto max_iter = std::max_element(current_pos_ptr, current_pos_ptr + chars_count);
      int max_idx = std::distance(current_pos_ptr, max_iter);
      maxs.push_back(max_idx);
      current_pos_ptr += chars_count; // Move to the next position block
    }
  } else {
    // 3D NCHW-like case [C, H, W] (operating directly on [C, H, W])
    // Using [Slice, C, W] interpretation. data_for_argmax points to the start.
    // We effectively operate on the first slice [0, C, W], which is like [C, W].
    // Data within the slice is arranged as [char][position] - chars vary slowest.
    std::vector<float> pos_values(chars_count);
    const size_t slice_stride = chars_count * positions; // Size of one slice [C, W]

    for (size_t pos = 0; pos < positions; ++pos) {
      // For each position, gather char values, taking the first head (h=0)
      for (size_t ch = 0; ch < chars_count; ++ch) {
        // Index within the first slice [0, ch, pos] -> flat index = ch * W + pos
        size_t flat_index = ch * positions + pos;
        // Bounds check within the conceptual first slice
        if (flat_index >= slice_stride) {
          logger(AX_ERROR) << "Calculated index " << flat_index
                           << " out of bounds for slice (size " << slice_stride << ")";
          throw std::runtime_error(
              "ctc_decode_to_meta: Calculated index out of bounds within slice");
        }
        pos_values[ch] = data_for_argmax[flat_index];
      }

      // Find max element (character index) for this position
      auto max_iter = std::max_element(pos_values.begin(), pos_values.end());
      int max_idx = std::distance(pos_values.begin(), max_iter);
      maxs.push_back(max_idx);
    }
  }

  // Decode the text from the max indices
  std::string sequence = ctc_greedy_decode(prop, maxs, prop->blank_index);
  sequence.erase(sequence.find_last_not_of(" \t\n\r\f\v") + 1); // Remove trailing whitespace if any
  logger(AX_INFO) << "Decoded text: '" << sequence << "'";

  // Check if master_meta is empty before using it
  if (!prop->master_meta.empty()) {
    // Use master_meta reference when it's not empty
    ax_utils::insert_meta<AxLicensePlateMeta>(map, prop->meta_key,
        prop->master_meta, current_frame, total_frames, std::move(sequence));
  } else {
    // Create a standalone meta when master_meta is empty
    auto position = map.find(prop->meta_key);
    if (position == map.end()) {
      auto ptr = std::make_unique<AxLicensePlateMeta>(std::move(sequence));
      map[prop->meta_key] = std::move(ptr);
    } else {
      map[prop->meta_key] = std::make_unique<AxLicensePlateMeta>(std::move(sequence));
    }
  }
}
