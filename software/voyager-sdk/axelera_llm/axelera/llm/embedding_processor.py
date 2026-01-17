# Copyright Axelera AI, 2025
"""
embedding_processor.py
EmbeddingProcessor class and batch processor utility for LLM inference.
"""

import mmap
import os
from typing import Dict, Optional, Tuple

from axelera.llm import logging_utils
import numpy as np

LOG = logging_utils.getLogger(__name__)


class EmbeddingProcessor:
    def __init__(self, embedding_file: str, max_batch_size: int = 1, max_seq_length: int = 2048):
        """
        Initialize with pre-dumped embedding file
        Args:
            embedding_file: Path to the .npz file containing embeddings
        """
        self.embedding_file = embedding_file
        self._load_embeddings()
        # Pre-allocate buffers for optimized processing
        self.embedding_buffer = np.zeros(
            (max_batch_size, max_seq_length, self.embedding_dim),
            dtype=np.float16,
            order="C",  # Use C-contiguous memory layout
        )
        self.mask_buffer = np.ones(
            (max_batch_size, max_seq_length),
            dtype=np.float16,
            order="C",  # Use C-contiguous memory layout
        )
        LOG.info(f"EmbeddingProcessor initialized with file: {embedding_file}")

    def _load_embeddings(self):
        """Load embeddings with memory mapping"""
        data = np.load(self.embedding_file)
        self.vocab_size = data["vocab_size"]
        self.embedding_dim = data["embedding_dim"]
        self.embeddings = np.load(self.embedding_file, mmap_mode="r")["embeddings"]
        LOG.info(
            f"Loaded embeddings: vocab_size={self.vocab_size}, embedding_dim={self.embedding_dim}"
        )

    def process_batch(
        self, input_ids: np.ndarray, padding_length: Optional[int] = None
    ) -> Dict[str, np.ndarray]:
        """Vectorized implementation"""
        batch_size, seq_length = input_ids.shape
        final_length = padding_length if padding_length else seq_length
        valid_length = min(seq_length, final_length)

        # Vectorized lookup
        flat_ids = input_ids[:, :valid_length].reshape(-1)
        flat_embeddings = self.embeddings[flat_ids]
        embeddings = flat_embeddings.reshape(batch_size, valid_length, self.embedding_dim)

        if final_length > valid_length:
            final_embeddings = np.zeros(
                (batch_size, final_length, self.embedding_dim), dtype=np.float16
            )
            final_embeddings[:, :valid_length] = embeddings
        else:
            final_embeddings = embeddings

        attention_mask = np.ones((batch_size, final_length), dtype=np.float16)
        if padding_length:
            attention_mask[:, seq_length:] = 0

        return final_embeddings, attention_mask
        # {"embeddings": final_embeddings, "attention_mask": attention_mask}

    def get_embedding_shape(self) -> Tuple[int, int]:
        """Return embedding matrix shape"""
        return (self.vocab_size, self.embedding_dim)

    def __del__(self):
        """Cleanup memory mapping"""
        if hasattr(self, "embeddings"):
            del self.embeddings


def create_batch_processor(embedding_file: str, batch_size: int = 32):
    """
    Create a batch processor with pre-allocated buffers
    """
    processor = EmbeddingProcessor(embedding_file)
    vocab_size, embedding_dim = processor.get_embedding_shape()

    # Pre-allocate buffers
    embeddings_buffer = np.zeros((batch_size, 512, embedding_dim), dtype=np.float16)
    attention_mask_buffer = np.ones((batch_size, 512), dtype=np.float16)

    LOG.info(f"Created batch processor for embedding file: {embedding_file}")
    return processor, embeddings_buffer, attention_mask_buffer
