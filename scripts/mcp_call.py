"""Call any lichess-analyzer MCP tool from the command line (no MCP client).

The tools are plain async functions; this runner imports the module that
defines the tool and calls it with JSON arguments. Handy when no IDE / MCP
host is available.

Examples
--------
    .venv\\Scripts\\python.exe -X utf8 scripts\\mcp_call.py --list
    .venv\\Scripts\\python.exe -X utf8 scripts\\mcp_call.py lichess_player_profile ^
        --args '{"username":"systeq"}'
    .venv\\Scripts\\python.exe -X utf8 scripts\\mcp_call.py lichess_analyze_position ^
        --args '{"fen":"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1","depth":14}'
    .venv\\Scripts\\python.exe -X utf8 scripts\\mcp_call.py lichess_workspace_info

PowerShell quoting: JSON must be quoted with single quotes; inside, use double
quotes only.
"""

import argparse
import asyncio
import importlib
import inspect
import json
import os
import pkgutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _load_env() -> None:
    path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                if key.strip() and key.strip() not in os.environ:
                    os.environ[key.strip()] = value.strip()


def discover_tools() -> dict:
    """Map tool name -> callable, scanning the tools package."""
    import lichess_analyzer_mcp.tools as tools_pkg

    found = {}
    for mod_info in pkgutil.iter_modules(tools_pkg.__path__):
        if mod_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"lichess_analyzer_mcp.tools.{mod_info.name}")
        for name, obj in vars(module).items():
            if not name.startswith("lichess_"):
                continue
            if inspect.iscoroutinefunction(obj) or inspect.isfunction(obj):
                found.setdefault(name, obj)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a lichess-analyzer tool from the shell")
    parser.add_argument(
        "tool", nargs="?", default="", help="Tool name (e.g. lichess_player_profile)"
    )
    parser.add_argument("--args", default="{}", help="JSON object with tool arguments")
    parser.add_argument("--list", action="store_true", help="List available tools and exit")
    parser.add_argument("--out", default="", help="Write the JSON result to this file")
    args = parser.parse_args()

    _load_env()
    tools = discover_tools()

    if args.list:
        for name in sorted(tools):
            signature = inspect.signature(tools[name])
            print(f"{name}{signature}")
        return 0

    if not args.tool:
        parser.error("tool name required (or use --list)")
    if args.tool not in tools:
        print(f"unknown tool: {args.tool}", file=sys.stderr)
        print("use --list to see available tools", file=sys.stderr)
        return 1

    try:
        kwargs = json.loads(args.args or "{}")
    except json.JSONDecodeError as exc:
        print(f"--args is not valid JSON: {exc}", file=sys.stderr)
        return 1
    if not isinstance(kwargs, dict):
        print("--args must be a JSON object", file=sys.stderr)
        return 1

    func = tools[args.tool]
    result = asyncio.run(func(**kwargs)) if inspect.iscoroutinefunction(func) else func(**kwargs)

    text = json.dumps(result, ensure_ascii=False, indent=2, default=str)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"json: {args.out} ({os.path.getsize(args.out)} bytes)")
    else:
        print(text)

    from lichess_analyzer_mcp.services.engine_client import close_engine

    close_engine()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
