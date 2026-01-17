# Copyright Axelera AI, 2025

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from axelera import types
from axelera.app import gst_builder
from axelera.app.meta import ImageMeta
from axelera.app.operators import AxOperator, PipelineContext

if TYPE_CHECKING:
    from axelera.app import gst_builder


class ImageDecoder(AxOperator):
    output_datatype: str = 'float32'
    scale: bool = False

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
        self._association = context.association or None

    def build_gst(self, gst: gst_builder.Builder, stream_idx: str):
        master_key = f'master_meta:{self._where};' if self._where else str()
        association_key = f'association_meta:{self._association};' if self._association else str()
        gst.decode_muxer(
            name=f'decoder_task{self._taskn}{stream_idx}',
            lib='libdecode_image.so',
            mode='read',
            options=f'meta_key:{str(self.task_name)};'
            f'{master_key}'
            f'{association_key}'
            f'output_datatype:{self.output_datatype};'
            f'scale:{int(self.scale)};',
        )

    def exec_torch(self, image, predict, axmeta):

        predict_np = predict.cpu().detach().numpy()

        if self.scale:
            predict_np = np.clip(predict_np * 255, 0, 255)

        if self.output_datatype in ('uint8', 'float32'):
            predict_np = predict_np.astype(self.output_datatype)
        else:
            raise ValueError(f"Unknown output_datatype in ImageDecoder: {self.output_datatype}")

        model_meta = ImageMeta(img=predict_np)
        axmeta.add_instance(self.task_name, model_meta)

        return image, predict_np, axmeta
