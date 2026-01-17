// Copyright Axelera AI, 2023
#include "AxDataInterface.h"
#include "AxLog.hpp"
#include "AxMeta.hpp"
#include "AxUtils.hpp"

#include <iostream>
#include <unordered_set>

#if defined __AVX2__
#define USE_AVX2
#endif

#if defined __ARM_NEON
#define USE_NEON
#include <arm_neon.h>
#endif

struct normalize_properties {
  std::string simd{};
  std::vector<float> mul{};
  std::vector<float> add{};
  float quant_scale = 1.0;
  float quant_zeropoint = 0.0;
};

extern "C" const std::unordered_set<std::string> &
allowed_properties()
{
  static const std::unordered_set<std::string> allowed_properties{ "mean",
    "std", "quant_scale", "quant_zeropoint", "simd" };
  return allowed_properties;
}

extern "C" std::shared_ptr<void>
init_and_set_static_properties(
    const std::unordered_map<std::string, std::string> &input, Ax::Logger &logger)
{
  std::shared_ptr<normalize_properties> prop = std::make_shared<normalize_properties>();
  return prop;
}

extern "C" void
set_dynamic_properties(const std::unordered_map<std::string, std::string> &input,
    normalize_properties *prop, Ax::Logger &logger)
{
  prop->simd = Ax::get_property(input, "simd", "normalize_dynamic_properties", prop->simd);
  prop->quant_scale = Ax::get_property(
      input, "quant_scale", "normalize_dynamic_properties", prop->quant_scale);
  prop->quant_zeropoint = Ax::get_property(input, "quant_zeropoint",
      "normalize_dynamic_properties", prop->quant_zeropoint);
  auto mean = Ax::get_property(
      input, "mean", "normalize_dynamic_properties", std::vector<float>());
  auto std = Ax::get_property(
      input, "std", "normalize_dynamic_properties", std::vector<float>());
  if (mean.empty() && std.empty()) {
    throw std::runtime_error("mean or std or both must be specified in inplace_normalize");
  }

  int valid_sizes[] = { 0, 1, 3, 4 };
  if (std::find(std::begin(valid_sizes), std::end(valid_sizes), mean.size())
          == std::end(valid_sizes)
      || std::find(std::begin(valid_sizes), std::end(valid_sizes), std.size())
             == std::end(valid_sizes)) {
    throw std::runtime_error(
        "If provided, mean and std must be of size 1, 3 or 4 in inplace_normalize");
  }
  auto max_size = std::max(mean.size(), std.size());
  if (mean.size() == 1) {
    auto filler = mean[0];
    mean.resize(max_size, filler);
  }
  if (std.size() == 1) {
    auto filler = std[0];
    std.resize(max_size, filler);
  }
  prop->add.resize(max_size, 0.0);
  prop->mul.resize(max_size, 1.0);
  for (int i = 0; i < std::min(mean.size(), std.size()); ++i) {
    prop->mul[i] = 1.0 / (prop->quant_scale * std[i]);
    prop->add[i] = prop->quant_zeropoint - prop->mul[i] * mean[i];
  }
}

std::pair<std::array<float, 4>, std::array<float, 4>>
correct_channel_numbers_and_div_by_255(
    const normalize_properties *details, size_t num_ch, int bytes)
{
  auto mul_norm = details->mul;
  if (bytes == 1) {
    constexpr float inv_255 = 1.0 / 255.0;
    std::transform(mul_norm.begin(), mul_norm.end(), mul_norm.begin(),
        [](float val) { return val * inv_255; });
  }

  auto result = std::make_pair(std::array<float, 4>{ 1.0f, 1.0f, 1.0f, 1.0f },
      std::array<float, 4>{ 0.0f, 0.0f, 0.0f, 0.0f });
  std::array<float, 4> &muls = result.first;
  std::array<float, 4> &adds = result.second;

  auto max_muls = std::min({ num_ch, muls.size(), mul_norm.size() });
  auto max_adds = std::min({ num_ch, adds.size(), details->add.size() });
  std::copy_n(mul_norm.begin(), max_muls, muls.begin());
  std::copy_n(details->add.begin(), max_adds, adds.begin());

  if (mul_norm.size() == 1) {
    std::fill_n(muls.begin(), num_ch, mul_norm[0]);
  }
  if (details->add.size() == 1) {
    std::fill_n(adds.begin(), num_ch, details->add[0]);
  }
  return result;
}

float
round_to_even(float val)
{
  float rounded = std::round(val);
  if (std::abs(val - rounded) == 0.5) {
    return 2.0f * std::round(val / 2.0f);
  }
  return rounded;
}

