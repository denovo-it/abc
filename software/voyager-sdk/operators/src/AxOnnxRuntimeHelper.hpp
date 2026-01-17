// Copyright Axelera AI, 2024
#pragma once

#include <onnxruntime_cxx_api.h>
#include <stdexcept>
#include <string>
#include <vector>
#include "AxDataInterface.h"
#include "AxLog.hpp"

namespace ax_onnxruntime
{

class OnnxRuntimeInference
{
  public:
  explicit OnnxRuntimeInference(const std::string &model_path, Ax::Logger &logger,
      int intra_op_num_threads = 4, int inter_op_num_threads = 4);
  // Old operator() kept for potential compatibility, but new method is preferred
  std::vector<Ort::Value> operator()(const std::vector<Ort::Value> &input_tensors);

  // New method using I/O Binding
  void run_with_io_binding(const std::vector<Ort::Value> &input_tensors,
      const std::vector<AxTensorInterface *> &output_tensors);

  std::vector<std::vector<int64_t>> get_input_node_dims() const
  {
    return input_node_dims;
  }
  std::vector<std::vector<int64_t>> get_output_node_dims() const
  {
    return output_node_dims;
  }
  const std::vector<std::string> &get_input_node_names() const
  {
    return input_node_names;
  }
  const std::vector<std::string> &get_output_node_names() const
  {
    return output_node_names;
  }

  std::vector<ONNXTensorElementDataType> get_input_node_types() const;
  std::vector<ONNXTensorElementDataType> get_output_node_types() const;
  std::vector<size_t> get_input_node_ranks() const;

  private:
  Ort::Env env;
  Ort::Session session;
  std::vector<std::string> input_node_names;
  std::vector<const char *> input_node_names_c;
  std::vector<std::vector<int64_t>> input_node_dims;
  std::vector<std::string> output_node_names;
  std::vector<const char *> output_node_names_c;
  std::vector<std::vector<int64_t>> output_node_dims;
  bool first_call = true;
  Ax::Logger &logger_;

  // Helper to create Ort::Value from AxTensorInterface for binding output
  Ort::Value create_output_ort_value(
      AxTensorInterface *ax_tensor, const std::vector<int64_t> &expected_dims);

  std::string inspect_format(const std::vector<int64_t> &providedDims,
      const std::vector<int64_t> &expectedDims, size_t inputIndex);
  std::vector<const char *> convert_to_c_str_vector(
      const std::vector<std::string> &string_vector);
};

} // namespace ax_onnxruntime
