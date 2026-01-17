# Copyright Axelera AI, 2025
from __future__ import annotations

from glob import glob
import os

import cv2
import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

from axelera import types
from axelera.app import data_utils, eval_interfaces, logging_utils


class LPRDataLoader(Dataset):
    def __init__(self, img_dir):
        self.img_paths = glob(os.path.join(img_dir, '*.jpg'))
        self.img_paths = sorted(self.img_paths)

    def __len__(self):
        return len(self.img_paths)

    def __getitem__(self, index):
        filename = self.img_paths[index]
        image = cv2.imread(filename)

        basename = os.path.basename(filename)
        imgname, _ = os.path.splitext(basename)
        imgname = imgname.split("-")[0].split("_")[0]
        label = imgname

        return image, label


class LPRNetDataAdapter(types.DataAdapter):
    def __init__(self, dataset_config, model_info):
        self.dataset_config = dataset_config
        self.model_info = model_info

    def create_validation_data_loader(self, root, target_split, **kwargs):
        data_utils.check_and_download_dataset(
            dataset_name='LPRNetDataset',
            data_root_dir=root,
            split='val',
            is_private=False,
        )

        return torch.utils.data.DataLoader(
            LPRDataLoader(os.path.join(root, 'test')),
            batch_size=1,
            shuffle=False,
            collate_fn=lambda x: x,
            num_workers=0,
        )

    def reformat_for_validation(self, batched_data):
        return [
            types.FrameInput.from_image(
                img=image,
                color_format=types.ColorFormat.RGB,
                ground_truth=eval_interfaces.LabelGroundTruthSample(label=label),
                img_id='',
            )
            for image, label in batched_data
        ]

    def evaluator(
        self, dataset_root, dataset_config, model_info, custom_config, pair_validation=False
    ):

        from ax_evaluators.license_plate_recog import LabelMatchEvaluator

        return LabelMatchEvaluator()
