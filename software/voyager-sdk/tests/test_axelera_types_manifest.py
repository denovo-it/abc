# Copyright Axelera AI, 2023

from axelera import types


def test_construction():
    manifest = types.Manifest(
        'path',
        input_shapes=[(1, 3, 224, 224)],
        input_dtypes=['uint8'],
        output_shapes=[(1, 1000)],
        output_dtypes=['float32'],
        quantize_params=((0.007, 0),),
        dequantize_params=(
            (0.084, 59),
            (0.14, -8),
        ),
    )
    assert manifest.quantized_model_file == 'path'
    assert manifest.quantize_params == ((0.007, 0),)
    assert manifest.dequantize_params == ((0.084, 59), (0.14, -8))
