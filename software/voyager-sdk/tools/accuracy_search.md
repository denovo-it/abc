# Accuracy Search and Calibration Images Analysis

This Python script (`accuracy_search.py`) automates the process of finding the best accuracy for various computer vision models by iterating through different calibration image counts and random seeds. It works with any object detection, instance segmentation, and keypoint detection models that use the `ObjDataAdapter` class, including YOLO, COCO, and PascalVOC formats. The script provides comprehensive logging, summary generation, visualization capabilities, and automatic tracking of calibration images used during the search process.

## Features

### 1. Automated Accuracy Search
- Iterates through a predefined list of calibration image counts (`num_cal_images_list`).
- Iterates through a predefined list of random seeds (`cal_seeds`).
- Runs the deployment and inference process for each combination of model, calibration image count, and seed.
- Calculates and logs accuracy metrics.
- Works with any model using `ObjDataAdapter`: object detection, instance segmentation, and keypoint detection.

### 2. Custom Model Support
- Supports running the script for any YAML model configuration using the `--model` command-line argument.
- Works with both built-in models (e.g., `yolov8s-coco-onnx`) and custom user-defined models (e.g., `yolov8n-license-plate`, `yolov8n-weapons-and-knives`).
- Compatible with all models using `ObjDataAdapter` class for object detection, instance segmentation, and keypoint detection tasks.
- Supports YOLO, COCO, and PascalVOC label formats through the `ObjDataAdapter` implementation.
- Dynamically determines the target (FP32) accuracy when running for custom models.

### 3. Calibration Images Tracking and Aggregation
When running accuracy search with different calibration seeds and number of calibration images, the system automatically tracks which specific images are used for calibration. This information is saved when exporting the best models, allowing you to:

- Know exactly which images were used for calibration for each best configuration
- Aggregate all unique calibration images from multiple runs into a single zip file using the `aggregate_calibration_images.py` helper script
- Analyze and reuse the most effective calibration image sets

### 4. Deterministic Validation
- Allows specifying the number of attempts per configuration using the `--n_try` argument.
- When `n_try` is greater than 1, the script runs in a deterministic mode, using only the first calibration image count and seed.

### 5. Comprehensive Logging
- Logs results to a CSV file (`accuracy_log_<timestamp>.csv`) in a dedicated `results/<timestamp>` directory.
- Logs include timestamp, model name, number of calibration images, seed, attempt number, accuracy, target accuracy, absolute accuracy drop, relative accuracy drop, and the name of the generated ZIP file (if applicable).

### 6. Summary Generation
- Generates a YAML summary file (`accuracy_summary_<timestamp>.yaml`) in the `results/<timestamp>` directory.
- The summary includes:
  - Timestamp of the run.
  - Source log file.
  - Results for each model:
    - Best accuracy achieved.
    - Worst accuracy achieved.
    - Absolute accuracy drop for the best accuracy.
    - Relative accuracy drop for the best accuracy.
    - Target accuracy.
    - Number of calibration images used for the best accuracy.
    - Seed used for the best accuracy.
    - Attempt number for the best accuracy.
    - Name of the ZIP file containing the best configuration.
    - Statistics (mean, standard deviation) of accuracy and relative drop, grouped by `num_cal_images` and `seed`.

### 7. Visualization and Plotting
- Generates plots to visualize accuracy and variance, saved in the `results/<timestamp>` directory.
- **Accuracy vs. Calibration Images:** Shows how accuracy changes with the number of calibration images, with a rolling average for smoother lines. Includes a horizontal line indicating the target accuracy and highlights the best accuracy achieved.
- **Accuracy vs. Seed:** Shows how accuracy changes with different random seeds. Includes a horizontal line indicating the target accuracy and highlights the best accuracy achieved.
- **Accuracy Box Plot:** Displays the distribution of accuracy for each combination of calibration images and seed, using a box plot.
- **Standard Deviation vs. Calibration Images:** Shows how the standard deviation of accuracy changes with the number of calibration images.
- **Cross-Model Relative Drop Variance:** A box plot showing the distribution of relative accuracy drop across different models, sorted by median relative drop. Includes a horizontal line indicating the average target relative drop (if available).
- All plots have dynamically adjusted y-axis limits.

### 8. Early Termination
- If a target relative accuracy drop is defined for a model, the script terminates early if this target is met.

## Usage

```bash
python3 tools/accuracy_search.py [-h] [-v] [-p [PLOT]] [--model MODEL] [--n_try N_TRY] [--models MODELS]
```

### Arguments

- `-h`, `--help`: Show help message and exit.
- `-v`, `--verbose`: Enable verbose output.
- `-p [PLOT]`, `--plot [PLOT]`: Generate plots.
  - If no filename is provided (just `-p` or `--plot`), the accuracy search is run, and plots are generated based on the newly created log file.
  - If a filename is provided (e.g., `-p accuracy_log.csv`), plots are generated from the specified log file.
