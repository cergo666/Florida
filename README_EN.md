# Florida

<p align="center">
  <a href="https://github.com/cergo666/Florida/releases"><img src="https://img.shields.io/github/v/release/cergo666/Florida?style=flat-square&logo=github" alt="release"></a>
  <a href="https://github.com/cergo666/Florida/releases"><img src="https://img.shields.io/github/downloads/cergo666/Florida/total?style=flat-square&color=blue" alt="downloads"></a>
  <a href="https://github.com/cergo666/Florida/releases/latest"><img src="https://img.shields.io/github/downloads/cergo666/Florida/latest/total?style=flat-square&label=latest%20downloads" alt="latest downloads"></a>
  <a href="https://github.com/cergo666/Florida/stargazers"><img src="https://img.shields.io/github/stars/cergo666/Florida?style=flat-square" alt="stars"></a>
  <a href="https://github.com/cergo666/Florida/actions/workflows/build.yml"><img src="https://img.shields.io/github/actions/workflow/status/cergo666/Florida/build.yml?style=flat-square&label=CI" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/cergo666/Florida?style=flat-square" alt="license"></a>
</p>

<p align="center">
  <a href="README.md">Русский</a> · <b>English</b>
  &nbsp;·&nbsp;
  <a href="https://github.com/cergo666/MagiskHluda"><img src="https://img.shields.io/github/v/release/cergo666/MagiskHluda?style=flat-square&label=MagiskHluda" alt="MagiskHluda"></a>
</p>

Patched [Frida](https://github.com/frida/frida) for Android that drops the well-known on-device fingerprints (`gum-js-loop`, `frida-agent-*.so`, `frida_agent_main`, port `27042`, `ggbond`, `/memfd:jit-cache`, and others).

Each CI run generates a **new** set of names and a **new** listen port. Values live in `florida-identities-<version>.json` next to the release assets.

## Ecosystem

| Repo | Role |
|---|---|
| **Florida** (this one) | builds `florida-server` / gadget / inject |
| [MagiskHluda](https://github.com/cergo666/MagiskHluda) | Magisk / KernelSU / APatch module, start on boot |
| [Ylarod/Florida](https://github.com/Ylarod/Florida) | original fork |

## What changed vs classic Florida patches

| Old patch | Now |
|---|---|
| `ggbond` / `jit-cache` / export `main` | random per build |
| double-Base64 of `frida:rpc` (known blob) | XOR at runtime; wire protocol still `frida:rpc` so stock `frida` CLI works |
| `sed` on the ELF | source rewrites + same-length `gmain`/`gdbus` replace in `post-process.py` |
| `git am` hunks that break on every bump | `scripts/rewrite.py` with counted anchors |
| strip only the agent `.so` | same strip on server, gadget, inject |
| default TCP **27042** | per-build port (see identities JSON) |

Intentionally **not** renamed: D-Bus API names `re.frida.*` (the official desktop client needs them). GObject type names such as `frida_agent_message_transmitter_*` also stay; they are not the strings public detectors scan for (`gum-js-loop`, `frida-agent-*.so`, port `27042`).

## Download

Assets: [`florida-server-*`](https://github.com/cergo666/Florida/releases) / `florida-gadget-*` / `florida-inject-*` + `florida-identities-<version>.json`.

## Connect

The server no longer listens on `27042`. Use the port from `florida-identities-*.json`:

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

Apps that only probe `27042` will miss the custom port. Apps that scan every localhost port still see the Frida handshake — that is not solvable without changing the protocol (and the client).

Rename the binary on the device. `frida-server` in `/data/local/tmp` is itself a detection string.

For start-on-boot, use [MagiskHluda](https://github.com/cergo666/MagiskHluda).

## Build

Needs a Frida checkout with `frida-core` and `frida-gum` submodules.

```bash
python3 scripts/identities.py -o identities.json
python3 scripts/rewrite.py --frida-dir /path/to/frida --identities identities.json

# verify anchors against a clean tree (does not modify it)
python3 scripts/rewrite.py --frida-dir /path/to/frida --check --seed ci
```

Then configure/build Frida as usual (`./configure --host=android-arm64 && make`).

`scripts/rewrite.py` must be pointed at a **working copy**. Do not run it against a Frida tree you want to keep pristine.

## Tests

Stdlib `unittest` only, no extra deps:

```bash
python3 -m unittest discover -s tests -v
```

CI runs those tests, then `rewrite.py --check` against a fresh Frida clone, then `scripts/scan_binary.py` on the built `frida-server` / gadget / inject.

## Limits

Source rewrites cannot hide inline hooks or `.text` vs disk checks. That is instrumentation, not a string. If Florida is still detected, [ZygiskFrida](https://github.com/lico-n/ZygiskFrida) is an alternative.

## Links

- [Frida](https://github.com/frida/frida)
- [DetectFrida](https://github.com/darvincisec/DetectFrida)
- [AntiFrida](https://github.com/qtfreet00/AntiFrida)
- [Ylarod/Florida](https://github.com/Ylarod/Florida)
- [MagiskHluda](https://github.com/cergo666/MagiskHluda)

<p align="center">
  <a href="https://github.com/cergo666/Florida/graphs/contributors">
    <img src="https://contrib.rocks/image?repo=cergo666/Florida" alt="contributors">
  </a>
</p>
