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

## Install on a device

Two paths. Do **not** copy MagiskHluda's `hluda` here: that wrapper reads the module's `module.cfg`. Florida's port lives in `identities.json`.

### Magisk / KernelSU / APatch

Install [MagiskHluda](https://github.com/cergo666/MagiskHluda). The server starts on boot; the port is in `module.cfg`. From the host:

```bash
hluda ps
hluda -f com.example.app
```

`hluda` lives in the MagiskHluda repo: `scripts/hluda`.

### Manual (this repo)

1. From [Releases](https://github.com/cergo666/Florida/releases) grab `florida-server-*-android-<arch>.gz` and the matching `florida-identities-<version>.json`.
2. Decompress the server and install with the helper — it pushes the binary, `chmod`s it, and prints commands using the port from the JSON:

```bash
gunzip -k florida-server-*-android-arm64.gz
python3 install.py \
  --server florida-server-*-android-arm64 \
  --identities florida-identities-*.json
```

3. Run what the script printed: start on device, then `adb forward`. The binary is stored as `/data/local/tmp/app_process` (not `frida-server` — that name is itself a detection string).

Without the helper, the same steps by hand — see [Connect](#connect).

## Scripts

Everything for the **build** is under `scripts/`. For **device install** use root [`install.py`](install.py).

| Script | Purpose |
|---|---|
| [`install.py`](install.py) | **Install** on a phone or emulator: `adb push` + chmod, then print `adb forward` / `frida-ps -H` using the identities port |
| [`identities.py`](scripts/identities.py) | Generate `identities.json` (names, port, RPC XOR) |
| [`rewrite.py`](scripts/rewrite.py) | Apply identities to a Frida checkout. `--check` verifies anchors without writing |
| [`strip-fingerprints.py`](scripts/strip-fingerprints.py) | Same-length ELF replace for `gmain` / `gdbus`. CI hooks it from `post-process.py`; rarely run by hand |
| [`scan_binary.py`](scripts/scan_binary.py) | Fail if the binary still contains `gum-js-loop`, `27042`, `frida:rpc`, etc. |

`rewrite.py` must be pointed at a **working copy**. Do not run it against a Frida tree you want to keep pristine.

## Connect

The server listens on `control_port` from identities, **not** `27042`. After `install.py` (or a manual push):

```bash
adb shell su -c '/data/local/tmp/app_process -l 127.0.0.1:<control_port>'
adb forward tcp:<control_port> tcp:<control_port>
frida-ps -H 127.0.0.1:<control_port>
frida -H 127.0.0.1:<control_port> -f com.example.app
```

Fully manual, no helper:

```bash
adb push florida-server /data/local/tmp/app_process
adb shell su -c 'chmod 755 /data/local/tmp/app_process'
adb shell su -c '/data/local/tmp/app_process'
```

To keep stock `frida -U` (it always opens `tcp:27042` on the device):

```bash
adb shell su -c '/data/local/tmp/app_process -l 127.0.0.1:27042'
```

Apps that only probe `27042` will miss the custom port. Apps that scan every localhost port still see the Frida handshake — that is not solvable without changing the protocol (and the client).

## How this fork differs from [Ylarod/Florida](https://github.com/Ylarod/Florida)

Same wire protocol: stock `frida` CLI still works. D-Bus `re.frida.*` and GObject names such as `frida_agent_message_transmitter_*` are **not** renamed (the official client needs them). Inline hooks and `.text` vs disk checks are still visible.

| | [Ylarod/Florida](https://github.com/Ylarod/Florida) | This fork |
|---|---|---|
| How Frida is patched | `git am` of numbered `.patch` files | `scripts/rewrite.py` — counted-anchor edits |
| Thread / memfd / agent names | fixed (`ggbond`, `jit-cache`, export `main`, …) | **new random set every CI build** (`identities.py`) |
| Listen port | classic **27042** | per-build `control_port` (not 27042) in `florida-identities-*.json` |
| Bind address | typically all interfaces | **127.0.0.1** by default (MagiskHluda) |
| `frida:rpc` in the binary | double-Base64 — a known blob | XOR at runtime; on the wire still `frida:rpc` |
| ELF string stripping | `sed` / mostly the agent `.so` | source rewrites + same-length `gmain`/`gdbus`; server, gadget, inject |
| Upstream Frida bumps | patches often fail to apply | anchors checked (`rewrite.py --check`); CI fails loudly on drift |
| Release assets | `florida-server-*` | same + **`florida-identities-<version>.json`** |
| Build checks | no fingerprint scan | unittest + `scan_binary.py` (no `gum-js-loop`, `27042`, `frida:rpc`, …) |
| Onto a device | manual `adb push` | [`install.py`](install.py); on boot — [this MagiskHluda](https://github.com/cergo666/MagiskHluda) + `hluda` |
| Magisk module | [Exo1i/MagiskHluda](https://github.com/Exo1i/MagiskHluda): `0.0.0.0:27042`, no identities | [cergo666/MagiskHluda](https://github.com/cergo666/MagiskHluda): port from JSON, **127.0.0.1**, `hluda` wrapper (table there) |
| Docs | short README | RU + EN, install paths and a scripts table |

## Build

Needs a Frida checkout with `frida-core` and `frida-gum` submodules.

```bash
python3 scripts/identities.py -o identities.json
python3 scripts/rewrite.py --frida-dir /path/to/frida --identities identities.json

# verify anchors against a clean tree (does not modify it)
python3 scripts/rewrite.py --frida-dir /path/to/frida --check --seed ci
```

Then configure/build Frida as usual (`./configure --host=android-arm64 && make`).

Onto a device from a local build:

```bash
python3 install.py \
  --server build-android-arm64/subprojects/frida-core/server/frida-server \
  --identities identities.json
```

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
