#!/usr/bin/env python
# Copyright Axelera AI, 2025
# Extract embeddings and/or download/zip tokenizer for a HuggingFace model

import argparse
import os
import shutil
import sys
from typing import Optional
import zipfile

import numpy as np
from transformers import AutoModelForCausalLM, AutoTokenizer


def dump_model_embeddings(
    model_name: str, output_path: str, hf_token: Optional[str] = None
) -> dict:
    """
    Dump model embeddings to file in FP16 format.
    Returns metadata dict.
    """
    print(f"[INFO] Loading model {model_name} to extract embeddings...")
    model = AutoModelForCausalLM.from_pretrained(model_name, token=hf_token)
    embedding_matrix = model.get_input_embeddings().weight.detach().half().cpu().numpy()
    metadata = {
        "vocab_size": embedding_matrix.shape[0],
        "embedding_dim": embedding_matrix.shape[1],
        "dtype": "float16",
    }
    np.savez_compressed(output_path, embeddings=embedding_matrix, **metadata)
    print(
        f"[INFO] Saved embeddings to {output_path} (shape: {embedding_matrix.shape}, dtype: {embedding_matrix.dtype})"
    )
    return metadata


def download_and_zip_tokenizer(
    model_name: str, output_zip: str, hf_token: Optional[str] = None
) -> bool:
    """
    Download tokenizer files for a model and zip them for local use.
    Returns True if successful, False otherwise.
    """
    local_dir = f"{model_name.replace('/', '_')}_tokenizer"
    if os.path.exists(local_dir):
        shutil.rmtree(local_dir)
    os.makedirs(local_dir, exist_ok=True)
    print(f"[INFO] Downloading tokenizer for {model_name} ...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            model_name, use_fast=True, padding_side="right", token=hf_token
        )
    except Exception as e:
        err_msg = str(e)
        if (
            'gated repo' in err_msg.lower()
            or '401' in err_msg
            or 'access to model' in err_msg.lower()
            or 'unauthorized' in err_msg.lower()
        ):
            if hf_token is not None:
                print("[INFO] Retrying with provided HuggingFace token...")
                try:
                    tokenizer = AutoTokenizer.from_pretrained(
                        model_name, use_fast=True, padding_side="right", token=hf_token
                    )
                except Exception as e2:
                    print(
                        f"[ERROR] Failed to download tokenizer for '{model_name}' even with token.\n{e2}"
                    )
                    return False
            else:
                print(
                    f"""
[ERROR] The tokenizer for '{model_name}' is in a gated (restricted) HuggingFace repository.
This script needs to download the tokenizer files from HuggingFace. Please provide a HuggingFace token using --hf_token or set the HF_TOKEN environment variable.
You can get a token at: https://huggingface.co/settings/tokens
"""
                )
                return False
        else:
            raise
    tokenizer.save_pretrained(local_dir)
    print(f"[INFO] Tokenizer files saved to {local_dir}")
    print(f"[INFO] Zipping tokenizer files to {output_zip} ...")
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(local_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, local_dir)
                zipf.write(file_path, arcname)
    print(f"[INFO] Done! Zipped tokenizer at {output_zip}")
    return True


def get_token_from_args_or_env(hf_token_arg: Optional[str]) -> Optional[str]:
    """Return the HuggingFace token from argument or environment, or None."""
    return hf_token_arg or os.environ.get("HF_TOKEN")


def get_safe_name(model_name: str) -> str:
    """Return a filesystem-safe version of the model name."""
    return model_name.replace("/", "_")


def main():
    parser = argparse.ArgumentParser(
        description="Extract embeddings and/or download/zip tokenizer for a HuggingFace model."
    )
    parser.add_argument(
        "model_name", help="HuggingFace model name (e.g. meta-llama/Llama-3-2-1B-Instruct)"
    )
    parser.add_argument("--embeddings-out", default=None, help="Output .npz file for embeddings")
    parser.add_argument("--tokenizer-zip", default=None, help="Output zip file for tokenizer")
    parser.add_argument(
        "--hf-token", default=None, help="HuggingFace token (or set HF_TOKEN env var)"
    )
    parser.add_argument(
        "--only-embeddings", action="store_true", help="Only extract and save embeddings"
    )
    parser.add_argument(
        "--only-tokenizer", action="store_true", help="Only download and zip tokenizer"
    )
    args = parser.parse_args()

    safe_name = get_safe_name(args.model_name)
    embeddings_out = args.embeddings_out or f"{safe_name}_embeddings.npz"
    tokenizer_zip = args.tokenizer_zip or f"{safe_name}_tokenizer.zip"
    token_to_use = get_token_from_args_or_env(args.hf_token)

    if token_to_use:
        print("[INFO] Using HuggingFace token from argument or environment.")
    else:
        print(
            "[INFO] No HuggingFace token provided; will attempt public access or rely on huggingface-cli login."
        )

    did_embeddings = did_tokenizer = False
    if args.only_embeddings and args.only_tokenizer:
        print("[WARNING] Both --only-embeddings and --only-tokenizer set. Doing both.")
        did_embeddings = (
            True
            if dump_model_embeddings(args.model_name, embeddings_out, hf_token=token_to_use)
            else False
        )
        did_tokenizer = download_and_zip_tokenizer(
            args.model_name, tokenizer_zip, hf_token=token_to_use
        )
    elif args.only_embeddings:
        did_embeddings = (
            True
            if dump_model_embeddings(args.model_name, embeddings_out, hf_token=token_to_use)
            else False
        )
    elif args.only_tokenizer:
        did_tokenizer = download_and_zip_tokenizer(
            args.model_name, tokenizer_zip, hf_token=token_to_use
        )
    else:
        # Default: do both
        did_embeddings = (
            True
            if dump_model_embeddings(args.model_name, embeddings_out, hf_token=token_to_use)
            else False
        )
        did_tokenizer = download_and_zip_tokenizer(
            args.model_name, tokenizer_zip, hf_token=token_to_use
        )

    print("\n[SUMMARY]")
    if did_embeddings:
        print(f"  Embeddings file: {embeddings_out}")
    if did_tokenizer:
        print(f"  Tokenizer zip:   {tokenizer_zip}")
    if not (did_embeddings or did_tokenizer):
        print("  No files produced due to errors or user options.")


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
