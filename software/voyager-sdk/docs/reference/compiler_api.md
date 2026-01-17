![](/docs/images/Ax_Page_Banner_2500x168_01.png)
# Python Compiler API

- [Python Compiler API](#python-compiler-api)
  - [Importing the API](#importing-the-api)
  - [Overview](#overview)
  - [API Reference](#api-reference)
    - [`quantize()`](#quantize)
    - [`compile()`](#compile)
  - [Basic Usage](#basic-usage)
  - [Configuration](#configuration)
    - [CompilerConfig](#compilerconfig)
  - [Usage Examples](#usage-examples)
    - [Example 1: Raw Image Data with Preprocessing](#example-1-raw-image-data-with-preprocessing)
    - [Example 2: Pre-processed Data Iterator](#example-2-pre-processed-data-iterator)
    - [Example 3: PyTorch DataLoader Integration](#example-3-pytorch-dataloader-integration)
    - [Example 4: Saving and Loading Quantized Models](#example-4-saving-and-loading-quantized-models)
    - [Example 5: Raw Image Data with Preprocessing](#example-5-raw-image-data-with-preprocessing)
  - [See Also](#see-also)

The Axelera Python Compiler API provides a streamlined workflow for quantizing and compiling neural networks for optimal inference performance on Axelera hardware.

## Importing the API

The Python Compiler API is included with the Axelera SDK. Import it using:

```python
# Recommended import pattern
from axelera import compiler
from axelera.compiler import CompilerConfig

# Usage:
# CompilerConfig()
# compiler.quantize()
# compiler.compile()
```

## Overview

The API provides a two-step workflow:
1. **Quantize**: Quantize fp32 model. Under the hood the model is analyzed and split into three parts:
   - **Preamble** (optional): Operations that must run on the host before the core model
   - **Core**: The main portion of the model that gets quantized to int8 precision and runs on the metis AIPU
   - **Postamble** (optional): Operations that must run on the host after the core model
   
   Preamble and postamble graphs are created only when the model contains operations that are not supported by the compiler/hardware or when it's more efficient to run them on the host.
2. **Compile**: Optimize the quantized model for Axelera hardware

## API Reference

### `quantize()`

```python
from axelera import compiler

def compiler.quantize(
    model: Union[torch.nn.Module, onnx.ModelProto, str],
    calibration_dataset: Iterator[Union[torch.Tensor, npt.NDArray]],
    config: CompilerConfig,
    transform_fn: Optional[Callable] = None,
) -> AxeleraQuantizedModel
```

Quantize a model to int8 precision using calibration data.

**Parameters:**

- **`model`**: Model to quantize. Supported formats:
    - `torch.nn.Module`: PyTorch model instance
    - `onnx.ModelProto`: ONNX model instance
    - `str`: Path to ONNX file

- **`calibration_dataset`**: Iterator that yields calibration samples for quantization

- **`config`**: Configuration object specifying quantization parameters

- **`transform_fn`** (optional): Preprocessing function to transform iterator output into model input format

**Returns:**

- `AxeleraQuantizedModel`: Quantized model that supports CPU inference for validation

**How the Quantized Model Works:**

The returned `AxeleraQuantizedModel` implements an inference pipeline with the following stages:

1. **Preamble** (optional): If the model has preamble operations (that cannot run on the AIPU), they are executed using ONNX Runtime
2. **Quantization**: Input tensors are quantized from float32 to int8 using scale and zero-point parameters
3. **Core Model**: The quantized PyTorch JIT model that can be compiled and run on the metis AIPU 
4. **Dequantization**: Output tensors are converted back from int8 to float32
5. **Postamble** (optional): Any remaining operations are executed using ONNX Runtime

When you call the quantized model with input data:
```python
# This happens internally when you call: output = quantized_model(fp32_input)
# 1. Preamble (if needed)
preamble_output = preamble_graph(fp32_input)
# 2. Quantize inputs
quantized_input = quantize(preamble_output, scale, zero_point)
# 3. Run core quantized model
quantized_output = core_model(quantized_input)
# 4. Dequantize outputs
dequantized = dequantize(quantized_output, scale, zero_point)
# 5. Postamble (if needed)
output = postamble_graph(dequantized)
```

This design allows:
- Validation of quantization accuracy on CPU before hardware compilation
- Automatic handling of pre/post-processing operations that can't be deployed on hardware

### `compile()`

```python
def compiler.compile(
    model: AxeleraQuantizedModel,
    config: CompilerConfig,
    output_dir: Path
) -> None
```

Compile a quantized model for deployment on Axelera hardware.

**Parameters:**

- **`model`**: Quantized model from `quantize()` function

- **`config`**: Compilation configuration

- **`output_dir`**: Directory where compiled artifacts will be saved

**Returns:**

- `None`: Compiled model artifacts are saved to output_dir

**Note:** The compiled artifacts include all necessary files for deployment on Axelera hardware.

## Basic Usage

The most basic use case might look like this:

```python
from pathlib import Path
from torch.utils.data import DataLoader
from axelera import compiler
from axelera.compiler import CompilerConfig

# 1. Prepare calibration dataloader
torch_loader = DataLoader(...)

# 2. Define a transform function to extract image tensor from DataLoader batch tuple. 
#    This step is optional if your calibration dataset already yields data in the correct format.
def extract_tensor_data(batch):
    images, labels = batch  # DataLoader returns (images, labels)
    return images

# 3. Configure and quantize
config = CompilerConfig()
quantized_model = compiler.quantize(
    model="model.onnx",  # or PyTorch model
    calibration_dataset=create_calibration_data(),
    config=config
    transform_fn=extract_tensor_data
)

# 4. Compile for hardware
compiler.compile(
    model=quantized_model,
    config=config,
    output_dir=Path("./compiled_model")
)
```

Here's a breakdown of the steps:
Steps to quantize and compile a model using PyTorch DataLoader:

1. **Create a DataLoader**: Set up a PyTorch DataLoader that provides batches of calibration data for the quantization process.
2. **Define transform function (optional)**: Create a function that extracts only the image tensors from DataLoader batches, discarding labels or other metadata. This step is optional if your calibration dataset already yields data in the correct format.
3. **Configure quantization**: Create a CompilerConfig object with desired settings.
4. **Quantize the model**: Call `quantize()` with the model, DataLoader, config, and transform function to create an int8 quantized model.
5. **Compile for hardware**: Call `compile()` to optimize the quantized model for Axelera AIPU hardware and save deployment artifacts.

Key point: The `transform_fn` parameter is optional and is only required when the calibration dataset returns data in a format that differs from the model's expected input. In this example, it is necessary because PyTorch DataLoaders typically return (image, label) tuples, while the quantization process requires only the image tensors. If your calibration dataset already yields data in the correct format (e.g., a custom iterator that returns only properly formatted input tensors), the `transform_fn` parameter can be omitted.


## Configuration

### CompilerConfig

The `CompilerConfig` object controls both quantization and compilation behavior:

```python
from axelera.compiler import CompilerConfig

# Create with default settings
config = CompilerConfig()

# Or customize specific parameters
config = CompilerConfig(
    # Quantization settings
    ptq_scheme="per_tensor_histogram",  # Quantization scheme
    
    # Hardware settings
    aipu_cores=1,                       # Number of cores (1-4)
    resources=1.0,                      # Memory fraction (0.0-1.0)
    
    # Debugging
    save_error_artifact=True           # Save error artifacts
)
```

See the [full configuration reference](/docs/reference/compiler_configs_full.md) for all available options. And [multi-core compilation](/docs/reference/compiler_configs.md#multi-core-modes) for detailed multi-core setup guide.

## Usage Examples

### Example 1: Raw Image Data with Preprocessing

Use this approach when working with raw image files that need preprocessing.

```python
import cv2
import numpy as np
import glob
from pathlib import Path
from axelera import compiler
from axelera.compiler import CompilerConfig

def create_calibration_data():
    """Generator that yields raw images from representative dataset."""
    for img_path in glob.glob("calib_images/*.jpg")[:100]:
        img = cv2.imread(img_path)  # Load as uint8 BGR
        yield img

def transform_to_nchw(img: np.ndarray) -> np.ndarray:
    """Preprocess raw image to model input format (NCHW)."""
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # Convert BGR to RGB (assuming model has been trained on RGB images)
    img = cv2.resize(img, (640, 640))
    img = img.astype(np.float32) / 255.0
    img = np.transpose(img, (2, 0, 1))  # HWC -> CHW
    img = np.expand_dims(img, 0)       # Add batch dimension
    return img

# Configure and quantize
config = CompilerConfig(ptq_scheme="per_tensor_min_max")

qmodel = compiler.quantize(
    model="yolo11n.onnx",
    calibration_dataset=create_calibration_data(),
    config=config,
    transform_fn=transform_to_nchw
)

# Validate quantized model on host CPU
test_input = cv2.imread("test_image.jpg")
tensor = transform_to_nchw(test_input)
result = qmodel(tensor)
print(f"Quantized model output shape: {result.shape}")

# Compile for hardware
compiler.compile(qmodel, config, Path("./yolo_compiled/"))
```

### Example 2: Pre-processed Data Iterator

Use this approach when your data pipeline already handles preprocessing. No need for a separate transform function.

```python
from axelera import compiler
from axelera.compiler import CompilerConfig

def create_preprocessed_data():
    """Generator that yields preprocessed tensors ready for model input."""
    for img_path in glob.glob("calib_images/*.jpg")[:100]:
        # Load and preprocess in one step
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # Convert BGR to RGB (assuming model has been trained on RGB images)
        img = cv2.imread(img_path)
        img = cv2.resize(img, (640, 640))
        img = img.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))  # HWC -> CHW
        img = np.expand_dims(img, 0)       # Add batch dimension
        yield img

config = CompilerConfig()

# No transform function needed since data is already preprocessed
qmodel = compiler.quantize(
    model="yolo.onnx",
    calibration_dataset=create_preprocessed_data(),
    config=config
    # transform_fn omitted - data already in correct format
)
```

### Example 3: PyTorch DataLoader Integration

Integrate seamlessly with existing PyTorch data pipelines.

```python
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from axelera import compiler
from axelera.compiler import CompilerConfig

# Create PyTorch dataset with transforms
transform_pipeline = transforms.Compose([
    transforms.Resize((640, 640)),
    transforms.ToTensor()  # Converts PIL to tensor and normalizes [0,1]
])

torch_dataset = datasets.ImageFolder(
    "calibration_images/",
    transform=transform_pipeline
)

torch_loader = DataLoader(
    torch_dataset, 
    batch_size=1, 
    shuffle=False,
    num_workers=2
)

def extract_tensor_data(batch):
    """Extract image tensor from DataLoader batch tuple."""
    images, labels = batch  # DataLoader returns (images, labels)
    return images.numpy()   # Convert PyTorch tensor to numpy array

# Quantize using PyTorch model and DataLoader
qmodel = compiler.quantize(
    model=pytorch_model,  # PyTorch nn.Module
    calibration_dataset=torch_loader,
    config=CompilerConfig(),
    transform_fn=extract_tensor_data
)
```

### Example 4: Saving and Loading Quantized Models

Quantized models can be saved to disk for later use or validation. Here's how to save and load a quantized model:
```python
from axelera import compiler
from axelera.compiler import CompilerConfig
from pathlib import Path

# Quantization configuration
config = CompilerConfig(
    ptq_scheme="per_tensor_histogram",
)

# Create calibration data generator
def create_calibration_data():
  ...

# Quantize model
qmodel = compiler.quantize(
    model="resnet50.onnx",
    calibration_dataset=create_calibration_data(),
    config=config
)

# Save quantized model to disk
qmodel.export("resnet50_quantized/")  # Save quantized model for validation
```

In other scripts, you can load it using:
```python
from axelera import compiler
from axelera.compiler.quantized_model import AxeleraQuantizedModel
from axelera.compiler import CompilerConfig
from pathlib import Path

# Load quantized model from disk
qmodel = AxeleraQuantizedModel.load("resnet50_quantized/")

# Compiler configuration for multi-core execution
config = CompilerConfig(
  aipu_cores=4,
  resources=1.0, # Use all available resources
)

# Deploy for 4-core AIPU execution
compiler.compile(
    model=qmodel,
    config=config,
    output_dir=Path("resnet50_multicore/")
)

print("Model compiled for 4-core AIPU execution")
print(f"Deployment artifacts saved to: resnet50_multicore/")
```

### Example 5: Raw Image Data with Preprocessing

This final example shows how to validate accuracy on a quantized model before compiling, starting from a pytorch model.

```python
from axelera.compiler import CompilerConfig
import numpy as np
import torch
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms
from tqdm import tqdm

from axelera import compiler

model = models.resnet18(pretrained=True)
model.eval()

dummy_input = torch.randn(64, 3, 224, 224)

# Export to ONNX
with torch.no_grad():
    torch.onnx.export(
        model,
        dummy_input,
        "resnet18.onnx",
        opset_version=11,
    )

# ImageNet validation transforms
val_transforms = transforms.Compose(
    [
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)

calibration_data_path = 'data/ImageNet/train_subset'
calibration_dataset = datasets.ImageFolder(root=calibration_data_path, transform=val_transforms)
calibration_loader = DataLoader(calibration_dataset, batch_size=64, shuffle=False, num_workers=4)

val_data_path = 'data/ImageNet/val'
val_dataset = datasets.ImageFolder(root=val_data_path, transform=val_transforms)
val_loader = DataLoader(val_dataset, batch_size=64, shuffle=False, num_workers=4)


def extract_tensor_data(batch):
    """Extract image tensor from DataLoader batch tuple."""
    images, labels = batch
    return images.numpy()


qmodel = compiler.quantize(
    model="resnet18.onnx",
    calibration_dataset=calibration_loader,
    config=CompilerConfig(),
    transform_fn=extract_tensor_data,
)

correct_top1 = 0
total = 0

print(f"Evaluating quantized model")

with torch.no_grad():
    for batch_idx, (images, labels) in enumerate(tqdm(val_loader, desc="Evaluating")):

        outputs = model(images)
        labels = labels

        # accumulate prediction results
        _, predicted = torch.max(outputs, 1)
        total += labels.size(0)
        correct_top1 += (predicted == labels).sum().item()

accuracy = 100 * correct_top1 / total

print(f"Quantized Model - Top-1 Accuracy: {quantized_accuracy:.2f}%")
```


## See Also

- [Compiler CLI Reference](/docs/reference/compiler_cli.md) - Command-line interface documentation
- [Compiler Configuration Reference](/docs/reference/compiler_configs_full.md) - Full list of configuration options
- [Multi-core Compilation](/docs/reference/compiler_configs.md#multi-core-modes) - Detailed multi-core setup guide
- [AxRunModel](/docs/reference/axrunmodel.md) - Tool for running compiled models with advanced features
