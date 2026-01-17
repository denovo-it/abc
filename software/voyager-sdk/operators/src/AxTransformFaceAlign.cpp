// Copyright Axelera AI, 2023
#include <AxOpUtils.hpp>
#include <opencv2/core/ocl.hpp>
#include <unordered_map>
#include <unordered_set>
#include "AxDataInterface.h"
#include "AxLog.hpp"
#include "AxMeta.hpp"
#include "AxMetaKptsDetection.hpp"
#include "AxMetaTracker.hpp"
#include "AxUtils.hpp"

struct facealign_properties {
  std::string master_meta{};
  std::string association_meta{};
  std::string keypoints_submeta_key{};
  int width = 0;
  int height = 0;
  float padding = 0.0;
  std::vector<float> XXn{};
  std::vector<float> YYn{};
  bool use_self_normalizing = false;
  bool save_aligned_images = false;

  // fmt: off
  constexpr static std::array<float, 5> XXn_5 = {
    60.59f / 192, // Left eye
    131.06f / 192, // Right eye
    96.05f / 192, // Nose
    67.10f / 192, // Left mouth
    125.46f / 192 // Right mouth
  };
  constexpr static std::array<float, 5> YYn_5 = {
    76.8f / 192, // Left eye (40% from top)
    76.8f / 192, // Right eye
    115.2f / 192, // Nose (60% from top)
    153.6f / 192, // Left mouth (80% from top)
    153.6f / 192 // Right mouth
  };

  constexpr static std::array<float, 51> XXn_51 = {
    0.000213256,
    0.0752622,
    0.18113,
    0.29077,
    0.393397,
    0.586856,
    0.689483,
    0.799124,
    0.904991,
    0.98004,
    0.490127,
    0.490127,
    0.490127,
    0.490127,
    0.36688,
    0.426036,
    0.490127,
    0.554217,
    0.613373,
    0.121737,
    0.187122,
    0.265825,
    0.334606,
    0.260918,
    0.182743,
    0.645647,
    0.714428,
    0.793132,
    0.858516,
    0.79751,
    0.719335,
    0.254149,
    0.340985,
    0.428858,
    0.490127,
    0.551395,
    0.639268,
    0.726104,
    0.642159,
    0.556721,
    0.490127,
    0.423532,
    0.338094,
    0.290379,
    0.428096,
    0.490127,
    0.552157,
    0.689874,
    0.553364,
    0.490127,
    0.42689,
  };
  constexpr static std::array<float, 51> YYn_51 = {
    0.106454,
    0.038915,
    0.0187482,
    0.0344891,
    0.0773906,
    0.0773906,
    0.0344891,
    0.0187482,
    0.038915,
    0.106454,
    0.203352,
    0.307009,
    0.409805,
    0.515625,
    0.587326,
    0.609345,
    0.628106,
    0.609345,
    0.587326,
    0.216423,
    0.178758,
    0.179852,
    0.231733,
    0.245099,
    0.244077,
    0.231733,
    0.179852,
    0.178758,
    0.216423,
    0.244077,
    0.245099,
    0.780233,
    0.745405,
    0.727388,
    0.742578,
    0.727388,
    0.745405,
    0.780233,
    0.864805,
    0.902192,
    0.909281,
    0.902192,
    0.864805,
    0.784792,
    0.778746,
    0.785343,
    0.778746,
    0.784792,
    0.824182,
    0.831803,
    0.824182,
  };
  // fmt: on
};

extern "C" const std::unordered_set<std::string> &
allowed_properties()
{
  static const std::unordered_set<std::string> allowed_properties{
    "master_meta",
    "association_meta",
    "keypoints_submeta_key",
    "width",
    "height",
    "padding",
    "template_keypoints_x",
    "template_keypoints_y",
    "use_self_normalizing",
    "save_aligned_images",
  };
  return allowed_properties;
}

