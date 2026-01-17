# Copyright Axelera AI, 2025
# Construct GStreamer application pipeline
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import call, patch

import pytest

from axelera.app import config, gst_builder, operators, pipe, pipeline
from axelera.app.pipe import FrameEvent, gst, gst_helper, io

# isort: off
from gi.repository import Gst

# isort: on


def _sorted(elements):
    return sorted(elements, key=lambda e: e.get_name())


@pytest.mark.parametrize('num_sinks', [0, 1, 2, 4])
def test_iteration_appsinks(num_sinks):
    if not Gst.is_initialized():
        Gst.init(None)

    pipeline = Gst.Pipeline()
    videosrc = Gst.ElementFactory.make('videotestsrc', 'source')
    pipeline.add(videosrc)
    appsinks = []
    for n in range(num_sinks):
        element = Gst.ElementFactory.make('appsink', f'sink{n}')
        pipeline.add(element)
        appsinks.append(element)

    assert [videosrc] == gst_helper.list_all_by_element_factory_name(pipeline, 'videotestsrc')
    assert _sorted(appsinks) == _sorted(
        gst_helper.list_all_by_element_factory_name(pipeline, 'appsink')
    )


def _expected_rtsp_input_builder(source_id_offset=0):
    exp = gst_builder.Builder(None, None, 4, 'auto')
    exp.rtspsrc(
        {'user-id': '', 'user-pw': ''},
        location='rtsp://localhost:8554/test',
        latency=500,
        connections={'stream_%u': f'rtspcapsfilter{source_id_offset}.sink'},
    )
    exp.capsfilter(
        {'caps': 'application/x-rtp,media=video'}, name=f'rtspcapsfilter{source_id_offset}'
    )
    exp.decodebin(
        {'expose-all-streams': False, 'force-sw-decoders': False},
        caps='video/x-raw(ANY)',
        connections={'src_%u': f'decodebin-link{source_id_offset}.sink'},
    )
    # exp.queue(name='queue_in0')
    exp.axinplace(
        lib='libinplace_addstreamid.so',
        mode='meta',
        options=f'stream_id:{source_id_offset}',
        name=f'decodebin-link{source_id_offset}',
    )
    return exp


def test_build_input_with_normal_input():
    pipein = io.SinglePipeInput('gst', config.Source('rtsp://localhost:8554/test'))
    builder = gst_builder.Builder(None, None, 4, 'auto')
    task = pipeline.AxTask('task0', operators.Input())
    pipe.gst._build_input_pipeline(builder, task, pipein)
    exp = _expected_rtsp_input_builder()
    exp.queue(connections={'src': 'inference-task0.sink_%u'})
    assert list(builder) == list(exp)


def test_build_input_with_normal_input_with_sourceid():
    pipein = io.SinglePipeInput('gst', config.Source('rtsp://localhost:8554/test'), source_id=4)
    builder = gst_builder.Builder(None, None, 4, 'auto')
    task = pipeline.AxTask('task0', operators.Input())
    pipe.gst._build_input_pipeline(builder, task, pipein)
    exp = _expected_rtsp_input_builder(4)
    exp.queue(connections={'src': 'inference-task0.sink_%u'})
    assert list(builder) == list(exp)


def test_save_axnet_files():
    elements = [
        {
            'instance': 'axinferencenet',
            'name': 'task0',
            'model': '/cwd/build/modelA.json',
            'p0_options': 'something:a;classlabels_file:bob;;mode:meta',
        },
        {
            'instance': 'axinferencenet',
            'name': 'task1',
            'model': '/abs/build/modelB.json',
            'p0_options': 'something:a;classlabels_file:bob',
        },
        {
            'instance': 'axinferencenet',
            'name': 'task2',
            'model': '/cwd/build/modelC.json',
            'p0_options': 'classlabels_file:bob;mode:meta',
        },
        {
            'instance': 'axinferencenet',
            'name': 'task3',
            'model': '/cwd/build/modelD.json',
            'p0_options': 'classlabels_file:bob',
        },
    ]
    task_names = ['model0', 'model1', 'model2', 'model3']
    with patch.object(os, 'getcwd', return_value='/cwd'):
        with patch.object(Path, 'write_text') as m:
            gst._save_axnet_files(elements, task_names, Path('/abs'))
        m.assert_has_calls(
            [
                call('model=build/modelA.json\np0_options=something:a;mode:meta'),
                call('model=/abs/build/modelB.json\np0_options=something:a'),
                call('model=build/modelC.json\np0_options=mode:meta'),
                call('model=build/modelD.json\np0_options='),
            ]
        )


