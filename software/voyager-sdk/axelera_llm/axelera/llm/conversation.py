# Copyright Axelera AI, 2025
"""
conversation.py
Core chat logic for LLM inference: ChatEncoder, history management, prompt building, etc.
"""

from typing import List, Optional, Tuple

from axelera.llm import logging_utils, utils
import numpy as np

LOG = logging_utils.getLogger(__name__)


def compute_min_response_space(max_tokens):
    return min(128, max(32, max_tokens // 8))


class ChatEncoder:
    """
    Encodes the chat history and message into input IDs and embeddings with the consideration of the minimum response space.
    Optimized to cache encoded history to avoid redundant encodings.
    """

    def __init__(
        self,
        tokenizer,
        max_tokens,
        embedding_processor=None,
        system_prompt="",
        min_response_space=None,
    ):
        self.tokenizer = tokenizer
        self.max_tokens = max_tokens
        self.embedding_processor = embedding_processor
        self.current_cutoff = None
        self.last_messages = ''
        self.min_response_space = (
            min_response_space
            if min_response_space is not None
            else compute_min_response_space(max_tokens)
        )
        self.prompt_length = 0
        self.current_context = None
        self.update_system_prompt(system_prompt)
        self.cached_history = []  # List of tuples: (human_text, assistant_text)
        self.cached_history_token_counts = (
            []
        )  # List of tuples: (human_token_count, assistant_token_count)
        self.cached_history_token_total = 0  # Total tokens in cached history

    def encode(self, message, history):
        TARGET_LENGTH = self.max_tokens - self.min_response_space
        encoded_message = self.tokenizer.encode(message, add_special_tokens=False)
        message_token_count = len(encoded_message)
        base_tokens = self.system_tokens + message_token_count
        if not history:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": message},
            ]
            text = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            input_ids = self.tokenizer.encode(text, return_tensors="np")
            self.last_messages = messages
            self.current_cutoff = 0
            self.prompt_length = input_ids.shape[1]
            self.current_context = input_ids
            self.cached_history = []
            self.cached_history_token_counts = []
            self.cached_history_token_total = 0
            return input_ids, self._process_embeddings(input_ids)
        available_tokens = TARGET_LENGTH - base_tokens
        if len(self.cached_history) != len(history):
            common_length = min(len(self.cached_history), len(history))
            for i in range(common_length):
                if self.cached_history[i] != history[i]:
                    self.cached_history = self.cached_history[:i]
                    self.cached_history_token_counts = self.cached_history_token_counts[:i]
                    self.cached_history_token_total = sum(
                        sum(counts) for counts in self.cached_history_token_counts
                    )
                    break
            for i in range(len(self.cached_history), len(history)):
                human_text, assistant_text = history[i]
                if assistant_text:
                    human_tokens = len(self.tokenizer.encode(human_text, add_special_tokens=False))
                    assistant_tokens = len(
                        self.tokenizer.encode(assistant_text, add_special_tokens=False)
                    )
                    self.cached_history.append((human_text, assistant_text))
                    self.cached_history_token_counts.append((human_tokens, assistant_tokens))
                    self.cached_history_token_total += human_tokens + assistant_tokens
        pairs_to_use = 0
        cumulative_tokens = 0
        for i in range(len(self.cached_history) - 1, -1, -1):
            tokens = sum(self.cached_history_token_counts[i])
            if cumulative_tokens + tokens > available_tokens:
                break
            cumulative_tokens += tokens
            pairs_to_use += 1
        messages = [{"role": "system", "content": self.system_prompt}]
        start_idx = len(self.cached_history) - pairs_to_use
        for i in range(start_idx, len(self.cached_history)):
            human_text, assistant_text = self.cached_history[i]
            messages.append({"role": "user", "content": human_text})
            messages.append({"role": "assistant", "content": assistant_text})
        messages.append({"role": "user", "content": message})
        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        input_ids = self.tokenizer.encode(text, return_tensors="np")
        if input_ids.shape[1] > self.max_tokens:
            pairs_to_use = max(0, pairs_to_use - 2)
            messages = [{"role": "system", "content": self.system_prompt}]
            start_idx = len(self.cached_history) - pairs_to_use
            for i in range(start_idx, len(self.cached_history)):
                human_text, assistant_text = self.cached_history[i]
                messages.append({"role": "user", "content": human_text})
                messages.append({"role": "assistant", "content": assistant_text})
            messages.append({"role": "user", "content": message})
            text = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            input_ids = self.tokenizer.encode(text, return_tensors="np")
        self.current_cutoff = pairs_to_use
        self.last_messages = messages
        self.prompt_length = input_ids.shape[1]
        self.current_context = input_ids
        return input_ids, self._process_embeddings(input_ids)

    def add_to_history(self, human_message, assistant_message):
        self.cached_history.append((human_message, assistant_message))
        human_encoded = self.tokenizer.encode(human_message, add_special_tokens=False)
        assistant_encoded = self.tokenizer.encode(assistant_message, add_special_tokens=False)
        human_token_count = len(human_encoded)
        assistant_token_count = len(assistant_encoded)
        self.cached_history_token_counts.append((human_token_count, assistant_token_count))
        self.cached_history_token_total += human_token_count + assistant_token_count

    def remove_from_history(self, num_pairs):
        for _ in range(num_pairs):
            if self.cached_history:
                removed_pair = self.cached_history.pop(0)
                removed_counts = self.cached_history_token_counts.pop(0)
                self.cached_history_token_total -= sum(removed_counts)

    def _process_embeddings(self, input_ids):
        if self.embedding_processor is None:
            return None
        return self.embedding_processor.process_batch(input_ids)[0]

    def reset(self, preserve_system_prompt=False):
        """
        Reset the chat encoder state, clearing all history.

        Args:
            preserve_system_prompt: If True, avoid re-initializing system prompt template
                                   which can be expensive. Default is False.
        """
        self.current_cutoff = None
        # Make sure to fully reset the last_messages to avoid any lingering system instructions
        self.last_messages = ''
        self.cached_history = []
        self.cached_history_token_counts = []
        self.cached_history_token_total = 0
        self.current_context = None
        self.prompt_length = 0

    def update_system_prompt(self, new_prompt):
        """
        Update the system prompt and related cached values.

        Args:
            new_prompt: The new system prompt text
        """
        # Only update if prompt has changed to avoid unnecessary processing
        if hasattr(self, 'system_prompt') and self.system_prompt == new_prompt:
            return

        self.system_prompt = new_prompt
        self.system_template = self.tokenizer.apply_chat_template(
            [{"role": "system", "content": new_prompt}], tokenize=False, add_generation_prompt=True
        )
        self.system_tokens = len(
            self.tokenizer.encode(self.system_template, add_special_tokens=False)
        )
        # Reset history but preserve system prompt to avoid circular call
        self.reset(preserve_system_prompt=True)

    def append_generated_token(self, token_id):
        if self.current_context is None:
            raise ValueError("No active context - encode() must be called first")
        new_token = np.array([[token_id]])
        new_token = np.asarray(new_token)
        # Robustly ensure new_token is always shape (1, 1)
        if new_token.ndim == 0:
            new_token = new_token.reshape(1, 1)
        elif new_token.ndim == 1:
            new_token = new_token[None, :]
            if new_token.shape[1] != 1:
                new_token = new_token[:, :1]
        elif new_token.ndim > 2:
            new_token = new_token.squeeze()
            if new_token.ndim == 0:
                new_token = new_token.reshape(1, 1)
            elif new_token.ndim == 1:
                new_token = new_token[None, :]
            elif new_token.ndim > 2:
                raise ValueError(
                    f"new_token has unexpected shape after squeeze: {new_token.shape}"
                )
        # Now new_token should be (1, 1)
        if self.current_context.shape[1] - self.prompt_length >= (
            self.max_tokens - self.prompt_length
        ):
            retained_tokens = self.max_tokens - self.prompt_length - 1
            context_start = self.current_context.shape[1] - retained_tokens
            self.current_context = np.concatenate(
                [
                    self.current_context[:, : self.prompt_length],
                    self.current_context[:, context_start:],
                    new_token,
                ],
                axis=1,
            )
        else:
            self.current_context = np.concatenate([self.current_context, new_token], axis=1)
        if self.embedding_processor is not None:
            return self.embedding_processor.process_batch(new_token)[0]
        return self.current_context

    def get_generated_text(self):
        if self.current_context is None:
            return ""
        generated_tokens = self.current_context[0, self.prompt_length :]
        return self.tokenizer.decode(generated_tokens, skip_special_tokens=True)


def stream_response(
    model_instance,
    chat_encoder,
    tokenizer,
    input_ids,
    embedding_features,
    max_tokens,
    temperature,
    eos_token_id,
    end_token_id,
    stats=None,
    tracers=None,
):
    """
    Generator that yields (new_text, stats_dict) as tokens are generated.
    stats_dict includes: ttft, tokens_per_sec, tokens, finished (bool)
    """
    import time

    generated_tokens = []
    prompt_length = input_ids.shape[1]
    old_text = ""
    word_buffer = ""
    response = ""
    updated = False
    start_time = time.time()
    ttft = None
    tokens = 0
    for i in range(max_tokens - prompt_length):
        if stats and i == 0:
            stats.end_prefill()
        with utils.suppress_stdout_stderr():
            logits = model_instance.run((input_ids, embedding_features))
        token_id, is_end_token = sample_next_token(logits, temperature, eos_token_id, end_token_id)
        if is_end_token:
            break
        if isinstance(token_id, (list, tuple, np.ndarray)):
            token_id_int = int(np.array(token_id).flatten()[0])
        else:
            token_id_int = int(token_id)
        generated_tokens.append(token_id_int)
        if stats:
            stats.record_token()
        tokens += 1
        embedding_features = chat_encoder.append_generated_token(token_id)
        input_ids = chat_encoder.current_context
        current_text = tokenizer.decode(generated_tokens, skip_special_tokens=False)
        new_part = current_text[len(old_text) :]
        word_buffer += new_part
        # Streaming logic
        while True:
            if ' ' in word_buffer:
                word, word_buffer = word_buffer.split(' ', 1)
                response += word + ' '
                if ttft is None:
                    ttft = time.time() - start_time
                tokens_per_sec = tokens / max(time.time() - start_time, 1e-6)
                stats_dict = dict(
                    ttft=ttft, tokens_per_sec=tokens_per_sec, tokens=tokens, finished=False
                )
                yield response, stats_dict
                updated = True
            elif '\n' in word_buffer:
                word, word_buffer = word_buffer.split('\n', 1)
                response += word + '\n'
                if ttft is None:
                    ttft = time.time() - start_time
                tokens_per_sec = tokens / max(time.time() - start_time, 1e-6)
                stats_dict = dict(
                    ttft=ttft, tokens_per_sec=tokens_per_sec, tokens=tokens, finished=False
                )
                yield response, stats_dict
                updated = True
            else:
                break
        old_text = current_text
    # Final yield for any remaining buffer or if nothing was yielded in the loop
    if word_buffer or not updated:
        response += word_buffer
        tokens_per_sec = tokens / max(time.time() - start_time, 1e-6)
        stats_dict = dict(
            ttft=ttft or 0, tokens_per_sec=tokens_per_sec, tokens=tokens, finished=True
        )
        yield response, stats_dict


def sample_next_token(logits, temperature, eos_token_id=None, end_token_id=None):
    """
    Sample the next token from logits using temperature. Returns token_id and is_end_token.
    """
    import numpy as np

    if isinstance(logits, list):
        logits = np.array(logits[0])
    if not isinstance(logits, (list, np.ndarray)) or len(logits) == 0:
        raise ValueError("logits must be a non-empty list or numpy array.")
    if temperature == 0:
        next_token_id = np.argmax(logits, axis=-1)
    else:
        scaled_logits = logits / temperature
        exp_logits = np.exp(scaled_logits - np.max(scaled_logits))
        probs = exp_logits / np.sum(exp_logits)
        next_token_id = np.random.choice(len(probs), p=probs)
    is_end_token = False
    if eos_token_id is not None:
        is_end_token = next_token_id == eos_token_id
    if end_token_id is not None:
        is_end_token = is_end_token or (next_token_id == end_token_id)
    return next_token_id, is_end_token
