#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from identities import generate, dumps_c_bytes  # noqa: E402


class IdentitiesTest(unittest.TestCase):
    def test_seed_is_stable(self) -> None:
        a = generate("ci-test")
        b = generate("ci-test")
        self.assertEqual(a, b)

    def test_different_seeds_differ(self) -> None:
        a = generate("a")
        b = generate("b")
        self.assertNotEqual(a["prgname"], b["prgname"])
        self.assertNotEqual(a["control_port"], b["control_port"])

    def test_rpc_xor_roundtrip(self) -> None:
        ident = generate("xor")
        key = ident["rpc_xor_key"]
        decoded = bytes(b ^ key for b in ident["rpc_xor_bytes"])
        self.assertEqual(decoded, b"frida:rpc")
        # Encoded blob must not contain the plaintext.
        blob = bytes(ident["rpc_xor_bytes"])
        self.assertNotIn(b"frida:rpc", blob)

    def test_dumps_c_bytes(self) -> None:
        self.assertEqual(dumps_c_bytes([1, 255]), "0x01, 0xff")

    def test_fixed_lengths(self) -> None:
        ident = generate("len")
        self.assertEqual(len(ident["gmain"]), 5)
        self.assertEqual(len(ident["gdbus"]), 5)
        self.assertEqual(len(ident["js_loop"]), 11)
        self.assertTrue(ident["agent_symbol"].endswith("_init"))
        self.assertNotEqual(ident["control_port"], 27042)
        self.assertNotEqual(ident["cluster_port"], 27052)
        for old, new in ident["resource_repls"].items():
            self.assertEqual(len(old), len(new), old)
            self.assertTrue(new.endswith(".so"))

    def test_no_forbidden_tokens(self) -> None:
        ident = generate("forbid")
        names = [
            ident["prgname"],
            ident["agent_symbol"],
            ident["js_loop"],
            ident["gmain"],
            ident["gdbus"],
            ident["main_loop"],
            ident["server_loop"],
            ident["agent_container"],
            ident["agent_emulated"],
            ident["gadget_thread"],
            ident["android_helper_thread"],
            ident["tmp_prefix"],
            ident["default_dir"],
            ident["agent_prefix"],
            ident["helper_prefix"],
            ident["memfd_name"],
        ]
        blob = " ".join(names).lower()
        self.assertNotIn("frida", blob)
        self.assertNotIn("ggbond", blob)
        self.assertNotIn("florida", blob)
        self.assertNotIn("jit-cache", blob)
        self.assertNotIn("gum-js-loop", blob)
        for word in ("gmain", "gdbus"):
            self.assertNotIn(word, names)

    def test_ports_in_range(self) -> None:
        for i in range(20):
            ident = generate(str(i))
            self.assertGreaterEqual(ident["control_port"], 37111)
            self.assertLessEqual(ident["control_port"], 48991)


if __name__ == "__main__":
    unittest.main()
