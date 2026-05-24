#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from huggingface_hub import snapshot_download


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download a Hugging Face model into a plain local directory."
    )
    parser.add_argument(
        "--model_id",
        default="facebook/seamless-m4t-v2-large",
        help="Hugging Face model id, e.g. facebook/seamless-m4t-v2-large",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("models/seamless-m4t-v2-large"),
        help="Destination directory that can be copied to the GPU server.",
    )
    parser.add_argument(
        "--revision",
        default=None,
        help="Optional Hugging Face revision, branch, tag, or commit hash.",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Optional Hugging Face token. If omitted, the local HF login is used.",
    )
    return parser.parse_args()


def _patch_max_new_tokens(model_dir: Path, *, value: int) -> None:
    """HF ships max_new_tokens=256 (~9s speech). Patch on-disk configs for local loads."""
    import json
    import re

    config_path = model_dir / "config.json"
    if config_path.is_file():
        data = json.loads(config_path.read_text(encoding="utf-8"))
        if data.get("max_new_tokens") != value:
            data["max_new_tokens"] = value
            config_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            logging.info("Set max_new_tokens=%s in %s", value, config_path)

    gen_path = model_dir / "generation_config.json"
    if gen_path.is_file():
        text = gen_path.read_text(encoding="utf-8")
        patched, count = re.subn(
            r'"max_new_tokens":\s*\d+',
            f'"max_new_tokens": {value}',
            text,
            count=1,
        )
        if count and patched != text:
            gen_path.write_text(patched, encoding="utf-8")
            logging.info("Set max_new_tokens=%s in %s", value, gen_path)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    logging.info("Downloading %s to %s", args.model_id, output_dir)
    snapshot_download(
        repo_id=args.model_id,
        revision=args.revision,
        token=args.token,
        local_dir=output_dir,
    )
    _patch_max_new_tokens(output_dir, value=4096)
    logging.info("Model is ready in %s", output_dir)
    logging.info("Copy this directory to the GPU server, for example:")
    logging.info("rsync -av %s/ user@gpu-server:/opt/models/seamless-m4t-v2-large/", output_dir)


if __name__ == "__main__":
    main()
