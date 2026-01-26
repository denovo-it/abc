# Copyright 2026 Denovo s.r.l.
# PP-OCRv3 Detection Model for Voyager SDK

import numpy as np
import torch
import PIL.Image

from ax_models import base_onnx
from axelera import types
from axelera.app import logging_utils

LOG = logging_utils.getLogger(__name__)


class PPOCRv3DetModel(base_onnx.AxONNXModel):
    """PP-OCRv3 Text Detection Model for Metis."""

    def override_preprocess(self, img: PIL.Image.Image | np.ndarray) -> torch.Tensor:
        """
        Preprocess image for PP-OCRv3 detection.

        Input: PIL Image or numpy array (RGB)
        Output: Tensor [1, 3, 640, 640] normalized to [-1, 1]
        """
        # Convert to numpy if PIL
        if isinstance(img, PIL.Image.Image):
            img = np.array(img)

        # Ensure RGB
        if len(img.shape) == 2:
            img = np.stack([img] * 3, axis=-1)

        h, w = img.shape[:2]
        target_size = 640

        # Resize keeping aspect ratio
        ratio = min(target_size / h, target_size / w)
        new_h = int(h * ratio)
        new_w = int(w * ratio)

        # Resize
        pil_img = PIL.Image.fromarray(img)
        pil_img = pil_img.resize((new_w, new_h), PIL.Image.BILINEAR)
        img_resized = np.array(pil_img)

        # Pad to target size
        padded = np.zeros((target_size, target_size, 3), dtype=np.float32)
        padded[:new_h, :new_w, :] = img_resized

        # Normalize to [-1, 1] (PP-OCRv3 style)
        padded = padded.astype(np.float32) / 255.0
        padded = (padded - 0.5) / 0.5

        # Convert to tensor [C, H, W]
        tensor = torch.from_numpy(padded.transpose(2, 0, 1))

        return tensor
