# Copyright Axelera AI, 2025

import os
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image
import numpy as np
import torch

from axelera import types
from axelera.app import data_utils, eval_interfaces, logging_utils, utils

LOG = logging_utils.getLogger(__name__)


def read_yolo_obb_labels(lbl_path: Path, img_wh):
    """
    Read OBB labels in the normalized format:
      - class x1 y1 x2 y2 x3 y3 x4 y4

    Returns boxes as (cx, cy, w, h, theta_radians) in pixels and class ids.
    """
    W, H = img_wh
    if not lbl_path.exists():
        raise FileNotFoundError(f"Please redownload dataset. Label file not found: {lbl_path}")

    boxes = []
    classes = []
    with open(lbl_path, "r", encoding="utf-8", errors="ignore") as f:
        for line_num, ln in enumerate(f, start=1):
            s = ln.strip()
            if not s:
                continue
            parts = s.split()

            assert len(parts) == 9, (
                f"Invalid OBB label format in {lbl_path} line {line_num}: "
                f"Expected 9 values (class_id x1 y1 x2 y2 x3 y3 x4 y4), "
                f"got {len(parts)} values: '{s}'"
            )
            k = int(parts[0])
            classes.append(k)

            coords = list(map(float, parts[1:9]))
            pts = np.array(coords, dtype=np.float32).reshape(4, 2)
            pts[:, 0] *= W
            pts[:, 1] *= H
            boxes.append(pts)

    if not boxes:
        return np.zeros((0, 8), dtype=np.float32), np.zeros((0,), dtype=np.int64)

    return np.asarray(boxes, dtype=np.float32), np.asarray(classes, dtype=np.int64)


class DOTAv1Dataset(torch.utils.data.Dataset):
    IMG_SUFFIXES = {'.jpg', '.jpeg', '.png'}

    def __init__(self, images_dir: str, labels_dir: str, transform=None):
        super().__init__()
        self.images_dir = Path(images_dir)
        self.labels_dir = Path(labels_dir)
        if not self.images_dir.is_dir():
            raise FileNotFoundError(f"Images dir not found: {self.images_dir}")
        if not self.labels_dir.is_dir():
            raise FileNotFoundError(f"Labels dir not found: {self.labels_dir}")
        self.items = [
            p for p in sorted(self.images_dir.iterdir()) if p.suffix.lower() in self.IMG_SUFFIXES
        ]
        if not self.items:
            raise RuntimeError(f"No images found in {self.images_dir}")

        self.transform = transform

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i: int):
        ip = self.items[i]
        try:
            with Image.open(ip) as pil_img:
                img = np.asarray(pil_img.convert("RGB"))
        except (FileNotFoundError, OSError) as exc:
            raise FileNotFoundError(
                f"Please redownload dataset. Image file not found or corrupted: {str(ip)}"
            ) from exc

        H0, W0 = img.shape[:2]

        if self.transform:
            img = self.transform(img)

        lbl_path = self.labels_dir / (ip.stem + '.txt')
        boxes, clses = read_yolo_obb_labels(lbl_path, (W0, H0))

        cl = clses.astype(np.int32)

        return {
            'img': img,
            'bboxes': boxes,
            'cls': cl,
            'path': str(ip),
        }


class OBBDataAdapter(types.DataAdapter):
    def __init__(self, dataset_config, model_info):
        self.dataset_config = dataset_config
        self.model_info = model_info

    def create_calibration_data_loader(self, transform, root, batch_size, **kwargs):
        data_utils.check_and_download_dataset(
            dataset_name='DOTAv1DetectionOBBDataset',
            data_root_dir=root,
            split='val',
            is_private=True,
        )

        return torch.utils.data.DataLoader(
            DOTAv1Dataset(
                os.path.join(root, 'DOTAv1/images/train'),
                os.path.join(root, 'DOTAv1/labels/train'),
                transform,
            ),
            batch_size=batch_size,
            shuffle=True,
            collate_fn=lambda x: x,
            num_workers=0,
        )

    def reformat_for_calibration(self, batched_data: Any):
        return torch.stack([data['img'] for data in batched_data], 0)

    def create_validation_data_loader(self, root, target_split, **kwargs):
        data_utils.check_and_download_dataset(
            dataset_name='DOTAv1DetectionOBBDataset',
            data_root_dir=root,
            split='val',
            is_private=True,
        )

        return torch.utils.data.DataLoader(
            DOTAv1Dataset(
                os.path.join(root, 'DOTAv1/images/val'), os.path.join(root, 'DOTAv1/labels/val')
            ),
            batch_size=1,
            shuffle=False,
            collate_fn=lambda x: x,
            num_workers=0,
        )

    def reformat_for_validation(self, batched_data):
        def as_ground_truth(d):
            if 'bboxes' in d:
                return eval_interfaces.ObjDetGroundTruthSample.from_numpy(
                    d['bboxes'], d['cls'], d['path']
                )
            return None

        def as_frame_input(d):
            return types.FrameInput.from_image(
                img=types.Image.fromany(d['img']),
                ground_truth=as_ground_truth(d),
                img_id=d['path'],
            )

        return [as_frame_input(d) for d in batched_data]

    def evaluator(
        self, dataset_root, dataset_config, model_info, custom_config, pair_validation=False
    ):
        from ax_evaluators.detection_obb import DetectionOBBEvaluator

        return DetectionOBBEvaluator()
