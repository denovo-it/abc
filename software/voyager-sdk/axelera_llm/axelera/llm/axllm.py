#!/usr/bin/env python
# Copyright Axelera AI, 2025
# Unified entry point for LLM inference: supports both CLI and UI modes.

from pathlib import Path
import sys
from typing import Callable, Iterator, Tuple

from rich.console import Console

from . import config, inf_tracers, logging_utils, utils, yaml_parser
from .cli_ui import display_plain, display_rich_factory
from .conversation import ChatEncoder, stream_response
from .generation_stats import GenerationStats
from .model_instance import AxInstance, TorchInstance
from .ui import build_llm_ui, build_llm_ui_native

LOG = logging_utils.getLogger(__name__)


def get_tokenizer_from_url(tokenizer_url, tokenizer_md5, model_name, build_root):
    """
    Download and extract tokenizer zip from tokenizer_url if not already present.
    Returns the local directory containing the tokenizer files as a string.
    """
    safe_name = model_name.replace("/", "_")
    local_dir = build_root / "tokenizers" / safe_name
    local_dir.mkdir(parents=True, exist_ok=True)
    extracted_flag = local_dir / ".extracted_tokenizer"
    zip_path = local_dir / "tokenizer.zip"

    existing_md5 = None
    if extracted_flag.exists():
        with open(extracted_flag, "r") as f:
            existing_md5 = f.read().strip()

    expected_md5 = tokenizer_md5 or "done"

    if not existing_md5 or existing_md5 != expected_md5:
        LOG.info(f"Downloading and extracting tokenizer from {tokenizer_url} ...")
        utils.download_and_extract_asset(
            tokenizer_url, zip_path, md5=tokenizer_md5, delete_archive=True
        )
        extracted_flag.write_text(expected_md5)

    return str(local_dir)


def load_tokenizer(
    tokenizer_dir: str, tokenizer_url: str, tokenizer_md5: str, model_name: str, build_root: Path
) -> 'AutoTokenizer':
    """Load tokenizer following priority order:
    1. Local tokenizer directory if specified
    2. Download from tokenizer_url if available
    3. Load directly from model_name as fallback

    Args:
        tokenizer_dir: Path to local tokenizer directory
        tokenizer_url: URL to download tokenizer from
        model_name: Name of the model to load tokenizer from
        build_root: Root directory for building/downloading

    Returns:
        Loaded tokenizer instance

    Raises:
        RuntimeError: If all tokenizer loading attempts fail
    """
    from transformers import AutoTokenizer

    input_source = None
    attempts = []

    try:
        if tokenizer_dir:
            LOG.info(f"Attempting to load tokenizer from local directory: {tokenizer_dir}")
            attempts.append(f"local directory: {tokenizer_dir}")
            input_source = tokenizer_dir
        elif tokenizer_url:
            LOG.info(f"Attempting to use tokenizer from URL: {tokenizer_url}")
            attempts.append(f"URL: {tokenizer_url}")
            input_source = get_tokenizer_from_url(
                tokenizer_url, tokenizer_md5, model_name, build_root
            )
        else:
            LOG.info(f"Attempting to load tokenizer directly from model: {model_name}")
            attempts.append(f"model: {model_name}")
            input_source = model_name

        return AutoTokenizer.from_pretrained(input_source, use_fast=True, padding_side="right")

    except Exception as e:
        error_msg = (
            "Failed to load tokenizer after attempting:\n"
            + "\n".join(f"- {attempt}" for attempt in attempts)
            + f"\nLast error: {str(e)}"
        )
        raise RuntimeError(error_msg)


def find_available_port(starting_port):
    """Find an available port starting from the specified port."""
    for port in range(starting_port, 65536):
        if is_port_available(port):
            return port
    raise RuntimeError("No available ports found")


def is_port_available(port):
    """Check if a port is available."""
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', port))
            return True
    except OSError:
        return False


