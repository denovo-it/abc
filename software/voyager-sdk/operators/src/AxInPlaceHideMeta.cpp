// Copyright Axelera AI, 2025
#include <unordered_set>
#include "AxDataInterface.h"
#include "AxLog.hpp"
#include "AxMeta.hpp"
#include "AxOpUtils.hpp"
#include "AxUtils.hpp"

struct streamid_properties {
  std::string meta_key{};
};

extern "C" const std::unordered_set<std::string> &
allowed_properties()
{
  static const std::unordered_set<std::string> allowed_properties{
    "meta_key",
  };
  return allowed_properties;
}

extern "C" std::shared_ptr<void>
init_and_set_static_properties(
    const std::unordered_map<std::string, std::string> &input, Ax::Logger &logger)
{
  auto prop = std::make_shared<streamid_properties>();
  prop->meta_key = Ax::get_property(
      input, "meta_key", "hidemeta_static_properties", prop->meta_key);

  return prop;
}

extern "C" void
inplace(const AxDataInterface &interface, const streamid_properties *details,
    unsigned int, unsigned int,
    std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> &map, Ax::Logger &logger)
{
  auto *meta = ax_utils::get_meta<AxMetaBase>(details->meta_key, map, "hidemeta");
  meta->enable_extern = false;
}
