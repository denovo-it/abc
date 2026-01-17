# Preparing the FastSAM pipeline for Deployment

This guide describes how to prepare the FastSAM pipeline to compile for metis using the voyager SDK.
The first section describes how the ONNX models for the FastSAM segmentation model and the CLIP vision encoder were obtained.
This allows users to reuse the pipeline for other variation of the models.
The second section explains how to deploy the ONNX models and also offers pre-exported ONNX models.
Finally, we offer a prebuilt package to get quickly started without needing to compile the models.


## Preparing the FastSAM segmentation model.

The ONNX file for the FastSAM segmentation model can be obtained from ultralytics:
https://docs.ultralytics.com/reference/models/fastsam/model/#ultralytics.models.fastsam.model.FastSAM

```bash
pip install ultralytics
```

```python
from ultralytics import FastSAM

# Load the FastSAM-S model
model = FastSAM('FastSAM-s.pt')

# Export to ONNX format
model.export(format='onnx', 
             dynamic=False,  # Enable dynamic input shapes
             simplify=True,  # Simplify the model
             opset=11)  # ONNX opset version
```

## Preparing the CLIP vision encoder

Users can choose between different variations: `RN50`, `RN101` or `RN50x4`. 

1. Export the vision encoder to ONNX
```python
import clip
import torch
import onnx
from onnxsim import simplify

model, preprocess = clip.load('RN50x4')
model_path = 'clip_rn50x4_bs1.onnx'

model.eval()

image_size = preprocess.transforms[0].size

with torch.no_grad():
    torch.onnx.export(model.visual,torch.randn(1,3,image_size,image_size),model_path,opset_version=14)

model = onnx.load(model_path)
# Simplify the model
model_simplified, check = simplify(model)
model_path_simp = 'clip_rn50x4_bs1_simp.onnx'
onnx.save(model_simplified, model_path_simp)
```

Required dependencies:

```bash
pip install git+https://github.com/openai/CLIP.git
```

2. Split the vision encoder in two parts
Currently, we offload the attention pooling of the vision encoder to the host. This requires the user to isolate this part in a separate ONNX graph. 

For the `RN50x4` model, the last node of the model that runs on metis is called `/layer4/layer4.7/relu3/Relu`. This is the first Relu after the last Conv. 
Note that this node is called differently for the different available vision encoders.


## Deploying the cascade

The above process has already been done for one variation of the CLIP encoder (`RN50x4`) and FastSAM segmentation model (`FastSAM-s`). 
Different variations of both models can be used depending on the required performance (FPS and accuracy).
When running `python deploy.py fastsams-rn50x4-onnx`, the ONNX file for the FastSAM segmentation model and the CLIP vision encoder are automatically downloaded. 
The postamble ONNX (containing the attention pooling of the vision encoder) can be manually downloaded from the following link: `https://media.axelera.ai/artifacts/reference/apps/clip_rn50x4_bs1_simp_part2_opt.onnx`

After downloading, specify the path to this file in the `pipeline/detections/inference/postamble_onnx` field within the `fastsams-rn50x4-onnx.yaml` configuration file. The file can be downloaded and saved to the appropriate location using the following command:

```bash
wget https://media.axelera.ai/artifacts/reference/apps/clip_rn50x4_bs1_simp_part2_opt.onnx -O ax_models/reference/apps/fastsam/clip-rn50x4-bs1-simp-part2-opt.onnx
```

## 📦 Precompiled cascade

To expedite setup, a precompiled model package is available for download. Extract the archive into the `build` directory using the following command:

```bash
wget https://media.axelera.ai/artifacts/reference/apps/fastsams-rn50x4-onnx-1.4-runtime4.0.zip -O fastsams-rn50x4-onnx.zip && mkdir -p build && unzip -o fastsams-rn50x4-onnx.zip -d build/fastsams-rn50x4-onnx
```

> [!NOTE]
 > The precompiled model package and the `postamble_onnx` field in the YAML configuration are supported only in SDK version 1.4 and later. These features are not compatible with earlier SDK versions. If you experience inference issues with SDK 1.4 or newer, remove the existing precompiled models using `rm -rf build/fastsams-rn50x4-onnx` and re-run the `deploy.py` script to recompile the models for your current SDK version.


## Running the FastSAM demo app

Download the test video, install the wxPython library, and run the demo app:

```bash
wget https://media.axelera.ai/artifacts/test_videos/bowl-of-fruit.mp4 -O ./media/bowl-of-fruit.mp4
sudo apt-get update && sudo apt-get install libgtk-3-dev
pip install wxpython
python ax_models/reference/apps/fastsam/fastsam-app.py
```

It will guide you to enter a text prompt to segment the video.
