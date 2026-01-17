// Copyright Axelera AI, 2025

#include <string>
#include <vector>
#include "AxMeta.hpp"
#include "AxMetaKptsDetection.hpp"
#include "AxMetaObjectDetection.hpp"
#include "AxMetaSegmentsDetection.hpp"
#include "opencv2/opencv.hpp"

namespace Ax
{
// This file provides some simple OpenCV rendering functions for keypoint
// detection, detection, and object detection. As well as a generic render
// function that will dispatch to the correct overload based on the dynamic type
// and submetas of the AxMetaBase object passed to it.

// These renderers are not higly optimised and are meant to be used as a
// debugging tool rather than a production renderer.

namespace OpenCV
{
struct RenderOptions {
  //! \brief The labels to use for the classes. If empty, the class id will be used in the form `cls=17`
  std::vector<std::string> labels;

  //! \brief Whether to render the bounding boxes of detections
  bool render_bboxes = true;

  //! \brief Whether to render the labels of detections
  bool render_labels = true;

  //! \brief Whether to render the keypoints of keypoint detections
  bool render_keypoints = true;

  //! \brief Whether to render the connecting lines of keypoint detections (see keypoint_lines)
  bool render_keypoint_lines = true;

  //! \brief Whether to render the segments of segmentations
  bool render_segments = true;

  //! \brief Whether to render the segments of segmentations in grayscale (render_segments must be true)
  bool segments_in_grayscale = true;

  //! \brief Whether to render the submetas in a cascaded network
  bool render_submeta = true;

  // Determine how keypoints should be connected by lines, if empty no lines will be drawn
  // A -1 indicates a stop in the line. The default is suitable for yolov8Xpose-coco
  std::vector<int> keypoint_lines = {
    15, 13, 11, 5, 6, 12, 14, 16, -1, // both legs + shoulders
    5, 7, 9, -1, // left arm
    6, 8, 10, -1 // right arm
  };

  int render_rate = 10; // Frame per second to render frames (used with Display), 0 means render all frames
};

void render(const AxMetaBase &detections, cv::Mat &buffer, const RenderOptions &options);
void render(const AxMetaSegmentsDetection &segs, cv::Mat &buffer,
    const RenderOptions &options);
void render(const AxMetaObjDetection &segs, cv::Mat &buffer, const RenderOptions &options);
void render(const AxMetaKptsDetection &detections, cv::Mat &buffer,
    const RenderOptions &options);

class Display
{
  public:
  /// \brief Show the image with the metadata rendered on it using OpenCV
  /// \param image The image to show, this may be modified by the renderer
  /// \param meta The metadata to render on the image (pass an empty map to skip rendering)
  /// \param format The video format of the image (must be RGB or BGR)
  /// \param options The render options to use
  /// \param stream_id The stream id of the image, used to identify the stream in multi-stream scenarios
  virtual void show(cv::Mat &image, const Ax::MetaMap &meta,
      AxVideoFormat format, const RenderOptions &options, int stream_id)
      = 0;

  virtual ~Display() = default;
};

/// \brief Create a display that uses an OpenCV window to display the results
/// \param name The name of the window
/// \return A unique pointer to the display, on destruction the window will be closed
std::unique_ptr<Display> create_cv_display(const std::string &name);

/// \brief Create a display that uses ANSI escape codes to display the results in the console
/// \return A unique pointer to the display, on destruction the console will be reset
/// \note This display is not suitable for high quality rendering, it is intended for debugging remotely
std::unique_ptr<Display> create_ansi_display();

/// \brief Create a display that does not render anything, but shows some
/// statistics during the run. \return A unique pointer to the display.
std::unique_ptr<Display> create_null_display();

/// \brief Create a display that uses either an OpenCV window or ANSI escape
/// codes based on the DISPLAY environment variable.  Use DISPLAY=none to
/// create a null display that only shows statistics.
/// \param name The name of the window
/// \return A unique pointer to the display, on destruction the window or console will be reset
inline std::unique_ptr<Display>
create_display(const std::string &name)
{
  auto display = Ax::get_env("DISPLAY", {});
  if (display.empty()) {
    return create_ansi_display();
  } else if (display == "none") {
    return create_null_display();
  } else {
    return create_cv_display(name);
  }
}

} // namespace OpenCV

} // namespace Ax
