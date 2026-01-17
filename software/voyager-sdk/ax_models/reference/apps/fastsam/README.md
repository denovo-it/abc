# FastSAM on metis

This reference app shows how to run a model in a hybrid fashion on both the metis AIPU and host CPU.
The app `fastsam-app.py` runs Fast Segment Anything (FastSAM) by running the vision pipeline on metis and the CLIP text encoder on the host CPU. This enables live text-based prompting on a video source.  
  
First, the vision pipeline in `fastsams-rn50x4-onnx.yaml` needs to be compiled by running `python deploy.py fastsams-rn50x4-onnx`. 
This pipeline will run FastSAM small (FastSAMs) followed by the CLIP ResNet50x4 vision encoder. These models can be modified in the fastsams-rn50x4-onnx.yaml. 

The pipeline is used in `fastsam-app.py` to generate image features on metis. Text features are generated from the CLIP text encoder that runs on the host CPU. 

  
The following diagram shows which parts of the pipeline run on metis and which parts run on the host CPU.
![fastsam_metis_diagram](https://github.com/user-attachments/assets/0445a514-fc6a-469a-b135-2391af18e7a7)

See here for a demo of this reference app https://community.axelera.ai/ideas/demo-drop-multimodal-segmentation-and-detection-on-metis-with-fast-segment-anything-177. 
