# Copyright Axelera AI, 2025
from __future__ import annotations

from pathlib import Path
import re

# import tempfile
from typing import Optional, Union

import numpy as np

from axelera import types
from axelera.app import gst_builder, logging_utils
from axelera.app.meta import BBoxState, PoseInsSegMeta
from axelera.app.meta.multihead import _translate_image_space_rect
from axelera.app.operators import AxOperator, PipelineContext, utils
from axelera.app.torch_utils import torch

LOG = logging_utils.getLogger(__name__)


def depad_str(pad):
    padding = [-x for x in pad]
    return ','.join(str(x) for x in pad)


def _generate_depadding(manifest: types.Manifest) -> str:
    padding = manifest.n_padded_ch_outputs if manifest.n_padded_ch_outputs else []
    padding = [depad_str(list(pad[:8])) for pad in padding]
    return '|'.join(x for x in padding)


class DecodeYoloPoseSeg(AxOperator):

    box_format: str = "xywh"
    normalized_coord: bool = False
    label_filter: Union[list, str] = []
    conf_threshold: float = 0.25
    max_nms_boxes: int = 30000
    nms_iou_threshold: float = 0.45
    nms_class_agnostic: bool = False
    nms_top_k: int = 300
    overwrite_labels: bool = False

    def _post_init(self):
        if self.box_format not in ["xyxy", "xywh", "ltwh"]:
            raise ValueError(f"Unknown box format {self.box_format}")
        if isinstance(self.overwrite_labels, int):
            self.overwrite_labels = bool(self.overwrite_labels)
        if isinstance(self.label_filter, str) and not self.label_filter.startswith('$$'):
            stripped = (self.label_filter or '').strip()
            self.label_filter = [x for x in re.split(r'\s*[,;]\s*', stripped) if x]
        else:
            self.label_filter = []
        self._tmp_labels: Optional[Path] = None
        super()._post_init()

    def configure_model_and_context_info(
        self,
        model_info: types.ModelInfo,
        context: PipelineContext,
        task_name: str,
        taskn: int,
        where: str,
        compiled_model_dir: Path | None,
    ):
        super().configure_model_and_context_info(
            model_info, context, task_name, taskn, where, compiled_model_dir
        )
        self.meta_type_name = "PoseInsSegMeta"
        if model_info.manifest and model_info.manifest.is_compiled():
            self._deq_scales, self._deq_zeropoints = zip(*model_info.manifest.dequantize_params)
            self._depadding = _generate_depadding(model_info.manifest)
        self.scaled = context.resize_status
        self.model_width = model_info.input_width
        self.model_height = model_info.input_height
        self.labels = model_info.labels
        self.num_classes = model_info.num_classes
        self._kpts_shape = PoseInsSegMeta.keypoints_shape

    def build_gst(self, gst: gst_builder.Builder, stream_idx: str):
        if self._tmp_labels is None:
            self._tmp_labels = utils.create_tmp_labels(self.labels)

        scales = ','.join(str(s) for s in self._deq_scales)
        zeros = ','.join(str(s) for s in self._deq_zeropoints)
        sieve = utils.build_class_sieve(self.label_filter, self._tmp_labels)
        kpt_shape = ','.join(str(s) for s in self._kpts_shape)

        gst.decode_muxer(
            name=f'decoder_task{self._taskn}{stream_idx}',
            lib='libdecode_multihead.so',
            mode='read',
            options=f'meta_key:{str(self.task_name)};'
            f'confidence_threshold:{self.conf_threshold};'
            f'classlabels_file:{self._tmp_labels};'
            f'max_boxes:{self.max_nms_boxes};'
            f'scales:{scales};'
            f'zero_points:{zeros};'
            f'kpts_shape:{kpt_shape};'
            f'classes:{self.num_classes};'
            f'decoder_name:{self.meta_type_name};'
            f'model_width:{self.model_width};'
            f'model_height:{self.model_height}'
            + (f';padding:{self._depadding}' if self._depadding else '')
            + (f';label_filter:{",".join(sieve)}' if sieve else ''),
        )
        gst.axinplace(
            lib='libinplace_nms.so',
            options=f'meta_key:{str(self.task_name)};nms_threshold:{self.nms_iou_threshold};class_agnostic:{int(self.nms_class_agnostic)};max_boxes:{self.nms_top_k}',
        )

    def _process_multi_label(self, box_coordinates, box_labels, mask_coef, key_points):
        i, j = np.where(box_labels > self.conf_threshold)
        boxes = box_coordinates[i]
        kpts = key_points[i]
        scores = box_labels[i, j]
        classes = j.astype(np.float32)
        mask_coef = mask_coef[i]
        return boxes, scores, classes, mask_coef, kpts

    def _process_predictions(self, pred):
        box_coordinates, box_labels, mask_coef, key_points = np.split(
            pred,
            [4, 4 + self.num_classes, 4 + self.num_classes + 32],
            axis=1,  # 4 coords per bbox, and 32 segment coefs per grid cell
        )

        boxes, scores, classes, mask_coef, kpts = self._process_multi_label(
            box_coordinates, box_labels, mask_coef, key_points
        )

        return boxes, scores, classes, mask_coef, kpts

    def exec_torch(self, image, predict, meta):
        protos = [
            t
            for t in predict
            if t.shape[2] == self.model_height / 4 and t.shape[3] == self.model_width / 4
        ][0]
        pred_bboxes = sorted(
            [t for t in predict if len(t.shape) == 3], key=lambda x: x.shape[1], reverse=True
        )[0]

        if isinstance(pred_bboxes, torch.Tensor):
            pred_bboxes = pred_bboxes.cpu().detach().numpy()
            protos = protos.cpu().detach().numpy()

        if pred_bboxes.shape[0] > 1:
            raise ValueError(
                f"Batch size >1 not supported for torch and torch-aipu pipelines, output tensor={predict[0].shape}"
            )

        if pred_bboxes.shape[1] < pred_bboxes.shape[2]:
            pred_bboxes = pred_bboxes.transpose([0, 2, 1])

        for pred, proto in zip(pred_bboxes, protos):
            (
                initial_boxes,
                initial_scores,
                classes,
                mask_coef,
                initial_kpts,
            ) = self._process_predictions(pred)

            src_img_width = image.size[0]
            src_img_height = image.size[1]

            state = BBoxState(
                self.model_width,
                self.model_height,
                src_img_width,
                src_img_height,
                self.box_format,
                self.normalized_coord,
                self.scaled,
                self.max_nms_boxes,
                self.nms_iou_threshold,
                nms_class_agnostic=self.nms_class_agnostic,
                output_top_k=self.nms_top_k,
                labels=self.labels,
                label_filter=self.label_filter,
            )

            (
                boxes,
                kpts,
                scores,
                classes,
                masks,
            ) = state.organize_bboxes_kpts_and_instance_seg(
                initial_boxes, initial_kpts, initial_scores, classes, mask_coef, proto, False
            )
            model_meta = PoseInsSegMeta(
                seg_shape=proto.shape[2:0:-1],
                labels=self.labels,
            )
            bbox = np.array([0, 0, src_img_width, src_img_height], dtype=int)
            aranged_masks = []
            if len(masks) != 0:
                for i, sbox in enumerate(masks[0]):
                    mbox = _translate_image_space_rect(sbox, bbox, proto.shape[2:0:-1])
                    aranged_masks.append((*sbox, *mbox, masks[1][i]))
            model_meta.add_results(
                aranged_masks, boxes.astype(int), kpts, classes.astype(int), scores
            )
            meta.add_instance(self.task_name, model_meta, self._where)
        return image, predict, meta
