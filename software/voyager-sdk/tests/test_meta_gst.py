# Copyright Axelera AI, 2025

from collections import OrderedDict

import numpy as np
import pytest

from axelera.app.meta import (
    AxMeta,
    ClassificationMeta,
    GstMetaAssembler,
    GstMetaInfo,
    ModelInfoProvider,
    ObjectDetectionMeta,
    TrackerMeta,
)


def test_gst_meta_assembler_adds_detection_with_labels():
    provider = ModelInfoProvider(labels_dict={'vehicles': ('car',)}, num_classes_dict={})
    assembler = GstMetaAssembler(provider)

    ax_meta = AxMeta('frame-1')
    detection = ObjectDetectionMeta.create_immutable_meta(
        boxes=np.array([[0, 1, 2, 3]], dtype=np.float32),
        scores=np.array([0.9], dtype=np.float32),
        class_ids=np.array([0], dtype=np.int32),
    )
    info = GstMetaInfo('vehicles', detection.__class__.__name__)

    assembler.process(ax_meta, {info: detection})

    stored = ax_meta['vehicles']
    assert stored is not detection  # assembler returns a wrapped instance
    assert stored.boxes is detection.boxes
    assert stored.labels == ('car',)


def test_gst_meta_assembler_honours_master_expectations():
    provider = ModelInfoProvider()
    assembler = GstMetaAssembler(provider)

    class _Graph:
        def __init__(self, mapping):
            self._mapping = mapping

        def get_master(self, task_name, view=None):
            return self._mapping.get(task_name)

    ax_meta = AxMeta('frame-2')
    classification = ClassificationMeta()
    classification.add_result([0], [0.5])
    info = GstMetaInfo('child_task', classification.__class__.__name__, master='other_task')

    graph = _Graph({'child_task': 'expected_master'})

    with pytest.raises(ValueError):
        assembler.process(ax_meta, {info: classification}, graph, result_view='RESULT')


def test_gst_meta_assembler_creates_secondary_relationship():
    provider = ModelInfoProvider(
        labels_dict={'vehicles': ('car',), 'vehicles_classifier': ('car',)},
        num_classes_dict={'vehicles_classifier': 3},
        softmax_lookup=lambda task: True if task == 'vehicles_classifier' else False,
    )
    assembler = GstMetaAssembler(provider)

    ax_meta = AxMeta('frame-3')

    detection = ObjectDetectionMeta.create_immutable_meta(
        boxes=np.array([[0, 1, 2, 3]], dtype=np.float32),
        scores=np.array([0.9], dtype=np.float32),
        class_ids=np.array([0], dtype=np.int32),
        make_extra_info_mutable=True,
    )
    classification = ClassificationMeta()
    classification.add_result([0], [0.5])

    items = OrderedDict(
        (
            (GstMetaInfo('vehicles', detection.__class__.__name__), detection),
            (
                GstMetaInfo(
                    'vehicles_classifier',
                    classification.__class__.__name__,
                    subframe_index=0,
                    master='vehicles',
                ),
                classification,
            ),
        )
    )

    class _Graph:
        def get_master(self, task_name, view=None):
            return 'vehicles' if task_name == 'vehicles_classifier' else None

    assembler.process(ax_meta, items, _Graph(), result_view='RESULT')

    stored_detection = ax_meta['vehicles']
    assert stored_detection.boxes is detection.boxes
    secondaries = stored_detection._secondary_metas['vehicles_classifier']
    assert len(secondaries) == 1
    stored_classification = secondaries[0]
    assert isinstance(stored_classification, ClassificationMeta)
    # Labels propagated and softmax flag honoured
    assert stored_classification.labels == ('car',)
    assert stored_classification.extra_info['softmax'] is True


