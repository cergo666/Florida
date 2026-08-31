# Florida

Patched Frida for Android that drops the well-known on-device fingerprints
(`gum-js-loop`, `frida-agent-*.so`, `frida_agent_main`, default port 27042,
`ggbond`, `/memfd:jit-cache`, …).

Each CI run generates a **new** set of names and a **new** listen port. The
values are in `florida-identities-<version>.json` next to the release assets.

## What changed vs classic Florida patches

| Old patch | Now |
|---|---|
| `ggbond` / `jit-cache` / export `main` | random per build |
| double-Base64 of `frida:rpc` (known blob) | XOR at runtime; wire protocol still `frida:rpc` so stock `frida` CLI works |
| `sed` on the ELF | source rewrites + same-length `gmain`/`gdbus` replace in `post-process.py` |
| `git am` hunks that break on every bump | `scripts/rewrite.py` with counted anchors |
| strip only the agent `.so` | same strip on server, gadget, inject |
| default TCP **27042** | per-build port (see identities JSON) |

Intentionally **not** renamed: D-Bus API names `re.frida.*` (the official
desktop client needs them). GObject type names such as
`frida_agent_message_transmitter_*` also stay; they are not the strings
public detectors scan for (`gum-js-loop`, `frida-agent-*.so`, port 27042).

Source rewrites cannot hide inline hooks or `.text` vs disk checks. That is
instrumentation, not a string.

## Download

Release assets are named `florida-server-*` / `florida-gadget-*` / `florida-inject-*`.

## Connect

The server no longer listens on 27042. Use the port from `florida-identities-*.json`:

```bash
adb push florida-server /data/local/tmp/app_process
adb shell su -c 'chmod 755 /data/local/tmp/app_process'
adb shell su -c '/data/local/tmp/app_process'   # listens on 127.0.0.1:<control_port>
adb forward tcp:<control_port> tcp:<control_port>
frida-ps -H 127.0.0.1:<control_port>
```

To keep stock `frida -U` (it always opens `tcp:27042` on the device):

```bash
adb shell su -c '/data/local/tmp/app_process -l 127.0.0.1:27042'
```

Apps that only probe 27042 will miss the custom port. Apps that scan every
localhost port still see the Frida handshake — that is not solvable without
changing the protocol (and the client).

Rename the binary on the device. `frida-server` in `/data/local/tmp` is itself
a detection string.

## Build

Needs a Frida checkout with `frida-core` and `frida-gum` submodules.

```bash
python3 scripts/identities.py -o identities.json
python3 scripts/rewrite.py --frida-dir /path/to/frida --identities identities.json

# verify anchors against a clean tree (does not modify it)
python3 scripts/rewrite.py --frida-dir /path/to/frida --check --seed ci
```

Unit tests (stdlib `unittest`, no extra deps):

```bash
python3 -m unittest discover -s tests -v
```

CI runs those tests, then `rewrite.py --check` against a fresh Frida clone, then
`scripts/scan_binary.py` on the built `frida-server` / gadget / inject.

Then configure/build Frida as usual (`./configure --host=android-arm64 && make`).

`scripts/rewrite.py` must be pointed at a **working copy**. Do not run it
against a Frida tree you want to keep pristine.

## References

- https://github.com/frida/frida
- https://github.com/darvincisec/DetectFrida
- https://github.com/qtfreet00/AntiFrida
- https://github.com/Ylarod/Florida