extern "C" std::shared_ptr<void>
init_and_set_static_properties(
    const std::unordered_map<std::string, std::string> &input, Ax::Logger &logger)
{
  std::shared_ptr<facealign_properties> prop = std::make_shared<facealign_properties>();
  prop->master_meta = Ax::get_property(
      input, "master_meta", "facealign_static_properties", prop->master_meta);
  if (prop->master_meta.empty()) {
    throw std::runtime_error("facealign: master meta key not provided");
  }
  prop->association_meta = Ax::get_property(input, "association_meta",
      "facealign_static_properties", prop->association_meta);
  prop->keypoints_submeta_key = Ax::get_property(input, "keypoints_submeta_key",
      "facealign_static_properties", prop->keypoints_submeta_key);
  prop->width = Ax::get_property(input, "width", "facealign_static_properties", prop->width);
  prop->height
      = Ax::get_property(input, "height", "facealign_static_properties", prop->height);
  prop->padding = Ax::get_property(
      input, "padding", "facealign_static_properties", prop->padding);
  prop->XXn = Ax::get_property(
      input, "template_keypoints_x", "facealign_static_properties", prop->XXn);
  prop->YYn = Ax::get_property(
      input, "template_keypoints_y", "facealign_static_properties", prop->YYn);
  if (prop->XXn.size() != prop->YYn.size()) {
    throw std::runtime_error(
        "facealign: template_keypoints_x and template_keypoints_y must have the same number of elements");
  }
  prop->use_self_normalizing = Ax::get_property(input, "use_self_normalizing",
      "facealign_static_properties", prop->use_self_normalizing);
  prop->save_aligned_images = Ax::get_property(input, "save_aligned_images",
      "facealign_static_properties", prop->save_aligned_images);
  return prop;
}

extern "C" AxDataInterface
set_output_interface(const AxDataInterface &interface,
    const facealign_properties *prop, Ax::Logger &logger)
{
  if (!std::holds_alternative<AxVideoInterface>(interface)) {
    throw std::runtime_error("facealign works on video input only");
  }
  AxDataInterface output = interface;
  if (prop->width == 0 || prop->height == 0) {
    return output;
  }
  auto &info = std::get<AxVideoInterface>(output).info;
  info.width = prop->width;
  info.height = prop->height;
  return output;
}

// Helper function to perform fallback alignment (simple resize)
static void
perform_fallback_alignment(const AxDataInterface &input,
    const AxDataInterface &output, Ax::Logger &logger)
{
  auto &input_video = std::get<AxVideoInterface>(input);
  auto &output_video = std::get<AxVideoInterface>(output);
  cv::Mat input_mat(cv::Size(input_video.info.width, input_video.info.height),
      Ax::opencv_type_u8(input_video.info.format), input_video.data,
      input_video.info.stride);
  cv::Mat output_mat(cv::Size(output_video.info.width, output_video.info.height),
      Ax::opencv_type_u8(output_video.info.format), output_video.data,
      output_video.info.stride);
  cv::resize(input_mat, output_mat, output_mat.size());
}

AxMetaKpts *
extract_keypoints_from_meta(AxMetaBase *meta, int &kpts_per_box)
{

  auto *kpts_meta = dynamic_cast<AxMetaKptsDetection *>(meta);
  if (kpts_meta) {
    kpts_per_box = kpts_meta->get_kpts_shape()[0];
    return kpts_meta;
  }

  // Fall back to AxMetaKpts
  auto *kpts_meta_base = dynamic_cast<AxMetaKpts *>(meta);
  if (kpts_meta_base) {
    kpts_per_box = kpts_meta_base->num_elements();
    return kpts_meta_base;
  }

  return nullptr;
}

AxMetaKpts *
extract_keypoints_from_tracker(
    AxMetaTracker *tracker_meta, int &kpts_per_box, Ax::Logger &logger)
{
  if (tracker_meta->track_id_to_tracking_descriptor.empty()) {
    throw std::runtime_error("facealign: tracker meta has no tracking descriptors");
  }

  int track_id = tracker_meta->track_id_to_tracking_descriptor.begin()->first;
  auto &descriptor = tracker_meta->track_id_to_tracking_descriptor.at(track_id);

  const TrackingElement *element = descriptor.collection->get_frame(descriptor.frame_id);
  if (!element) {
    throw std::runtime_error("facealign: no frame data for current frame in tracker");
  }

  for (const auto &[key, meta_ptr] : element->frame_data_map) {
    auto *kpts = extract_keypoints_from_meta(meta_ptr.get(), kpts_per_box);
    if (kpts)
      return kpts;
  }

  throw std::runtime_error("facealign: could not find keypoints in tracker meta");
}


