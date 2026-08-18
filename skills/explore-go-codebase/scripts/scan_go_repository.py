#!/usr/bin/env python3
"""Create a lightweight, evidence-oriented inventory of a Go repository."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


SKIP_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode", ".cache",
    "vendor", "node_modules", "testdata", "dist", "build", "tmp",
}
GENERATED_RE = re.compile(r"^// Code generated .* DO NOT EDIT\.$", re.MULTILINE)
PACKAGE_RE = re.compile(r"(?m)^\s*package\s+([A-Za-z_]\w*)")
IMPORT_BLOCK_RE = re.compile(r"(?ms)^\s*import\s*\((.*?)\)")
IMPORT_ONE_RE = re.compile(r'(?m)^\s*import\s+(?:[.\w]+\s+)?"([^"]+)"')
QUOTED_IMPORT_RE = re.compile(r'(?:^|\s)(?:[.\w]+\s+)?"([^"]+)"')
FUNC_RE = re.compile(
    r"(?m)^func\s+(?:\((?P<recv>[^)]*)\)\s+)?(?P<name>[A-Za-z_]\w*)\s*(?:\[[^\]]+\]\s*)?\("
)
TYPE_RE = re.compile(r"(?m)^type\s+([A-Za-z_]\w*)\s+(struct|interface)\b")

REGISTRATION_PATTERNS = {
    "http": re.compile(r"\b(?:HandleFunc|Handle|Methods|Method|Any|GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s*\("),
    "rpc": re.compile(r"\bRegister\w*(?:Server|Handler)\s*\("),
    "graphql": re.compile(r"\b(?:Query|Mutation|Subscription|Resolver|GraphQL)\w*\s*\("),
    "websocket-sse": re.compile(r"\b(?:Upgrade|WebSocket|Websocket|EventSource|ServerSentEvents)\w*\s*\("),
    "cli": re.compile(r"\b(?:AddCommand|cobra\.Command)\b"),
    "consumer": re.compile(r"\b(?:Subscribe|Consume|Consumer|HandleMessage|RegisterConsumer)\w*\s*\("),
    "scheduler": re.compile(r"\b(?:Cron|Schedule|Every|AddFunc|AddJob)\w*\s*\("),
    "dependency-injection": re.compile(r"\b(?:wire\.Build|fx\.Provide|fx\.Invoke|dig\.In)\b"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan Go source and emit a discovery inventory (not an authoritative call graph)."
    )
    parser.add_argument("root", nargs="?", default=".", help="repository root (default: current directory)")
    parser.add_argument("--output", "-o", help="write output to this file instead of stdout")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--max-symbols", type=int, default=40, help="maximum symbols per section")
    parser.add_argument("--include-tests", action="store_true", help="include _test.go symbols and registrations")
    return parser.parse_args()


def walk_files(root: Path, suffix: str | None = None) -> Iterable[Path]:
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(files):
            path = Path(current, name)
            if suffix is None or path.name.endswith(suffix):
                yield path


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def parse_module_file(path: Path, root: Path) -> dict[str, Any]:
    text = read_text(path) or ""
    modules = re.findall(r"(?m)^\s*module\s+(\S+)", text)
    go_versions = re.findall(r"(?m)^\s*go\s+(\S+)", text)
    toolchains = re.findall(r"(?m)^\s*toolchain\s+(\S+)", text)
    replaces = re.findall(r"(?m)^\s*replace\s+([^\n]+)", text)
    return {
        "path": rel(path, root), "modules": modules, "go": go_versions,
        "toolchain": toolchains, "replaces": replaces,
    }


def imports_from(text: str) -> list[str]:
    imports = IMPORT_ONE_RE.findall(text)
    for block in IMPORT_BLOCK_RE.findall(text):
        imports.extend(QUOTED_IMPORT_RE.findall(block))
    return imports


def scan(root: Path, include_tests: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "root": str(root), "module_files": [], "workspace_files": [],
        "counts": {}, "packages": [], "entry_points": [], "functions": [],
        "types": [], "registrations": [], "imports": [], "notable_files": [],
    }
    all_files = list(walk_files(root))
    go_files = [p for p in all_files if p.suffix == ".go"]
    owned_go_files: list[Path] = []
    generated_count = 0
    test_count = 0
    package_files: dict[tuple[str, str], list[str]] = defaultdict(list)
    import_counts: Counter[str] = Counter()

    for path in all_files:
        if path.name == "go.mod":
            result["module_files"].append(parse_module_file(path, root))
        elif path.name == "go.work":
            result["workspace_files"].append(rel(path, root))
        if path.name in {"Dockerfile", "Makefile", "Taskfile.yml", "buf.yaml"} or path.suffix in {
            ".proto", ".sql", ".yaml", ".yml", ".json"
        }:
            result["notable_files"].append(rel(path, root))

    for path in go_files:
        text = read_text(path)
        if text is None:
            continue
        relative = rel(path, root)
        generated = bool(GENERATED_RE.search(text[:4096]))
        is_test = path.name.endswith("_test.go")
        generated_count += int(generated)
        test_count += int(is_test)
        if generated:
            continue
        owned_go_files.append(path)
        package_match = PACKAGE_RE.search(text)
        package = package_match.group(1) if package_match else "<unknown>"
        package_files[(path.parent.relative_to(root).as_posix() or ".", package)].append(relative)
        import_counts.update(imports_from(text))

        if package == "main":
            for match in FUNC_RE.finditer(text):
                if match.group("name") == "main" and not match.group("recv"):
                    result["entry_points"].append({"symbol": "main", "file": relative, "line": line_of(text, match.start())})

        if is_test and not include_tests:
            continue
        for match in FUNC_RE.finditer(text):
            receiver = " ".join((match.group("recv") or "").split())
            name = match.group("name")
            symbol = f"({receiver}).{name}" if receiver else name
            result["functions"].append({"symbol": symbol, "file": relative, "line": line_of(text, match.start())})
        for match in TYPE_RE.finditer(text):
            result["types"].append({"symbol": match.group(1), "kind": match.group(2), "file": relative, "line": line_of(text, match.start())})
        for kind, pattern in REGISTRATION_PATTERNS.items():
            for match in pattern.finditer(text):
                snippet = " ".join(text[match.start():text.find("\n", match.start())].strip().split())[:180]
                result["registrations"].append({"kind": kind, "file": relative, "line": line_of(text, match.start()), "snippet": snippet})

    result["packages"] = [
        {"directory": directory, "package": package, "files": files, "file_count": len(files)}
        for (directory, package), files in sorted(package_files.items())
    ]
    result["imports"] = [{"path": path, "count": count} for path, count in import_counts.most_common()]
    result["counts"] = {
        "all_files": len(all_files), "go_files": len(go_files), "owned_go_files": len(owned_go_files),
        "test_go_files": test_count, "generated_go_files": generated_count, "packages": len(package_files),
    }
    return result


def md_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    if not rows:
        return ["_None found by the scanner._"]
    safe = lambda value: str(value).replace("|", "\\|").replace("\n", " ")
    return [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
        *["| " + " | ".join(safe(value) for value in row) + " |" for row in rows],
    ]


def render_markdown(data: dict[str, Any], limit: int) -> str:
    lines = [
        "# Go repository inventory", "",
        f"Root: `{data['root']}`", "",
        "> Discovery output only. Verify important call edges and runtime behavior in source.", "",
        "## Summary", "",
    ]
    lines += md_table(["Metric", "Count"], [[k.replace("_", " "), v] for k, v in data["counts"].items()])
    lines += ["", "## Modules and workspaces", ""]
    module_rows = []
    for item in data["module_files"]:
        module_rows.append([item["path"], ", ".join(item["modules"]) or "-", ", ".join(item["go"]) or "-", "; ".join(item["replaces"]) or "-"])
    lines += md_table(["File", "Module", "Go", "Replace directives"], module_rows)
    if data["workspace_files"]:
        lines += ["", "Workspaces: " + ", ".join(f"`{p}`" for p in data["workspace_files"])]
    lines += ["", "## Entry points", ""]
    lines += md_table(["Symbol", "Evidence"], [[x["symbol"], f"`{x['file']}:L{x['line']}`"] for x in data["entry_points"][:limit]])
    lines += ["", "## Packages", ""]
    lines += md_table(["Directory", "Package", "Owned files"], [[x["directory"], x["package"], x["file_count"]] for x in data["packages"][:limit]])
    lines += ["", "## Registration candidates", ""]
    lines += md_table(["Kind", "Evidence", "Source line"], [[x["kind"], f"`{x['file']}:L{x['line']}`", f"`{x['snippet']}`"] for x in data["registrations"][:limit]])
    lines += ["", "## Declared types", ""]
    lines += md_table(["Kind", "Symbol", "Evidence"], [[x["kind"], x["symbol"], f"`{x['file']}:L{x['line']}`"] for x in data["types"][:limit]])
    lines += ["", "## Declared functions and methods", ""]
    lines += md_table(["Symbol", "Evidence"], [[x["symbol"], f"`{x['file']}:L{x['line']}`"] for x in data["functions"][:limit]])
    lines += ["", "## Frequent imports", ""]
    lines += md_table(["Import", "Files"], [[x["path"], x["count"]] for x in data["imports"][:limit]])
    lines += ["", "## Notable non-Go files", ""]
    notable = data["notable_files"][:limit]
    lines += [*(f"- `{item}`" for item in notable)] if notable else ["_None found by the scanner._"]
    lines += ["", "## Next investigation", "", "1. Verify registrations and composition roots in source.", "2. Select the highest-value external flows and trace bounded call chains.", "3. Inspect tests, configuration, schemas, concurrency, and failure paths.", ""]
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2
    data = scan(root, args.include_tests)
    output = json.dumps(data, indent=2, ensure_ascii=False) + "\n" if args.format == "json" else render_markdown(data, max(1, args.max_symbols))
    if args.output:
        destination = Path(args.output).expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
