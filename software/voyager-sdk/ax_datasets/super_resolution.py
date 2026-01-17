# Copyright Axelera AI, 2025
from __future__ import annotations

import os

from PIL import Image
import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

from axelera import types
from axelera.app import data_utils, eval_interfaces, logging_utils, meta

LOG = logging_utils.getLogger(__name__)


class SuperResolutionDataset(Dataset):
    def __init__(self, low_res_dir, high_res_dir, lr_transform=None, hr_transform=None):
        """
        Args:
            low_res_dir (str): Path to the directory containing low-resolution (LR) images.
            high_res_dir (str): Path to the directory containing high-resolution (HR) images.
            lr_transform (callable, optional): Optional transform to be applied on a LR sample.
            hr_transform (callable, optional): Optional transform to be applied on a HR sample.
        """
        self.low_res_dir = low_res_dir
        self.high_res_dir = high_res_dir

        self.low_res_images = os.listdir(low_res_dir)

        self.lr_transform = lr_transform
        self.hr_transform = hr_transform

    def __len__(self):
        return len(self.low_res_images)

    def __getitem__(self, idx):
        low_res_image_path = os.path.join(self.low_res_dir, self.low_res_images[idx])
        # filenames for LR and HR are the same
        high_res_image_path = os.path.join(self.high_res_dir, self.low_res_images[idx])

        low_res_image = Image.open(low_res_image_path).convert('RGB')
        high_res_image = Image.open(high_res_image_path).convert('RGB')

        # Apply transformations (if any)
        if self.lr_transform:
            low_res_image = self.lr_transform(low_res_image)

        if self.hr_transform:
            high_res_image = self.hr_transform(high_res_image)

        return low_res_image, high_res_image


class SuperResolutionDataAdapter(types.DataAdapter):
    def __init__(self, dataset_config, model_info):
        self.dataset_config = dataset_config
        self.model_info = model_info

    def create_validation_data_loader(self, root, target_split, **kwargs):
        data_utils.check_and_download_dataset(
            dataset_name='SuperResolutionCustomSet128x128',
            data_root_dir=root,
            split='val',
            is_private=False,
        )
        assert 'val_data' in kwargs, "val_data is required in the YAML dataset config"

        return torch.utils.data.DataLoader(
            SuperResolutionDataset(
                os.path.join(root, kwargs['val_data'], 'lr_x4'),
                os.path.join(root, kwargs['val_data'], 'hr'),
            ),
            batch_size=1,
            shuffle=False,
            collate_fn=lambda x: x,
            num_workers=0,
        )

    def reformat_for_validation(self, batched_data):
        return [
            types.FrameInput.from_image(
                img=lr,
                color_format=types.ColorFormat.RGB,
                ground_truth=eval_interfaces.ImageSample(img=hr),
                img_id='',
            )
            for lr, hr in batched_data
        ]

    def evaluator(
        self, dataset_root, dataset_config, model_info, custom_config, pair_validation=False
    ):

        from ax_evaluators.image_enhancement import SuperResolutionEvaluator

        return SuperResolutionEvaluator()
