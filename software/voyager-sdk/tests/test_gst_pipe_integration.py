# Copyright Axelera AI, 2025

import numpy as np

from axelera import types
from axelera.app import config
from axelera.app.meta import (
    AxMeta,
    ClassificationMeta,
    GstMetaInfo,
    ObjectDetectionMeta,
    TrackerMeta,
)
from axelera.app.pipe import graph
from axelera.app.pipe import gst as gst_pipe


class _DummyModelInfo:
    def __init__(self, name, labels, num_classes, task_category):
        self.name = name
        self.labels = labels
        self.num_classes = num_classes
        self.task_category = task_category


class _DummyTask:
    def __init__(self, name, model_info, postprocess=None):
        self.name = name
        self.model_info = model_info
        self.postprocess = postprocess or []
        self.inference = None


class _DummySoftmax:
    def __init__(self, softmax):
        self.softmax = softmax


class _DummyGraph:
    def __init__(self, mapping):
        self._mapping = mapping

    def get_master(self, task_name, view=None):
        return self._mapping.get(task_name)


def _make_detection_meta():
    return ObjectDetectionMeta.create_immutable_meta(
        boxes=np.array([[0, 1, 10, 11]], dtype=np.float32),
        scores=np.array([0.9], dtype=np.float32),
        class_ids=np.array([0], dtype=np.int32),
        make_extra_info_mutable=True,
    )


def _make_tracker_meta():
    history = {101: np.array([[0, 1, 10, 11]], dtype=np.int32)}
    tracker = TrackerMeta(tracking_history=history, class_ids=[0])
    classifier = ClassificationMeta()
    classifier.add_result([0], [0.75])
    tracker.object_meta.setdefault('vehicles_classifier', {})[101] = classifier
    return tracker


def test_gst_pipe_assembler_integration_builds_detection_and_tracker():
    pipe = object.__new__(gst_pipe.GstPipe)
    nn = type(
        "DummyNN",
        (),
        {
            "tasks": [
                _DummyTask(
                    "vehicles",
                    _DummyModelInfo(
                        name="vehicles",
                        labels=('car',),
                        num_classes=1,
                        task_category=types.TaskCategory.ObjectDetection,
                    ),
                    postprocess=[_DummySoftmax(False)],
                ),
                _DummyTask(
                    "pedestrian_and_vehicle_tracker",
                    _DummyModelInfo(
                        name="pedestrian_and_vehicle_tracker",
                        labels=('car',),
                        num_classes=1,
                        task_category=types.TaskCategory.ObjectTracking,
                    ),
                ),
            ]
        },
    )()

    pipe.nn = nn
    pipe.model_info_labels_dict = {
        "vehicles": ('car',),
        "pedestrian_and_vehicle_tracker": ('car',),
        "vehicles_classifier": ('car',),
    }
    pipe.model_info_num_classes_dict = {
        "vehicles": 1,
        "pedestrian_and_vehicle_tracker": 1,
        "vehicles_classifier": 1,
    }
    pipe.task_graph = _DummyGraph(
        {
            "pedestrian_and_vehicle_tracker": "vehicles",
        }
    )
    pipe._meta_assembler = None

    pipe._ensure_meta_assembler()
    assert pipe._meta_assembler is not None

    ax_meta = AxMeta('frame-0')
    detection = _make_detection_meta()
    tracker = _make_tracker_meta()
    decoded_meta = {
        GstMetaInfo('vehicles', detection.__class__.__name__): detection,
        GstMetaInfo(
            'pedestrian_and_vehicle_tracker',
            tracker.__class__.__name__,
            subframe_index=0,
            master='vehicles',
        ): tracker,
    }

    pipe._meta_assembler.process(
        ax_meta,
        decoded_meta,
        pipe.task_graph,
        graph.EdgeType.RESULT,
    )

    stored_detection = ax_meta['vehicles']
    assert stored_detection.boxes is detection.boxes
    stored_tracker = stored_detection._secondary_metas['pedestrian_and_vehicle_tracker'][0]
    assert isinstance(stored_tracker, TrackerMeta)
    assert stored_tracker.tracking_history is tracker.tracking_history
    assert stored_tracker.labels == ('car',)

    sub_classifiers = stored_tracker._secondary_metas['vehicles_classifier']
    assert len(sub_classifiers) == 1
    stored_classifier = sub_classifiers[0]
    assert isinstance(stored_classifier, ClassificationMeta)
    assert stored_classifier.labels == ('car',)
    assert stored_classifier.extra_info.get('softmax') is False
