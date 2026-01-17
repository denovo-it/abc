# Copyright Axelera AI, 2025
"""
generation_stats.py
Utility for tracking and reporting LLM generation statistics (TTFT, tokens/sec, etc).
"""

import time

from axelera.llm import logging_utils

LOG = logging_utils.getLogger(__name__)


class GenerationStats:
    def __init__(self):
        self.reset()

    def reset(self):
        self.tokenize_start = None
        self.tokenize_end = None
        self.prefill_end = None
        self.first_token_time = None
        self.generation_start = None
        self.generation_end = None
        self.token_times = []
        self.num_tokens = 0
        self.cpu_data = None
        self.temp_data = None

    def start_tokenization(self):
        self.tokenize_start = time.time()

    def end_tokenization(self):
        self.tokenize_end = time.time()

    def end_prefill(self):
        self.prefill_end = time.time()

    def start_generation(self):
        self.generation_start = time.time()

    def record_token(self):
        now = time.time()
        if self.first_token_time is None:
            self.first_token_time = now
        self.token_times.append(now)
        self.num_tokens += 1

    def end_generation(self):
        self.generation_end = time.time()

    def get_stats(self):
        tokenize_time = (
            (self.tokenize_end - self.tokenize_start)
            if self.tokenize_start and self.tokenize_end
            else None
        )
        prefill_time = (
            (self.prefill_end - self.tokenize_end)
            if self.prefill_end and self.tokenize_end
            else None
        )
        ttft = (
            (self.first_token_time - self.generation_start)
            if self.first_token_time and self.generation_start
            else None
        )
        total_time = (
            (self.generation_end - self.generation_start)
            if self.generation_end and self.generation_start
            else None
        )
        tokens_sec = (self.num_tokens / total_time) if total_time and self.num_tokens > 0 else None
        stats = {
            "tokenize_time": tokenize_time,
            "prefill_time": prefill_time,
            "ttft": ttft,
            "total_time": total_time,
            "tokens_sec": tokens_sec,
            "num_tokens": self.num_tokens,
        }

        # Include CPU and temperature data if available
        if self.cpu_data:
            stats["cpu_data"] = self.cpu_data
        if self.temp_data:
            stats["temp_data"] = self.temp_data

        return stats

    def _format_time_ms_us(self, seconds):
        if seconds is None:
            return "N/A"
        ms = seconds * 1000
        if ms < 1:
            return f"{seconds * 1_000_000:.1f}us"
        else:
            return f"{ms:.1f}ms"

    def summary(self, log=True):
        stats = self.get_stats()
        summary_str = (
            f"Tokenization: {stats['tokenize_time']*1000:.1f}ms | "
            f"Prefill: {self._format_time_ms_us(stats['prefill_time'])} | "
            f"TTFT: {stats['ttft']:.3f}s | "
            f"Gen: {stats['total_time']:.3f}s | "
            f"Tokens/sec: {stats['tokens_sec']:.2f} | "
            f"Tokens: {stats['num_tokens']}"
        )

        # Add CPU and temperature data if available
        if "cpu_data" in stats:
            for title, value in stats["cpu_data"].items():
                summary_str += f"\n{title}: {value:.1f}%"

        if "temp_data" in stats:
            for title, value in stats["temp_data"].items():
                summary_str += f"\n{title}: {value:.1f}°C"

        if log:
            LOG.info(summary_str)
        return summary_str

    def update_system_metrics(self, tracers):
        """
        Update CPU and temperature data from tracers.
        """
        if not tracers:
            return

        cpu_data = {}
        temp_data = {}

        for tracer in tracers:
            for metric in tracer.get_metrics():
                if "CPU" in metric.title:
                    cpu_data[metric.title] = metric.value
                elif "Temperature" in metric.title or "Temp" in metric.title:
                    temp_data[metric.title] = metric.value

        # Update statistics with collected data
        if cpu_data:
            self.cpu_data = cpu_data
        if temp_data:
            self.temp_data = temp_data
