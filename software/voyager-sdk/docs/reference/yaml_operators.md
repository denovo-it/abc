![](/docs/images/Ax_Page_Banner_2500x168_01.png)
# Operators available for use in network YAML files

- [Operators available for use in network YAML files](#operators-available-for-use-in-network-yaml-files)
  - [Input](#input)
  - [Preprocess](#preprocess)
    - [Geometric Transformations](#geometric-transformations)
    - [Pixel Value Transformations](#pixel-value-transformations)
    - [Color Space Transformations](#color-space-transformations)
    - [Tensor Conversion](#tensor-conversion)
  - [Mapping Your Existing Preprocess Code](#mapping-your-existing-preprocess-code)
    - [Common Code Patterns and Their Equivalents](#common-code-patterns-and-their-equivalents)
    - [Important Considerations About Normalization](#important-considerations-about-normalization)
  - [Postprocess](#postprocess)

This is a list of non-neural pre- & post-processing operators that may be referred to in the
`pipeline:` sections of network YAML files. The name in brackets is the operator name as used in the
YAML files.

## Input

*   **Input (`input`)**
    *   **Description:** Loads the input image.
    *   **Parameters:**
        *   `color_format`: (String, optional, default: `RGB`) Specifies the color format of the input image. Supported values include: `RGB`, `BGR`, and `Gray`. If not specified, the image is loaded in `RGB` format.

*   **InputFromROI (`input-from-roi`)**
    *   **Description:** Loads a region of interest (ROI) from the input image. This is used in a cascade network where the first model must output a bounding box.
    *   **Parameters:**
        *   `color_format`: (String, optional, default: `RGB`) Specifies the color format of the input image for the ROI. Supported values include: `RGB`, `BGR`, and `Gray`. If not specified, the ROI is loaded assuming the source image is in `RGB` format.
        *   Other parameters related to ROI definition (e.g., coordinates, size) would be listed here.

**Explanation of `color_format` Parameter:**

The `color_format` parameter in the `Input` and `InputFromROI` steps allows you to directly specify the color format of the source image being loaded. By setting this parameter to `RGB`, `BGR`, or `Gray`, the system can load the image in the desired color format from the beginning. The default color format is `RGB`.

**Benefit:**

Specifying the `color_format` at the input stage can potentially eliminate the need for a separate `ConvertColor` preprocessing step later in the pipeline. This can simplify your preprocessing configuration and potentially improve efficiency by avoiding an unnecessary color conversion operation. The system will handle the color format conversion during the image loading process itself.


## Preprocess

### Geometric Transformations
This category includes transformations that modify the spatial arrangement of pixels in an image.

*   **CenterCrop (`centercrop`)**:
    *   **Description:** Crops the input image from the center.
    *   **Equivalence:** Equivalent to torchvision.transforms.CenterCrop().
*   **Letterbox (`letterbox`)**:
    *   **Description:** Resizes the input image while maintaining its aspect ratio and pads the remaining areas with a constant value to fit the target dimensions. This technique is commonly used in YOLO models.
*   **Resize (`resize`)**:
    *   **Description:** Resizes the input image to the specified dimensions.
    *   **Parameters:**
        - width: Target width (integer).
        - height: Target height (integer).
        - size: If specified, the smaller edge of the image is scaled to this size while preserving the aspect ratio. Do not specify both width/height and size.
        - half_pixel_centers: (Boolean, default: False) If True, uses half-pixel centers for resizing (currently supported by the OpenCV backend only).
        - interpolation: (String or InterpolationMode, default: bilinear) Specifies the interpolation algorithm to use. Supported options include: nearest, bilinear, bicubic, and lanczos.
        - Note: The backend may choose a different interpolation mode if the specified one is not supported, and a warning will be logged.
        - Examples:
        - YAML: interpolation: nearest
        - Python: operators.Resize(interpolation=operators.InterpolationMode.nearest) or Resize(interpolation='nearest')

### Pixel Value Transformations
This category includes various normalization techniques that modify the intensity values of the pixels in an image. It's important to understand the color format of your images (e.g., RGB, BGR, Grayscale) to apply these transformations correctly.

*   **ContrastNormalize (`contrast-normalize`)**
    *   **Description:** Performs contrast stretching by linearly mapping the pixel values to the full available range.
    *   **Formula:** `(input - min) / (max - min)`
    *   **When to use:** For enhancing image contrast, especially for images with poor contrast.
    *   **Identifying in code:** Look for operations that find min/max values of an image and scale based on that range.

*   **LinearScaling (`linear-scaling`)**
    *   **Description:** Applies a linear transformation using scale and shift values.
    *   **Formula:** `output = input * scale + shift`
    *   **When to use:** When transforming from one value range to another, e.g., [0,255] → [-1,1]
    *   **Common patterns:**
        - `img / 255.0` → scales [0,255] to [0,1]
        - `img * (2/255) - 1` → scales [0,255] to [-1,1]
        - `img -= 127.5; img *= 0.0078125` → scales [0,255] to [-1,1] (0.0078125 = 1/128)

*   **Normalize (`normalize`)**
    *   **Description:** Standardizes pixel values using specified mean and standard deviation.
    *   **Formula:** `output[channel] = (input[channel] - mean[channel]) / std[channel]`
    *   **When to use:** When using pre-trained models that expect standardized inputs.
    *   **Common examples:**
        - ImageNet normalization: mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
        - Mean centering: mean=127.5, std=127.5 or std=128.0

**Important Note on Color Channels:** When using `Normalize`, provide the correct `mean` and `std` values for each color channel of your input image. For RGB images, provide three values for both `mean` and `std`. If you provide only single values, they'll be applied to all channels.

### Color Space Transformations
This category includes transformations that change the color representation of the image.

*   **ConvertColor (`convert-color`)**
    *   **Description:** Converts the color space of the input image.
    *   **Parameter Format:** Follows OpenCV's cvtColor conventions (e.g., RGB2BGR, YUV2RGB). Developers must know the exact input and output color formats.
    *   **Supported Conversions:**
        - RGB2GRAY
        - GRAY2RGB
        - RGB2BGR
        - BGR2RGB
        - BGR2GRAY
        - GRAY2BGR

### Tensor Conversion

*   **TorchToTensor (`torch-totensor`)**
    *   **Description:** Converts the input image to a PyTorch tensor.
    *   **Functionality:** Permutes the dimensions to NCHW (Number of channels, Height, Width) and, by default, normalizes pixel values to the range [0, 1].
    *   **Parameter:**
        - scale: (Boolean, default: True) If False, the pixel values are not normalized to the range [0, 1].
        - **Note:** The `scale` parameter controls whether pixel values are divided by 255. This is important to consider when combining with other normalization operations.

## Mapping Your Existing Preprocess Code

When deploying a model, you'll need to replicate the same preprocessing used during training. This section helps you identify common transform patterns from your training code and map them to our library's operators.

### Common Code Patterns and Their Equivalents

**Pattern 1: PyTorch ToTensor style normalization**
```python
# Either directly using torchvision:
transforms.ToTensor()

# Or manually implemented as:
def transform(img):
    img = img.astype('float32')
    img = img / 255.0  # Scale to [0,1]
    img = np.transpose(img, (2, 0, 1))  # HWC to CHW
    return img
```

Map to: Our library's torch-totensor operator with default settings:

```yaml
- torch-totensor:
    scale: true  # Default value, can be omitted
```

**Pattern 2: Scale to [-1,1] with transpose**

```python
def transform(img):
    img = img.astype('float32')
    img = img / 127.5 - 1  # Scale to [-1,1]
    img = np.transpose(img, (2, 0, 1))  # HWC to CHW
    return img
```

Map to:

```yaml
- linear-scaling:
    scale: 0.00784  # 1/127.5
    shift: -1
- torch-totensor:
    scale: false  # Important: disable scaling in torch-totensor
```

**Pattern 3: Mean and std normalization (e.g., ImageNet preprocessing)**

```python
# Using torchvision:
transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# Or manually:
def transform(img):
    # ImageNet normalization values (RGB channels)
    mean = [0.485, 0.456, 0.406]  # Pre-computed from ImageNet training set
    std = [0.229, 0.224, 0.225]   # Pre-computed from ImageNet training set
    
    img = img.astype('float32')
    img = img / 255.0  # Scale to [0,1]
    img = (img - mean) / std  # Standardization using dataset statistics
    img = np.transpose(img, (2, 0, 1))  # HWC to CHW
    return img

# Alternative: parameterized version
def transform(img, mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]):
    img = img.astype('float32')
    img = img / 255.0
    img = (img - np.array(mean)) / np.array(std)
    img = np.transpose(img, (2, 0, 1))
    return img
```

**Note**: The mean and std values should be chosen based on your use case:

- **Transfer Learning from ImageNet models**: Use ImageNet stats `[0.485, 0.456, 0.406]` and `[0.229, 0.224, 0.225]` to match what the pre-trained model expects
- **Training from scratch**: Compute mean and std from your own dataset statistics for optimal performance
- **Fine-tuning**: Generally use the same normalization as the original pre-trained model

The ImageNet values shown are the standard statistics computed across millions of training images and are required when using models pre-trained on ImageNet (ResNet, EfficientNet, etc.).

Map to:

```yaml
# For torchvision's standard pattern (ToTensor followed by Normalize):
- torch-totensor:
    scale: true
- normalize:
    mean: [0.485, 0.456, 0.406]
    std: [0.229, 0.224, 0.225]
```

**Pattern 4: Scaling with offset (common in many frameworks)**

```python
def transform(img):
    img = img.astype('float32')
    img -= 127.5
    img *= 0.0078125  # This is 1/128
    img = np.transpose(img, (2, 0, 1))
```

Map to:

```yaml
- normalize:
    mean: 127.5
    std: 128
- torch-totensor:
    scale: false  # Important: disable scaling in torch-totensor
```

### Important Considerations About Normalization

- **Torchvision's approach:** Torchvision typically uses a two-step normalization process:
  1. `ToTensor()` scales pixel values from [0,255] to [0,1]
  2. `Normalize()` then applies (pixel-mean)/std normalization

  When using this standard pattern, you should keep `scale=true` in `torch-totensor` followed by the `normalize` operator:
  ```yaml
  - torch-totensor:
      scale: true
  - normalize:
      mean: [0.485, 0.456, 0.406]
      std: [0.229, 0.224, 0.225]
  ```
  Our C++ operators will automatically optimize these calculations to avoid redundant operations.

- **Custom normalization:** When implementing custom normalization that doesn't follow torchvision's pattern (like direct scaling to [-1,1]), be careful about the hidden scaling in `torch-totensor`. In these cases, you typically want to set `scale=false`:
  ```yaml
  - linear-scaling:
      scale: 0.00784
      shift: -1
  - torch-totensor:
      scale: false
  ```
- **Color channel order:** Verify if your model expects RGB or BGR format, and use convert-color if needed.
- **Framework differences:**
  - PyTorch models typically expect CHW format with normalized values.
  - TensorFlow models often use HWC format with scaled values.
  - YOLO models frequently use letterboxing for maintaining aspect ratio.

For ready-to-use examples, refer to the pipeline templates in the [pipeline-template](/pipeline-template) directory that demonstrate preprocessing setups for various model architectures.

## Postprocess

*   DecodeSsdMobilenet (decode-ssd-mobilenet)

*   DecodeYolo (decodeyolo)

*   TopK (topk)

*   Multi-Object Tracker (SORT, OC-SORT, ByteTrack)
