// Copyright Axelera AI, 2025
#include <gtest/gtest.h>

#include <gmodule.h>

#include <memory>
#include <stdexcept>
#include <string>
#include <unordered_map>

#include <filesystem>
#include "AxDataInterface.h"
#include "AxLog.hpp"
#include "AxMeta.hpp"
#include "AxMetaBBox.hpp"
#include "AxMetaClassification.hpp"
#include "AxStreamerUtils.hpp"

namespace fs = std::filesystem;


class tempfile
{
  public:
  explicit tempfile(const std::string &content)
  {
    int fd = ::mkstemp(name.data());
    if (fd == -1) {
      throw std::runtime_error("Failed to create temporary file");
    }
    auto total_written = ssize_t{ 0 };
    auto to_write = content.size();
    const char *p = content.c_str();
    while (total_written != content.size()) {
      auto num_written = ::write(fd, p, to_write - total_written);
      if (num_written == -1) {
        ::close(fd);
        throw std::runtime_error("Failed to write temporary file");
      }
      total_written += num_written;
      p += num_written;
    }
    ::close(fd);
  }

  tempfile(const tempfile &) = delete;
  tempfile &operator=(const tempfile &) = delete;

  ~tempfile()
  {
    ::unlink(name.c_str());
  }

  std::string filename() const
  {
    return name;
  }

  private:
  std::string name = "/tmp/ax.XXXXXX";
};

template <typename T>
AxTensorsInterface
tensors_from_vector(std::vector<T> &tensors)
{
  return { { { int(tensors.size()) }, sizeof tensors[0], tensors.data() } };
}

inline bool
has_dma_heap()
{
  return fs::is_directory("/dev/dma_heap");
}

struct FormatParam {
  AxVideoFormat format;
  int out_format;
};

namespace Ax
{
inline std::string
StringMapAsOptions(const StringMap &m)
{
  std::vector<std::string> pairs;
  pairs.reserve(m.size());
  for (const auto &p : m) {
    pairs.push_back(p.first + ":" + p.second);
  }
  return Ax::Internal::join(pairs, ";");
}

template <typename Loaded, typename Plugin>
std::unique_ptr<Plugin>
LoadPlugin(std::string name, const StringMap &input)
{
  static Ax::Logger logger{ Ax::Severity::error, nullptr, nullptr };
  name = Ax::libname("lib" + name + ".so"); // replace .so with .so/.dll/.dylib etc
  const auto plugin_path = Ax::get_env("AX_SUBPLUGIN_PATH", "");
  name = plugin_path.empty() ? std::string{ fs::path(plugin_path) / name } : name;
  Ax::SharedLib shared(logger, name);
  auto opts = StringMapAsOptions(input);
  return std::make_unique<Loaded>(logger, std::move(shared), std::move(opts), nullptr);
}

inline auto
LoadInPlace(const std::string &name, const StringMap &input)
{
  return LoadPlugin<Ax::LoadedInPlace, Ax::InPlace>("inplace_" + name, input);
}

inline auto
LoadTransform(const std::string &name, const StringMap &input)
{
  return LoadPlugin<Ax::LoadedTransform, Ax::Transform>("transform_" + name, input);
}

inline auto
LoadDecode(const std::string &name, const StringMap &input)
{
  return LoadPlugin<Ax::LoadedDecode, Ax::Decode>("decode_" + name, input);
}
} // namespace Ax
