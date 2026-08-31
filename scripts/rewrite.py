#!/usr/bin/env python3
"""Rewrite Frida sources with per-build identities.

Replaces git-am patches so upstream line-number drift does not silently
produce a known Florida fingerprint (ggbond, jit-cache, main, ...).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from identities import dumps_c_bytes, generate, load, save


@dataclass
class Edit:
    rel: str
    old: str
    new: str
    count: int


def fail(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def apply_edit(root: Path, edit: Edit, check_only: bool) -> None:
    path = root / edit.rel
    if not path.is_file():
        fail(f"missing {edit.rel}")
    text = path.read_text(encoding="utf-8")
    found = text.count(edit.old)
    if found != edit.count:
        fail(
            f"{edit.rel}: expected {edit.count} occurrence(s) of {edit.old!r}, "
            f"found {found}"
        )
    if check_only:
        return
    path.write_text(text.replace(edit.old, edit.new), encoding="utf-8")


def insert_after(root: Path, rel: str, anchor: str, insertion: str, check_only: bool) -> None:
    path = root / rel
    if not path.is_file():
        fail(f"missing {rel}")
    text = path.read_text(encoding="utf-8")
    if text.count(anchor) != 1:
        fail(f"{rel}: expected 1 anchor {anchor!r}, found {text.count(anchor)}")
    if check_only:
        return
    path.write_text(text.replace(anchor, anchor + insertion, 1), encoding="utf-8")


def rpc_js_const(ident: dict) -> str:
    return (
        "const RPC_TAG = String.fromCharCode("
        f"...[{dumps_c_bytes(ident['rpc_xor_bytes'])}].map(c => c ^ {ident['rpc_xor_key']}));\n"
    )


def rpc_vala_fn(ident: dict) -> str:
    return (
        "\n\t\tprivate static string rpc_tag () {\n"
        f"\t\t\tuint8 key = {ident['rpc_xor_key']};\n"
        f"\t\t\tuint8[] x = {{ {dumps_c_bytes(ident['rpc_xor_bytes'])} }};\n"
        "\t\t\tvar b = new StringBuilder.sized (9);\n"
        "\t\t\tforeach (uint8 c in x)\n"
        "\t\t\t\tb.append_c ((char) (c ^ key));\n"
        "\t\t\treturn b.str;\n"
        "\t\t}\n"
    )


def edits_for(ident: dict) -> list[Edit]:
    s = ident["agent_symbol"]
    prefix = ident["agent_prefix"]
    helper = ident["helper_prefix"]
    js = rpc_js_const(ident)
    return [
        # --- ports (server listen; stock `frida -U` still expects 27042) ---
        Edit(
            "subprojects/frida-core/lib/base/socket.vala",
            "\tpublic const uint16 DEFAULT_CONTROL_PORT = 27042;\n"
            "\tpublic const uint16 DEFAULT_CLUSTER_PORT = 27052;",
            f"\tpublic const uint16 DEFAULT_CONTROL_PORT = {ident['control_port']};\n"
            f"\tpublic const uint16 DEFAULT_CLUSTER_PORT = {ident['cluster_port']};",
            1,
        ),
        # --- RPC protocol tag constructed at runtime; wire value stays frida:rpc ---
        Edit(
            "subprojects/frida-core/lib/base/rpc.vala",
            '\t\t\t\t.add_string_value ("frida:rpc")',
            "\t\t\t\t.add_string_value (rpc_tag ())",
            1,
        ),
        Edit(
            "subprojects/frida-core/lib/base/rpc.vala",
            '\t\t\tif (json.index_of ("\\"frida:rpc\\"") == -1)',
            '\t\t\tif (json.index_of ("\\"" + rpc_tag () + "\\"") == -1)',
            1,
        ),
        Edit(
            "subprojects/frida-core/lib/base/rpc.vala",
            '\t\t\tif (type == null || type != "frida:rpc")',
            "\t\t\tif (type == null || type != rpc_tag ())",
            1,
        ),
        Edit(
            "subprojects/frida-gum/bindings/gumjs/runtime/message-dispatcher.js",
            "export function MessageDispatcher() {\n",
            js + "\nexport function MessageDispatcher() {\n",
            1,
        ),
        Edit(
            "subprojects/frida-gum/bindings/gumjs/runtime/message-dispatcher.js",
            "'frida:rpc'",
            "RPC_TAG",
            4,
        ),
        Edit(
            "subprojects/frida-gum/bindings/gumjs/runtime/worker.js",
            "export class Worker {\n",
            js + "\nexport class Worker {\n",
            1,
        ),
        Edit(
            "subprojects/frida-gum/bindings/gumjs/runtime/worker.js",
            "'frida:rpc'",
            "RPC_TAG",
            2,
        ),
        Edit(
            "subprojects/frida-core/src/barebone/script-runtime/message-dispatcher.ts",
            'export class MessageDispatcher {\n',
            js + "\nexport class MessageDispatcher {\n",
            1,
        ),
        Edit(
            "subprojects/frida-core/src/barebone/script-runtime/message-dispatcher.ts",
            '"frida:rpc"',
            "RPC_TAG",
            3,
        ),
        Edit(
            "subprojects/frida-core/src/host-session-service.vala",
            'either refused to load frida-agent, "',
            f'either refused to load {prefix}, "',
            1,
        ),
        # --- tmpdir / server directory / memfd ---
        Edit(
            "subprojects/frida-core/src/system.vala",
            '\t\t\tvar builder = new StringBuilder ("frida-");',
            f'\t\t\tvar builder = new StringBuilder ("{ident["tmp_prefix"]}");',
            1,
        ),
        Edit(
            "subprojects/frida-core/server/server.vala",
            '\tprivate const string DEFAULT_DIRECTORY = "re.frida.server";',
            f'\tprivate const string DEFAULT_DIRECTORY = "{ident["default_dir"]}";',
            1,
        ),
        Edit(
            "subprojects/frida-core/lib/base/linux.vala",
            "\t\tprivate int memfd_create (string name, uint flags) {\n"
            "\t\t\treturn Linux.syscall (LinuxSyscall.MEMFD_CREATE, name, flags);\n"
            "\t\t}",
            "\t\tprivate int memfd_create (string name, uint flags) {\n"
            f'\t\t\treturn Linux.syscall (LinuxSyscall.MEMFD_CREATE, "{ident["memfd_name"]}", flags);\n'
            "\t\t}",
            1,
        ),
        # --- agent filename on disk / maps ---
        Edit(
            "subprojects/frida-core/src/linux/linux-host-session.vala",
            'agent = new AgentDescriptor (PathTemplate ("frida-agent-<arch>.so"),',
            f'agent = new AgentDescriptor (PathTemplate ("{prefix}-<arch>.so"),',
            1,
        ),
        Edit(
            "subprojects/frida-core/src/linux/linux-host-session.vala",
            'new AgentResource ("frida-agent-arm.so", new Bytes.static (emulated_arm.data), tempdir),',
            f'new AgentResource ("{prefix}-arm.so", new Bytes.static (emulated_arm.data), tempdir),',
            1,
        ),
        Edit(
            "subprojects/frida-core/src/linux/linux-host-session.vala",
            'new AgentResource ("frida-agent-arm64.so", new Bytes.static (emulated_arm64.data), tempdir),',
            f'new AgentResource ("{prefix}-arm64.so", new Bytes.static (emulated_arm64.data), tempdir),',
            1,
        ),
        Edit(
            "subprojects/frida-core/src/linux/linux-host-session.vala",
            'name = "frida-agent-arm.so";',
            f'name = "{prefix}-arm.so";',
            1,
        ),
        Edit(
            "subprojects/frida-core/src/linux/linux-host-session.vala",
            'name = "frida-agent-arm64.so";',
            f'name = "{prefix}-arm64.so";',
            1,
        ),
        Edit(
            "subprojects/frida-core/src/linux/linux-host-session.vala",
            'string helper_path = "/data/local/tmp/frida-helper-" + instance_id + ".dex";',
            f'string helper_path = "/data/local/tmp/{helper}-" + instance_id + ".dex";',
            1,
        ),
        Edit(
            "subprojects/frida-core/src/linux/frida-helper-process.vala",
            'helper32 = make_temporary_helper ("frida-helper-32", blob32.data);',
            f'helper32 = make_temporary_helper ("{helper}-32", blob32.data);',
            1,
        ),
        Edit(
            "subprojects/frida-core/src/linux/frida-helper-process.vala",
            'helper64 = make_temporary_helper ("frida-helper-64", blob64.data);',
            f'helper64 = make_temporary_helper ("{helper}-64", blob64.data);',
            1,
        ),
        # --- exported agent symbol (not "main") ---
        Edit(
            "subprojects/frida-core/lib/agent/agent.vala",
            "\tpublic void main (string agent_parameters, ref Frida.UnloadPolicy unload_policy, void * injector_state) {",
            f'\t[CCode (cname = "{s}")]\n'
            "\tpublic void main (string agent_parameters, ref Frida.UnloadPolicy unload_policy, void * injector_state) {",
            1,
        ),
        Edit(
            "subprojects/frida-core/lib/agent/agent-glue.c",
            "  frida_agent_main (state->agent_parameters, &state->unload_policy, state->injector_state);",
            f"  {s} (state->agent_parameters, &state->unload_policy, state->injector_state);",
            1,
        ),
        Edit(
            "subprojects/frida-core/lib/agent/frida-agent.version",
            "    frida_agent_main;",
            f"    {s};",
            1,
        ),
        Edit(
            "subprojects/frida-core/lib/agent/frida-agent-android.version",
            "    frida_agent_main;",
            f"    {s};",
            1,
        ),
        Edit(
            "subprojects/frida-core/lib/agent/frida-agent-glibc.version",
            "    frida_agent_main;",
            f"    {s};",
            1,
        ),
        Edit(
            "subprojects/frida-core/lib/agent/frida-agent.symbols",
            "frida_agent_main\n",
            f"{s}\n",
            1,
        ),
        Edit(
            "subprojects/frida-core/lib/agent/frida-agent-x86.symbols",
            "_frida_agent_main\n",
            f"_{s}\n",
            1,
        ),
        Edit(
            "subprojects/frida-core/lib/agent/frida-agent.def",
            "\tfrida_agent_main\n",
            f"\t{s}\n",
            1,
        ),
        Edit(
            "subprojects/frida-core/lib/agent/meson.build",
            "extra_link_args += '-Wl,-exported_symbol,_frida_agent_main'",
            f"extra_link_args += '-Wl,-exported_symbol,_{s}'",
            1,
        ),
        Edit(
            "subprojects/frida-core/src/linux/linux-host-session.vala",
            'string entrypoint = "frida_agent_main";',
            f'string entrypoint = "{s}";',
            1,
        ),
        Edit(
            "subprojects/frida-core/src/agent-container.vala",
            'var main_func_found = container.module.symbol ("frida_agent_main", out main_func_symbol);',
            f'var main_func_found = container.module.symbol ("{s}", out main_func_symbol);',
            1,
        ),
        Edit(
            "subprojects/frida-core/src/darwin/darwin-host-session.vala",
            'unowned string entrypoint = "frida_agent_main";',
            f'unowned string entrypoint = "{s}";',
            1,
        ),
        Edit(
            "subprojects/frida-core/src/freebsd/freebsd-host-session.vala",
            'var id = yield binjector.inject_library_resource (pid, agent_desc, "frida_agent_main",',
            f'var id = yield binjector.inject_library_resource (pid, agent_desc, "{s}",',
            1,
        ),
        Edit(
            "subprojects/frida-core/src/qnx/qnx-host-session.vala",
            'var id = yield qinjector.inject_library_resource (pid, agent_desc, "frida_agent_main",',
            f'var id = yield qinjector.inject_library_resource (pid, agent_desc, "{s}",',
            1,
        ),
        Edit(
            "subprojects/frida-core/src/windows/windows-host-session.vala",
            'var id = yield winjector.inject_library_resource (pid, agent, "frida_agent_main",',
            f'var id = yield winjector.inject_library_resource (pid, agent, "{s}",',
            1,
        ),
        Edit(
            "subprojects/frida-core/src/windows/windows-host-session.vala",
            'installed_agent_path_template (), "frida_agent_main",',
            f'installed_agent_path_template (), "{s}",',
            1,
        ),
        # --- thread names / prgname (source-level; no sed) ---
        Edit(
            "subprojects/frida-gum/gum/gum.c",
            '  g_set_prgname ("frida");',
            f'  g_set_prgname ("{ident["prgname"]}");',
            1,
        ),
        Edit(
            "subprojects/frida-gum/bindings/gumjs/gumscriptscheduler.c",
            '    self->js_thread = g_thread_new ("gum-js-loop",',
            f'    self->js_thread = g_thread_new ("{ident["js_loop"]}",',
            1,
        ),
        Edit(
            "subprojects/frida-core/src/frida-glue.c",
            '      main_thread = g_thread_new ("frida-main-loop", run_main_loop, NULL);',
            f'      main_thread = g_thread_new ("{ident["main_loop"]}", run_main_loop, NULL);',
            1,
        ),
        Edit(
            "subprojects/frida-core/server/server.vala",
            '		var worker = new Thread<int> ("frida-server-main-loop", () => {',
            f'		var worker = new Thread<int> ("{ident["server_loop"]}", () => {{',
            1,
        ),
        Edit(
            "subprojects/frida-core/src/agent-container.vala",
            '			thread = new Thread<bool> ("frida-agent-container", run);',
            f'			thread = new Thread<bool> ("{ident["agent_container"]}", run);',
            1,
        ),
        Edit(
            "subprojects/frida-core/lib/agent/agent.vala",
            '				emulated_worker = new Thread<void> ("frida-agent-emulated", run_emulated_agent);',
            f'				emulated_worker = new Thread<void> ("{ident["agent_emulated"]}", run_emulated_agent);',
            1,
        ),
        Edit(
            "subprojects/frida-core/src/linux/linux-host-session.vala",
            '			worker_thread = new Thread<void> ("frida-android-helper", run);',
            f'			worker_thread = new Thread<void> ("{ident["android_helper_thread"]}", run);',
            1,
        ),
        Edit(
            "subprojects/frida-core/lib/gadget/gadget-glue.c",
            '  worker_thread = g_thread_new ("frida-gadget", run_worker_loop, NULL);',
            f'  worker_thread = g_thread_new ("{ident["gadget_thread"]}", run_worker_loop, NULL);',
            1,
        ),
        Edit(
            "subprojects/frida-core/lib/gadget/gadget.vala",
            '					Environment.set_thread_name ("frida-gadget-tcp-%u".printf (listen_port));',
            f'					Environment.set_thread_name ("{ident["gadget_thread"]}-tcp-%u".printf (listen_port));',
            1,
        ),
        Edit(
            "subprojects/frida-core/lib/gadget/gadget.vala",
            '					Environment.set_thread_name ("frida-gadget-unix");',
            f'					Environment.set_thread_name ("{ident["gadget_thread"]}-unix");',
            1,
        ),
    ]


POST_PROCESS_HOOK = '''
        strip_fp = Path(__file__).with_name("strip-fingerprints.py")
        idents = Path(__file__).with_name("florida-identities.json")
        if strip_fp.exists() and idents.exists():
            subprocess.run([sys.executable, str(strip_fp), "--identities", str(idents),
                            str(intermediate_path)], **run_kwargs)
'''

POST_PROCESS_ANCHOR = """        if strip_enabled and strip_command is not None:
            subprocess.run(strip_command + [intermediate_path], **run_kwargs)
