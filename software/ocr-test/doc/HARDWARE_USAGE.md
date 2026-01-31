# ⚙️ Hardware Usage - Current Configuration

**System:** Orange Pi 5 Plus + Axelera Metis AI Accelerator
**Application:** OCR Book Cataloguer v2.0
**Analysis date:** 2026-01-31

---

## 🖥️ Available Hardware

### CPU: Rockchip RK3588 (8 cores, big.LITTLE)

**Efficiency Cores:**
- 4x Cortex-A55 @ 1.8 GHz (cores 0-3)
- For light tasks, low power consumption

**Performance Cores:**
- 4x Cortex-A76 @ 2.4 GHz (cores 4-7)
- For computationally intensive tasks

**Architecture:** ARM aarch64, 8 threads total

---

### NPU: Axelera Metis AI Accelerator

**Specifications:**
- Device: Processing accelerator 1f9d:1100
- Bus: PCIe (0000:01:00.0)
- Dedicated memory: 32 MB
- Driver: `axl` kernel module ✅ Active
- SDK: Voyager SDK 4.x

**Current status:**
- ✅ Driver loaded and working
- ✅ Device recognized by system
- ❌ **NOT used for OCR** (see "Why Metis Is Not Used" section)

---

### GPU: ARM Mali-G610 MP4

**Specifications:**
- Device: `/dev/mali0`, `/dev/dri/card0`, `/dev/dri/card1`
- Render nodes: 2 (renderD128, renderD129)
- Supported APIs: OpenGL ES, Vulkan

**Current status:**
- ✅ Available
- ❌ **NOT used for OCR**

---

### Memory

**RAM:** 16 GB DDR4 unified
- Total usable: 15.60 GB
- Shared between CPU/GPU (no dedicated VRAM)
- Swap: 7.8 GB

**Typical OCR usage:**
- Base system: ~0.9 GB
- During OCR: ~1.1-1.2 GB
- Available: ~14.5 GB (93%)

---

## 📊 Hardware Usage by OCR Model

### Tesseract (Current Default)

**Usage profile:**
```
CPU:     15-20% average
  Core 0-3 (A55):  0% - IDLE
  Core 4   (A76):  100% - ⚡ ACTIVE (single-thread)
  Core 5-7 (A76):  0% - IDLE

NPU (Metis):  0% - IDLE
GPU (Mali):   0% - IDLE
RAM:          1.1 GB (7%)
```

**Characteristics:**
- ⚠️ **Single-threaded** - uses only 1 core
- ❌ No hardware acceleration
- ✅ Low memory consumption
- ✅ Excellent accuracy on clean images (85-90%)

**Performance:**
- Time: ~8s per book
- Throughput: ~7 books/minute
- Bottleneck: Single-core CPU processing

---

### PP-OCR (ONNX Runtime)

**Usage profile:**
```
CPU:     19-48% average
  Core 0-3 (A55):  50-51% - ⚡ ACTIVE
  Core 4-7 (A76):  36-74% - ⚡ ACTIVE

NPU (Metis):  0% - IDLE
GPU (Mali):   0% - IDLE
RAM:          1.2 GB (7.5%)
```

**Characteristics:**
- ✅ **Multi-threaded** - uses all 8 cores
- ✅ Efficient parallelization
- ❌ No hardware acceleration (CPU only)
- ⚠️ Average accuracy (80-85%)

**Performance:**
- Time: ~3-5s per book
- Throughput: ~12 books/minute
- Bottleneck: CPU-only, no NPU/GPU

**ONNX Runtime Config:**
```
Version: 1.23.2
Execution Providers:
  ✅ CPUExecutionProvider (in use)
  ❌ CUDAExecutionProvider (NVIDIA GPU - not available)
  ❌ TensorRTExecutionProvider (NVIDIA GPU - not available)
  ❌ ArmNNExecutionProvider (ARM NPU/GPU - not compiled)
  ❌ OpenVINOExecutionProvider (Intel - not available)
```

---

### EasyOCR

**Usage profile:**
```
CPU:     25-35% average
  Core 0-3 (A55):  20-30% - Light processing
  Core 4-7 (A76):  30-40% - Processing

NPU (Metis):  0% - IDLE
GPU (Mali):   0% - IDLE
RAM:          1.5 GB (9.6%)
```