- `--model MODEL`: Run for a single model (e.g., `--model yolov8s-coco-onnx` or `--model yolov8n-license-plate`). Overrides the default model list.
- `--n_try N_TRY`: Number of attempts per configuration (default: 1). Use a value greater than 1 for deterministic validation.
- `--models MODELS`: Run for a list of models from a YAML file (e.g., `--models ./model_list.yaml:VALIDATION`).

## Usage Examples

### 1. Run accuracy search for built-in models

```bash
# Run the full accuracy search for all default models and generate plots
python3 tools/accuracy_search.py -p

# Run the accuracy search with verbose output
python3 tools/accuracy_search.py -v -p
```

### 2. Run accuracy search for custom models

```bash
# Run accuracy search for custom models (any format supported by ObjDataAdapter)
python3 tools/accuracy_search.py --model yolov8n-license-plate
python3 tools/accuracy_search.py --model yolov8n-weapons-and-knives

# Run accuracy search for built-in models
python3 tools/accuracy_search.py --model yolov8s-coco-onnx

# Run accuracy search for a list of models from a YAML file
python3 tools/accuracy_search.py --models ./model_list.yaml:VALIDATION
```

### 3. Deterministic validation and analysis

```bash
# Run in deterministic mode with 3 attempts
python3 tools/accuracy_search.py --n_try 3

# Generate plots from an existing log file
python3 tools/accuracy_search.py -p accuracy_log_2024-03-08_11-22-33.csv
```

## Calibration Images Workflow

### How Calibration Images Tracking Works

#### 1. Image Tracking During Calibration
The system automatically tracks calibration images in the `UnifiedDataset` class:
- When a dataset is used in 'train' mode (calibration), each accessed image path is recorded
- The tracking is global and accumulates all images used during a calibration run
- Images are tracked by their full absolute paths

#### 2. Saving Calibration Images List
During the export process in `compile.py`:
- When `--export` is used, the system saves the list of used calibration images
- The list is saved as `{model_name}_calibration_images.txt` in the model build directory
- The file contains one image path per line
- After saving, the tracking is cleared for the next run

#### 3. Aggregating Multiple Calibration Sets
Use the `aggregate_calibration_images.py` helper script to combine multiple calibration image lists:

```bash
python3 tools/aggregate_calibration_images.py /path/to/directory/with/txt/files
```

### Complete Workflow Example

```bash
# Step 1: Run accuracy search (automatically tracks and saves calibration images)
python3 tools/accuracy_search.py --model yolov8n-license-plate

# Step 2: Check the generated calibration images text files
ls build/yolov8n-license-plate/*_calibration_images.txt

# Step 3: Aggregate the best calibration images using the helper script
python3 tools/aggregate_calibration_images.py build/yolov8n-license-plate/ \
    -o yolov8n_license_plate_best_calibration_images.zip \
    --create-list \
    -v

# Step 4: Extract the aggregated images to a directory for reuse
unzip yolov8n_license_plate_best_calibration_images.zip -d data/yolov8n_license_plate_repr_imgs/

# Step 5: Update your YAML config to use the representative images for future deployments
# Add this line to your dataset configuration:
# repr_imgs_dir_path: $AXELERA_FRAMEWORK/data/yolov8n_license_plate_repr_imgs

# Step 6: Now future deployments will use these proven calibration images automatically
python3 deploy.py mc-yolov8n-license-plate --export  # Uses repr_imgs_dir_path automatically
```

### Calibration Images Aggregation Script Options

The `aggregate_calibration_images.py` helper script supports the following options:

- `input_dir`: Directory containing calibration images text files (required)
- `-o, --output`: Output zip file path (default: `aggregated_calibration_images.zip`)
- `-p, --pattern`: File pattern to match (default: `*calibration_images.txt`)
- `--no-preserve-structure`: Don't preserve directory structure in zip
- `--create-list`: Also create a text file with all unique image paths
- `-v, --verbose`: Enable verbose logging

#### Usage Examples:

```bash
# Basic usage - aggregate all *calibration_images.txt files in the directory
python3 tools/aggregate_calibration_images.py ./build/

# Specify output file
python3 tools/aggregate_calibration_images.py ./build/ -o best_calibration_images.zip

# Create a text file listing all unique images
python3 tools/aggregate_calibration_images.py ./build/ --create-list

# Don't preserve directory structure (flatten the zip)
python3 tools/aggregate_calibration_images.py ./build/ --no-preserve-structure

# Custom file pattern
python3 tools/aggregate_calibration_images.py ./build/ -p "*_calibration_*.txt"

# Verbose output
python3 tools/aggregate_calibration_images.py ./build/ -v
```

## Model Compatibility and Support

The accuracy search script works with **any computer vision model** that uses the `ObjDataAdapter` class, which includes:

- **Object Detection Models**: YOLO (v5, v8, v11, etc.), DETR, RetinaNet, SSD, etc.
- **Instance Segmentation Models**: YOLOv8-seg, Mask R-CNN, etc.
- **Keypoint Detection Models**: YOLOv8-pose, PoseNet, etc.

