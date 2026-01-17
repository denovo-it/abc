# Copyright Axelera AI, 2025

import numpy as np
import sewar

from axelera import types
from axelera.app import logging_utils

LOG = logging_utils.getLogger(__name__)


def organize_results(psnr, ssim):
    metric_names = ['PSNR', 'SSIM']
    aggregator_dict = {'PSNR': ['average'], 'SSIM': ['average']}

    eval_result = types.EvalResult(
        metric_names=metric_names,
        aggregators=aggregator_dict,
        key_metric='PSNR',
        key_aggregator='average',
    )

    eval_result.set_metric_result('PSNR', psnr, 'average', is_percentage=False)
    eval_result.set_metric_result('SSIM', ssim, 'average', is_percentage=False)

    return eval_result


class SuperResolutionEvaluator(types.Evaluator):
    def __init__(self, **kwargs):
        self.total_samples = 0
        self.psnr_sum = 0
        self.ssim_sum = 0

    def process_meta(self, meta) -> None:
        self.total_samples += 1

        data = meta.to_evaluation().data
        if data.shape[0] == 1:
            data = data.squeeze(0)
        output = np.array(data)
        if output.shape[0] != 3:
            # In cpp decoder image is in interleaved format (HWC) in torch it is in CHW
            # so we need to transpose it to CHW
            output = output.transpose((2, 0, 1))

        gt_hwc = np.array(meta.access_ground_truth().data)
        gt_chw = np.transpose(gt_hwc, (2, 0, 1))

        psnr = sewar.full_ref.psnr(gt_chw, output)
        self.psnr_sum += psnr

        ssim = sewar.full_ref.ssim(gt_chw, output, mode='same')
        self.ssim_sum += ssim[0]

    def collect_metrics(self):
        avg_psnr = self.psnr_sum / self.total_samples if self.total_samples > 0 else 0.0
        avg_ssim = self.ssim_sum / self.total_samples if self.total_samples > 0 else 0.0

        return organize_results(avg_psnr, avg_ssim)