extern "C" void
transform(const AxDataInterface &input, const AxDataInterface &output,
    const facealign_properties *prop, unsigned int subframe_index, unsigned int number_of_subframes,
    std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> &map, Ax::Logger &logger)
{
  const std::string &master_meta_key
      = !prop->association_meta.empty() ? prop->association_meta : prop->master_meta;
  auto *master_meta_base = map.at(master_meta_key).get();
  auto *master_meta = dynamic_cast<AxMetaBbox *>(master_meta_base);

  if (!master_meta || master_meta->get_number_of_subframes() != number_of_subframes) {
    throw std::runtime_error("facealign: invalid master meta");
  }

  box_xyxy box = master_meta->get_box_xyxy(subframe_index);
  if (box.x2 <= box.x1 || box.y2 <= box.y1) {
    perform_fallback_alignment(input, output, logger);
    return;
  }
  AxMetaKpts *kpts_meta_base = nullptr;
  int kpts_start = 0;
  int kpts_per_box = 0;

  auto *tracker_meta = dynamic_cast<AxMetaTracker *>(master_meta_base);
  if (prop->keypoints_submeta_key.empty()) {
    if (tracker_meta) {
      kpts_meta_base = extract_keypoints_from_tracker(tracker_meta, kpts_per_box, logger);
      kpts_start = 0;
    } else {
      kpts_meta_base = extract_keypoints_from_meta(master_meta, kpts_per_box);
      if (!kpts_meta_base) {
        throw std::runtime_error("facealign: no keypoint interface found");
      }
      kpts_start = subframe_index;
    }
  } else if (prop->keypoints_submeta_key == prop->master_meta) {
    auto *orig_meta = map.at(prop->master_meta).get();
    if (auto *tracker_direct = dynamic_cast<AxMetaTracker *>(orig_meta)) {
      kpts_meta_base = extract_keypoints_from_tracker(tracker_direct, kpts_per_box, logger);
      // Map subframe index if association_meta is used
      if (!prop->association_meta.empty()) {
        int master_subframe_index = master_meta->get_id(subframe_index);
        if (master_subframe_index < 0
            || master_subframe_index >= tracker_direct->get_number_of_subframes()) {
          throw std::runtime_error("facealign: subframe index error (tracker mapping)");
        }
        kpts_start = master_subframe_index;
      } else {
        kpts_start = 0;
      }
    } else {
      kpts_meta_base = extract_keypoints_from_meta(orig_meta, kpts_per_box);
      if (!kpts_meta_base) {
        throw std::runtime_error("facealign: master meta doesn't implement keypoint interface");
      }
      if (!prop->association_meta.empty()) {
        int master_subframe_index = master_meta->get_id(subframe_index);
        auto *container_meta = dynamic_cast<AxMetaBbox *>(orig_meta);
        if (!container_meta) {
          throw std::runtime_error("facealign: invalid container meta for keypoints");
        }
        if (master_subframe_index < 0
            || master_subframe_index >= container_meta->get_number_of_subframes()) {
          throw std::runtime_error("facealign: subframe index error (bbox mapping)");
        }
        kpts_start = master_subframe_index;
      } else {
        kpts_start = subframe_index;
      }
    }
  } else {
    auto *container_meta
        = prop->association_meta.empty() ?
              master_meta :
              dynamic_cast<AxMetaBbox *>(map.at(prop->master_meta).get());
    if (!container_meta) {
      throw std::runtime_error("facealign: invalid container meta");
    }

    int master_subframe_index = prop->association_meta.empty() ?
                                    subframe_index :
                                    master_meta->get_id(subframe_index);
    if (master_subframe_index < 0
        || master_subframe_index >= container_meta->get_number_of_subframes()) {
      throw std::runtime_error("facealign: subframe index error");
    }

    try {
      auto *submeta = container_meta->get_submeta<AxMetaBase>(prop->keypoints_submeta_key,
          master_subframe_index, container_meta->get_number_of_subframes());
      if (submeta) {
        kpts_meta_base = extract_keypoints_from_meta(submeta, kpts_per_box);
      }
    } catch (const std::exception &) {
      throw std::runtime_error("facealign: keypoints submeta '" + prop->keypoints_submeta_key
                               + "' not found in container meta");
    }

    if (!kpts_meta_base) {
      auto *container_tracker = dynamic_cast<AxMetaTracker *>(container_meta);
      if (container_tracker) {
        kpts_meta_base
            = extract_keypoints_from_tracker(container_tracker, kpts_per_box, logger);
      } else {
        kpts_meta_base = extract_keypoints_from_meta(container_meta, kpts_per_box);
      }
    }

    if (!kpts_meta_base) {
      throw std::runtime_error("facealign: could not find keypoints");
    }
    kpts_start = master_subframe_index;
  }

  std::vector<float> X, Y;
  X.reserve(kpts_per_box);
  Y.reserve(kpts_per_box);

  for (int i = 0; i < kpts_per_box; ++i) {
    int kpt_index = kpts_start * kpts_per_box + i;
    if (kpt_index >= static_cast<int>(kpts_meta_base->num_elements())) {
      perform_fallback_alignment(input, output, logger);
      return;
    }

    KptXyv kpt = kpts_meta_base->get_kpt_xy(kpt_index);
    float rel_x = kpt.x - box.x1;
    float rel_y = kpt.y - box.y1;

    if (!std::isfinite(rel_x) || !std::isfinite(rel_y)) {
      perform_fallback_alignment(input, output, logger);
      return;
    }

    X.push_back(rel_x);
    Y.push_back(rel_y);
  }

  auto &input_video = std::get<AxVideoInterface>(input);
  auto &output_video = std::get<AxVideoInterface>(output);
  cv::Mat input_mat(cv::Size(input_video.info.width, input_video.info.height),
      Ax::opencv_type_u8(input_video.info.format), input_video.data,
      input_video.info.stride);
  cv::Mat output_mat(cv::Size(output_video.info.width, output_video.info.height),
      Ax::opencv_type_u8(output_video.info.format), output_video.data,
      output_video.info.stride);

  if (prop->use_self_normalizing) {
    // Self-normalizing alignment
    if (kpts_per_box == 5) {
      cv::Point2f left_eye(X[0], Y[0]);
      cv::Point2f right_eye(X[1], Y[1]);

      float eye_distance = cv::norm(right_eye - left_eye);
      if (eye_distance < 10.0f) {
        perform_fallback_alignment(input, output, logger);
        return;
      }

      float desired_eye_y = output_mat.rows * 0.4f;
      float desired_eye_center_x = output_mat.cols / 2.0f;
      float desired_eye_distance = output_mat.cols * 0.35f;

      cv::Point2f eye_center = (left_eye + right_eye) * 0.5f;
      cv::Point2f eye_diff = right_eye - left_eye;
      float angle = std::atan2(eye_diff.y, eye_diff.x) * 180.0f / CV_PI;
      float scale = std::clamp(desired_eye_distance / eye_distance, 0.1f, 5.0f);

      cv::Mat rotation_matrix = cv::getRotationMatrix2D(eye_center, angle, scale);
      rotation_matrix.at<double>(0, 2) += desired_eye_center_x - eye_center.x;
      rotation_matrix.at<double>(1, 2) += desired_eye_y - eye_center.y;

      // Use (0,0,0,255) for border pixels
      cv::warpAffine(input_mat, output_mat, rotation_matrix, output_mat.size(),
          cv::INTER_LINEAR, cv::BORDER_CONSTANT, cv::Scalar(0, 0, 0, 255));
    } else {
      perform_fallback_alignment(input, output, logger);
    }
  } else {
    // Template-based alignment
    std::vector<float> XX = prop->XXn;
    std::vector<float> YY = prop->YYn;
    int kpts_offset = 0;

    // Select template
    if (XX.empty() || YY.empty()) {
      if (kpts_per_box >= 68) {
        XX.assign(prop->XXn_51.begin(), prop->XXn_51.end());
        YY.assign(prop->YYn_51.begin(), prop->YYn_51.end());
        kpts_offset = 17;
      } else if (kpts_per_box >= 51) {
        XX.assign(prop->XXn_51.begin(), prop->XXn_51.end());
        YY.assign(prop->YYn_51.begin(), prop->YYn_51.end());
        kpts_offset = 0;
      } else if (kpts_per_box >= 5) {
        XX.assign(prop->XXn_5.begin(), prop->XXn_5.end());
        YY.assign(prop->YYn_5.begin(), prop->YYn_5.end());
        kpts_offset = 0;
      } else {
        perform_fallback_alignment(input, output, logger);
        return;
      }
    }

    if (XX.size() != static_cast<size_t>(kpts_per_box - kpts_offset)) {
      perform_fallback_alignment(input, output, logger);
      return;
    }

    std::vector<float> X_template(X.begin() + kpts_offset, X.end());
    std::vector<float> Y_template(Y.begin() + kpts_offset, Y.end());

    float meanX = std::accumulate(X_template.begin(), X_template.end(), 0.0f)
                  / X_template.size();
    float meanY = std::accumulate(Y_template.begin(), Y_template.end(), 0.0f)
                  / Y_template.size();

    float varX = 0, varY = 0;
    for (size_t i = 0; i < X_template.size(); ++i) {
      varX += (X_template[i] - meanX) * (X_template[i] - meanX);
      varY += (Y_template[i] - meanY) * (Y_template[i] - meanY);
    }
    float stdX = std::sqrt(varX / X_template.size());
    float stdY = std::sqrt(varY / Y_template.size());

    const float min_std = 1e-6f;
    if (stdX < min_std || stdY < min_std) {
      perform_fallback_alignment(input, output, logger);
      return;
    }

    for (float &x : X_template)
      x = (x - meanX) / stdX;
    for (float &y : Y_template)
      y = (y - meanY) / stdY;

    float inv_padding_factor = 1.0f / (2 * prop->padding + 1);
    for (float &x : XX)
      x = (x + prop->padding) * inv_padding_factor * output_mat.cols;
    for (float &y : YY)
      y = (y + prop->padding) * inv_padding_factor * output_mat.rows;

    float meanXX = std::accumulate(XX.begin(), XX.end(), 0.0f) / XX.size();
    float meanYY = std::accumulate(YY.begin(), YY.end(), 0.0f) / YY.size();

    float varXX = 0, varYY = 0;
    for (size_t i = 0; i < XX.size(); ++i) {
      varXX += (XX[i] - meanXX) * (XX[i] - meanXX);
      varYY += (YY[i] - meanYY) * (YY[i] - meanYY);
    }
    float stdXX = std::sqrt(varXX / XX.size());
    float stdYY = std::sqrt(varYY / YY.size());

    if (stdXX < min_std || stdYY < min_std) {
      perform_fallback_alignment(input, output, logger);
      return;
    }

    for (float &x : XX)
      x = (x - meanXX) / stdXX;
    for (float &y : YY)
      y = (y - meanYY) / stdYY;

    cv::Mat_<float> A(2, 2);
    A(0, 0) = std::inner_product(X_template.begin(), X_template.end(), XX.begin(), 0.0f);
    A(0, 1) = std::inner_product(X_template.begin(), X_template.end(), YY.begin(), 0.0f);
    A(1, 0) = std::inner_product(Y_template.begin(), Y_template.end(), XX.begin(), 0.0f);
    A(1, 1) = std::inner_product(Y_template.begin(), Y_template.end(), YY.begin(), 0.0f);

    cv::Mat_<float> W, U, Vt;
    cv::SVD::compute(A, W, U, Vt);
    cv::Mat_<float> R = (U * Vt).t();

    cv::Mat_<float> M(2, 3);
    float stdXX_over_stdX = stdXX / stdX;
    float stdYY_over_stdY = stdYY / stdY;
    M(0, 0) = R(0, 0) * stdXX_over_stdX;
    M(1, 0) = R(1, 0) * stdYY_over_stdY;
    M(0, 1) = R(0, 1) * stdXX_over_stdX;
    M(1, 1) = R(1, 1) * stdYY_over_stdY;
    M(0, 2) = meanXX - stdXX_over_stdX * (R(0, 0) * meanX + R(0, 1) * meanY);
    M(1, 2) = meanYY - stdYY_over_stdY * (R(1, 0) * meanX + R(1, 1) * meanY);

    bool valid_matrix = true;
    for (int i = 0; i < 2 && valid_matrix; ++i) {
      for (int j = 0; j < 3 && valid_matrix; ++j) {
        if (!std::isfinite(M(i, j)))
          valid_matrix = false;
      }
    }

    if (!valid_matrix) {
      perform_fallback_alignment(input, output, logger);
      return;
    }

    // Use (0,0,0,255) for border pixels
    cv::warpAffine(input_mat, output_mat, M, output_mat.size(),
        cv::INTER_LINEAR, cv::BORDER_CONSTANT, cv::Scalar(0, 0, 0, 255));
  }

  if (prop->save_aligned_images) {
    static int frame_counter = 0;
    try {
      [[maybe_unused]] int ret = system("mkdir -p face_align_debug");
      cv::imwrite("face_align_debug/aligned_" + std::to_string(frame_counter) + ".png",
          output_mat);

      // Create a copy for keypoint visualization (don't modify original input)
      cv::Mat debug_img = input_mat.clone();
      for (size_t i = 0; i < X.size(); ++i) {
        cv::Point2f pt(X[i], Y[i]);
        if (pt.x >= 0 && pt.x < debug_img.cols && pt.y >= 0 && pt.y < debug_img.rows) {
          cv::circle(debug_img, pt, 8, cv::Scalar(0, 255, 0), -1);
        }
      }
      cv::imwrite("face_align_debug/original_" + std::to_string(frame_counter) + ".png",
          debug_img);
      frame_counter++;
    } catch (...) {
      logger(AX_WARN) << "facealign: failed to save aligned images, check permissions or disk space"
                      << std::endl;
    }
  }
}