"""


def install_strip_hook(frida_root: Path, ident: dict, scripts_dir: Path, check_only: bool) -> None:
    tools = frida_root / "subprojects" / "frida-core" / "tools"
    if not tools.is_dir():
        fail("frida-core/tools is missing")
    post = tools / "post-process.py"
    text = post.read_text(encoding="utf-8")
    if POST_PROCESS_ANCHOR not in text:
        fail("post-process.py: strip anchor not found")
    if "strip-fingerprints.py" in text:
        # already hooked
        pass
    elif check_only:
        pass
    else:
        post.write_text(text.replace(POST_PROCESS_ANCHOR, POST_PROCESS_ANCHOR + POST_PROCESS_HOOK, 1), encoding="utf-8")

    if check_only:
        return
    shutil.copy(scripts_dir / "strip-fingerprints.py", tools / "strip-fingerprints.py")
    (tools / "florida-identities.json").write_text(json.dumps(ident, indent=2) + "\n", encoding="utf-8")


def run(frida_root: Path, ident: dict, scripts_dir: Path, check_only: bool) -> None:
    if not (frida_root / "subprojects" / "frida-core" / "lib" / "base" / "rpc.vala").is_file():
        fail(f"{frida_root} does not contain checked-out frida-core")
    if not (frida_root / "subprojects" / "frida-gum" / "gum" / "gum.c").is_file():
        fail(f"{frida_root} does not contain checked-out frida-gum")

    rpc_path = frida_root / "subprojects/frida-core/lib/base/rpc.vala"
    if "private static string rpc_tag ()" not in rpc_path.read_text(encoding="utf-8"):
        insert_after(
            frida_root,
            "subprojects/frida-core/lib/base/rpc.vala",
            "\t\tpublic RpcClient (RpcPeer peer) {\n\t\t\tObject (peer: peer);\n\t\t}\n",
            rpc_vala_fn(ident),
            check_only,
        )

    glue = frida_root / "subprojects/frida-core/src/frida-glue.c"
    glue_text = glue.read_text(encoding="utf-8")
    prgname_line = f'    g_set_prgname ("{ident["prgname"]}");\n\n'
    glue_anchor = "#endif\n\n    if (runtime == FRIDA_RUNTIME_OTHER)"
    if glue_text.count(glue_anchor) != 1:
        fail("frida-glue.c: prgname anchor not found")
    if not check_only and f'g_set_prgname ("{ident["prgname"]}")' not in glue_text:
        glue.write_text(glue_text.replace(glue_anchor, "#endif\n\n" + prgname_line + "    if (runtime == FRIDA_RUNTIME_OTHER)", 1), encoding="utf-8")

    for edit in edits_for(ident):
        apply_edit(frida_root, edit, check_only)

    install_strip_hook(frida_root, ident, scripts_dir, check_only)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply Florida rewrites to a Frida checkout")
    parser.add_argument("--frida-dir", type=Path, required=True)
    parser.add_argument("--identities", type=Path, help="Existing identities.json")
    parser.add_argument("--seed", help="Seed used when generating identities")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify anchors exist; do not modify the Frida tree",
    )
    args = parser.parse_args(argv)

    scripts_dir = Path(__file__).resolve().parent
    frida_root = args.frida_dir.resolve()

    if args.identities and args.identities.is_file():
        ident = load(args.identities)
    else:
        ident = generate(args.seed)
        if not args.check:
            out = args.identities or Path("identities.json")
            save(ident, out)
            print(f"wrote {out}")

    run(frida_root, ident, scripts_dir, check_only=args.check)
    mode = "checked" if args.check else "rewrote"
    print(f"{mode} {frida_root}")
    print(f"  control_port = {ident['control_port']}")
    print(f"  agent_symbol = {ident['agent_symbol']}")
    print(f"  prgname      = {ident['prgname']}")
    print(f"  js_loop      = {ident['js_loop']}")
    print(f"  memfd_name   = {ident['memfd_name']}")
    print(f"  agent_prefix = {ident['agent_prefix']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
