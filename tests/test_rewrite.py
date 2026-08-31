#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from identities import generate  # noqa: E402
from rewrite import edits_for  # noqa: E402
from scan_binary import find_classic, load_bytes  # noqa: E402


class RewriteUnitTest(unittest.TestCase):
    def test_edits_have_unique_old_strings_per_file(self) -> None:
        ident = generate("edits")
        seen: set[tuple[str, str]] = set()
        for edit in edits_for(ident):
            key = (edit.rel, edit.old)
            self.assertNotIn(key, seen, f"duplicate edit {key}")
            seen.add(key)
            self.assertGreater(edit.count, 0)
            self.assertNotEqual(edit.old, edit.new)
            self.assertNotIn("ggbond", edit.new)
            self.assertNotIn("jit-cache", edit.new)
            self.assertNotIn('"main"', edit.new)

    def test_port_edit_drops_27042(self) -> None:
        ident = generate("edits")
        port_edits = [e for e in edits_for(ident) if "DEFAULT_CONTROL_PORT" in e.old]
        self.assertEqual(len(port_edits), 1)
        self.assertIn("27042", port_edits[0].old)
        self.assertNotIn("27042", port_edits[0].new)
        self.assertIn(str(ident["control_port"]), port_edits[0].new)


class ScanBinaryTest(unittest.TestCase):
    def test_finds_classic_strings(self) -> None:
        blob = b"aaa\0gum-js-loop\0bbb\0frida_agent_main\0cccfrida:rpcddd"
        hits = find_classic(blob)
        self.assertIn("gum-js-loop", hits)
        self.assertIn("frida_agent_main", hits)
        self.assertIn("frida:rpc", hits)

    def test_clean_blob_is_ok(self) -> None:
        self.assertEqual(find_classic(b"hello\0world\0"), [])

    def test_load_gz(self) -> None:
        import gzip

        raw = b"not a fingerprint"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.gz"
            path.write_bytes(gzip.compress(raw))
            self.assertEqual(load_bytes(path), raw)


@unittest.skipUnless(
    os.environ.get("FLORIDA_FRIDA_DIR")
    or (ROOT.parent / "frida" / "subprojects" / "frida-core" / "lib" / "base" / "rpc.vala").is_file(),
    "frida checkout not available",
)
class RewriteAnchorTest(unittest.TestCase):
    def test_anchors_match_upstream(self) -> None:
        from rewrite import run

        frida = Path(os.environ.get("FLORIDA_FRIDA_DIR", ROOT.parent / "frida"))
        ident = generate("anchor-check")
        run(frida, ident, ROOT / "scripts", check_only=True)


if __name__ == "__main__":
    unittest.main()
