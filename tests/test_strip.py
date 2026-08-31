#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import importlib.util

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from identities import generate  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "strip_fingerprints", ROOT / "scripts" / "strip-fingerprints.py"
)
_strip = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_strip)
patch_file = _strip.patch_file
replacements_from_identities = _strip.replacements_from_identities


class StripTest(unittest.TestCase):
    def test_replacements_are_same_length(self) -> None:
        ident = generate("strip")
        for old, new in replacements_from_identities(ident):
            self.assertEqual(len(old), len(new))
            self.assertTrue(old.endswith(b"\0"))
            self.assertTrue(new.endswith(b"\0"))

    def test_patch_file_rewrites_cstrings(self) -> None:
        ident = generate("strip")
        reps = replacements_from_identities(ident)
        blob = (
            b"xxxx\0gmain\0yyyy\0gdbus\0zzzz\0gum-js-loop\0"
            b"frida-agent-64.so\0end"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bin"
            path.write_bytes(blob)
            hits = patch_file(path, reps)
            self.assertGreater(hits, 0)
            data = path.read_bytes()
            self.assertNotIn(b"\0gmain\0", data)
            self.assertNotIn(b"\0gdbus\0", data)
            self.assertNotIn(b"gum-js-loop\0", data)
            self.assertNotIn(b"frida-agent-64.so\0", data)
            self.assertIn(ident["gmain"].encode() + b"\0", data)
            self.assertIn(ident["js_loop"].encode() + b"\0", data)


if __name__ == "__main__":
    unittest.main()
