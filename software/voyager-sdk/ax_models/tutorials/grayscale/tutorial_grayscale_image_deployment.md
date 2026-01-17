# Training and Deploying Grayscale Models with Voyager SDK

## Introduction

This tutorial demonstrates how to train, deploy, and build inference pipelines for grayscale-adapted deep learning models using the Voyager SDK. While many computer vision applications prefer grayscale images for specific domains like medical imaging, document scanning, or manufacturing, the computational benefits in modern CNNs are limited since the reduction only affects the first convolutional layer. Most pretrained models are trained on RGB datasets like ImageNet, creating a compatibility challenge when working with grayscale data.

However, for domain-specific applications where grayscale data is natural (X-rays, MRI scans, MNIST digits) or where datasets are inherently grayscale, adapting pretrained models can still provide significant advantages over training from scratch. Research has shown that transfer learning approaches generally outperform training from scratch on grayscale images, even when architectural modifications are required.

## Theoretical Background: Approaches for Grayscale Adaptation

Before diving into implementation, let's understand the three main approaches to handle the RGB-grayscale mismatch:

1. **Modify the model architecture**: Convert the first convolutional layer to accept single-channel inputs by combining RGB channel weights
2. **Convert grayscale to RGB**: Duplicate the grayscale channel three times to create pseudo-RGB images during preprocessing
3. **Train with RGB**: Use RGB images during training (baseline approach)

According to empirical studies, converting grayscale to RGB often yields better results than modifying the model architecture, though the optimal approach varies depending on the specific dataset and task. The Voyager SDK provides utilities to support both architectural modification and preprocessing approaches seamlessly.

