#!/usr/bin/env python3
"""Install Florida onto a device and print connect instructions."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Install Florida onto a phone or emulator: adb push the server, "
            "chmod it, and print start / adb forward / frida -H commands using "
            "control_port from identities.json."
        )
    )
    parser.add_argument("--identities", type=Path, default=Path("identities.json"))
    parser.add_argument("--server", type=Path, required=True, help="Path to florida-server / frida-server")
    parser.add_argument("--remote", default="/data/local/tmp/app_process")
    parser.add_argument("--adb", default="adb")
    args = parser.parse_args(argv)

    ident = json.loads(args.identities.read_text(encoding="utf-8"))
    port = ident["control_port"]
    remote_name = args.remote

    run([args.adb, "push", str(args.server), remote_name])
    run([args.adb, "shell", "su", "-c", f"chmod 755 {remote_name}"])
    print()
    print("Start on the device (root):")
    print(f"  adb shell su -c '{remote_name} -l 127.0.0.1:{port}'")
    print()
    print("Stock frida CLI talks to tcp:27042 on the device. Forward the custom port:")
    print(f"  adb forward tcp:{port} tcp:{port}")
    print(f"  frida-ps -H 127.0.0.1:{port}")
    print()
    print("To keep `frida -U` (USB / tcp:27042) working, start instead with:")
    print(f"  adb shell su -c '{remote_name} -l 127.0.0.1:27042'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
