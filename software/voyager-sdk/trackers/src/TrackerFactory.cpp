// Copyright Axelera AI, 2025
#include <stdexcept>

#include "MultiObjTracker.hpp"
#include "TrackerFactory.h"

namespace ax
{
std::string
to_string(TrackState &state)
{
  switch (state) {
    case kUndefined:
      return "Undefined";
    case kNew:
      return "New";
    case kTracked:
      return "Tracked";
    case kLost:
      return "Lost";
    case kRemoved:
      return "Removed";
    default:
      return "Unknown State";
  }
}
} // namespace ax


std::unique_ptr<ax::MultiObjTracker>
CreateMultiObjTracker(const std::string &tracker_type_str, const TrackerParams &params)
{
  static const std::unordered_map<std::string, std::function<std::unique_ptr<ax::MultiObjTracker>(const TrackerParams &)>> tracker_factory = {
    { "scalarmot",
        [](const TrackerParams &p) {
          return std::make_unique<ScalarMOTWrapper>(p);
        } },
    { "sort",
        [](const TrackerParams &p) { return std::make_unique<SORTWrapper>(p); } },
#ifdef HAVE_BYTETRACK
    { "bytetrack",
        [](const TrackerParams &p) {
          return std::make_unique<BytetrackWrapper>(p);
        } },
#endif
#ifdef HAVE_OC_SORT
    { "oc-sort",
        [](const TrackerParams &p) { return std::make_unique<OCSortWrapper>(p); } },
    { "oc_sort",
        [](const TrackerParams &p) { return std::make_unique<OCSortWrapper>(p); } },
#endif
  };

  std::string type_lower = tracker_type_str;
  std::transform(type_lower.begin(), type_lower.end(), type_lower.begin(), ::tolower);
  auto it = tracker_factory.find(type_lower);
  if (it != tracker_factory.end()) {
    return it->second(params);
  }

  throw std::runtime_error("Unknown tracker type: " + tracker_type_str);
}

//************** Wrappers of Axelera Multiple Object Trackers ***********
ScalarMOTWrapper::ScalarMOTWrapper(const TrackerParams &params)
    : tracker_(GetParamOrDefault<int>(params, "maxLostFrames", 30))
{
}

const std::vector<ax::TrackedObject>
ScalarMOTWrapper::Update(const std::vector<ax::ObservedObject> &detections,
    const std::vector<std::vector<float>> &embeddings,
    const std::optional<Eigen::Matrix<float, 2, 3>> &transform)
{
  std::vector<axtracker::BboxXyxyRelative> inputs;
  for (const auto &det : detections) {
    axtracker::BboxXyxyRelative bbox;
    bbox.x1 = det.bbox.x1;
    bbox.y1 = det.bbox.y1;
    bbox.x2 = det.bbox.x2;
    bbox.y2 = det.bbox.y2;
    bbox.class_id = det.class_id;
    bbox.score = det.score;
    inputs.push_back(bbox);
  }
  tracker_.update(inputs);

  std::vector<ax::TrackedObject> objects;
  const auto trks = tracker_.getTrackers();
  for (const auto &trk : trks) {
    auto result = trk.get_state();
    ax::TrackedObject obj(result.x1, result.y1, result.x2, result.y2,
        trk.getTrackId(), trk.getClassId());
    objects.push_back(obj);
  }

  return objects;
}

SORTWrapper::SORTWrapper(const TrackerParams &params)
    : tracker_(GetParamOrDefault<int>(params, "maxAge", 30),
        GetParamOrDefault<int>(params, "minHits", 3),
        GetParamOrDefault<float>(params, "iouThreshold", 0.3))
{
}

const std::vector<ax::TrackedObject>
SORTWrapper::Update(const std::vector<ax::ObservedObject> &detections,
    const std::vector<std::vector<float>> &embeddings,
    const std::optional<Eigen::Matrix<float, 2, 3>> &transform)
{
  std::vector<axtracker::BboxXyxyRelative> inputs;
  for (const auto &det : detections) {
    axtracker::BboxXyxyRelative bbox;
    bbox.x1 = det.bbox.x1;
    bbox.y1 = det.bbox.y1;
    bbox.x2 = det.bbox.x2;
    bbox.y2 = det.bbox.y2;
    bbox.class_id = det.class_id;
    bbox.score = det.score;
    inputs.push_back(bbox);
  }
  tracker_.update(inputs);

  std::vector<ax::TrackedObject> objects;
  const auto &trks = tracker_.getTrackers();
  for (const auto &trk : trks) {
    auto result = trk.get_state();
    ax::TrackedObject obj(result.x1, result.y1, result.x2, result.y2,
        trk.getTrackId(), trk.getClassId());
    objects.push_back(obj);
  }
  return objects;
}

// unlink axtracker

//************** Wrappers of Third-party Multiple Object Trackers ***********
#ifdef HAVE_BYTETRACK

ax::TrackState
MapSTrackTrackState(int state)
{
  using namespace ax;
  switch (state) {
    case 0: // STrack's 'New'
      return kNew;
    case 1: // STrack's 'Tracked'
      return kTracked;
    case 2: // STrack's 'Lost'
      return kLost;
    case 3: // STrack's 'Removed'
      return kRemoved;
    default:
      return kUndefined;
  }
}

BytetrackWrapper::BytetrackWrapper(const TrackerParams &params)
    : tracker_(GetParamOrDefault<int>(params, "frame_rate", 30),
        GetParamOrDefault<int>(params, "track_buffer", 30))
{
}

