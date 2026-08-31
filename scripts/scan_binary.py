#!/usr/bin/env python3
"""Fail the build if a Florida binary still contains classic Frida fingerprints."""

from __future__ import annotations

import argparse
import gzip
import sys
from pathlib import Path

# Exact C-strings / ASCII sequences that public detectors look for.
CLASSIC = [
    b"gum-js-loop\0",
    b"frida_agent_main\0",
    b"ggbond",
    b"frida:rpc",
    b"frida-agent-64.so\0",
    b"frida-agent-32.so\0",
    b"frida-agent-arm.so\0",
    b"frida-agent-arm64.so\0",
    b"libfrida-agent-raw.so\0",
    b"pool-frida",
]


def load_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    if path.suffix == ".gz" or data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    return data


def find_classic(data: bytes) -> list[str]:
    hits: list[str] = []
    # Thread name gmain/gdbus only as standalone C strings.
    if b"\0gmain\0" in data:
        hits.append("gmain")
    if b"\0gdbus\0" in data:
        hits.append("gdbus")
    if b"27042" in data:
        hits.append("27042")
    for needle in CLASSIC:
        if needle in data:
            label = needle.replace(b"\0", b"").decode("ascii", "replace")
            hits.append(label)
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("binaries", nargs="+", type=Path)
    args = parser.parse_args(argv)

    failed = False
    for path in args.binaries:
        if not path.is_file():
            failed = True
            print(f"FAIL missing {path}", file=sys.stderr)
            continue
        data = load_bytes(path)
        hits = find_classic(data)
        if hits:
            failed = True
            print(f"FAIL {path}: {', '.join(hits)}", file=sys.stderr)
        else:
            print(f"ok {path} ({len(data)} bytes)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
