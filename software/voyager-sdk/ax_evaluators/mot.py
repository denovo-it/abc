# Copyright Axelera AI, 2025

from collections import OrderedDict
import glob
import os
from pathlib import Path
import typing
from typing import Any, Dict, List

from axelera.app import utils

motmetrics_dep = [
    "git+https://github.com/cheind/py-motmetrics.git@c199b3e853d589af4b6a7d88f5bcc8b8802fc434"
]
utils.ensure_dependencies_are_installed(motmetrics_dep)

import motmetrics as mmp
import pandas as pd

from axelera import types
from axelera.app import logging_utils

LOG = logging_utils.getLogger(__name__)


class MotEvaluator(types.Evaluator):
    """
    Evaluator for MOT-17 and MOT20 (dataformat MOT15)
    """

    def __init__(self):
        super().__init__()

        self.tracked_detection = {}
        self.mot_columns = [
            'FrameId',
            'Id',
            'X',
            'Y',
            'Width',
            'Height',
            'Confidence',
            'ClassId',
            'Visibility',
        ]

        self.mot_gtfiles = None

    def process_meta(self, meta):
        meta_ground_truth = meta.access_ground_truth().data

        if self.mot_gtfiles is None:
            mot_gt_template = meta_ground_truth['gt_template']
            mot_gt_root = meta_ground_truth['gt_root']

            self.mot_gtfiles = glob.glob(os.path.join(mot_gt_root, mot_gt_template))

            assert (
                len(self.mot_gtfiles) > 0
            ), f'No MOT ground truth files found in {self.mot_gt_root}'

        video_name = meta_ground_truth['video_name']
        # need video name to create a new entry, is it possible to put video name in the TrackerMeta?
        if video_name not in self.tracked_detection:
            self.tracked_detection[video_name] = {}
            self.tracked_detection[video_name]['frame_idx'] = 1
            self.tracked_detection[video_name]['all_tracking_history'] = []

        tracks = meta.to_evaluation().data
        for i in range(len(tracks['labels'])):
            track_id = tracks['track_ids'][i]
            bbox = tracks['boxes'][i]

            frame_id = self.tracked_detection[video_name]['frame_idx']

            x = bbox[0]
            y = bbox[1]
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]

            tmp = [frame_id, track_id, x, y, w, h, -1, -1, -1]
            self.tracked_detection[video_name]['all_tracking_history'].append(tmp)

        self.tracked_detection[video_name]['frame_idx'] += 1

    def collect_metrics(self):
        pred_mot_tracking = OrderedDict()
        for k in self.tracked_detection:
            df = pd.DataFrame(
                self.tracked_detection[k]['all_tracking_history'], columns=self.mot_columns
            )
            pred_mot_tracking[k] = df.reset_index(drop=True).set_index(self.mot_columns[:2])

        mmp.lap.default_solver = 'lap'
        gt_mot_tracking = OrderedDict(
            [
                (Path(f).parts[-3], mmp.io.loadtxt(f, fmt='mot15-2D', min_confidence=1))
                for f in self.mot_gtfiles
            ]
        )

        mh = mmp.metrics.create()
        accs, names = self.compare_dataframes(gt_mot_tracking, pred_mot_tracking)

        metrics = [
            'recall',
            'precision',
            'num_unique_objects',
            'mostly_tracked',
            'partially_tracked',
            'mostly_lost',
            'num_false_positives',  # FP
            'num_misses',  # FN
            'num_switches',  # IDSW
            'num_fragmentations',
            'mota',
            'motp',
            'num_objects',
            'idf1',  # IDF1
            'idtp',  # TP (True Positives in ID space)
            'idfp',
            'idfn',
            'idp',
            'idr',
            'deta_alpha',  # DetA
            'assa_alpha',  # AssA
            'hota_alpha',  # HOTA
        ]

        summary = mh.compute_many(accs, names=names, metrics=metrics, generate_overall=True)
        div_dict = {
            'num_objects': [
                'num_false_positives',
                'num_misses',
                'num_switches',
                'num_fragmentations',
            ],
            'num_unique_objects': ['mostly_tracked', 'partially_tracked', 'mostly_lost'],
        }
        for divisor in div_dict:
            for divided in div_dict[divisor]:
                summary[divided] = summary[divided] / summary[divisor]

        fmt = mh.formatters
        change_fmt_list = [
            'num_false_positives',
            'num_misses',
            'num_switches',
            'num_fragmentations',
            'mostly_tracked',
            'partially_tracked',
            'mostly_lost',
        ]
        for k in change_fmt_list:
            fmt[k] = fmt['mota']

        LOG.info(
            mmp.io.render_summary(
                summary, formatters=fmt, namemap=mmp.io.motchallenge_metric_names
            )
        )

        LOG.info('Completed MOT metrics evaluation')

        # Update the result with all the requested metrics
        result = types.EvalResult(
            ['mota', 'hota', 'idf1', 'assa', 'deta', 'tp', 'fn', 'fp', 'idsw'],
            {
                'mota': ['average'],
                'hota': ['average'],
                'idf1': ['average'],
                'assa': ['average'],
                'deta': ['average'],
                'tp': ['average'],
                'fn': ['average'],
                'fp': ['average'],
                'idsw': ['average'],
            },
            key_metric='hota',
            key_aggregator='average',
        )

        # Add values for all metrics
        mota_value = summary.loc['OVERALL', 'mota']
        result.set_metric_result('mota', mota_value, 'average')

        # Use the built-in or calculated HOTA value
        hota_value = summary.loc['OVERALL', 'hota_alpha']
        result.set_metric_result('hota', hota_value, 'average')

        # Add remaining metrics
        if 'idf1' in summary.columns:
            idf1_value = summary.loc['OVERALL', 'idf1']
            result.set_metric_result('idf1', idf1_value, 'average')

        # Use built-in or calculated AssA
        assa_value = summary.loc['OVERALL', 'assa_alpha']
        result.set_metric_result('assa', assa_value, 'average')

        # Use built-in or calculated DetA
        deta_value = summary.loc['OVERALL', 'deta_alpha']
        result.set_metric_result('deta', deta_value, 'average')

        # Get TP from idtp if available
        if 'idtp' in summary.columns:
            tp_value = summary.loc['OVERALL', 'idtp']
            result.set_metric_result('tp', tp_value, 'average')

        # Get FP from num_false_positives
        fp_value = summary.loc['OVERALL', 'num_false_positives']
        result.set_metric_result('fp', fp_value, 'average')

        # Get FN from num_misses
        fn_value = summary.loc['OVERALL', 'num_misses']
        result.set_metric_result('fn', fn_value, 'average')

        # Get IDSW from num_switches
        idsw_value = summary.loc['OVERALL', 'num_switches']
        result.set_metric_result('idsw', idsw_value, 'average')

        return result

    @staticmethod
    def compare_dataframes(gts, pts):
        accs = []
        names = []
        for k, tsacc in pts.items():
            if k in gts:
                LOG.info(f'Comparing {k}...')
                accs.append(mmp.utils.compare_to_groundtruth(gts[k], tsacc, 'iou', distth=0.5))
                names.append(k)
            else:
                LOG.warning(f'No ground truth for {k}, skipping.')

        return accs, names