def _main(args, tracers):
    try:
        network_path = args.network

        # load network yaml directly instead of using schema, as there is a bug making the runtime env changed, making Context failed to load if I put this after schema.load
        network_yaml = utils.load_yamlfile(network_path)

        network_build_root = args.build_root / network_yaml['name']
        if not network_build_root.exists():
            network_build_root.mkdir(parents=True, exist_ok=True)

        # --- Tokenizer creation ---
        if len(network_yaml['models']) > 1:
            raise ValueError("Only one model is supported for LLM inference.")
        model = next(iter(network_yaml['models'].values()))
        extra_kwargs = model.get('extra_kwargs', {}).get('llm', {})
        ddr_requirement_gb = extra_kwargs.get('ddr_requirement_gb', 4)

        model_name = extra_kwargs.get('model_name', None)
        if not model_name:
            raise ValueError("No 'model_name' found in extra_kwargs for torch pipeline.")
        tokenizer_url = extra_kwargs.get('tokenizer_url', None)
        tokenizer_md5 = extra_kwargs.get('tokenizer_md5', '')

        system_prompt = args.system_prompt
        if 'Velvet' in model_name and system_prompt is config.GENAI_SYSTEM_PROMPT:
            # we already know that velvet-2b-1024-static doesn't function well with our default system prompt
            # so we set it to empty string if not provided by the user
            LOG.debug("Set default system prompt for velvet-2b-1024-static as empty string")
            system_prompt = ""

        tokenizer = load_tokenizer(
            tokenizer_dir=args.tokenizer_dir,
            tokenizer_url=tokenizer_url,
            tokenizer_md5=tokenizer_md5,
            model_name=model_name,
            build_root=args.build_root,
        )

        max_tokens = extra_kwargs.get('max_tokens', 1024)
        temperature = args.temperature
        min_response_space = extra_kwargs.get('min_response_space', None)

        # --- Model/instance creation  ---
        pipeline = args.pipeline
        if pipeline == 'transformers-aipu':
            model_instance = AxInstance(
                yaml=network_yaml,
                build_root=args.build_root,
                ddr_requirement_gb=ddr_requirement_gb,
                device_selector=args.devices,
            )
            embedding_processor = model_instance.embedding_processor
        elif pipeline == 'transformers':
            # torch (cpu/gpu)
            model_instance = TorchInstance(model_name)
            embedding_processor = None
        else:
            raise ValueError(f"Invalid pipeline: {pipeline}")

        eos_token_id = tokenizer.eos_token_id
        end_token_id = next(
            (
                token_id
                for token_id, token in tokenizer.added_tokens_decoder.items()
                if token.content == "<|end|>"
            ),
            None,
        )

        chat_encoder = ChatEncoder(
            tokenizer,
            max_tokens,
            embedding_processor=embedding_processor,
            system_prompt=system_prompt,
            min_response_space=min_response_space,
        )

        # --- Mode selection: CLI or UI ---
        if args.ui:
            if args.ui in ('local_simple', 'share_simple'):
                demo = build_llm_ui_native(
                    model_instance,
                    chat_encoder,
                    tokenizer,
                    max_tokens,
                    system_prompt,
                    temperature,
                    model_name,
                    end_token_id,
                    keep_history=args.history,
                    tracers=tracers,
                )
            else:
                demo = build_llm_ui(
                    model_instance,
                    chat_encoder,
                    tokenizer,
                    max_tokens,
                    system_prompt,
                    temperature,
                    model_name,
                    end_token_id,
                    keep_history=args.history,
                    tracers=tracers,
                )
            demo.queue()

            port = args.port
            if not is_port_available(port):
                LOG.debug(f"Port {port} is in use, searching for available port...")
                port = find_available_port(port + 1)
                LOG.info(f"Using port {port} instead of {args.port} as it was in use.")

            share_mode = args.ui not in ('local', 'local_simple')
            demo.launch(share=share_mode, server_port=port)
        else:
            show_stats = args.show_stats
            history = []
            use_rich = args.rich_cli
            display_fn = display_rich_factory(Console()) if use_rich else display_plain
            if args.prompt is not None:
                # Single-prompt CLI mode (one-shot)
                stats = GenerationStats()
                stats.start_tokenization()
                input_ids, embedding_features = chat_encoder.encode(args.prompt, history)
                stats.end_tokenization()
                stats.start_generation()
                response_stream = stream_response(
                    model_instance,
                    chat_encoder,
                    tokenizer,
                    input_ids,
                    embedding_features,
                    max_tokens,
                    temperature,
                    eos_token_id,
                    end_token_id,
                    stats,
                )
                response = display_fn(args.prompt, response_stream, False, history)
                stats.end_generation()

                if tracers and show_stats:
                    stats.update_system_metrics(tracers)

                history.append((args.prompt, response))
                if show_stats:
                    stats.summary(log=True)
            else:
                # Interactive CLI mode
                LOG.info("Welcome to LLM CLI. Type 'exit' to quit.")
                run_chat_loop(
                    display_fn,
                    show_stats,
                    history,
                    chat_encoder,
                    model_instance,
                    tokenizer,
                    max_tokens,
                    temperature,
                    eos_token_id,
                    end_token_id,
                    LOG,
                    keep_history=args.history,
                    tracers=tracers,
                )
    except Exception:
        raise


