#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "faster-whisper",
#     "openai-whisper",
#     "rich",
#     "torch",
# ]
#
# [tool.uv]
# extra-index-url = ["https://download.pytorch.org/whl/cu128"]
# ///
"""Transcribe audio/video files using faster-whisper with GPU acceleration."""

import argparse
import ast
import time

from dataclasses import asdict
from pathlib import Path

import torch

from faster_whisper import WhisperModel
from rich.console import Console
from rich.text import Text
from whisper.utils import get_writer

OUTPUT_FORMATS = ["txt", "vtt", "srt", "tsv", "json", "all"]

console = Console()


def format_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def parse_set_value(value: str):
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return value


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transcribe audio/video files using faster-whisper on GPU.",
        epilog=(
            "Pass any faster-whisper transcribe option via --set key=value. "
            "e.g. --set beam_size=8 --set vad_filter=False"
        ),
    )
    parser.add_argument(
        "files", nargs="+", type=Path, help="audio/video files to transcribe"
    )
    parser.add_argument("--model", default="turbo", help="model name (default: turbo)")
    parser.add_argument(
        "--output-format",
        default="txt",
        choices=OUTPUT_FORMATS,
        help="output format (default: txt)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="output directory (default: same as input)",
    )
    parser.add_argument(
        "--language", default=None, help="language code (auto-detect if omitted)"
    )
    parser.add_argument(
        "--set",
        action="append",
        metavar="KEY=VALUE",
        dest="overrides",
        help="pass options to model.transcribe() (repeatable)",
    )
    args = parser.parse_args()

    transcribe_kwargs: dict = {"vad_filter": True}
    if args.language:
        transcribe_kwargs["language"] = args.language
    for override in args.overrides or []:
        if "=" not in override:
            parser.error(f"--set requires KEY=VALUE format, got: {override}")
        key, value = override.split("=", 1)
        transcribe_kwargs[key] = parse_set_value(value)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    device_label = (
        f"[bold green]{device}[/]" if device == "cuda" else f"[bold yellow]{device}[/]"
    )

    console.print()
    console.print(f"  Device  {device_label}")
    console.print(f"  Model   [bold green]{args.model}[/]")
    console.print()

    with console.status("[dim]Loading model...[/]"):
        model = WhisperModel(args.model, device=device, compute_type=compute_type)

    for file_path in args.files:
        if not file_path.exists():
            console.print(f"[bold red]File not found:[/] {file_path}", highlight=False)
            continue

        console.rule(f"[bold]{file_path.name}[/]")
        start = time.time()

        segments, info = model.transcribe(str(file_path), **transcribe_kwargs)
        console.print(
            f"  [dim]Language:[/] {info.language} "
            f"[dim]({info.language_probability:.0%})[/]  "
            f"[dim]Duration:[/] {format_time(info.duration)}"
        )
        console.print()

        segment_list = []
        for segment in segments:
            ts = Text(f"  {format_time(segment.start):>7} ", style="dim cyan")
            ts.append(segment.text.strip(), style="")
            console.print(ts)
            segment_list.append(segment)

        elapsed = time.time() - start
        speed = info.duration / elapsed if elapsed > 0 else 0

        console.print()
        console.print(
            f"  [dim]Transcribed in[/] [bold]{elapsed:.1f}s[/] "
            f"[dim]({speed:.0f}x realtime)[/]"
        )

        out_dir = str(args.output_dir or file_path.parent)
        result = {"segments": [asdict(s) for s in segment_list]}
        writer = get_writer(args.output_format, out_dir)
        writer(result, str(file_path))

        out_name = f"{file_path.stem}.{args.output_format}"
        if args.output_format == "all":
            out_name = f"{file_path.stem}.*"
        console.print(f"  [dim]Saved:[/] [bold]{Path(out_dir) / out_name}[/]")
        console.print()


if __name__ == "__main__":
    main()
