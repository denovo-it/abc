// Copyright Axelera AI, 2025
#include <map>
#include <opencv2/core.hpp>
#include "AxVideoDecode.hpp"

extern "C" {
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/imgutils.h>
#include <libavutil/mem.h>
#include <libswscale/swscale.h>
}

namespace Ax
{
class FFMpegVideoDecoder : public VideoDecode
{
  public:
  FFMpegVideoDecoder(const std::string &input,
      std::function<void(cv::Mat)> frame_callback, AxVideoFormat format);
  ~FFMpegVideoDecoder();

  protected:
  void reader_func() override;

  private:
  AVCodecContext *codec_ctx;
  AVFormatContext *format_ctx;
  SwsContext *sws_ctx;
  int video_stream_index;
  static const std::map<AxVideoFormat, AVPixelFormat> format_map;
};
} // namespace Ax
