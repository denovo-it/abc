![](/docs/images/Ax_Page_Banner_2500x168_01.png)
# CompilerConfig

- [CompilerConfig](#compilerconfig)
  - [Properties](#properties)
  - [Definitions](#definitions)
    - [CompilerMode](#compilermode)
    - [DPUAllocationAlgorithm](#dpuallocationalgorithm)
    - [GraphCleanerCondition](#graphcleanercondition)
    - [GraphCleanerNode](#graphcleanernode)
    - [MulticoreMode](#multicoremode)
    - [ProfilingLevel](#profilinglevel)
    - [QuantizationScheme](#quantizationscheme)


*The Configuration for the Axelera AI Compiler.*


## Properties


- **`apply_pword_padding`** *(boolean)*: Applies a graph transformation to ensure that all inputs have the channel number a multiple of the PWORD. This is a requirement of the hardware and needs to be done as part of compilation. Default: `true`.

- **`rewrite_concat_to_resadd`** *(boolean)*: Converts concatenation operations to binary addition. The hardware does not have native support for concatenation. It is achieved by padding and shifting inputs and adding them together. This modification makes the graph legal by converting concatenation ops. Default: `true`.

- **`rewrite_dense_to_conv2d`** *(boolean)*: Instances of nn.dense are canonicalized to conv2d with kernel size 1x1. Native support for dense operations will come in upcoming changes. Default: `true`.

- **`remove_io_padding_and_layout_transform`** *(boolean)*: After compilation, the graph is modified such that the inputs are padded and their layouts has changed. Provided that inputs will be padded and transposed in a pre-processing step on the host, such operations should be removed from the graph. This step should always run when using the SDK and its preprocessing elements. Default: `true`.

- **`apply_arithmetic_simplification`** *(boolean)*: Applies arithmetic simplification rules (also known as fast-math) to improve performance. Warning, this optimization is not guaranteed to preserve numerics. Default: `true`.

- **`simplify_mac_before_after_lut`** *(boolean)*: Attemtps to optimize multiply-add operations preceding and following look-up-table operations. Warning, this optimization is not guaranteed to preserve numerics. Default: `true`.

- **`validate_operators`** *(boolean)*: Performs validation checks on operators to ensure compatibility with the hardware. Default: `true`.

- **`output_dir`** *(string, format: path)*: Directory path where compiler outputs, including generated code and artifacts, will be stored.

- **`remove_output_dir`** *(boolean)*: Whether to remove aka. clean the output directory before compilation. Default: `false`.

- **`compiler_dir`** *(string, format: path)*: Root directory of the compiler package, used to locate internal resources and dependencies.

- **`compiler_mode`**: The mode in which the compiler is running. This replaces the previous field 'quantize_only'. Default: `"quantize_and_lower"`.

  - **All of**

    - Refer to [CompilerMode](#compilermode)

- **`model_name`** *(string)*: Name of the model to run. This is used in logging, as well as to determine the model-specific configuration, ie a set of optimal settings for a particular model that the compiler can not yet determine on its own. Default: `""`.

- **`onnx_opset_version`** *(integer)*: ONNX opset version used during PyTorch to ONNX conversion, which is a required step in the quantization pipeline for model deployment. PyTorch models must be converted to the ONNX format before quantization and compilation for edge devices. . Minimum: `17`. Default: `17`.

- **`quantization_debug`** *(boolean)*: Debugging mode for quantization. Dumps the model after quantization for accuracy measurement and debugging. Default: `false`.

- **`quantization_scheme`**: The type of quantization to use for post-training quantization. Default: `"per_tensor_histogram"`.

  - **All of**

    - Refer to [QuantizationScheme](#quantizationscheme)

- **`model_debug_save_dir`** *(string, format: path)*: Directory to store the quantized/optimized model for debugging.

- **`quantize_dw_channel_wise`** *(boolean)*: Quantize depthwise convolution channel-wise. Default: `false`.

- **`quantized_graph_export`** *(boolean)*: Export the quantized graph to json file. Default: `true`.

- **`remove_io_quantization`** *(boolean)*: Remove quantization/dequantization of inputs/outputs from the graph. Default: `false`.

- **`run_graph_cleaner`** *(boolean)*: Whether to run the ONNX graph cleaner. Default: `true`.

- **`graph_cleaner_split_pre_post_processing`** *(boolean)*: Whether to split pre/post graph processing in graph cleaner. Default: `true`.

- **`graph_cleaner_condition`**: Condition to use for graph cleaning. Default: `null`.

  - **Any of**

    - Refer to [GraphCleanerCondition](#graphcleanercondition)

    - *null*

- **`graph_cleaner_node`**: Node name to use condition on. Default: `null`.

  - **Any of**

    - Refer to [GraphCleanerNode](#graphcleanernode)

    - *null*

- **`graph_cleaner_threshold`** *(integer)*: Threshold to use for the condition. Default: `0`.

- **`graph_cleaner_dump_core_onnx`**: Optional filename to save the ONNX model's core part after graph cleaning for debugging. Default: `null`.

  - **Any of**

    - *string*

    - *null*

- **`graph_cleaner_dump_full_opt_onnx`**: Optional filename to save the full optimized ONNX model after graph cleaning (but before any splitting) for debugging or inference. Default: `null`.

  - **Any of**

    - *string*

    - *null*

- **`remove_layout_transform_from_preamble`** *(boolean)*: Remove layout transform node (transpose or reshape) from preamble of the model in case of NHWC data layout. Default: `false`.

- **`pipeline_spatial_tiles`** *(boolean)*: Create a software pipeline for tasks within a spatial loop, across height tiles. Default: `true`.

- **`pipeline_channel_tiles`** *(boolean)*: Create a software pipeline for tasks within a channel loop, across output channel tiles. Default: `true`.

- **`inter_operator_async`** *(boolean)*: Enable asynchronous scheduling of operators in sequential pieces of IR. Default: `true`.

- **`use_list_scheduler`** *(boolean)*: Use resource-aware list scheduler for async scheduling in the compiler. Default: `false`.

- **`unroll_prologue_epilogue`** *(boolean)*: Unroll Prologue and Epilogue loops of software pipelines prior to scheduling in order to expose more parallelism to the compiler. Default: `false`.

- **`use_hw_tokens`** *(boolean)*: Enable hardware tokens to manage synchronization where possible. Default: `true`.

- **`group_ifdw_tasks`** *(boolean)*: Hoist IFDW operations to an earlier point in time. This is for better IMC weightset utilization. This also merges the DMA transfers of a group. Default: `false`.

- **`double_buffer`** *(boolean)*: Use a double-buffering scheme between the host and device memory when transferring network input and output data. This can be used to hide the latency of data transfers between the host and device. Default: `true`.

- **`max_memplan_attempts`** *(integer)*: The maximum number of loops the memory planner can take to find a valid network configuration that satisfies the memory constraints. If the memory is still overflowing after this number of attempts, the compiler will raise an error and stop the compilation. Minimum: `1`. Default: `5`.

- **`max_tiling_attempts`** *(integer)*: The number of attempts the compiler can use to tile an operator to make it fit in the memory. If the operator still does not fit after this number of attempts, the compiler will raise an error and stop the compilation. Minimum: `1`. Default: `8`.

- **`force_h_tiling`**: Force the compiler to use a specific set of tiling factors for the height dimension of the operator. Default: `null`.

  - **Any of**

    - *integer*: Minimum: `1`.

    - *null*

- **`force_oc_tiling`**: Force the compiler to use a specific set of tiling factors for the output channel dim. of the operator. Default: `null`.

  - **Any of**

    - *integer*: Minimum: `1`.

    - *null*

- **`tiling_depth`** *(integer)*: The maximum tiling depth to search for. Setting this to a value higher than 1 will make the compiler attempt to apply depth-first scheduling to the network. A good setting for this parameter is either 1 to disable depth-first scheduling or 6 if one wants to enable depth-first scheduling. Minimum: `1`. Default: `1`.

- **`dfs_search_constraint`**: Limit the search space of the depth-first algorithm. This is currently needed for large networks. If set to None, the compiler will do its default full search. If set to an integer value, the compiler will do a limited search, where 'search_space[:dfs_search_constraint]' will be the constraint search space. A good first value to set this is 1. Default: `null`.

  - **Any of**

    - *integer*

    - *null*

- **`enable_buffer_promotion`** *(boolean)*: Controls the memory optimization mechanism that allows buffers to be strategically relocated from lower memory hierarchies (e.g., DDR) to higher, faster memory levels (e.g., L2, L1). When enabled, the compiler analyzes buffer usage patterns and automatically promotes frequently accessed buffers to faster memory tiers when possible, reducing memory access latency and potentially improving execution performance. The promotion process respects configured memory constraints and works in conjunction with the defined memory pools. For fine-grained control, this can be used together with split_buffer_promotion to improve depth-first scheduling between promotion passes. Default: `true`.

- **`split_buffer_promotion`** *(boolean)*: Split buffer promotion into two separate passes: one for L1 and one for L2 such that DFS scheduling can be applied in between the two passes. This enables DFS to more effectively choose buffers for scheduling in L1. Default: `false`.

- **`io_memory_pool`** *(string)*: The initial memory home for the input/output buffers. During buffer promotion, buffers can be moved up. Must be one of: `["global.ddr", "global.l2", "global.l1"]`. Default: `"global.ddr"`.

- **`constant_memory_pool`** *(string)*: The initial memory home for the constant buffers. During buffer promotion, buffers can be moved up. Must be one of: `["global.ddr", "global.l2", "global.l1"]`. Default: `"global.ddr"`.

- **`workspace_memory_pool`** *(string)*: The initial memory home for the workspace buffers. During buffer promotion, buffers can be moved up. Must be one of: `["global.ddr", "global.l2", "global.l1"]`. Default: `"global.ddr"`.

- **`l1_constraint`**: The maximum amount of memory that the compiler is allowed to use for L1 memory. This can be used to teach the compiler about the memory constraints of the target device. Default: `null`.

  - **Any of**

    - *integer*

    - *null*

- **`l2_constraint`**: The maximum amount of memory that the compiler is allowed to use for L2 memory. This can be used to teach the compiler about the memory constraints of the target device. Default: `null`.

  - **Any of**

    - *integer*

    - *null*

- **`ddr_constraint`**: The maximum amount of memory that the compiler is allowed to use for DDR memory. This can be used to teach the compiler about the memory constraints of the target device. Default: `null`.

  - **Any of**

    - *integer*

    - *null*

- **`use_sysdma`** *(boolean)*: Use the System DMA for weight transfers between DDR and L2 and Core DMA L2 to L1 transfers. This will also create intermediate buffers in L2. If set to False, the Core DMA will directly transfer from DDR to L1. Default: `false`.

- **`ignore_weight_buffers`** *(boolean)*: Ignore weight buffers when determining tiling factor during memory scheduling. Default: `true`.

- **`dma_dual_channel`** *(boolean)*: Whether to enable the dual channel DMA optimization. Default: `true`.

- **`dpu_constants_home`** *(string)*: Determine where DPU constants are placed. Must be one of: `["global.ddr", "global.l2"]`. Default: `"global.l2"`.

- **`dpu_instructions_home`** *(string)*: Determine where DPU instructions are placed. Ok values: 'default', 'l2'. Default: `"default"`.

- **`dwpu_instructions_home`** *(string)*: Determine where DWPU instructions are placed. Ok values: 'default', 'l2'. Default: `"default"`.

- **`page_memory`** *(boolean)*: Apply paging to L2 and DDR memory to reduce memory fragmentation and increase memory utilization. Default: `true`.

- **`elf_in_ddr`** *(boolean)*: Store the ELF file in DDR memory, instead of L2 memory. Default: `true`.

- **`stream_tasklist`** *(boolean)*: Enable tasklist streaming, ie loading chunks of the tasklist into the AIPU memory on-the-fly. Default: `true`.

- **`mvm_utilization_limit`** *(number)*: The utilization limit for the MVM array. This can be used to reduce the power consumption of the MVM array by reducing the number of active MACs. Reducing the utilization limit can lead to some features, such as swICR, being automatically disabled. If that is the case, a warning message will be shown. Minimum: `0.125`. Maximum: `1.0`. Default: `1.0`.

- **`enable_icr`** *(boolean)*: Enable In-Core Replication (ICR) for layers with small output-channel counts. This can be used to improve the performance of layers with small output-channel counts. Default: `true`.

- **`icrx_force`** *(integer)*: Force a specific In-Core Replication (ICR) factor. Useful for debugging purposes. If set to -1, the factor will be automatically determined and not forced. Default: `-1`.

- **`icrx_parallel_block_threshold`** *(integer)*: The maximum number of parallel blocks on the IMC for which ICR is still applied. This can be used to limit the number of parallel blocks on the IMC for which ICR is applied. Minimum: `1`. Maximum: `4`. Default: `4`.

- **`icrx_max_factor`** *(integer)*: The maximum In-Core Replication (ICR) factor along the X direction of the image. This can be used to limit the maximum ICR factor along the X direction of the image. Minimum: `2`. Maximum: `8`. Default: `8`.

- **`enable_swicr`** *(boolean)*: Enable Subword In-Core Replication (swICR) for first layers with small input channel counts. This can be used to improve the performance of first layers with small input channel counts. Default: `true`.

- **`imc_double_buffer_pipeline`** *(boolean)*: Enable a double-buffering scheme when loading weights into the weight sets of the MVM IMC array in software pipelines. This can be used to hide the latency of loading weights. Default: `false`.

- **`imc_double_buffer_sequential`** *(boolean)*: Enable a double-buffering scheme when loading weights into the weight sets of the MVM IMC array in sequential sections of IR. This can be used to hide the latency of loading weights. Default: `false`.

- **`dpu_allocation_algorithm`**: Selects the register-allocation algorithm used by the DPU vector unit. Selecting all, tries all methods until allocation has succeeded. Default: `"try_all"`.

  - **All of**

    - Refer to [DPUAllocationAlgorithm](#dpuallocationalgorithm)

- **`softmax_neutral_value`** *(number)*: This value is used for elements that should not influence the numerics of the softmax. For example, this is used when padding dimensions so that they are pword aligned. Paddding with zeros affects the numerics, but padding this value should cause the LUTs that implement the softmax approximation to output zero. Note that this value is not ninf since that can cause rounding issues in float18. A sufficiently negative value is enough as it will exceed the highest bin of the LUT. Default: `-100000.0`.

- **`frequency`** *(integer)*: The clock frequency of the device in Hz. Minimum: `20000000`. Maximum: `800000000`. Default: `800000000`.

- **`aipu_cores_used`** *(integer)*: The number of AIPU the compiler will compile for. Minimum: `1`. Maximum: `4`. Default: `1`.

- **`resources_used`** *(number)*: The fraction of (memory) resources that the compiled model is allowed to use. Exclusive minimum: `0.0`. Maximum: `1.0`. Default: `1.0`.

- **`multicore_mode`**: The mode for multicore execution. Default: `"multiprocess"`.

  - **All of**

    - Refer to [MulticoreMode](#multicoremode)

- **`l1_size_reserved`** *(integer)*: The size of the L1 memory reserved for the system in bytes. Default: `524288`.

- **`l1_size_used`** *(integer)*: The size of the L1 memory in bytes that is available for the compiler to use. Default: `4194304`.

- **`l1_virtual_address`** *(integer)*: The virtual address of the L1 memory. Copied from mmap_config.h. Default: `206175207424`.

- **`l1_core0_physical_address`** *(integer)*: The physical address of the L1 memory in core 0. Copied from memorymap.h. This is needed because the aicore sim does not support virtual memory. Default: `402653184`.

- **`l2_size_reserved`** *(integer)*: The size of the L2 memory reserved for the system in bytes. See SDK-4992 for details on the default value. Default: `1245184`.

- **`l2_size_reserved_tasklist`** *(integer)*: The size of the L2 memory reserved per core in bytes. This primarily used to store the tasklist. Default: `1048576`.

- **`l2_size_used`** *(integer)*: The size of the L2 memory in bytes. Default: `33554432`.

- **`ddr_size_max`** *(integer)*: The size of the DDR memory in bytes. Default: `1073741824`.

- **`ddr_size_reserved`** *(integer)*: The size of the DDR memory reserved for the system in bytes. Default: `33554432`.

- **`ddr_size_used`** *(integer)*: The size of the DDR memory in bytes. Default: `1073741824`.

- **`host_processes_used`** *(integer)*: The number of host processes to use during execution. Default: `1`.

- **`input_dmabuf`** *(boolean)*: Use DMA for input data transfer. Default: `false`.

- **`output_dmabuf`** *(boolean)*: Use DMA for output data transfer. Default: `false`.

- **`runtime_dir`** *(string, format: path)*: The directory for the Axelera runtime.

- **`device_dir`** *(string, format: path)*: The directory for the device.

- **`trace_tvm_passes`** *(boolean)*: Whether to trace TVM passes. Enabling this flag collects execution details for each TVM pass, including start/end timestamps, parent-child relationships, optimization levels, etc. This information is written to the pass_dependency_graph.json file. Default: `false`.

- **`propagate_span_information`** *(boolean)*: Whether to propagate span information through the compiler. Default: `true`.

- **`profiling_levels`** *(array)*: The profiling levels to enable. Enabling multiple levels simultaneously can cause the tracing to be inaccurate. Default: `[]`.

  - **Items**: Refer to [ProfilingLevel](#profilinglevel)

- **`profiling_drop_percentile`** *(number)*: Drop the first and last n percentiles of the profiling data. This gets rid of outliers, where the chip is spinning up/down. Minimum: `0.0`. Exclusive maximum: `1.0`. Default: `0.25`.

- **`randomize_onnx_model`** *(boolean)*: Randomize the weights of any cached ONNX models before generating the error artifact. Default: `true`.

- **`save_error_artifact`** *(boolean)*: Creates an archive containing a copy of the lowered model and relevant error messages. Default: `false`.

## Definitions

### CompilerMode
  *(string)*: The operational mode of the compiler. Must be one of: `["quantize_and_lower", "quantize_only", "lower_only"]`.

### DPUAllocationAlgorithm
  *(string)*: The DPU register-allocation algorithm to use. Must be one of: `["graph", "lazy", "backjump_recursive", "try_all"]`.

### GraphCleanerCondition
  *(string)*: Available conditions for ONNX graph cleaning. Must be one of: `["maximum_weight_tensor_size", "maximum_weight_tensor_first_dimension_size"]`.

### GraphCleanerNode
  *(string)*: Available node types for graph cleaning. Must be one of: `["MatMul", "Gemm", "Clip"]`.

### MulticoreMode
  *(string)*: Multicore mode for multicore execution. Must be one of: `["multiprocess", "multithread", "batch", "cooperative", "pipeline"]`.

### ProfilingLevel
  *(string)*: Levels used to identify the type of trace line in the trace file. Must be one of: `["[?]", "[B]", "[PB]", "[PE]", "[K]", "[M]", "[T]"]`.

### QuantizationScheme
  *(string)*: Symbolic names for the quantization scheme.<br>  Attributes:
    - PER_TENSOR_HISTOGRAM: Quantizes activations per-tensor with a histogram observer,
        and weights per-channel with a minmax observer.
    - PER_TENSOR_MIN_MAX: Quantizes activations per-tensor with a min-max observer,
        and weights per-channel with a minmax observer.
    - HYBRID_PER_TENSOR_PER_CHANNEL: Quantizes the activations per-tensor with a histogram observer.
        If the activations are inputs to a depth-wise convolution, it uses per-channel
        quantization with a min-max observer. Weights are quantizers per-channel with a
        min-max observer. Must be one of: `["per_tensor_histogram", "per_tensor_min_max", "hybrid_per_tensor_per_channel"]`.
