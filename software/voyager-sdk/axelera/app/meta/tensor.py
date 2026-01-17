# Copyright Axelera AI, 2025

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Union

import numpy as np

from .. import exceptions
from .base import AxTaskMeta


@dataclass(frozen=True)
class TensorMeta(AxTaskMeta):
    tensors: List[np.ndarray]

    def to_evaluation(self):
        raise exceptions.NotSupportedForTask("TensorMeta", "to_evaluation")

    def draw(self, draw: Any):
        raise exceptions.NotSupportedForTask("TensorMeta", "draw")

    @classmethod
    def decode(cls, data: Dict[str, Union[bytes, bytearray]]) -> TensorMeta:
        """Decodes TensorMeta from a dictionary containing serialized tensor data.

        Assumes the dictionary keys follow the pattern 'data_0', 'dims_0', 'dtype_0', 'data_1', 'dims_1', 'dtype_1' ...
        where 'data_i' keys hold tensor data bytes, 'dims_i' keys hold dimension bytes, and 'dtype_i' keys hold dtype string bytes.
        Example: data = {'data_0': <data0_bytes>, 'dims_0': <dims0_bytes>, 'dtype_0': b'f4', ...}
        If 'dtype_i' is missing, defaults to float32 for backward compatibility.
        """

        decoded_tensors: List[np.ndarray] = []

        i = 0
        while True:
            data_key = f'data_{i}'
            dims_key = f'dims_{i}'
            dtype_key = f'dtype_{i}'

            # Check if the next pair of keys exists
            if data_key not in data or dims_key not in data:
                break  # No more tensors

            # --- Process tensor i ---
            try:
                tensor_data_bytes = data[data_key]
                dims_bytes = data[dims_key]
                dtype_bytes = data.get(dtype_key, None)
                if dtype_bytes is not None:
                    dtype_str = dtype_bytes.decode('utf-8')
                else:
                    dtype_str = 'f4'  # Default to float32 for backward compatibility

                # Handle potentially empty buffers
                if not dims_bytes:
                    dims = np.array([], dtype=np.int64)  # Empty dimensions
                else:
                    if len(dims_bytes) % 8 != 0:
                        raise ValueError(
                            f"Dimensions buffer size ({len(dims_bytes)}) for tensor {i} (key {dims_key}) is not a multiple of 8."
                        )
                    dims = np.frombuffer(dims_bytes, dtype=np.int64)

                if not tensor_data_bytes:
                    tensor_data_flat = np.array([], dtype=np.dtype(dtype_str))  # Empty data
                else:
                    # Ensure buffer size is multiple of dtype itemsize
                    itemsize = np.dtype(dtype_str).itemsize
                    if len(tensor_data_bytes) % itemsize != 0:
                        raise ValueError(
                            f"Data buffer size ({len(tensor_data_bytes)}) for tensor {i} (key {data_key}) is not a multiple of dtype itemsize ({itemsize})."
                        )
                    tensor_data_flat = np.frombuffer(tensor_data_bytes, dtype=np.dtype(dtype_str))

                expected_size = np.prod(dims) if dims.size > 0 else 0

                if tensor_data_flat.size != expected_size:
                    raise ValueError(
                        f"Data size mismatch for tensor {i} (keys {data_key}, {dims_key}): "
                        f"expected {expected_size} (from dims {dims}), got {tensor_data_flat.size}"
                    )

                # Reshape
                if expected_size > 0:
                    if not np.all(dims > 0):
                        raise ValueError(
                            f"Invalid dimensions {dims} for non-empty tensor {i} (keys {data_key}, {dims_key})"
                        )
                    tensor = tensor_data_flat.reshape(dims)
                elif dims.size > 0:
                    tensor = np.empty(shape=dims, dtype=np.dtype(dtype_str))
                else:
                    if expected_size == 0 and tensor_data_flat.size == 0:
                        tensor = np.empty(shape=(0,), dtype=np.dtype(dtype_str))
                    elif expected_size == 1 and tensor_data_flat.size == 1:
                        tensor = tensor_data_flat.reshape(())
                    else:
                        raise ValueError(
                            f"Inconsistent state for tensor {i} with no dimensions (keys {data_key}, {dims_key}). "
                            f"Expected size {expected_size}, Data size {tensor_data_flat.size}"
                        )

                decoded_tensors.append(tensor)

            except ValueError as e:
                raise ValueError(f"Error decoding tensor {i} (keys {data_key}, {dims_key}): {e}")
            except KeyError:
                raise RuntimeError(
                    f"Logic error: Missing expected key {data_key} or {dims_key} for tensor {i}"
                )
            except Exception as e:
                raise RuntimeError(
                    f"Unexpected error processing tensor {i} (keys {data_key}, {dims_key}): {e}"
                )
            # --- End Process tensor i ---

            i += 1  # Move to the next tensor index

        return cls(tensors=decoded_tensors)
