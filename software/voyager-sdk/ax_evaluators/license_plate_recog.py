# Copyright Axelera AI, 2025

import collections
import os
from typing import Any, List

from ax_evaluators.classification import MetricBase, MetricDefinitions
from ax_evaluators.statistic_aggregator import AggregatorAverage

from axelera import types
from axelera.app.meta import LicensePlateMeta


class MetricWLA(MetricBase):
    '''
    Measures the percentage of correctly recognized full license plates.
    Formula:
          Number of correctly predicted plates
    WLA = -------------------------------------
          Total number of plates in dataset

    Example: If 80 out of 100 plates are recognized perfectly, WLA = 80%.
    '''

    def __init__(self) -> None:
        self.NAME = "WLA"

    def __call__(self, predicted, actual) -> float:
        return 1.0 if predicted == actual else 0.0


class MetricCLA(MetricBase):
    '''
    Character-Level Accuracy (CLA)
    Measures the percentage of correctly recognized characters compared to the ground truth.
    Formula:
          Number of correctly predicted characters
    CLA = ---------------------------------------
          Total number of characters in ground truth

    Example: If the ground truth is "AB123CD" and the prediction is "AB12CD", the CLA is 6/7 = 85.7%.
    '''

    def __init__(self) -> None:
        self.NAME = "CLA"

    def pad_strings(self, predicted: str, ground_truth: str) -> tuple:
        max_length = max(len(predicted), len(ground_truth))
        if len(predicted) == 0 or len(ground_truth) == 0:
            return predicted.ljust(max_length), ground_truth.ljust(max_length)
        if predicted[0] == ground_truth[0]:
            return predicted.ljust(max_length), ground_truth.ljust(max_length)
        else:
            return predicted.rjust(max_length), ground_truth.rjust(max_length)

    def __call__(self, predicted, actual) -> float:
        p, a = self.pad_strings(predicted, actual)
        if len(p) == 0:
            return 0
        accuracy = sum(c1 == c2 for c1, c2 in zip(p, a)) / len(a)
        return accuracy


def create_lprnet_metric_definitions() -> MetricDefinitions:
    metric_defs = MetricDefinitions()
    metric_map = dict()

    metric_map["WLA"] = MetricWLA(), AggregatorAverage()
    metric_map["CLA"] = MetricCLA(), AggregatorAverage()
    metric_defs.add(*metric_map["WLA"])
    metric_defs.add(*metric_map["CLA"])

    return metric_defs


class LabelMatchEvaluator(types.Evaluator):
    def __init__(self):
        super().__init__()
        self.metric_defs = create_lprnet_metric_definitions()
        self.metric_results = collections.defaultdict(list)

    def process_meta(self, meta: LicensePlateMeta):
        prediction = meta.to_evaluation().data
        label = meta.access_ground_truth().data
        for metric in self.metric_defs.get_metrics():
            result = metric(prediction, label)
            self.metric_results[metric.NAME].append(result)

    def collect_metrics(self):
        results = collections.defaultdict(dict)
        for metric, aggregators in self.metric_defs.items():
            for aggregator in aggregators:
                results[metric.NAME][aggregator.NAME] = aggregator(
                    self.metric_results[metric.NAME]
                )
        metric_names = list(results.keys())
        aggregator_dict = {metric: list(aggs.keys()) for metric, aggs in results.items()}
        eval_result = types.EvalResult(
            metric_names,
            aggregator_dict,
            "WLA",
            "average",
        )
        for metric_name, aggregators in results.items():
            for agg_name, value in aggregators.items():
                eval_result.set_metric_result(metric_name, value, agg_name, is_percentage=True)
        return eval_result
