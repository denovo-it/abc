# Copyright Axelera AI, 2025

import math

import cv2
import numpy as np

from axelera import types
from axelera.app import logging_utils

LOG = logging_utils.getLogger(__name__)


def organize_results(rmse, delta1):
    metric_names = ['RMSE', 'delta1']
    aggregator_dict = {'RMSE': ['average'], 'delta1': ['average']}

    eval_result = types.EvalResult(
        metric_names=metric_names,
        aggregators=aggregator_dict,
        key_metric='RMSE',
        key_aggregator='average',
    )

    eval_result.set_metric_result('RMSE', rmse, 'average', is_percentage=False)
    eval_result.set_metric_result('delta1', delta1, 'average', is_percentage=False)

    return eval_result


def evaluate(output, target):
    valid_mask = (target > 0) & (output > 0)

    output = output[valid_mask]
    target = target[valid_mask]

    abs_diff = np.abs(output - target)

    mse = np.mean(np.square(abs_diff))
    rmse = np.sqrt(mse)

    max_ratio = np.maximum(output / target, target / output)
    delta1 = np.mean(max_ratio < 1.25)

    return rmse, delta1


class DepthEstimationEvaluator(types.Evaluator):
    def __init__(self, **kwargs):
        self.total_samples = 0
        self.rmse_sum = 0
        self.delta1_sum = 0

    def process_meta(self, meta) -> None:
        self.total_samples += 1

        depth = np.array(meta.to_evaluation().data)
        depth = np.squeeze(depth)

        target = np.array(meta.access_ground_truth().data)
        target = cv2.resize(target, (depth.shape[1], depth.shape[0]))

        rmse, delta1 = evaluate(depth, target)

        self.rmse_sum += rmse
        self.delta1_sum += delta1

    def collect_metrics(self):
        avg_rmse = self.rmse_sum / self.total_samples if self.total_samples > 0 else 0.0
        avg_delta1 = self.delta1_sum / self.total_samples if self.total_samples > 0 else 0.0

        return organize_results(avg_rmse, avg_delta1)
