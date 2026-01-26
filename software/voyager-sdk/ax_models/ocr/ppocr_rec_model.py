# Copyright 2026 Denovo s.r.l.
# PP-OCRv3 Recognition Model for Voyager SDK

import numpy as np
import torch
import PIL.Image

from ax_models import base_onnx
from axelera import types
from axelera.app import logging_utils

LOG = logging_utils.getLogger(__name__)


class PPOCRv3RecModel(base_onnx.AxONNXModel):
    """PP-OCRv3 Latin Recognition Model for Metis."""

    def override_preprocess(self, img: PIL.Image.Image | np.ndarray) -> torch.Tensor:
        """
        Preprocess image for PP-OCRv3 recognition.

        Input: PIL Image or numpy array (RGB)
        Output: Tensor [1, 3, 48, 320] normalized to [-1, 1]
        """
        # Convert to numpy if PIL
        if isinstance(img, PIL.Image.Image):
            img = np.array(img)

        # Ensure RGB
        if len(img.shape) == 2:
            img = np.stack([img] * 3, axis=-1)

        h, w = img.shape[:2]
        target_h = 48
        target_w = 320

        # Resize keeping aspect ratio
        ratio = target_h / float(h)
        new_w = min(int(w * ratio), target_w)

        # Resize
        pil_img = PIL.Image.fromarray(img)
        pil_img = pil_img.resize((new_w, target_h), PIL.Image.BILINEAR)
        img_resized = np.array(pil_img)

        # Pad to target width
        padded = np.zeros((target_h, target_w, 3), dtype=np.float32)
        padded[:, :new_w, :] = img_resized

        # Normalize to [-1, 1] (PP-OCRv3 style)
        padded = padded.astype(np.float32) / 255.0
        padded = (padded - 0.5) / 0.5

        # Convert to tensor [C, H, W]
        tensor = torch.from_numpy(padded.transpose(2, 0, 1))

        return tensor