def main() -> int:
    try:
        network_yaml_info = yaml_parser.get_network_yaml_info(
            include_collections=['llm_local', 'llm_cards', 'llm_zoo']
        )
        parser = config.create_llm_argparser(
            network_yaml_info, description='Perform LLM inference on an Axelera platform'
        )

        args = parser.parse_args()

        logging_utils.configure_logging(logging_utils.get_config_from_args(args))

        if args.show_stats and args.pipeline == 'transformers-aipu':
            args.show_cpu_usage = True
            args.show_temp = True
        elif args.pipeline == 'transformers':
            # temperature monitoring is not supported for non-AIPU pipelines
            args.show_temp = False
        requested = []
        if args.show_cpu_usage:
            requested.append('cpu_usage')
        if args.show_temp:
            requested.append('core_temp')
        tracers = inf_tracers.create_tracers(*requested)

        for tracer in tracers:
            tracer.start_monitoring()

        try:
            _main(args, tracers)
        finally:
            for tracer in tracers:
                try:
                    tracer.stop_monitoring()
                except Exception as e:
                    LOG.debug(f"Error stopping tracer: {e}")

    except Exception as e:
        import traceback

        LOG.error("An error occurred during inference:")
        traceback.print_exc()
        LOG.error("\n[ERROR] An exception occurred during inference. See above for details.")
        raise


def run_chat_loop(
    display_fn: Callable[[str, Iterator[Tuple[str, dict]], bool, list], str],
    show_stats: bool,
    history: list,
    chat_encoder,
    model_instance,
    tokenizer,
    max_tokens,
    temperature,
    eos_token_id,
    end_token_id,
    LOG,
    keep_history=True,
    tracers=None,
):
    while True:
        try:
            user_input = display_fn(None, None, True, history)  # Prompt for user input
        except (EOFError, KeyboardInterrupt):
            display_fn("Goodbye!", None, False, history)
            break

        # Check for the special clear history command
        if user_input == "!CLEAR_HISTORY!":
            history.clear()
            chat_encoder.reset()
            LOG.info("Chat history cleared.")
            print("\nHistory cleared. Type 'exit' or 'quit' to exit.\n")
            continue

        if user_input is None or user_input.strip().lower() in {"exit", "quit"}:
            display_fn("Goodbye!", None, False, history)
            break

        stats = GenerationStats()
        stats.start_tokenization()
        input_ids, embedding_features = chat_encoder.encode(user_input, history)
        stats.end_tokenization()
        stats.start_generation()
        response_stream = stream_response(
            model_instance,
            chat_encoder,
            tokenizer,
            input_ids,
            embedding_features,
            max_tokens,
            temperature,
            eos_token_id,
            end_token_id,
            stats,
        )
        response = display_fn(user_input, response_stream, False, history)
        stats.end_generation()

        if tracers and show_stats:
            stats.update_system_metrics(tracers)

        history.append((user_input, response))

        if not keep_history:
            LOG.debug("--no-history flag is set, clearing conversation history after response")
            history.clear()
            # Reset history but preserve system prompt to avoid unnecessary reprocessing
            chat_encoder.reset(preserve_system_prompt=True)

        if show_stats:
            stats.summary(log=True)


def entrypoint_main() -> int:
    """Setuptools entry point."""
    try:
        main()
        return 0
    except Exception as e:
        print(f'ERROR: {e}', file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(entrypoint_main())