def test_gst_meta_assembler_handles_tracker_secondary():
    provider = ModelInfoProvider(
        labels_dict={
            'vehicles': ('car',),
            'pedestrian_and_vehicle_tracker': ('car',),
        }
    )
    assembler = GstMetaAssembler(provider)

    ax_meta = AxMeta('frame-4')

    detection = ObjectDetectionMeta.create_immutable_meta(
        boxes=np.array([[0, 1, 2, 3]], dtype=np.float32),
        scores=np.array([0.9], dtype=np.float32),
        class_ids=np.array([0], dtype=np.int32),
        make_extra_info_mutable=True,
    )

    tracker = TrackerMeta(
        tracking_history={101: np.array([[0, 1, 2, 3]], dtype=np.int32)},
        class_ids=[0],
    )

    items = OrderedDict(
        (
            (GstMetaInfo('vehicles', detection.__class__.__name__), detection),
            (
                GstMetaInfo(
                    'pedestrian_and_vehicle_tracker',
                    tracker.__class__.__name__,
                    subframe_index=0,
                    master='vehicles',
                ),
                tracker,
            ),
        )
    )

    class _Graph:
        def get_master(self, task_name, view=None):
            return 'vehicles' if task_name == 'pedestrian_and_vehicle_tracker' else None

    assembler.process(ax_meta, items, _Graph(), result_view='RESULT')

    stored_detection = ax_meta['vehicles']
    assert stored_detection.boxes is detection.boxes
    secondaries = stored_detection._secondary_metas['pedestrian_and_vehicle_tracker']
    assert len(secondaries) == 1
    stored_tracker = secondaries[0]
    assert isinstance(stored_tracker, TrackerMeta)
    # Labels pulled from provider for tracker as well
    assert stored_tracker.labels == ('car',)
    assert stored_tracker.tracking_history is tracker.tracking_history
    # Tracking history preserved (no extra copy expected)
    np.testing.assert_array_equal(
        stored_tracker.tracking_history[101], tracker.tracking_history[101]
    )


def test_gst_meta_assembler_handles_tracker_cascade_with_duplicates():
    """Test that tracker cascades handle duplicate track_ids in object_meta and frame_object_meta.

    When the same track_id appears in both dictionaries, it should only be processed once.
    """
    provider = ModelInfoProvider(
        labels_dict={
            'vehicles': ('car',),
            'pedestrian_and_vehicle_tracker': ('car',),
            'vehicles_classifier': ('sedan', 'truck', 'bus'),
        },
        num_classes_dict={'vehicles_classifier': 3},
        softmax_lookup=lambda task: False,
    )
    assembler = GstMetaAssembler(provider)

    ax_meta = AxMeta('frame-5')

    detection = ObjectDetectionMeta.create_immutable_meta(
        boxes=np.array([[10, 20, 100, 120]], dtype=np.float32),
        scores=np.array([0.9], dtype=np.float32),
        class_ids=np.array([0], dtype=np.int32),
        make_extra_info_mutable=True,
    )

    classifier_101 = ClassificationMeta()
    classifier_101.add_result([1], [0.85])

    classifier_102 = ClassificationMeta()
    classifier_102.add_result([2], [0.75])

    tracker = TrackerMeta(
        tracking_history={
            101: np.array([[10, 20, 100, 120]], dtype=np.int32),
            102: np.array([[200, 30, 300, 150]], dtype=np.int32),
        },
        class_ids=[0, 0],
        object_meta={'classifications': {101: classifier_101, 102: classifier_102}},
        frame_object_meta={'classifications': {101: classifier_101, 102: classifier_102}},
    )

    items = OrderedDict(
        (
            (GstMetaInfo('vehicles', detection.__class__.__name__), detection),
            (
                GstMetaInfo(
                    'pedestrian_and_vehicle_tracker',
                    tracker.__class__.__name__,
                    subframe_index=0,
                    master='vehicles',
                ),
                tracker,
            ),
        )
    )

    class _Graph:
        def get_master(self, task_name, view=None):
            if task_name == 'pedestrian_and_vehicle_tracker':
                return 'vehicles'
            return None

    assembler.process(ax_meta, items, _Graph(), result_view='RESULT')

    stored_tracker = ax_meta['vehicles']._secondary_metas['pedestrian_and_vehicle_tracker'][0]
    assert 'classifications' in stored_tracker._secondary_metas
    classifications = stored_tracker._secondary_metas['classifications']
    assert len(classifications) == 2  # Should have exactly 2, not 4

    # Verify the indices were registered correctly
    assert 'classifications' in stored_tracker.secondary_frame_indices
    indices = stored_tracker.secondary_frame_indices['classifications']
    assert set(indices) == {101, 102}  # Should contain both track IDs exactly once


