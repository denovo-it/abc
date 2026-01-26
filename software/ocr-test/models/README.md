# OCR Models

This directory contains the ONNX models for OCR.

## Download PP-OCRv3 Models

### Text Detection (optional for first phase)

```bash
# PP-OCRv3 Detection Model
wget https://paddleocr.bj.bcebos.com/PP-OCRv3/chinese/ch_PP-OCRv3_det_infer.tar
tar xf ch_PP-OCRv3_det_infer.tar
# Convert to ONNX with paddle2onnx if needed
```

### Text Recognition (Main model)

```bash
# PP-OCRv3 Latin Recognition Model
wget https://paddleocr.bj.bcebos.com/PP-OCRv3/multilingual/latin_PP-OCRv3_rec_infer.tar
tar xf latin_PP-OCRv3_rec_infer.tar

# Latin character dictionary
wget https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/release/2.6/ppocr/utils/dict/latin_dict.txt
```

### Conversion to ONNX

PaddlePaddle models must be converted to ONNX:

```bash
pip install paddle2onnx

# Convert recognition model
paddle2onnx --model_dir latin_PP-OCRv3_rec_infer \
    --model_filename inference.pdmodel \
    --params_filename inference.pdiparams \
    --save_file latin_PP-OCRv3_rec_infer.onnx \
    --opset_version 11
```

## Model Structure

After download, the structure should be:

```
models/
├── README.md                          # This file
├── latin_PP-OCRv3_rec_infer.onnx     # Recognition model ONNX
├── latin_dict.txt                     # Character dictionary
└── ch_PP-OCRv3_det_infer.onnx        # Detection model (optional)
```

## Recognition Model Specifications

- **Input**: `[batch, 3, 48, 320]` (NCHW)
- **Output**: Logits sequence for CTC decoding
- **Supported characters**: Extended Latin alphabet (A-Z, a-z, accents, numbers, punctuation)

## Compilation for Metis (Future)

Once the ONNX model works, it can be compiled for Metis:

```bash
cd ../voyager-sdk
source venv/bin/activate
./deploy.py ../ocr-test/models/ppocr_rec.yaml
```

See `ppocr_rec.yaml` file for Metis pipeline configuration.

## Alternatives

### EasyOCR
- URL: https://github.com/JaidedAI/EasyOCR
- Pros: Simple API
- Cons: Less optimized for edge

### TrOCR (Microsoft)
- URL: https://huggingface.co/microsoft/trocr-base-printed
- Pros: High accuracy
- Cons: Large model, difficult to compile for Metis