const std::vector<ax::TrackedObject>
BytetrackWrapper::Update(const std::vector<ax::ObservedObject> &detections,
    const std::vector<std::vector<float>> &embeddings,
    const std::optional<Eigen::Matrix<float, 2, 3>> &transform)
{
  std::vector<Object> inputs;
  std::vector<ax::TrackedObject> outputs;
  for (const auto &det : detections) {
    Object obj;
    obj.rect = cv::Rect_<float>(det.bbox.x1, det.bbox.y1,
        det.bbox.x2 - det.bbox.x1, det.bbox.y2 - det.bbox.y1);
    obj.label = det.class_id;
    obj.prob = det.score;
    inputs.push_back(obj);
  }
  vector<STrack> output_stracks = tracker_.update(inputs);

  for (const auto &trk : output_stracks) {
    ax::TrackedObject obj(trk.tlbr[0], trk.tlbr[1], trk.tlbr[2], trk.tlbr[3],
        trk.track_id, trk.label, trk.score, MapSTrackTrackState(trk.state));
    outputs.push_back(obj);
  }

  return outputs;
}
#endif

#ifdef HAVE_OC_SORT
template <int Cols>
Eigen::Matrix<float, Eigen::Dynamic, Cols>
VectorOfArrays2Matrix(const std::vector<std::array<float, Cols>> &data)
{
  Eigen::Matrix<float, Eigen::Dynamic, Cols> matrix(data.size(), Cols);
  for (int i = 0; i < data.size(); ++i) {
    for (int j = 0; j < Cols; ++j) {
      matrix(i, j) = data[i][j];
    }
  }
  return matrix;
}

Eigen::Matrix<float, Eigen::Dynamic, Eigen::Dynamic>
VectorOfVectors2Matrix(const std::vector<std::vector<float>> &data)
{
  if (data.empty()) {
    return Eigen::Matrix<float, Eigen::Dynamic, Eigen::Dynamic>();
  }
  int rows = data.size();
  int cols = data[0].size();
  Eigen::Matrix<float, Eigen::Dynamic, Eigen::Dynamic> matrix(rows, cols);
  for (int i = 0; i < rows; ++i) {
    if (data[i].size() != cols) {
      throw std::runtime_error("All rows must have the same number of columns");
    }
    for (int j = 0; j < cols; ++j) {
      matrix(i, j) = data[i][j];
    }
  }
  return matrix;
}

OCSortWrapper::OCSortWrapper(const TrackerParams &params)
    : tracker_(GetParamOrDefault<float>(params, "det_thresh", 0),
        GetParamOrDefault<int>(params, "max_age", 30),
        GetParamOrDefault<int>(params, "min_hits", 3),
        GetParamOrDefault<float>(params, "iou_threshold", 0.3),
        GetParamOrDefault<int>(params, "delta", 3),
        GetParamOrDefault<float>(params, "inertia", 0.2),
        GetParamOrDefault<float>(params, "w_assoc_emb", 0.75),
        GetParamOrDefault<float>(params, "alpha_fixed_emb", 0.95),
        // default as 0 for measurement which never reset id; 999 for demo
        GetParamOrDefault<int>(params, "max_id", 999),
        // Deep-OC-SORT parameters
        !GetParamOrDefault<bool>(params, "aw_enabled", false),
        GetParamOrDefault<float>(params, "aw_param", 0.5),
        !GetParamOrDefault<bool>(params, "cmc_enabled", false),
        GetParamOrDefault<bool>(params, "enable_id_recovery", false),
        GetParamOrDefault<int>(params, "img_width", 0),
        GetParamOrDefault<int>(params, "img_height", 0),
        GetParamOrDefault<int>(params, "rec_image_rect_margin", 20),
        GetParamOrDefault<int>(params, "rec_track_min_time_since_update_at_boundary", 6),
        GetParamOrDefault<int>(params, "rec_track_min_time_since_update_inside", 300),
        GetParamOrDefault<int>(params, "rec_track_min_age", 30),
        GetParamOrDefault<float>(params, "rec_track_merge_lap_thresh", 0.09f),
        GetParamOrDefault<int>(params, "rec_track_memory_capacity", 1000),
        GetParamOrDefault<int>(params, "rec_track_memory_max_age", 54000)) // 30min at 30fps
{
}

const std::vector<ax::TrackedObject>
OCSortWrapper::Update(const std::vector<ax::ObservedObject> &detections,
    const std::vector<std::vector<float>> &embeddings,
    const std::optional<Eigen::Matrix<float, 2, 3>> &transform)
{
  std::vector<ax::TrackedObject> outputs;
  std::vector<std::array<float, 6>> inputs;
  inputs.reserve(detections.size());

  for (const auto &det : detections) {
    inputs.emplace_back(std::array<float, 6>{ det.bbox.x1, det.bbox.y1,
        det.bbox.x2, det.bbox.y2, det.score, static_cast<float>(det.class_id) });
  }
  // Use CMC transform directly - no conversion needed!
  Eigen::Matrix<float, 2, 3> cmc_transform = Eigen::Matrix<float, 2, 3>::Identity();
  if (transform.has_value()) {
    cmc_transform = transform.value();
  }

  std::vector<Eigen::RowVectorXf> res = tracker_.update(VectorOfArrays2Matrix<6>(inputs),
      VectorOfVectors2Matrix(embeddings), cmc_transform);
  outputs.reserve(res.size()); // Reserve memory based on the expected size

  for (const auto &det : res) {
    if (det.size() != 8) {
      throw std::runtime_error("Invalid output from OC-SORT");
    }
    int class_id = static_cast<int>(det[5]);
    int latest_detection_id = static_cast<int>(det[7]);
    outputs.emplace_back(
        det[0], det[1], det[2], det[3], det[4], class_id, det[6], ax::kTracked);
    outputs.back().latest_detection_id = latest_detection_id;
  }
  return outputs;
}
#endif
