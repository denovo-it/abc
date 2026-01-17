#ifndef OC_SORT_CPP_ASSOCIATION_HPP
#define OC_SORT_CPP_ASSOCIATION_HPP

#include <algorithm>
#include <cmath>

#include "Eigen/Dense"
#include "lapjv.hpp"
#include "vector"

namespace ocsort
{
constexpr float pi = static_cast<float>(M_PI);

std::tuple<Eigen::MatrixXf, Eigen::MatrixXf> speed_direction_batch(
    const Eigen::MatrixXf &dets, const Eigen::MatrixXf &tracks);
Eigen::MatrixXf iou_batch(const Eigen::MatrixXf &bboxes1, const Eigen::MatrixXf &bboxes2);
Eigen::MatrixXf giou_batch(const Eigen::MatrixXf &bboxes1, const Eigen::MatrixXf &bboxes2);
std::tuple<std::vector<Eigen::Matrix<int, 1, 2>>, std::vector<int>, std::vector<int>>
associate(Eigen::MatrixXf detections, Eigen::MatrixXf trackers,
    Eigen::MatrixXf dets_embs, Eigen::MatrixXf trk_embs, float iou_threshold,
    Eigen::MatrixXf velocities, Eigen::MatrixXf previous_obs_,
    float vdc_weightfloat, float w_assoc_emb, bool aw_off, float aw_param);
} // namespace ocsort

#endif // OC_SORT_CPP_ASSOCIATION_HPP
