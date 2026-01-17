// Copyright Axelera AI, 2023
#include <fstream>
#include <nlohmann/json.hpp>
#include <unordered_set>

#include "AxDataInterface.h"
#include "AxLog.hpp"
#include "AxMetaClassification.hpp"
#include "AxOpUtils.hpp"
#include "AxUtils.hpp"

extern "C" const std::unordered_set<std::string> &
allowed_properties()
{
  static const std::unordered_set<std::string> allowed_properties{ "meta_key",
    "master_meta", "score_threshold", "embeddings_file" };
  return allowed_properties;
}

struct facerec_properties {
  std::string meta_key
      = "meta_" + std::to_string(reinterpret_cast<long long unsigned int>(this));
  std::map<std::string, std::vector<double>> ref_embeddings;
  float score_threshold = 0.8;
  std::string master_meta;
};

extern "C" std::shared_ptr<void>
init_and_set_static_properties(
    const std::unordered_map<std::string, std::string> &input, Ax::Logger &logger)
{
  std::shared_ptr<facerec_properties> prop = std::make_shared<facerec_properties>();
  prop->ref_embeddings = nlohmann::json::parse(std::ifstream(input.at("embeddings_file")))
                             .get<std::map<std::string, std::vector<double>>>();
  // above throws if file not found, parse not success, get not working

  prop->meta_key = Ax::get_property(
      input, "meta_key", "landmarks_static_properties", prop->meta_key);

  prop->master_meta = Ax::get_property(
      input, "master_meta", "landmarks_static_properties", prop->master_meta);

  return prop;
}

extern "C" void
set_dynamic_properties(const std::unordered_map<std::string, std::string> &input,
    facerec_properties *prop, Ax::Logger &logger)
{
  if (input.count("score_threshold")
      && !(std::istringstream(input.at("score_threshold")) >> prop->score_threshold)) {
    throw std::runtime_error("facerec_set_dynamic_properties: Error converting score_threshold");
  }
  logger(AX_INFO) << "prop->score_threshold is " << prop->score_threshold << std::endl;
}

extern "C" void
decode_to_meta(AxTensorsInterface &tensors, facerec_properties *prop,
    unsigned int current_frame, unsigned int total_frames,
    std::unordered_map<std::string, std::unique_ptr<AxMetaBase>> &map,
    const AxDataInterface &, Ax::Logger &logger)
{
  if (1 != tensors.size()) {
    throw std::runtime_error("facerec_decode_to_meta: Number of tensors must be 1, given "
                             + std::to_string(tensors.size()));
  }
  size_t total = tensors[0].total();

  float *input_data = (float *) tensors[0].data;
  float denomsq = 0.0;
  for (size_t i_emb = 0; i_emb < total; ++i_emb) {
    denomsq += input_data[i_emb] * input_data[i_emb];
  }
  float denom = std::sqrt(denomsq);
  for (size_t i_emb = 0; i_emb < total; ++i_emb) {
    input_data[i_emb] = input_data[i_emb] / denom;
  }

  double lowest_dist = 10000;
  std::string closest_match;
  int class_id = 0;
  int id = 0;
  for (const auto &name_emb : prop->ref_embeddings) {
    auto &name = name_emb.first;
    auto &emb = name_emb.second;
    if (emb.size() != total) {
      throw std::runtime_error(
          "facerec_decode_to_meta: Size of embeddings must match size of tensor");
    }
    double dist = 0.0;
    for (size_t i_emb = 0; i_emb < total; ++i_emb) {
      dist += (emb[i_emb] - input_data[i_emb]) * (emb[i_emb] - input_data[i_emb]);
    }
    if (dist < lowest_dist) {
      lowest_dist = dist;
      closest_match = name;
      class_id = id;
    }
    ++id;
  }

  if (lowest_dist > prop->score_threshold) {
    closest_match = "No employee";
    class_id = id;
  }

  std::vector<float> scores{ static_cast<float>(lowest_dist) };
  std::vector<int> classes{ class_id };
  std::vector<std::string> labels{ closest_match };

  logger(AX_INFO) << "Employee = " << closest_match << ", id = " << class_id
                  << ", score = " << lowest_dist << std::endl;

  ax_utils::insert_meta<AxMetaClassification>(map, prop->meta_key, prop->master_meta,
      current_frame, total_frames, AxMetaClassification::scores_vec{ scores },
      AxMetaClassification::classes_vec{ classes },
      AxMetaClassification::labels_vec{ labels });
}
