# Hardware Setup - Current Configuration

**System:** Orange Pi 5 Plus + Axelera Metis AI Accelerator
**Application:** A.I. Book Cataloguer (A.B.C.)
**Last update:** 2026-02-22

---

## Available Hardware

### CPU: Rockchip RK3588 (8 cores, big.LITTLE)

- 4x Cortex-A55 @ 1.8 GHz (efficiency cores, 0-3)
- 4x Cortex-A76 @ 2.4 GHz (performance cores, 4-7)
- Architecture: ARM aarch64

### NPU: Axelera Metis AI Accelerator

- Bus: PCIe (M.2)
- Dedicated memory: 32 MB
- Driver: `axl` kernel module
- SDK: Voyager SDK 1.5.2
- **Status: ACTIVE** - Used for text detection in `metis` and `hybrid` modes

### Camera: SONOFF CAM-S2

- Connection: RTSP streaming (H.264)
- Resolution: 1920x1080
- Position: Fixed above book loading area
- Used for live book cover image acquisition

### GPU: ARM Mali-G610 MP4

- Not used for OCR

### Memory

- RAM: 16 GB DDR4
- Typical OCR usage: ~1.2 GB
- Available: ~14.5 GB (93%)

---

## Hardware Usage by OCR Mode

### CPU Mode (`--model cpu`)

PP-OCR v3 Latin, full pipeline on CPU.

```
CPU:     19-48% (all 8 cores active)
Metis:   0% - IDLE
RAM:     ~1.2 GB
Speed:   ~6s/book (with multi-pass)
```

### Metis Mode (`--model metis`)

Metis accelerated text detection + CPU text recognition.

```
CPU:     10-25% (recognition only)
Metis:   ACTIVE (text detection)
RAM:     ~1.2 GB
Speed:   ~4s/book (with multi-pass)
```

The compiled PP-OCR detection model (`ppocr_det.axnet`) runs on the Metis
accelerator. Input is preprocessed to quantized int8 NHWC format, output
heatmap is dequantized and postprocessed on CPU. Text regions are then
cropped and sent to PaddleOCR CPU recognition.

### Hybrid Mode (`--model hybrid`) - DEFAULT

Runs both CPU and Metis detection in parallel, merges best results per line.

```
CPU:     25-50% (full PP-OCR + recognition)
Metis:   ACTIVE (text detection)
RAM:     ~1.2 GB
Speed:   ~8s/book (with multi-pass)
```

For each text line detected, the result with the highest confidence is selected
from either the CPU or Metis pipeline. This provides the best overall accuracy
at the cost of slightly more processing time.

---

## Multi-Pass OCR Pipeline

All three modes support multi-pass OCR (enabled by default):

1. **Pass 1:** Image upscaled 2x with light denoising (captures small text)
2. **Pass 2:** Raw original image (captures large/artistic text)
3. **Merge:** Highest confidence per text line

This doubles the OCR time but significantly improves detection of both small
publisher/subtitle text and large artistic title text.

---

## Why Metis Is Used

The Metis accelerator runs the PP-OCR text detection model, providing:

- Hardware-accelerated inference for text region detection
- Complementary detection to CPU PP-OCR (different quantization/precision)
- Ensemble approach improves accuracy over either pipeline alone

The compiled model is at:
`software/voyager-sdk/build/ppocr-det/ppocr_det/1/model.json`

### Metis API (Voyager SDK 1.5.2)

```python
from axelera import runtime as axrt

context = axrt.Context()
model = context.load_model('model.json')
input_info = model.inputs()[0]     # Tensor shape, scale, zero_point
output_info = model.outputs()[0]
device = context.device_connect()
model_inst = device.load_model_instance(model)
model_inst.run([input_buf], [output_buf])
```

---

## Performance Summary

| Mode | Speed | CPU | Metis | Best for |
|------|-------|-----|-------|----------|
| cpu | ~6s/book | 48% | idle | No accelerator available |
| metis | ~4s/book | 25% | active | Speed priority |
| hybrid | ~8s/book | 50% | active | Maximum accuracy (default) |

All times include multi-pass OCR. With `--no-preprocessing`: roughly half.

---

## OCR Engine

**PaddleOCR v3 Latin** - best balance of speed, accuracy, and multi-core
utilization on the RK3588 platform.