int8_t
clamp_and_round(float val)
{
  return static_cast<int8_t>(std::round(std::clamp(val, -128.0f, 127.0f)));
}

extern "C" void
inplace(const AxDataInterface &data, const normalize_properties *details,
    unsigned int, unsigned int,
    std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> &, Ax::Logger &logger)
{
  if (!std::holds_alternative<AxTensorsInterface>(data)) {
    throw std::runtime_error("inplace_normalize only works with tensors");
  }

  auto &tensors = std::get<AxTensorsInterface>(data);
  if (tensors.size() != 1) {
    throw std::runtime_error("inplace_normalize only works on single tensors");
  }
  auto &tensor = tensors[0];

  int ch_dim = tensor.bytes == 4 ? 1 : 3; // this means we assume f32 is NCHW format, else NHWC
  // beware, here the channel dim is counted from left to right, i.e. N is the dim0, W is dim3
  if (tensor.sizes.size() <= ch_dim) {
    throw std::runtime_error("inplace_normalize works on tensors with at least 4 dimensions");
  }
  size_t num_ch = tensor.sizes[ch_dim];
  if (num_ch > 4) {
    throw std::runtime_error("inplace_normalize works on tensors with at most 4 channels");
  }
  auto [muls, adds]
      = correct_channel_numbers_and_div_by_255(details, num_ch, tensor.bytes);


  if (details->simd == "avx512") {
#ifdef __AVX512F__
    if (tensor.bytes != 1) {
      throw std::runtime_error("inplace_normalize with avx512 works on (u)int8 tensors only");
    }
    if (muls.size() != 4) {
      throw std::runtime_error("inplace_normalize with avx512 works on 4 channels only");
    }
    if (ch_dim != 3) {
      throw std::runtime_error(
          "inplace_normalize with avx512 works on channel as most contiguous dimension only");
    }
    auto mul_512 = _mm512_setr_ps(muls[0], muls[1], muls[2], muls[3], muls[0],
        muls[1], muls[2], muls[3], muls[0], muls[1], muls[2], muls[3], muls[0],
        muls[1], muls[2], muls[3]);
    auto add_512 = _mm512_setr_ps(adds[0], adds[1], adds[2], adds[3], adds[0],
        adds[1], adds[2], adds[3], adds[0], adds[1], adds[2], adds[3], adds[0],
        adds[1], adds[2], adds[3]);
    for (int i_16 = 0; i_16 < tensor.total(); i_16 = i_16 + 16) {
      int8_t *ptr = static_cast<int8_t *>(tensor.data) + i_16;
      auto input_128 = _mm_loadu_epi8(ptr);
      auto input_512 = _mm512_cvtepu8_epi32(input_128);
      auto input_512_f32 = _mm512_cvtepi32_ps(input_512);
      auto output_512_f32 = _mm512_fmadd_ps(input_512_f32, mul_512, add_512);
      auto output_512 = _mm512_cvt_roundps_epi32(
          output_512_f32, _MM_FROUND_TO_NEAREST_INT | _MM_FROUND_NO_EXC);
      auto output_128 = _mm512_cvtepi32_epi8(output_512);
      _mm_storeu_epi8(ptr, output_128);
    }

    for (int i = (tensor.total() / 16) * 16; i < tensor.total(); i++) {
      uint8_t val = static_cast<uint8_t *>(tensor.data)[i];
      int8_t *ptr = static_cast<int8_t *>(tensor.data);
      ptr[i] = clamp_and_round(val * muls[i % 4] + adds[i % 4]);
    }
    return;
#endif
    logger(AX_WARN) << "inplace_normalize is not compiled with AVX512F, defaulting to AVX2 implementation"
                    << std::endl;
  }


  if (details->simd == "avx2" || details->simd == "avx512") {
#ifdef USE_AVX2
    if (tensor.bytes != 1) {
      throw std::runtime_error("inplace_normalize with avx2 works on (u)int8 tensors only");
    }
    if (ch_dim != 3) {
      throw std::runtime_error(
          "inplace_normalize with avx2 works on channel as most contiguous dimension only");
    }

    _MM_SET_ROUNDING_MODE(_MM_ROUND_NEAREST);

    int processing_stride = std::lcm(8, num_ch);
    int num_processings = processing_stride / 8;
    int num_strides = tensor.total() / processing_stride;

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wignored-attributes"
    std::vector<__m256> mul_256;
    mul_256.reserve(num_processings);
    std::vector<__m256> add_256;
    add_256.reserve(num_processings);
#pragma GCC diagnostic pop

    for (int i = 0; i < num_processings; ++i) {
      int i0 = (i * 8 + 0) % num_ch;
      int i1 = (i * 8 + 1) % num_ch;
      int i2 = (i * 8 + 2) % num_ch;
      int i3 = (i * 8 + 3) % num_ch;
      int i4 = (i * 8 + 4) % num_ch;
      int i5 = (i * 8 + 5) % num_ch;
      int i6 = (i * 8 + 6) % num_ch;
      int i7 = (i * 8 + 7) % num_ch;

      mul_256.push_back(_mm256_setr_ps(muls[i0], muls[i1], muls[i2], muls[i3],
          muls[i4], muls[i5], muls[i6], muls[i7]));
      add_256.push_back(_mm256_setr_ps(adds[i0], adds[i1], adds[i2], adds[i3],
          adds[i4], adds[i5], adds[i6], adds[i7]));
    }

    int64_t *ptr64 = static_cast<int64_t *>(tensor.data);
    int32_t *ptr32 = static_cast<int32_t *>(tensor.data);
    for (int i = 0; i < num_strides; ++i) {
      for (int j = 0; j < num_processings; ++j) {
        auto input_128 = _mm_cvtsi64_si128(*ptr64++);
        auto input_256 = _mm256_cvtepu8_epi32(input_128);
        auto input_256_f32 = _mm256_cvtepi32_ps(input_256);
#if __aarch64__
        //  libsimde does not seem to support fused multiply and add
        auto tmp = _mm256_mul_ps(input_256_f32, mul_256[j]);
        auto output_256_f32 = _mm256_add_ps(tmp, add_256[j]);
#else
        auto output_256_f32 = _mm256_fmadd_ps(input_256_f32, mul_256[j], add_256[j]);
#endif
        auto output_256 = _mm256_cvtps_epi32(output_256_f32);
        auto output_128 = _mm256_packs_epi32(output_256, output_256);
        auto output_64 = _mm256_packs_epi16(output_128, output_128);
        *ptr32++ = _mm256_extract_epi32(output_64, 0);
        *ptr32++ = _mm256_extract_epi32(output_64, 4);
      }
    }

    for (int i = num_strides * processing_stride; i < tensor.total(); ++i) {
      uint8_t val = static_cast<uint8_t *>(tensor.data)[i];
      int8_t *ptr = static_cast<int8_t *>(tensor.data);
      ptr[i] = clamp_and_round(val * muls[i % num_ch] + adds[i % num_ch]);
    }
    return;
#endif
    logger(AX_WARN) << "inplace_normalize is not compiled with AVX2, defaulting to non SIMD implementation"
                    << std::endl;
  }

  if (details->simd == "neon") {
#ifdef USE_NEON
    if (tensor.bytes != 1) {
      throw std::runtime_error("inplace_normalize with NEON works on (u)int8 tensors only");
    }
    if (ch_dim != 3) {
      throw std::runtime_error(
          "inplace_normalize with NEON works on channel as most contiguous dimension only");
    }
    if (num_ch != 4) {
      throw std::runtime_error("inplace_normalize with NEON works on 4 channels only");
    }

    // Pre-compute the multiplication and addition vectors
    float32x4_t mul_neon = vld1q_f32(muls.data());
    float32x4_t add_neon = vld1q_f32(adds.data());

    // Process 16 pixels (64 bytes) at a time for better vectorization
    size_t total_elements = tensor.total();
    size_t vec_size = 16;
    size_t vec_count = total_elements / vec_size;

    uint8_t *input_ptr = static_cast<uint8_t *>(tensor.data);
    int8_t *output_ptr = static_cast<int8_t *>(tensor.data);

    // Constants for clamping
    float32x4_t min_val = vdupq_n_f32(-128.0f);
    float32x4_t max_val = vdupq_n_f32(127.0f);

    for (size_t i = 0; i < vec_count; ++i) {
      // Process first 8 bytes (2 pixels with 4 channels each)
      uint8x8_t input1 = vld1_u8(input_ptr);
      uint16x8_t input1_u16 = vmovl_u8(input1);

      // Process first 4 elements (first pixel)
      uint16x4_t pixel0_u16 = vget_low_u16(input1_u16);
      uint32x4_t pixel0_u32 = vmovl_u16(pixel0_u16);
      float32x4_t pixel0_f32 = vcvtq_f32_u32(pixel0_u32);
      float32x4_t result0_f32 = vmlaq_f32(add_neon, pixel0_f32, mul_neon);
      result0_f32 = vminq_f32(vmaxq_f32(result0_f32, min_val), max_val);
      int32x4_t result0_s32 = vcvtnq_s32_f32(result0_f32);

      // Process next 4 elements (second pixel)
      uint32x4_t pixel1_u32 = vmovl_high_u16(input1_u16);
      float32x4_t pixel1_f32 = vcvtq_f32_u32(pixel1_u32);
      float32x4_t result1_f32 = vmlaq_f32(add_neon, pixel1_f32, mul_neon);
      result1_f32 = vminq_f32(vmaxq_f32(result1_f32, min_val), max_val);
      int32x4_t result1_s32 = vcvtnq_s32_f32(result1_f32);

      // Narrow and combine first 8 results
      int16x8_t result1_s16
          = vcombine_s16(vmovn_s32(result0_s32), vmovn_s32(result1_s32));
      int8x8_t result1 = vmovn_s16(result1_s16);

      // Process next 8 bytes (2 more pixels with 4 channels each)
      uint8x8_t input2 = vld1_u8(input_ptr + 8);
      uint16x8_t input2_u16 = vmovl_u8(input2);

      // Process next 4 elements (third pixel)
      uint16x4_t pixel2_u16 = vget_low_u16(input2_u16);
      uint32x4_t pixel2_u32 = vmovl_u16(pixel2_u16);
      float32x4_t pixel2_f32 = vcvtq_f32_u32(pixel2_u32);
      float32x4_t result2_f32 = vmlaq_f32(add_neon, pixel2_f32, mul_neon);
      result2_f32 = vminq_f32(vmaxq_f32(result2_f32, min_val), max_val);
      int32x4_t result2_s32 = vcvtnq_s32_f32(result2_f32);

      // Process next 4 elements (fourth pixel)
      uint32x4_t pixel3_u32 = vmovl_high_u16(input2_u16);
      float32x4_t pixel3_f32 = vcvtq_f32_u32(pixel3_u32);
      float32x4_t result3_f32 = vmlaq_f32(add_neon, pixel3_f32, mul_neon);
      result3_f32 = vminq_f32(vmaxq_f32(result3_f32, min_val), max_val);
      int32x4_t result3_s32 = vcvtnq_s32_f32(result3_f32);

      // Narrow and combine second 8 results
      int16x8_t result2_s16
          = vcombine_s16(vmovn_s32(result2_s32), vmovn_s32(result3_s32));
      int8x8_t result2 = vmovn_s16(result2_s16);

      // Store results
      vst1_s8(output_ptr, result1);
      vst1_s8(output_ptr + 8, result2);

      // Advance pointers
      input_ptr += vec_size;
      output_ptr += vec_size;
    }

    // Handle remaining elements
    for (size_t i = vec_count * vec_size; i < total_elements; ++i) {
      uint8_t val = static_cast<uint8_t *>(tensor.data)[i];
      int8_t *ptr = static_cast<int8_t *>(tensor.data);
      ptr[i] = clamp_and_round(val * muls[i % 4] + adds[i % 4]);
    }

    return;
#endif
    logger(AX_WARN) << "inplace_normalize is not compiled with NEON, defaulting to non SIMD implementation"
                    << std::endl;
  }

  int inner = 1;
  int outer = 1;
  for (int i = 0; i < ch_dim; ++i) {
    outer *= tensor.sizes[i];
  }
  for (int i = ch_dim + 1; i < tensor.sizes.size(); ++i) {
    inner *= tensor.sizes[i];
  }

  if (inner == 1 && tensor.bytes == 1 && tensor.sizes[ch_dim] == 4) {
    // Special case for 4-channel NHWC uint8 tensors
    int ind = 0;
    uint8_t *p_in = static_cast<uint8_t *>(tensor.data);
    int8_t *p_out = static_cast<int8_t *>(tensor.data);
    for (int i = 0; i < 4 * outer; ++i) {
      auto v = p_in[ind] * muls[ind & 3] + adds[ind & 3];
      p_out[ind] = std::round(std::clamp(v, -128.0f, 127.0f));
      ++ind;
    }
  } else {
    int ind = 0;
    for (int i = 0; i < outer; ++i) {
      for (int ch = 0; ch < tensor.sizes[ch_dim]; ++ch) {
        for (int j = 0; j < inner; ++j) {
          if (tensor.bytes == 4) {
            float *ptr = static_cast<float *>(tensor.data);
            ptr[ind] = ptr[ind] * muls[ch] + adds[ch];
          } else if (tensor.bytes == 1) {
            uint8_t val = static_cast<uint8_t *>(tensor.data)[ind];
            int8_t *ptr = static_cast<int8_t *>(tensor.data);
            ptr[ind] = clamp_and_round(val * muls[ch] + adds[ch]);
          } else {
            throw std::runtime_error("inplace_normalize works on (u)int8 or float32");
          }
          ++ind;
        }
      }
    }
  }
}
