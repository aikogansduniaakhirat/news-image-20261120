"""Validate and ship the repository's PNG artwork."""

import os
from pathlib import Path
import stat
import struct
import sys

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_SIDE = 1024
MAX_BYTES = 1024 * 1024


def png_dimensions(data: bytes) -> tuple[int, int]:
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("invalid PNG signature")
    if len(data) < 33 or data[8:16] != b"\x00\x00\x00\x0dIHDR":
        raise ValueError("missing or malformed PNG IHDR chunk")
    return struct.unpack_from(">II", data, 16)


def validate(source: Path) -> tuple[bytes, int, int]:
    info = source.stat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"source is not a regular file: {source}")
    if info.st_size > MAX_BYTES:
        raise ValueError(f"PNG size is {info.st_size} bytes (limit: {MAX_BYTES})")
    # Bound the read even if the file changes after stat().
    with source.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError(f"PNG size is at least {len(data)} bytes (limit: {MAX_BYTES})")
    width, height = png_dimensions(data)
    if not (1 <= width <= MAX_SIDE and 1 <= height <= MAX_SIDE):
        raise ValueError(f"PNG dimensions are {width}x{height} (allowed: 1–{MAX_SIDE} pixels per side)")
    return data, width, height


def copy_and_verify(source: Path, destination: Path, data: bytes) -> None:
    if destination.exists():
        if destination.is_dir():
            raise ValueError(f"destination is a directory: {destination}")
        if destination.samefile(source):
            raise ValueError(f"destination is the source file: {destination}")
    destination.write_bytes(data)
    written = destination.read_bytes()
    if written != data:
        raise ValueError(f"copied bytes do not match the source: {destination}")


def main() -> int:
    source = Path(__file__).resolve().parent / "art" / "entry.png"
    try:
        output_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        destination = output_dir / "entry.png"
        data, width, height = validate(source)
        copy_and_verify(source, destination, data)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"{source} | {len(data)} bytes | {width}x{height} | {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
