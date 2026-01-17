// Copyright Axelera AI, 2025

#include <opencv2/imgproc.hpp>
#include "AxOpenCVVideoDecoder.hpp"

Ax::OpenCVVideoDecoder::OpenCVVideoDecoder(const std::string &input,
    std::function<void(cv::Mat)> frame_callback, AxVideoFormat format)
    : Ax::VideoDecode(input, frame_callback, format)
{

  try {
    // Open the video capture
    cap.open(input);
    if (!cap.isOpened()) {
      throw std::runtime_error("Could not open video input: " + input);
    }
  } catch (const std::exception &e) {
    throw std::runtime_error(
        "Error initializing OpenCVVideoDecoder: " + std::string(e.what()));
  }
}

void
Ax::OpenCVVideoDecoder::reader_func()
{
  cv::Mat frame;
  while (cap.read(frame)) {
    if (frame.empty()) {
      break; // End of video
    }
    if (format == AxVideoFormat::RGB) {
      cv::cvtColor(frame, frame, cv::COLOR_BGR2RGB);
    }
    frame_callback(std::move(frame));
  }
  frame_callback(std::move(frame));
}
