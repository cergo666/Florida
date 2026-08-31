# Patches directory (legacy)

Florida no longer ships `git am` hunks. They broke on every Frida bump and
baked in public fingerprints (`ggbond`, `jit-cache`, `main`, double-Base64
`frida:rpc`).

Source rewrites live in `scripts/rewrite.py`. Per-build names/ports live in
`scripts/identities.py`. GLib `gmain`/`gdbus` strings are rewritten in the
final ELF by `scripts/strip-fingerprints.py` (hooked from Frida's
`post-process.py`).
