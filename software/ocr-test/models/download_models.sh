#!/bin/bash
# Download ONNX models for A.B.C. OCR PoC
# Run from models/ directory

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "==================================="
echo "Download PP-OCRv3 ONNX Models"
echo "==================================="
echo

# Check for required tools
if ! command -v pip &> /dev/null; then
    echo "Error: pip not found"
    exit 1
fi

# Install paddle2onnx if needed
if ! python3 -c "import paddle2onnx" 2>/dev/null; then
    echo "Installing paddle2onnx and paddlepaddle..."
    pip install paddle2onnx paddlepaddle --quiet
fi

# Download PP-OCRv3 Latin Recognition Model
echo "Downloading PP-OCRv3 Recognition Model..."
if [ ! -f "latin_PP-OCRv3_rec_infer.onnx" ]; then
    wget -q --show-progress https://paddleocr.bj.bcebos.com/PP-OCRv3/multilingual/latin_PP-OCRv3_rec_infer.tar
    tar xf latin_PP-OCRv3_rec_infer.tar

    echo "Converting to ONNX..."
    paddle2onnx \
        --model_dir latin_PP-OCRv3_rec_infer \
        --model_filename inference.pdmodel \
        --params_filename inference.pdiparams \
        --save_file latin_PP-OCRv3_rec_infer.onnx \
        --opset_version 11

    rm -rf latin_PP-OCRv3_rec_infer latin_PP-OCRv3_rec_infer.tar
    echo "Recognition model: OK"
else
    echo "Recognition model: already present"
fi

# Download character dictionary
echo
echo "Downloading character dictionary..."
if [ ! -f "latin_dict.txt" ]; then
    wget -q --show-progress \
        https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/release/2.6/ppocr/utils/dict/latin_dict.txt
    echo "Dictionary: OK"
else
    echo "Dictionary: already present"
fi

# Download PP-OCRv3 Detection Model
echo
echo "Downloading PP-OCRv3 Detection Model..."
if [ ! -f "ch_PP-OCRv3_det_infer.onnx" ]; then
    wget -q --show-progress https://paddleocr.bj.bcebos.com/PP-OCRv3/chinese/ch_PP-OCRv3_det_infer.tar
    tar xf ch_PP-OCRv3_det_infer.tar

    echo "Converting to ONNX..."
    paddle2onnx \
        --model_dir ch_PP-OCRv3_det_infer \
        --model_filename inference.pdmodel \
        --params_filename inference.pdiparams \
        --save_file ch_PP-OCRv3_det_infer.onnx \
        --opset_version 11

    rm -rf ch_PP-OCRv3_det_infer ch_PP-OCRv3_det_infer.tar
    echo "Detection model: OK"
else
    echo "Detection model: already present"
fi

echo
echo "==================================="
echo "Download complete!"
echo "==================================="
echo
echo "Downloaded files:"
ls -lh *.onnx *.txt 2>/dev/null || echo "(no files)"
