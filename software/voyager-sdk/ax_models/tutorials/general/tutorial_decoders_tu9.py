# Copyright Axelera AI, 2025
from __future__ import annotations

from pathlib import Path

import torch
import torch.nn.functional as TF

from axelera import types
from axelera.app import gst_builder, logging_utils, meta
from axelera.app.operators import AxOperator, PipelineContext

LOG = logging_utils.getLogger(__name__)


# Tutorial-10: Decoder for submodel in cascaded pipeline
class TopKDecoderCascadedWithMyGstPlugin(AxOperator):
    def _post_init(self):
        pass

    def configure_model_and_context_info(
        self,
        model_info: types.ModelInfo,
        context: PipelineContext,
        task_name: str,
        taskn: int,
        compiled_model_dir: Path | None,
        task_graph,
    ):
        super().configure_model_and_context_info(
            model_info, context, task_name, taskn, compiled_model_dir, task_graph
        )
        self.labels = model_info.labels
        self.num_classes = model_info.num_classes
        assert self._where is not None
        self._association = context.association or None

    def build_gst(self, gst: gst_builder.Builder, stream_idx: str):
        master_key = f'master_meta_key:{self._where};' if self._where else str()
        association_key = (
            f'association_meta_key:{self._association};' if self._association else str()
        )

        gst.decode_muxer(
            lib='libdecode_tu9.so',
            options=f'meta_key:{str(self.task_name)};' f'{master_key}' f'{association_key}',
        )

    def exec_torch(self, image, predict, axmeta):
        model_meta = meta.ClassificationMeta(
            labels=self.labels,
            num_classes=self.num_classes,
        )

        top_scores, top_ids = torch.topk(predict, k=1)
        top_scores = top_scores.cpu().detach().numpy()[0]
        top_ids = top_ids.cpu().detach().numpy()[0]

        model_meta.add_result(top_ids, top_scores)

        axmeta.add_instance(self.task_name, model_meta, self._where)
        return image, predict, axmeta


class AccessSubMetaOperator(AxOperator):
    def _post_init(self):
        pass

    def build_gst(self, gst: gst_builder.Builder, stream_idx: str):
        gst.axinplace(
            lib='libinplace_tu9.so',
            options=f'master_task_name:{self._where};' f'subtask_name:{self.task_name};',
        )

    def exec_torch(self, image, predict, axmeta):
        pass