For deeper insights into the theory and experimental results across different datasets, we encourage you to refer to [Transfer Learning on Grayscale Images](https://towardsdatascience.com/transfer-learning-on-greyscale-images-how-to-fine-tune-pretrained-models-on-black-and-white-9a5150755c7a/), which provides comprehensive analysis of when different approaches work best.

## Tutorial Overview

This tutorial demonstrates how to:

1. Set up a dedicated training environment
2. Train models using different grayscale adaptation approaches on the Beans dataset
3. Create deployment configurations with automatic grayscale handling
4. Build efficient inference pipelines
5. Integrate with applications using AxInferenceNet APIs

**Important Note**: We recommend training on a machine with GPU support or using Mac for optimal performance. If you're not interested in training, you can download the pre-trained model directly:

```bash
wget https://media.axelera.ai/artifacts/tutorials/grayscale_res2net50d_beans.pth -O ax_models/tutorials/grayscale/grayscale_res2net50d_beans.pth
```

## The Beans Dataset  

We'll use the Beans dataset from the AI Lab at Makerere University (MIT license), containing images of bean leaves with three classes: healthy, angular leaf spot, and bean rust. The dataset is hosted on Hugging Face and will be downloaded automatically during training.

## Part 1: Training with Different Grayscale Approaches

### Setting Up the Training Environment

To maintain separation between training and deployment dependencies, we create a dedicated training environment. This approach allows users to maintain their own training setups while keeping the deployment environment clean.

**Prerequisites**: 
- Navigate to the Voyager SDK root directory
- Ensure you're NOT in the Voyager SDK virtual environment

```bash
# From Voyager SDK root directory, ensure you're not in the SDK venv
python3 tools/setup_training_env.py
```

This script:
- Creates a new virtual environment with PyTorch and required dependencies
- Automatically detects available CUDA versions and installs appropriate PyTorch builds
- Keeps training dependencies separate from deployment environment

After setup, activate the training environment:

```bash
source training_env/bin/activate
```

### Training Models with Grayscale Support

The `train_beans.py` script implements all three approaches mentioned in the theoretical background:

1. **Modified Architecture**: Uses Voyager SDK's `convert_first_node_to_1_channel` utility to adapt the first convolutional layer
2. **RGB Model Baseline**: Standard approach using 3-channel images
3. **Grayscale to RGB**: Preprocessing approach that duplicates grayscale channels

Run the training script:

```bash
python ax_models/tutorials/grayscale/train_beans.py
```

The training configuration demonstrates the implementation of our theoretical approaches:

```python
CONFIG = {
    "model_name": "res2net50d.in1k",  # Model from timm
    "batch_size": 32,
    "num_epochs": 20,
    "learning_rate": 0.001,
    "weight_decay": 2e-5,
    "grayscale_conversion_method": "sum",  # "sum", "weighted", "average"
    "data_dir": "data/beans_dataset",
    "results_dir": Path(__file__).parent,
    "mixup_alpha": 0.2,
    "cutmix_alpha": 1.0,
    "label_smoothing": 0.1,
}
```

### Understanding the Voyager SDK Utilities

The key utility that implements our theoretical approach is `convert_first_node_to_1_channel`:

```python
from ax_models.torch.utils import convert_first_node_to_1_channel

def convert_first_node_to_1_channel(model, conversion_method='sum'):
    """
    Convert the first convolutional layer to accept grayscale input (1 channel).

    Args:
        model: The PyTorch model to modify
        conversion_method: How to combine RGB channels - options:
            - 'sum': Sum the weights of all channels
            - 'weighted': Use RGB to grayscale conversion weights (0.2989, 0.5870, 0.1140)
            - 'average': Simple average of the channel weights

    Returns:
        Modified model with first convolutional layer accepting 1-channel input
    """
```

This utility supports the three weight conversion methods we discussed in the theoretical section.

### Training Results

After training completion, you'll see performance comparisons that validate our theoretical discussion:

```
========== Results ==========
Grayscale Model (Modified Architecture): 94.53%
RGB Model: 93.75%
Grayscale-to-RGB Model (Preprocessing Approach): 93.75%
```

Interestingly, our results show that the **Modified Architecture approach performs best** with the Beans dataset, demonstrating that the optimal approach can indeed vary by dataset as mentioned in our theoretical background.

### Cleanup Training Environment

When training is complete, deactivate the training environment:

```bash
deactivate
```

## Part 2: Deployment with Automatic Grayscale Handling

Now we'll deploy our trained model using the Voyager SDK's automatic grayscale handling capabilities.

### Step 1: Create Model Configuration YAML

Create the deployment configuration file at `ax_models/tutorials/grayscale/res2net50d-grayscale-beans.yaml`:

```yaml
axelera-model-format: 1.0.0

name: res2net50d-grayscale-beans

description: res2net50d.in1k from timm, transfer learning for grayscale on iBeans dataset

model-env:
  dependencies:
    - timm
    - datasets

pipeline:
  - classifications:
      model_name: res2net50d-grayscale-beans
      input:
        color_format: GRAY
      preprocess:
        - resize:
            width: 256
            height: 256
        - centercrop:
            width: 224
            height: 224
        - torch-totensor:
        - normalize:
            mean: 0.456
            std: 0.224
      postprocess:
        - topk:
            k: 1

models:
  res2net50d-grayscale-beans:
    class: AxTimmModel
    class_path: $AXELERA_FRAMEWORK/ax_models/torch/ax_timm.py
    task_category: Classification
    input_tensor_layout: NCHW
    input_tensor_shape: [1, 1, 224, 224]
    input_color_format: GRAY
    weight_path: grayscale_best_model.pth
    dataset: BeansDataset
    num_classes: 3
    extra_kwargs:
      timm_model_args:
        name: res2net50d.in1k
        grayscale_conversion_method: sum

datasets:
  BeansDataset:
    class: CustomDataAdapter
    class_path: dataadapter.py
    data_dir_name: beans_dataset
    labels: ["angular_leaf_spot", "bean_rust", "healthy"]
```

### Automatic Grayscale Handling in AxTimmModel

The `AxTimmModel` class in `ax_timm.py` automatically handles grayscale adaptation using the same `convert_first_node_to_1_channel` utility we used in training. Key features:

1. **Automatic Architecture Modification**: When `input_color_format: GRAY` is specified, the model automatically applies grayscale conversion
2. **Configurable Conversion Method**: You can specify `grayscale_conversion_method` in `timm_model_args` (default is "sum")
3. **Classification Layer Adaptation**: Automatically adjusts the final layer for the specified number of classes:

```python
# Modify final layer to match the number of classes before loading weights
num_classes = model_info.num_classes
if num_classes:
    LOG.info(f"Adjusting output layer to {num_classes} classes")
    if hasattr(self.torch_model, 'fc'):
        in_features = self.torch_model.fc.in_features
        self.torch_model.fc = torch.nn.Linear(in_features, num_classes)
    elif hasattr(self.torch_model, 'classifier'):
        in_features = self.torch_model.classifier.in_features
        self.torch_model.classifier = torch.nn.Linear(in_features, num_classes)
    else:
        LOG.warning("Could not find classification layer to modify")
```

### Alternative Deployment Approaches

If you need a different approach for model architecture modification, you have two options:

1. **Custom Model Class**: Modify the model loading logic in your custom model class
2. **ONNX Export**: Export your trained model to ONNX format and use:

```yaml
models:
  your-model-name:
    class: AxONNXModel
    class_path: $AXELERA_FRAMEWORK/ax_models/base_onnx.py
    weight_path: your_model.onnx
```

### Step 2: Create Custom Data Adapter

The data adapter handles dataset loading and preprocessing. Create `dataadapter.py` in the same directory:

```python
import os

from datasets import load_dataset
import torch
from torch.utils.data import DataLoader
from torchvision import transforms

from ax_models.tutorials.grayscale.beans_dataset import BeansDataset
from axelera import types
from axelera.app import eval_interfaces


class CustomDataAdapter(types.DataAdapter):
    def __init__(self, dataset_config, model_info):
        pass

    def create_calibration_data_loader(self, transform, root, batch_size, **kwargs):
        return DataLoader(
            BeansDataset(
                load_dataset("AI-Lab-Makerere/beans", cache_dir=root)["train"],
                transform=transform,
            ),
            batch_size=batch_size,
            shuffle=True,
            collate_fn=lambda x: x,
            num_workers=4,
        )

    def reformat_for_calibration(self, batched_data):
        images = []
        for data, _ in batched_data:
            images.append(data)
        return torch.stack(images, 0)

    def create_validation_data_loader(self, root, target_split, **kwargs):
        # Map target splits to Hugging Face dataset splits
        if target_split == 'train':
            split = 'train'
        elif target_split == 'val':
            split = 'validation'
        elif target_split == 'test':
            split = 'test'

        return DataLoader(
            BeansDataset(
                load_dataset("AI-Lab-Makerere/beans", cache_dir=root)[split],
            ),
            batch_size=1,
            shuffle=True,
            collate_fn=lambda x: x,
            num_workers=4,
        )

    def reformat_for_validation(self, batched_data):
        return [
            types.FrameInput.from_image(
                img=img,
                color_format=types.ColorFormat.GRAY,
                ground_truth=eval_interfaces.ClassificationGroundTruthSample(class_id=target),
                img_id=f'img_{i}',
            )
            for i, (img, target) in enumerate(batched_data)
        ]

    def evaluator(
        self, dataset_root, dataset_config, model_info, custom_config, pair_validation=False
    ):
        from ax_evaluators.classification import ClassificationEvaluator
        return ClassificationEvaluator(top_k=1)
```

**Note on Dataset Split Mapping**: The split mapping (`train`/`val`/`test` to Hugging Face splits) is implemented in our custom data adapter as a convenience feature. This is not mandatory - you can have a single dataset split and use just `dataset` in the inference command to run on that set.

## Part 3: Pipeline Building and Deployment

### Deploy the Model

Navigate to the Voyager SDK root directory and activate the deployment environment:

```bash
# Ensure you're in the Voyager SDK root directory
source venv/bin/activate
```

Deploy the model (this builds the inference pipeline):

```bash
./deploy.py res2net50d-grayscale-beans
```

The deployment process:
1. Loads the model with automatic grayscale handling
2. Builds the preprocessing pipeline from YAML configuration
3. Deploys the model for running on the AIPU

### Run Inference and Validation

#### Validate FP32 Accuracy on Host/GPU

```bash
./inference.py res2net50d-grayscale-beans dataset --pipe=torch -v --no-display
```

#### Validate Quantized Accuracy on AIPU

```bash
./inference.py res2net50d-grayscale-beans dataset --pipe=torch-aipu -v --no-display
```

#### High-Performance Pipeline Inference

```bash
./inference.py res2net50d-grayscale-beans dataset --pipe=gst -v --no-display
```

The `--pipe=gst` option uses the default high-efficiency GStreamer pipeline for optimal performance.

#### Dataset Split Options

The `dataset` option is a convenience feature to allow users to specify which dataset split to use during inference. As your implementation of `create_validation_data_loader` in the custom data adapter supports multiple dataset splits, you can specify which dataset split to use during inference.
- `dataset:test` - Use test set (default if available)
- `dataset:val` - Use validation set  
- `dataset:train` - Use training set

The implementation is optional, or you can use the default dataset split while simplifying the implementation.
- `dataset` - Use the default/single dataset split

## Part 4: Application Integration

### Using AxInferenceNet APIs

For application integration, you can use the AxInferenceNet APIs to integrate the deployed model directly into your applications. Refer to `docs/tutorials/axinferencenet.md` for detailed integration examples and API documentation.

The AxInferenceNet APIs provide:
- High-level inference interfaces
- Automatic preprocessing pipeline integration
- Efficient memory management
- Multi-threading support for production applications

## Key Deployment Considerations

**Performance vs. Memory Trade-offs**: While grayscale images require less storage and memory, the computational benefits in CNNs are limited since the reduction primarily affects only the first convolutional layer. Consider this when deciding between grayscale adaptation and standard RGB models for your specific hardware constraints.

**Preprocessing Efficiency**: Declaring `input_color_format: GRAY` in your YAML configuration eliminates redundant color conversion operations in the deployment pipeline, providing measurable performance improvements in production environments.

**Model Selection Strategy**: Always experiment with multiple approaches on your specific dataset. Our Beans dataset results showed the modified architecture approach outperformed preprocessing approaches, contrary to some general literature findings.

**Conversion Method Impact**: The choice between "sum", "weighted", and "average" conversion methods can affect both accuracy and inference speed. Test all three options during validation to find the optimal balance for your use case.

**Dataset Adapter Flexibility**: Custom data adapters allow you to handle various dataset formats and split configurations. You can implement single-split datasets or complex multi-split mappings based on your validation requirements.

## Conclusion

You've successfully trained grayscale-adapted models, deployed them with automatic handling through the Voyager SDK, and built efficient inference pipelines. The complete workflow covers:

- **Training comparison** across three grayscale adaptation approaches using Voyager SDK utilities
- **Automatic deployment** with AxTimmModel's built-in grayscale conversion capabilities  
- **Pipeline optimization** through proper YAML configuration and preprocessing setup
- **Production integration** pathways via AxInferenceNet APIs

**Next Steps**: 
- Experiment with your own datasets using Voyager SDK
- Integrate the deployed models into your applications using the AxInferenceNet documentation
- Consider ONNX export for models requiring custom architecture modifications beyond what AxTimmModel provides

## References

- [Transfer Learning on Grayscale Images: Comprehensive Analysis](https://towardsdatascience.com/transfer-learning-on-greyscale-images-how-to-fine-tune-pretrained-models-on-black-and-white-9a5150755c7a/)
- [Beans Dataset](https://github.com/AI-Lab-Makerere/ibean/)
- [TIMM Library Documentation](https://timm.fast.ai/)
