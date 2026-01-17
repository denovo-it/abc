![](/docs/images/Ax_Page_Banner_2500x168_01.png)
# Compiler configuration

- [Compiler configuration](#compiler-configuration)
  - [Compiler configuration in YAML](#compiler-configuration-in-yaml)
  - [Multi-core modes](#multi-core-modes)

## Compiler configuration in YAML
The compiler configuration parameters can be found in the `compilation_config` portion of `extra_kwargs` for each model in its corresponding YAML file.
```
models:
  model-name:
    class: XYZ
    ...
    extra_kwargs:
      compilation_config:
          ...
```

A full list of all configuration parameters is available [here](/docs/reference/compiler_configs_full.md).

## Multi-core modes
The default configuration will compile a model to run on a single core. To execute a model on multiple cores you can compile a model in two ways:
- Batch-1
- Batch-x (with `x > 1`)

In case of the Batch-1 mode, compilation is essentially done for a single core with constrained resources based on the `resources_used` configuration parameter. The term "resources" here mainly refers to available on-chip memory. If 4-core execution is desired, `resources_used` must be set to `1.0 / 4 = 0.25` and `aipu_cores_used` is set to `1`. Multi-core execution would normally then be achieved by instantiating the model multiple times, and dispatching frames to it in an asynchronous way.  The low level library `axruntime` can be used to achieve this, and the higher level `axinferencenet` will also do this. Please refer to [axrunmodel.md](/docs/reference/axrunmodel.md) and [axinferencenet.md](/docs/reference/axinferencenet.md) for more information. As far as the compiler is concerned, there is no dependency between the different cores, which gives the runtime freedom in running the compiled model on the available cores. This usually results in lower latency for the model as each core can begin execution immediately rather than waiting for multiple inputs to be ready. However, on some models this may result in lower throughput as resources are not shared as efficiently between cores.

The Batch-x mode assumes that `x` cores share the underlying on-chip memory in a co-dependent way, where memory is shared amongst all cores. Within that available on-chip memory budget, the compiler has freedom in optimizing for all cores jointly. Setting `aipu_cores_used` to a certain number, e.g. `4`, indicates to the compiler that `4` cores share all the on-chip memory made available during compilation (i.e. the memory budget). The `resources_used` flag indicates how large the on-chip memory budget for the specified group of cores is. Setting it to `1.0` in the previous example indicates that `100%` of available on-chip memory is given to the group of `4` cores during compilation. Because memory optimization is applied across all cores, this can lead to more optimal allocations and result in higher overall troughput. Contrary to the Batch-1 mode, the runtime always executes at the granularity of `x` cores jointly, which can lead to higher latencies since individual cores cannot asynchronously fetch new inputs.

The following configurations show the most commonly used multi-core setups:
- Batch-1 running on `4` cores:
  ```
  "aipu_cores_used": 1,
  "resources_used": 0.25,
  ```
  and the model will be instantiated `4` times by the runtime.
- Batch-4 running on `4` cores:
  ```
  "aipu_cores_used": 4,
  "resources_used": 1.0,
  ```
  and the model would be instantiated just once for all 4 cores.

When setting up pipelines with multiple concatenated models, it can be desired to e.g. run one model using 3 cores and another one using 1 core. In this case, the above settings can be modified to reflect the resource allocation to the different models accordingly. For every single configuration, the `resources_used` flag must be a multiple of `0.25` and across different configurations, the sum of all `resources_used` flags must be smaller or equal to `1.0`.