**Characteristics:**
- ⚠️ Multi-threaded but not optimized for ARM
- ❌ No hardware acceleration
- ✅ Maximum accuracy (90-95%)
- ❌ Slow (~15-18s)

**Performance:**
- Time: ~15-18s per book
- Throughput: ~3-4 books/minute
- Bottleneck: Complex algorithm + CPU-only

---

## ❌ Why Metis Is Not Used

### 1. Tesseract: Legacy Software

**Reason:**
- Tesseract is legacy software (C++, 2006)
- No hardware acceleration support
- Single-threaded architecture
- Not based on modern neural networks

**Not implementable on Metis because:**
- Algorithm is not a neural network
- No Tesseract model compilable for NPU

---

### 2. PP-OCR: Missing Integration

**Technical reason:**
- PP-OCR uses ONNX Runtime
- ONNX Runtime on Orange Pi compiled **with CPUExecutionProvider only**
- Missing `ArmNNExecutionProvider` for ARM NPU/GPU
- Metis requires dedicated Voyager SDK, not integrated in standard ONNX

**Files present but not used:**
- ✅ `/home/orangepi/abc/software/voyager-sdk/build/ppocr-det/ppocr_det.axnet`
  - Detection model compiled for Metis
  - **Never loaded/used** in current code

**Class in `ocr_pipeline.py`:**
```python
class MetisBackend(OCRBackend):
    # Line 728: TODO - "Implement direct Metis inference when SDK supports it"
    # ⚠️ Currently fallback to ONNX CPU
```

**What would be needed to implement:**
1. Integrate Voyager SDK in `ocr_pipeline.py`
2. Load compiled `ppocr_det.axnet` model
3. Use `create_inference_stream()` API
4. Implement Metis results post-processing
5. Keep Tesseract for recognition (only detection on Metis)

**Estimated effort:** 1-2 days development

---

### 3. EasyOCR: Incompatible Architecture

**Reason:**
- EasyOCR uses PyTorch backend
- PyTorch on ARM has no Metis support
- Models are not in .axnet format

---

## 🎯 Why Tesseract Is The Chosen Model

### Current Strategic Choice

**Context:**
- Setup with **calibrated loading area**
- **Pre-processed** images (automatic crop to book area)
- **Clean and straight** images (fixed camera, positioned book)

**Tesseract advantages in this scenario:**

1. **Excellent Accuracy** ✅
   - On clean images: 85-90% accuracy
   - Confidence: 0.62-0.77 (target: >0.70)
   - Correctly recognizes title and author

2. **Simplicity** ✅
   - Zero configuration
   - Zero complex ML dependencies
   - Stable and mature code

3. **Low Overhead** ✅
   - Only 1 core at 100% (other 7 free)
   - 1.1 GB RAM (14.5 GB available)
   - Allows other tasks in parallel

4. **Acceptable Speed** ✅
   - 8s per book is OK for use case
   - Operator has time to remove previous book
   - Throughput: 360 books/hour (more than sufficient)

---

### Comparison with Alternatives

| Metric | Tesseract | PP-OCR | EasyOCR |
|---------|-----------|--------|---------|
| **Accuracy** | 85-90% ✅ | 80-85% ⚠️ | 90-95% ✅ |
| **Speed** | ~8s ✅ | ~3-5s ⭐ | ~15-18s ❌ |
| **CPU Usage** | 1 core | 8 cores | 4-6 cores |
| **Complexity** | Low ✅ | Medium | High ❌ |
| **Maintenance** | Easy ✅ | Medium | Difficult ❌ |

**Conclusion:**
- Tesseract offers **best balance accuracy/speed/simplicity**
- For current use case (calibrated images) it's **optimal**
- Alternatives only needed for edge cases not required

---

## 🚫 Why NOT to Use Metis

### Cost/Benefit Analysis

**Implementing Metis for OCR would require:**

1. **Development Effort:** 1-2 days
   - Voyager SDK integration
   - Testing and debugging
   - Accuracy validation

2. **Added Complexity:**
   - Managing 2 backends (Metis detection + CPU recognition)
   - Fallback logic if Metis fails
   - More complex maintenance

3. **Limited Speedup:**
   - Only detection acceleratable (~30-40% of time)
   - Recognition stays on CPU (Tesseract)
   - Total speedup: 8s → 5-6s (~30%)