The `ObjDataAdapter` class supports multiple label formats:
- **YOLO/Darknet format**: Normalized xywh with center coordinates
- **COCO format**: xyxy absolute coordinates with upper-left origin
- **PascalVOC format**: xyxy absolute coordinates

## Custom Model Configuration

To use your own YAML model configuration with the accuracy search, ensure your YAML file follows the standard format. Here's an example for a license plate detection model:

```yaml
axelera-model-format: 1.0.0

name: yolov8n-license-plate

description: YOLOv8n 640x640 (license plate dataset)

pipeline:
  - detections:
      model_name: yolov8n-license-plate
      # ... pipeline configuration ...

models:
  yolov8n-license-plate:
    class: AxONNXModel
    # ... model configuration ...

datasets:
  CocoDataset-LicensePlate:
    class: ObjDataAdapter
    # ... dataset configuration ...
```

The accuracy search script will automatically:
1. Determine the target FP32 accuracy by running inference with the torch pipe
2. Test different calibration image counts and seeds
3. Track which calibration images provide the best results
4. Export the best configuration and save the calibration images list

## Default Models and Target Accuracies

The script includes a default list of models with their corresponding target accuracies and relative accuracy drops:

```python
models = {
    "yolov8s-coco-onnx": (44.8, 0.0144),
    "yolov8m-coco-onnx": (50.16, 0.0162),
    "yolov8l-coco-onnx": (52.83, 0.0126),
    "yolov8nseg-coco-onnx": (30.09, 0.0224),
    "yolov8sseg-coco-onnx": (36.65, 0.015),
    "yolov8lseg-coco-onnx": (42.75, 0.015),
    "yolov8npose-coco-onnx": (51.11, 0.015),
    "yolov8spose-coco-onnx": (60.56, 0.015),
    "yolov8lpose-coco-onnx": (68.39, 0.015),
}
```

When running for a custom model using `--model`, the target accuracy is determined dynamically by running inference with the `torch` pipe.

## File Formats

### Calibration Images Text File

Each line contains the absolute path to a calibration image:

```
/path/to/dataset/images/train2017/000000000009.jpg
/path/to/dataset/images/train2017/000000000025.jpg
/path/to/dataset/images/train2017/000000000030.jpg
...
```

### Aggregated Zip File

The zip file contains all unique images from the input text files:
- By default, preserves the original directory structure
- Use `--no-preserve-structure` to flatten the structure
- Handles duplicate filenames automatically when flattening

## Integration and Workflow

The calibration images tracking works seamlessly with the accuracy search workflow:

1. **accuracy_search.py** runs multiple experiments with different seeds/image counts
2. For each experiment, the `deploy.py` script is called with `--export`
3. During deployment, calibration images are tracked automatically
4. When the best accuracy is found and exported, the calibration images list is saved
5. You can then use `aggregate_calibration_images.py` to combine all the best sets

## Advanced Features

### Representative Images Analysis and Reuse

The `aggregate_calibration_images.py` script serves as a helper function to collect which images are most representative when searching from the calibration data. This is particularly valuable for the following workflow:

1. **One-Time Search**: Run accuracy search once to identify the best calibration images for your model
2. **Aggregate Best Images**: Use `aggregate_calibration_images.py` to collect all the best-performing calibration images into a single directory
3. **Reuse for Future Deployments**: When you update your model weights and need to redeploy, instead of spending time searching again, you can specify the aggregated calibration images directory in your YAML configuration:

```yaml
datasets:
  YourDataset:
    class: ObjDataAdapter
    class_path: $AXELERA_FRAMEWORK/ax_datasets/objdataadapter.py
    # ... other configuration ...
    repr_imgs_dir_path: $AXELERA_FRAMEWORK/data/your_best_calibration_images
```

This approach provides several benefits:

1. **Time Efficiency**: Skip the calibration search process for subsequent deployments
2. **Consistency**: Use the same proven calibration set across different model versions
3. **Reproducibility**: Ensure consistent quantization results when redeploying models
4. **Resource Optimization**: Avoid redundant computation when the calibration data quality is already established

## Notes

- **Universal Compatibility**: Works with any model using `ObjDataAdapter` - not limited to YOLO models
- **Label Format Support**: Handles YOLO, COCO, and PascalVOC formats seamlessly through `ObjDataAdapter`
- **One-Time Investment**: Run accuracy search once, then reuse the best calibration images for all future deployments
- **Efficiency Gains**: Using `repr_imgs_dir_path` eliminates the need to repeat calibration searches when updating model weights
- Image tracking only occurs during 'train' split usage (calibration)
- The tracking is global and thread-safe within a single process
- Absolute paths are used to ensure images can be found regardless of working directory
- The system handles missing images gracefully during aggregation
- Duplicate images across different runs are automatically deduplicated
- All results are timestamped and organized in the `results/` directory for easy tracking and comparison
