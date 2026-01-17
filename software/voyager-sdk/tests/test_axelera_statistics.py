#!/usr/bin/env python
# Copyright Axelera AI, 2024

import os
import pathlib
import tempfile
from unittest.mock import patch

from axelera.app import statistics

GOLD_SRC = pathlib.Path(__file__).parent / "example_gst_tracer_log.txt"


class MockMetric:
    def __init__(self, value, title):
        self.value = value
        self.title = title

    def get_metrics(self):
        return [self]


EXPECTED = '''\
========================================================================
Element                                         Time(𝜇s)   Effective FPS
========================================================================
qtdemux0                                              11        88,393.0
h265parse0                                            31        32,002.8
capsfilter0                                            9       109,694.1
decodebin-link0                                        9       103,046.1
axtransform-colorconvert0                          6,389           156.5
inference-task0:libtransform_resize_cl_0             138         7,246.1
inference-task0:libtransform_padding_0               501         1,994.8
inference-task0:inference                          2,760           362.3
 └─ Metis                                          6,666           150.0
 └─ Host                                           5,000           200.0
inference-task0:Inference latency                106,989             n/a
inference-task0:libdecode_yolov5_0                   254         3,937.0
inference-task0:libinplace_nms_0                      18        53,637.8
inference-task0:Postprocessing latency             6,125             n/a
inference-task0:Total latency                    154,221             n/a
========================================================================
End-to-end average measurement                                       0.0
========================================================================'''


def test_format_table_host_and_metis():
    tracers = [MockMetric(200, 'Host'), MockMetric(150, 'Metis')]
    got = statistics.format_table(GOLD_SRC, tracers, statistics.Plain)
    assert got == EXPECTED


def test_format_table_host():
    tracers = [MockMetric(200, 'Host')]
    got = statistics.format_table(GOLD_SRC, tracers, statistics.Plain)
    exp = '\n'.join(l for l in EXPECTED.splitlines() if 'Metis' not in l)
    assert got == exp


def test_format_table_metis():
    tracers = [MockMetric(150, 'Metis')]
    got = statistics.format_table(GOLD_SRC, tracers, statistics.Plain)
    exp = '\n'.join(l for l in EXPECTED.splitlines() if 'Host' not in l)
    assert got == exp


def test_format_table_no_tracers():
    tracers = []
    got = statistics.format_table(GOLD_SRC, tracers, statistics.Plain)
    exp = '\n'.join(l for l in EXPECTED.splitlines() if 'Host' not in l and 'Metis' not in l)
    assert got == exp


def test_format_table_tracers_present_but_no_value(caplog):
    tracers = [MockMetric(0, 'Host'), MockMetric(0, 'Metis')]
    got = statistics.format_table(GOLD_SRC, tracers, statistics.Plain)
    exp = '\n'.join(l for l in EXPECTED.splitlines() if 'Host' not in l and 'Metis' not in l)
    assert got == exp
    assert [r.message for r in caplog.records] == [
        'Unable to determine Host metrics',
        'Unable to determine Metis metrics',
    ]


def test_format_empty_table():
    tracers = []
    with patch.object(pathlib.Path, 'read_text', return_value=''):
        got = statistics.format_table(GOLD_SRC, tracers, statistics.Plain)
    assert (
        got
        == '''\
========================================================================
Element                                         Time(𝜇s)   Effective FPS
========================================================================
========================================================================
End-to-end average measurement                                       0.0
========================================================================'''
    )


def test_initialise_logging():
    with patch.object(tempfile, 'NamedTemporaryFile') as mock:
        mock.return_value.name = '/some/fake_log_file'
        with patch.dict(os.environ, {}, clear=True):
            got = statistics.initialise_logging()
            assert os.environ['GST_DEBUG'] == 'GST_TRACER:7'
            assert os.environ['GST_TRACERS'] == 'latency(flags=element)'
            assert os.environ['GST_DEBUG_FILE'] == '/some/fake_log_file'
    mock.assert_called_once_with(mode='w')
    assert got[1] == pathlib.Path('/some/fake_log_file')
    assert hasattr(got[0], 'name')