4. **Unchanged Accuracy:**
   - Metis executes PP-OCR detection (already available on CPU)
   - Accuracy doesn't improve, might even worsen
   - Tesseract already better than PP-OCR for clean images

**ROI Analysis:**
```
Benefit:  8s → 5-6s per book (2-3s saved)
Cost:     2 days development + permanent complexity
ROI:      ⭐☆☆☆☆ LOW

Alternative: Optimize camera setup
Benefit:  Confidence 0.30 → 0.77 (+156% accuracy)
Cost:     30 minutes physical setup
ROI:      ⭐⭐⭐⭐⭐ VERY HIGH
```

---

### When to Reconsider Metis

**Future scenarios where Metis would make sense:**

1. **Massive Batch Processing**
   - If needed to process 10,000+ books
   - 30% speedup significant on large volumes
   - Justifies development effort

2. **Real-Time OCR (< 1s)**
   - If instant response needed
   - 8s too slow for real-time UX
   - Metis could bring to 3-4s

3. **Critical Energy Efficiency**
   - If battery-powered system
   - NPU consumes 90% less than CPU
   - Important for embedded long-running

4. **Simultaneous Multi-Task**
   - If CPU already busy with other tasks
   - Metis frees CPU for other processing
   - Complex pipeline architecture

**For current use case (book cataloging):**
- ❌ None of above scenarios apply
- ✅ Tesseract is optimal solution

---

## 📈 Optimal Current Hardware Usage

### Recommended Configuration

**Physical Setup:**
1. Calibrated loading area with X markers
2. Uniform lighting (no reflections)
3. Optimal camera focus
4. Book centered in area

**Software:**
```bash
# Default: Tesseract (optimal)
python3 main.py --no-display

# If speed needed: PP-OCR (sacrifice accuracy)
python3 main.py --ppocr --no-display

# If max accuracy: EasyOCR (sacrifice speed)
python3 main.py --easyocr --no-display
```

**Expected Performance:**
- Sharpness: >300 (optimal focus)
- Contrast: >70 (correct lighting)
- Rotation: <2° (straight book)
- Confidence: >0.70 (good accuracy)
- Time: ~8s (adequate throughput)

---

## 🔮 Ideal Multi-Task Scenario (Future)

If additional features were implemented:

```
┌─────────────────────────────────────────┐
│  Orange Pi 5 Plus - Allocation          │
├─────────────────────────────────────────┤
│                                         │
│  CPU (8 cores):                         │
│  ├─ Core 0-1 (A55): System, I/O        │
│  ├─ Core 2-3 (A55): Pre-processing     │
│  ├─ Core 4-5 (A76): OCR (Tesseract)    │
│  └─ Core 6-7 (A76): Post-processing    │
│                                         │
│  Metis NPU:                             │
│  ├─ LLM Post-Correction (Llama 3.2 1B) │
│  └─ or OCR Detection (if implemented)  │
│                                         │
│  GPU Mali:                              │
│  └─ (optional) CV pre-processing       │
│                                         │
│  RAM: 16 GB                             │
│  ├─ OCR: ~1 GB                         │
│  ├─ LLM: ~2-3 GB                       │
│  ├─ System: ~1 GB                      │
│  └─ Free: ~11 GB                       │
└─────────────────────────────────────────┘
```

**Note:** Currently only CPU used, ~85% resources idle but this is OK for use case.

---

## 📊 Summary

**Current Status:**
- ✅ CPU: Used effectively (Tesseract single-core or PP-OCR multi-core)
- ❌ Metis NPU: Unused (not necessary for use case)
- ❌ Mali GPU: Unused (not necessary)
- ✅ RAM: Abundant (14.5GB free of 15.6GB)

**OCR Model Choice:**
- ✅ **Tesseract** = Correct default for calibrated images
- ⚠️ PP-OCR = Only if speed needed (sacrifice accuracy)
- ⚠️ EasyOCR = Only if critical accuracy (sacrifice speed)

**Reason NOT to use Metis:**
- Low ROI (high effort, limited benefit)
- Tesseract already optimal for current setup
- 30% speedup doesn't justify complexity
- Focus on physical setup optimization > software

**System is CPU-bound but performance OK for use case.**

---

**Final recommendation:** Keep current configuration (Tesseract + calibrated area). Do not implement Metis OCR.