def test_tracker_meta_boxes_property():
    """Test that TrackerMeta.boxes property returns current boxes for all tracks.

    This tests the fix for SDK-XXXX where ClassificationMeta.draw() tried to access
    tracker.boxes[track_id] but TrackerMeta didn't have a boxes property.
    """
    tracker = TrackerMeta(
        tracking_history={
            101: np.array([[10, 20, 100, 120], [15, 25, 105, 125]], dtype=np.float32),
            102: np.array([[200, 30, 300, 150]], dtype=np.float32),
            103: np.array(
                [[50, 60, 150, 160], [55, 65, 155, 165], [60, 70, 160, 170]], dtype=np.float32
            ),
        },
        class_ids=[0, 1, 0],
    )

    boxes = tracker.boxes

    # Should return a dict mapping track_id to last box
    assert isinstance(boxes, dict)
    assert len(boxes) == 3

    # Verify it returns the LAST box from each track's history
    np.testing.assert_array_equal(boxes[101], np.array([15, 25, 105, 125]))
    np.testing.assert_array_equal(boxes[102], np.array([200, 30, 300, 150]))
    np.testing.assert_array_equal(boxes[103], np.array([60, 70, 160, 170]))


def test_tracker_cascade_classification_can_access_boxes():
    """Test that classifications in a tracker cascade can access boxes from their master TrackerMeta.

    This verifies the complete fix where ClassificationMeta.draw() needs to access
    boxes via get_master_meta().boxes[subframe_index] when the master is a TrackerMeta.
    """
    provider = ModelInfoProvider(
        labels_dict={
            'vehicles': ('car',),
            'pedestrian_and_vehicle_tracker': ('car',),
            'classifications': ('sedan', 'truck'),
        },
        num_classes_dict={'classifications': 2},
        softmax_lookup=lambda task: False,
    )
    assembler = GstMetaAssembler(provider)

    ax_meta = AxMeta('frame-6')

    detection = ObjectDetectionMeta.create_immutable_meta(
        boxes=np.array([[10, 20, 100, 120]], dtype=np.float32),
        scores=np.array([0.9], dtype=np.float32),
        class_ids=np.array([0], dtype=np.int32),
        make_extra_info_mutable=True,
    )

    classifier = ClassificationMeta()
    classifier.add_result([0], [0.92])

    tracker = TrackerMeta(
        tracking_history={
            101: np.array([[10, 20, 100, 120]], dtype=np.float32),
        },
        class_ids=[0],
        object_meta={'classifications': {101: classifier}},
    )

    items = OrderedDict(
        (
            (GstMetaInfo('vehicles', detection.__class__.__name__), detection),
            (
                GstMetaInfo(
                    'pedestrian_and_vehicle_tracker',
                    tracker.__class__.__name__,
                    subframe_index=0,
                    master='vehicles',
                ),
                tracker,
            ),
        )
    )

    class _Graph:
        def get_master(self, task_name, view=None):
            if task_name == 'pedestrian_and_vehicle_tracker':
                return 'vehicles'
            return None

    assembler.process(ax_meta, items, _Graph(), result_view='RESULT')

    stored_tracker = ax_meta['vehicles']._secondary_metas['pedestrian_and_vehicle_tracker'][0]
    stored_classifier = stored_tracker._secondary_metas['classifications'][0]

    # Verify the classification metadata is set correctly
    assert stored_classifier.master_meta_name == 'pedestrian_and_vehicle_tracker'
    assert stored_classifier.subframe_index == 101

    # The key test: TrackerMeta.boxes should be accessible and indexable by track_id
    # This is what ClassificationMeta.draw() needs when drawing cascaded classifications
    assert isinstance(stored_tracker, TrackerMeta)
    boxes = stored_tracker.boxes
    assert 101 in boxes
    np.testing.assert_array_equal(boxes[101], np.array([10, 20, 100, 120]))

    # Verify the boxes property returns the correct box for the classification's track_id
    classifier_box = boxes[stored_classifier.subframe_index]
    np.testing.assert_array_equal(classifier_box, np.array([10, 20, 100, 120]))
