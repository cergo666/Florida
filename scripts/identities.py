#!/usr/bin/env python3
"""Per-build Florida identities. Nothing here is a fixed public fingerprint."""

from __future__ import annotations

import argparse
import json
import random
import string
import sys
from pathlib import Path

FORBIDDEN = {
    "frida",
    "gum",
    "gmain",
    "gdbus",
    "florida",
    "ggbond",
    "agent",
    "gadget",
    "linjector",
    "rpc",
}

SKIP_PORTS = {27042, 27047, 27052, 27043, 5037, 8080, 8000, 8443, 31337, 4444}


def _letters(rng: random.Random, n: int) -> str:
    alphabet = string.ascii_lowercase
    while True:
        s = rng.choice(alphabet) + "".join(rng.choice(alphabet) for _ in range(n - 1))
        if s not in FORBIDDEN and "frida" not in s and "gum" not in s:
            return s


def generate(seed: str | None = None) -> dict:
    rng = random.Random(seed)
    rpc = b"frida:rpc"
    xor_key = rng.randint(0x21, 0xFE)
    xor_bytes = [b ^ xor_key for b in rpc]

    control_port = rng.randint(37111, 48991)
    while control_port in SKIP_PORTS:
        control_port = rng.randint(37111, 48991)

    ident = {
        "seed": seed,
        "prgname": _letters(rng, 7),
        "agent_symbol": _letters(rng, 8) + "_init",
        "js_loop": _letters(rng, 11),
        "gmain": _letters(rng, 5),
        "gdbus": _letters(rng, 5),
        "main_loop": _letters(rng, 12),
        "server_loop": _letters(rng, 14),
        "agent_container": _letters(rng, 14),
        "agent_emulated": _letters(rng, 14),
        "gadget_thread": _letters(rng, 10),
        "android_helper_thread": _letters(rng, 12),
        "tmp_prefix": _letters(rng, 5) + "-",
        "default_dir": "re." + _letters(rng, 6) + ".d",
        "control_port": control_port,
        "cluster_port": control_port + 17,
        "agent_prefix": _letters(rng, 8),
        "helper_prefix": _letters(rng, 8),
        "memfd_name": _letters(rng, 8),
        "rpc_xor_key": xor_key,
        "rpc_xor_bytes": xor_bytes,
        "resource_repls": {
            old: _same_len_filename(rng, old)
            for old in (
                "frida-agent-64.so",
                "frida-agent-32.so",
                "frida-agent-arm.so",
                "frida-agent-arm64.so",
                "frida-agent.so",
                "libfrida-agent-raw.so",
            )
        },
    }
    return ident


def _same_len_filename(rng: random.Random, old: str) -> str:
    if old.endswith(".so"):
        stem = old[:-3]
        return _letters(rng, len(stem)) + ".so"
    return _letters(rng, len(old))


def dumps_c_bytes(values: list[int]) -> str:
    return ", ".join(f"0x{v:02x}" for v in values)


def save(ident: dict, path: Path) -> None:
    path.write_text(json.dumps(ident, indent=2) + "\n", encoding="utf-8")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate per-build Florida identities")
    parser.add_argument("--seed", help="Deterministic seed (e.g. GitHub run id)")
    parser.add_argument("-o", "--output", type=Path, default=Path("identities.json"))
    args = parser.parse_args(argv)

    ident = generate(args.seed)
    save(ident, args.output)
    print(f"wrote {args.output}")
    print(f"  control_port = {ident['control_port']}")
    print(f"  agent_symbol = {ident['agent_symbol']}")
    print(f"  prgname      = {ident['prgname']}")
    print(f"  agent_prefix = {ident['agent_prefix']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
