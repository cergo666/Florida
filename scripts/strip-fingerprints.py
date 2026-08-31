#!/usr/bin/env python3
"""Same-length C-string replacements in ELF/Mach-O binaries.

Used for GLib thread names (gmain, gdbus) that live in the statically linked
copy of GLib and cannot be changed from Frida sources alone.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def replacements_from_identities(ident: dict) -> list[tuple[bytes, bytes]]:
    pairs = [
        ("gmain", ident["gmain"]),
        ("gdbus", ident["gdbus"]),
        ("gum-js-loop", ident["js_loop"]),
    ]
    pairs.extend(ident.get("resource_repls", {}).items())
    out: list[tuple[bytes, bytes]] = []
    for old, new in pairs:
        if len(old) != len(new):
            raise SystemExit(f"length mismatch: {old!r} -> {new!r}")
        out.append((old.encode("ascii") + b"\0", new.encode("ascii") + b"\0"))
    return out


def patch_file(path: Path, reps: list[tuple[bytes, bytes]]) -> int:
    data = path.read_bytes()
    hits = 0
    for old, new in reps:
        n = data.count(old)
        if n:
            data = data.replace(old, new)
            hits += n
    if hits:
        path.write_bytes(data)
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identities", type=Path, required=True)
    parser.add_argument("binaries", nargs="+", type=Path)
    args = parser.parse_args(argv)

    ident = json.loads(args.identities.read_text(encoding="utf-8"))
    reps = replacements_from_identities(ident)

    total = 0
    for binary in args.binaries:
        if not binary.is_file() or binary.stat().st_size == 0:
            print(f"[florida] skip empty {binary}")
            continue
        hits = patch_file(binary, reps)
        total += hits
        print(f"[florida] {binary.name}: {hits} fingerprint string(s) rewritten")
    return 0 if total >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