def test_handle_pair_validation():
    """Test the pair validation handling logic in GstPipe."""
    from unittest.mock import MagicMock, patch

    import numpy as np

    from axelera.app.meta import pair_validation
    from axelera.app.pipe import gst
    from axelera.app.pipe.gst import GstPipe

    # Patch the __init__ method to avoid needing actual dependencies
    with patch.object(GstPipe, '__init__', return_value=None):
        # Create a mock GstPipe object with is_pair_validation=True
        pipe = GstPipe()
        pipe.is_pair_validation = True
        pipe._cached_ax_meta = None

        # Create metadata instances
        ax_meta = gst.meta.AxMeta('id1')
        pv_meta = pair_validation.PairValidationMeta()
        ax_meta.add_instance('task1', pv_meta)

        # Create embeddings - using 2D arrays to match the shape expected by PairValidationMeta
        embeddings1 = np.array([[0.1, 0.2, 0.3, 0.4]])
        embeddings2 = np.array([[0.5, 0.6, 0.7, 0.8]])

        # Create a GstMetaInfo that simulates what we'd get from inference
        meta_info = MagicMock()
        meta_info.task_name = 'task1'
        meta_info.meta_type = pair_validation.PairValidationMeta

        # Create mock task_meta with results
        task_meta = MagicMock()
        task_meta.results = [embeddings1]

        # Create decoded_meta dictionary
        decoded_meta = {meta_info: task_meta}

        # First call to _handle_pair_validation should store the first result and return ax_meta
        cached_meta = pipe._handle_pair_validation(ax_meta, decoded_meta)
        assert cached_meta is not None, "First call should return the metadata for caching"
        assert (
            len(cached_meta.get_instance('task1', pair_validation.PairValidationMeta).results) == 1
        )
        assert np.array_equal(
            cached_meta.get_instance('task1', pair_validation.PairValidationMeta).results[0],
            embeddings1,
        )

        # Update decoded meta with second embedding
        task_meta.results = [embeddings2]

        # Second call to _handle_pair_validation with second embedding should return None
        # indicating processing is complete
        result = pipe._handle_pair_validation(cached_meta, decoded_meta)
        assert result is None, "Second call should return None to indicate pair is complete"

        # Verify both embeddings were collected
        assert (
            len(cached_meta.get_instance('task1', pair_validation.PairValidationMeta).results) == 2
        )
        assert np.array_equal(
            cached_meta.get_instance('task1', pair_validation.PairValidationMeta).results[0],
            embeddings1,
        )
        assert np.array_equal(
            cached_meta.get_instance('task1', pair_validation.PairValidationMeta).results[1],
            embeddings2,
        )


def test_gstpipe_loop_with_pair_validation():
    """Test the _loop method's handling of pair validation within GstPipe."""
    from unittest.mock import MagicMock, patch

    import numpy as np

    from axelera.app.meta import pair_validation
    from axelera.app.pipe import gst
    from axelera.app.pipe.gst import GstPipe, GstStream

    # Patch the __init__ method to avoid needing actual dependencies
    with patch.object(GstPipe, '__init__', return_value=None):
        # Create a mock GstPipe object
        pipe = GstPipe()
        pipe._cached_ax_meta = None
        pipe._meta_assembler = MagicMock()
        pipe.task_graph = MagicMock()
        pipe._stop_event = MagicMock()
        pipe._stop_event.is_set.side_effect = [False, False, True]  # Run loop twice then exit
        pipe.pipeout = MagicMock()
        pipe._on_event = MagicMock()

        # Create metadata instances
        ax_meta1 = gst.meta.AxMeta('id1')
        pv_meta1 = pair_validation.PairValidationMeta()
        ax_meta1.add_instance('task1', pv_meta1)

        ax_meta2 = gst.meta.AxMeta('id2')
        pv_meta2 = pair_validation.PairValidationMeta()
        ax_meta2.add_instance('task1', pv_meta2)

        # Create embeddings - using 2D arrays to match the shape expected by PairValidationMeta
        embeddings1 = np.array([[0.1, 0.2, 0.3, 0.4]])
        embeddings2 = np.array([[0.5, 0.6, 0.7, 0.8]])

        # Create two frames with metadata
        frame1 = MagicMock()
        frame1.stream_id = 0
        frame1.meta = ax_meta1
        frame2 = MagicMock()
        frame2.stream_id = 0
        frame2.meta = ax_meta2

        # Mock decoded metadata
        meta_info = MagicMock()
        meta_info.task_name = 'task1'
        meta_info.meta_type = pair_validation.PairValidationMeta
        meta_info.master = None  # Set master to None to avoid validation errors

        task_meta1 = MagicMock()
        task_meta1.results = [embeddings1]
        decoded_meta1 = {meta_info: task_meta1}

        task_meta2 = MagicMock()
        task_meta2.results = [embeddings2]
        decoded_meta2 = {meta_info: task_meta2}

        # Create a mock stream that yields frame and decoded metadata pairs
        pipe._stream = stream = MagicMock(spec=GstStream)
        evt1 = FrameEvent(result=frame1)
        evt2 = FrameEvent(result=frame2)
        stream.__iter__.return_value = [(evt1, decoded_meta1), (evt2, decoded_meta2)]

        # Test the _loop method's handling of pair validation
        with patch.object(
            pipe, '_handle_pair_validation', wraps=pipe._handle_pair_validation
        ) as mock_handle:
            pipe._loop()

            # Verify _handle_pair_validation was called twice
            assert mock_handle.call_count == 2

            # First call should use frame1.meta and first decoded metadata
            assert mock_handle.call_args_list[0][0][0] == frame1.meta
            assert mock_handle.call_args_list[0][0][1] == decoded_meta1

            # Second call should use cached metadata and second decoded metadata
            assert mock_handle.call_args_list[1][0][1] == decoded_meta2
