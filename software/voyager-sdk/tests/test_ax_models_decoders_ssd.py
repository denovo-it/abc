# Copyright Axelera AI, 2025
import pytest

from ax_models.decoders import ssd


@pytest.mark.parametrize(
    'input, expected',
    [
        (None, []),
        ('', []),
        ('person', ['person']),
        ('person,car', ['person', 'car']),
        ('person, car', ['person', 'car']),
        (' person ; car ; bus ', ['person', 'car', 'bus']),
        ([], []),
        (['person'], ['person']),
        (['person', 'car'], ['person', 'car']),
        (['person', ' car'], ['person', 'car']),
        ([' person ', ' car ', ' bus '], ['person', 'car', 'bus']),
        ("$$Variable", "$$Variable"),
    ],
)
def test_label_filter_formats(input, expected):
    """Test the label filter parsing logic."""
    decoder = ssd.DecodeSsdMobilenet(
        box_format="xywh",
        normalized_coord=True,
        label_filter=input,
    )
    assert decoder.label_filter == expected
