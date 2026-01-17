# Copyright Axelera AI, 2025

import os
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image
import numpy as np
from pycocotools.coco import COCO
import torch
from torch.utils.data.dataset import Dataset

from axelera import types
from axelera.app import data_utils, eval_interfaces, logging_utils, utils

LOG = logging_utils.getLogger(__name__)


class MOTDataset(Dataset):
    """
    COCO dataset class for MOTChallenge datasets (MOT17, MOT20)
    """

    def __init__(
        self, data_root: Path, dataset_name: str = 'MOT17', split: str = 'val', transform=None
    ):
        self.data_root = data_root

        if dataset_name == 'MOT17' or dataset_name == 'MOT20':
            self.data_dir_name = 'train'
            self.mot_dir = dataset_name
            if split == 'val':
                self.json_file = 'val_half.json'
                self.mot_gt_template = 'train/*/gt/gt_val_half.txt'
            elif split == 'train':
                self.json_file = 'train_half.json'
                self.mot_gt_template = 'train/*/gt/gt_train_half.txt'
            else:
                raise ValueError(
                    f"Split {split} not found in MOT17/20 datasets. Should be 'val' or 'train'"
                )
        elif dataset_name == 'DanceTrack':
            self.data_dir_name = 'val'
            self.mot_dir = "dancetrack"
            if split == 'val':
                self.json_file = 'val.json'
                self.mot_gt_template = 'val/*/gt/gt.txt'
            else:
                raise ValueError(
                    f"Split {split} not found in dancetrack datasets. Should be 'val'"
                )
        else:
            raise ValueError(
                f"Dataset {dataset_name} not found in MOT datasets. Should be 'MOT17', 'MOT20' or 'DanceTrack'"
            )

        self.mot_gt_root = os.path.join(self.data_root, self.mot_dir)

        # COCO dataset initialization. Annotation data are read into memory by COCO API.
        self.coco = COCO(os.path.join(self.data_root, self.mot_dir, "annotations", self.json_file))
        self.ids = self.coco.getImgIds()
        self.class_ids = sorted(self.coco.getCatIds())
        self.annotations = self.load_coco_annotations()
        self.transform = transform

    def __len__(self):
        return len(self.ids)

    def load_coco_annotations(self):
        return [self.load_anno_from_ids(ids) for ids in self.ids]

    def load_anno_from_ids(self, id):
        im_ann = self.coco.loadImgs(id)[0]
        width = im_ann["width"]
        height = im_ann["height"]
        frame_id = im_ann["frame_id"]
        video_id = im_ann["video_id"]
        anno_ids = self.coco.getAnnIds(imgIds=[int(id)], iscrowd=False)
        annotations = self.coco.loadAnns(anno_ids)
        objs = []
        for obj in annotations:
            x1 = obj["bbox"][0]
            y1 = obj["bbox"][1]
            x2 = x1 + obj["bbox"][2]
            y2 = y1 + obj["bbox"][3]
            if obj["area"] > 0 and x2 >= x1 and y2 >= y1:
                obj["clean_bbox"] = [x1, y1, x2, y2]
                objs.append(obj)

        num_objs = len(objs)

        res = np.zeros((num_objs, 4))
        classes = np.zeros((num_objs, 1))

        for ix, obj in enumerate(objs):
            classes[ix, 0] = self.class_ids.index(obj["category_id"])
            res[ix, 0:4] = obj["clean_bbox"]

        file_name = im_ann["file_name"] if "file_name" in im_ann else "{:012}".format(id) + ".jpg"
        frame_id = '_'.join([str(video_id), str(frame_id)])
        img_info = (height, width, frame_id, video_id, file_name)

        del im_ann, annotations
        # video_id is 1-indexed
        return (torch.tensor(res), torch.tensor(classes), img_info, file_name, video_id - 1)

    def load_anno(self, index):
        return self.annotations[index][0]

    def pull_item(self, index):
        res, classes, img_info, file_name, video_id = self.annotations[index]

        img_file = os.path.join(self.data_root, self.mot_dir, self.data_dir_name, file_name)
        img = Image.open(img_file).convert('RGB')

        sample = {}
        sample['raw_w'] = img.size[0]
        sample['raw_h'] = img.size[1]

        if self.transform:
            img = self.transform(img)

        sample['image'] = img
        sample['image_id'] = self.ids[index]
        sample['bboxes'] = res
        sample['category_id'] = classes
        sample['video_name'] = img_info[-1].split('/')[0]
        sample['video_id'] = video_id
        sample['gt_template'] = self.mot_gt_template
        sample['gt_root'] = self.mot_gt_root

        assert img is not None

        return sample

    def __getitem__(self, index):
        return self.pull_item(index)


class MotDataAdapter(types.DataAdapter):
    def __init__(self, dataset_config, model_info):
        self.dataset_config = dataset_config
        self.model_info = model_info

        if 'dataset_name' not in dataset_config:
            raise ValueError('Please specify dataset_name in the YAML dataset config')

        self.dataset_name = dataset_config['dataset_name']
        self.is_private = False
        if self.dataset_name == 'DanceTrack':
            self.is_private = True

    def create_calibration_data_loader(self, transform, root, batch_size, **kwargs):
        data_utils.check_and_download_dataset(
            dataset_name=self.dataset_name,
            data_root_dir=root,
            split='val',
            is_private=self.is_private,
        )

        return torch.utils.data.DataLoader(
            MOTDataset(root, self.dataset_name, 'train', transform),
            batch_size=batch_size,
            shuffle=True,
            generator=kwargs.get('generator'),
            collate_fn=lambda x: x,
            num_workers=0,
        )

    def reformat_for_calibration(self, batched_data: Any):
        return torch.stack([data['image'] for data in batched_data], 0)

    def create_validation_data_loader(self, root, target_split, **kwargs):
        data_utils.check_and_download_dataset(
            dataset_name=self.dataset_name,
            data_root_dir=root,
            split='val',
            is_private=self.is_private,
        )

        return torch.utils.data.DataLoader(
            MOTDataset(root, self.dataset_name, 'val'),
            batch_size=1,
            shuffle=False,
            collate_fn=lambda x: x,
            num_workers=0,
        )

    def reformat_for_validation(self, batched_data):
        def as_ground_truth(d):
            if 'bboxes' in d:
                return eval_interfaces.TrackerGroundTruthSample(
                    d['bboxes'],
                    d['category_id'],
                    d['image_id'],
                    video_id=d['video_id'],
                    video_name=d['video_name'],
                    gt_template=d['gt_template'],
                    gt_root=d['gt_root'],
                )
            return None

        def as_frame_input(d):
            return types.FrameInput.from_image(
                img=types.Image.fromany(d['image']),
                ground_truth=as_ground_truth(d),
                img_id=d['image_id'],
            )

        return [as_frame_input(d) for d in batched_data]

    def evaluator(
        self, dataset_root, dataset_config, model_info, custom_config, pair_validation=False
    ):
        from ax_evaluators.mot import MotEvaluator

        return MotEvaluator()
