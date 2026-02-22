# Hardware Setup - Current Configuration

**System:** Orange Pi 5 Plus + Axelera Metis AI Accelerator
**Application:** A.I. Book Cataloguer (A.B.C.)

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

### Camera: SONOFF CAM-S2

- Connection: RTSP streaming (H.264)
- Resolution: 1920x1080
- Position: Fixed above book loading area
- Used for live book cover image acquisition

### GPU: ARM Mali-G610 MP4

- Not used

### Memory

- RAM: 16 GB DDR4
- Typical usage: ~1.2 GB
- Available: ~14.5 GB (93%)

---

## Metis API (Voyager SDK 1.5.2)

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

The compiled detection model is at:
`software/voyager-sdk/build/ppocr-det/ppocr_det/1/model.json`
