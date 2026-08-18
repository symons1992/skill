#!/usr/bin/env python3
"""Create a safe, evidence-oriented inventory of a Python repository.

The scanner parses source with ``ast`` and never imports repository modules. Its
registration results are discovery candidates, not an authoritative runtime graph.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Optional


SKIP_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode", ".cache", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", ".tox", ".nox", ".venv", "venv", "env",
    "site-packages", "node_modules", "vendor", "dist", "build", "htmlcov",
    "__pycache__", ".eggs", "tmp",
}
PROJECT_FILES = {
    "pyproject.toml", "setup.py", "setup.cfg", "Pipfile", "Pipfile.lock",
    "poetry.lock", "pdm.lock", "uv.lock", "tox.ini", "noxfile.py",
    "pytest.ini", "mypy.ini", "ruff.toml", ".python-version", "manage.py",
}
NOTABLE_NAMES = {
    "Dockerfile", "Makefile", "Procfile", "compose.yaml", "compose.yml",
    "serverless.yml", "serverless.yaml", "template.yaml", "app.yaml",
}
NOTABLE_SUFFIXES = {
    ".proto", ".graphql", ".gql", ".sql", ".yaml", ".yml", ".json",
    ".toml", ".ini", ".cfg",
}
GENERATED_RE = re.compile(
    r"(?im)^\s*#.*(?:code generated|generated (?:file|by)|auto-?generated|do not edit)"
)
FRAMEWORK_NAMES = {
    "fastapi", "starlette", "django", "rest_framework", "flask", "aiohttp",
    "grpc", "graphene", "strawberry", "ariadne", "celery", "rq", "dramatiq",
    "apscheduler", "airflow", "prefect", "dagster", "click", "typer", "falcon",
    "litestar", "sanic", "tornado", "boto3", "sqlalchemy", "pydantic",
}
HTTP_DECORATORS = {
    "route", "api_route", "get", "post", "put", "patch", "delete", "head",
    "options", "websocket", "websocket_route",
}
CLI_DECORATORS = {"command", "group", "callback"}
GRAPHQL_DECORATORS = {"field", "resolver", "mutation", "subscription"}
TASK_DECORATORS = {"shared_task", "actor", "job", "periodic_task"}
WORKFLOW_DECORATORS = {"dag", "flow", "op", "asset", "sensor", "schedule"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scan Python source without importing it and emit a discovery inventory "
            "(not an authoritative call graph)."
        )
    )
    parser.add_argument("root", nargs="?", default=".", help="repository root (default: current directory)")
    parser.add_argument("--output", "-o", help="write output to this file instead of stdout")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--max-symbols", type=int, default=60, help="maximum records per Markdown section")
    parser.add_argument("--include-tests", action="store_true", help="include test symbols and registrations")
    return parser.parse_args()


def walk_files(root: Path) -> Iterable[Path]:
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(
            directory for directory in dirs
            if directory not in SKIP_DIRS and not directory.endswith(".egg-info")
        )
        for name in sorted(files):
            yield Path(current, name)


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    if isinstance(node, ast.Call):
        return dotted_name(node.func)
    return ""


def target_names(node: ast.AST) -> list[str]:
    if isinstance(node, (ast.Tuple, ast.List)):
        return [name for item in node.elts for name in target_names(item)]
    name = dotted_name(node)
    return [name] if name else []


def compact_source(text: str, node: ast.AST, limit: int = 220) -> str:
    source = ast.get_source_segment(text, node) or ""
    return " ".join(source.split())[:limit]


def module_name(path: Path, root: Path) -> str:
    relative = path.relative_to(root)
    parts = list(relative.with_suffix("").parts)
    if parts and parts[0] == "src":
        parts.pop(0)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) or "<root>"


def is_test_file(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    return (
        path.name.startswith("test_")
        or path.name.endswith("_test.py")
        or any(part in {"test", "tests"} for part in relative.parts[:-1])
    )


def classify_decorator(name: str) -> Optional[str]:
    tail = name.rsplit(".", 1)[-1].lower()
    lowered = name.lower()
    if tail in HTTP_DECORATORS:
        return "http-or-websocket"
    if tail in TASK_DECORATORS or "celery" in lowered:
        return "task"
    if tail == "task":
        return "task-or-workflow"
    if tail in WORKFLOW_DECORATORS:
        return "scheduler-or-workflow"
    if tail in GRAPHQL_DECORATORS or any(x in lowered for x in ("strawberry", "graphene", "ariadne")):
        return "graphql"
    if tail in CLI_DECORATORS:
        return "cli"
    if tail in {"consumer", "subscribe"}:
        return "consumer"
    if tail in {"receiver", "listens_for", "on_event", "before_request", "after_request", "errorhandler"}:
        return "hook-or-signal"
    return None


def classify_call(name: str) -> Optional[str]:
    tail = name.rsplit(".", 1)[-1].lower()
    lowered = name.lower()
    if re.fullmatch(r"add_\w+servicer_to_server", tail):
        return "rpc"
    if tail in {"add_api_route", "add_route", "add_url_rule", "register_blueprint", "include_router", "mount"}:
        return "http-registration"
    if tail in {"path", "re_path", "include", "register"}:
        return "route-or-router-candidate"
    if tail in {"route", "get", "post", "put", "patch", "delete", "websocket", "websocket_route"}:
        return "http-or-websocket"
    if tail in {"add_routes", "add_get", "add_post", "add_put", "add_patch", "add_delete", "add_subapp"}:
        return "http-registration"
    if tail in {"subscribe", "consume", "register_consumer", "add_consumer", "connect"}:
        return "consumer-or-signal"
    if tail in {"add_job", "add_task", "schedule", "cron", "every"}:
        return "scheduler-or-workflow"
    if tail in {"add_command", "add_typer", "set_defaults"}:
        return "cli"
    if tail in {"schema", "make_executable_schema"} and any(x in lowered for x in ("graphql", "strawberry", "graphene", "ariadne", "schema")):
        return "graphql"
    return None


def is_main_guard(node: ast.If) -> bool:
    test = node.test
    if not isinstance(test, ast.Compare) or len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
        return False
    values = [test.left, *test.comparators]
    has_name = any(isinstance(value, ast.Name) and value.id == "__name__" for value in values)
    has_main = any(isinstance(value, ast.Constant) and value.value == "__main__" for value in values)
    return has_name and has_main


class InventoryVisitor(ast.NodeVisitor):
    def __init__(self, text: str, relative: str, module: str) -> None:
        self.text = text
        self.relative = relative
        self.module = module
        self.scope: list[str] = []
        self.functions: list[dict[str, Any]] = []
        self.classes: list[dict[str, Any]] = []
        self.imports: list[str] = []
        self.registrations: list[dict[str, Any]] = []
        self.entry_points: list[dict[str, Any]] = []
        self.decorator_call_ids: set[int] = set()

    def qualified(self, name: str) -> str:
        local = ".".join([*self.scope, name])
        return f"{self.module}.{local}" if self.module != "<root>" else local

    def evidence(self, node: ast.AST) -> dict[str, Any]:
        return {"file": self.relative, "line": getattr(node, "lineno", 1)}

    def record_decorators(self, node: ast.AST, decorators: list[ast.expr], target: str) -> None:
        for decorator in decorators:
            if isinstance(decorator, ast.Call):
                self.decorator_call_ids.add(id(decorator))
            name = dotted_name(decorator)
            kind = classify_decorator(name)
            if kind:
                self.registrations.append({
                    "kind": kind,
                    **self.evidence(decorator),
                    "target": target,
                    "expression": compact_source(self.text, decorator),
                })

    def visit_Import(self, node: ast.Import) -> None:
        self.imports.extend(alias.name for alias in node.names)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        prefix = "." * node.level + (node.module or "")
        self.imports.append(prefix or ".")

    def _visit_function(self, node: ast.AST, async_kind: bool) -> None:
        assert isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        qualified = self.qualified(node.name)
        decorators = [dotted_name(item) for item in node.decorator_list]
        self.functions.append({
            "symbol": qualified,
            "file": self.relative,
            "line": node.lineno,
            "async": async_kind,
            "decorators": decorators,
        })
        self.record_decorators(node, node.decorator_list, qualified)
        if node.name in {"lambda_handler", "handler"}:
            self.entry_points.append({"kind": "serverless-candidate", "symbol": qualified, **self.evidence(node)})
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node, False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node, True)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        qualified = self.qualified(node.name)
        self.classes.append({
            "symbol": qualified,
            "file": self.relative,
            "line": node.lineno,
            "bases": [dotted_name(base) or compact_source(self.text, base) for base in node.bases],
            "decorators": [dotted_name(item) for item in node.decorator_list],
        })
        self.record_decorators(node, node.decorator_list, qualified)
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        if isinstance(node.value, ast.Call):
            constructor = dotted_name(node.value.func)
            tail = constructor.rsplit(".", 1)[-1]
            if tail in {
                "FastAPI", "Starlette", "Flask", "Celery", "Falcon", "Sanic", "Litestar",
                "get_asgi_application", "get_wsgi_application", "create_app", "create_application",
                "make_asgi_app",
            }:
                for target in node.targets:
                    for name in target_names(target):
                        self.entry_points.append({
                            "kind": "application-object",
                            "symbol": self.qualified(name),
                            "constructor": constructor,
                            **self.evidence(node),
                        })
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        if is_main_guard(node):
            self.entry_points.append({
                "kind": "python-main-guard",
                "symbol": f"{self.module}.__main__",
                **self.evidence(node),
            })
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if id(node) in self.decorator_call_ids:
            self.generic_visit(node)
            return
        name = dotted_name(node.func)
        kind = classify_call(name)
        if kind:
            self.registrations.append({
                "kind": kind,
                **self.evidence(node),
                "target": name,
                "expression": compact_source(self.text, node),
            })
        self.generic_visit(node)


def parse_pyproject(path: Path, root: Path) -> dict[str, Any]:
    data: dict[str, Any] = {"path": rel(path, root), "name": "", "requires_python": "", "dependencies": [], "scripts": {}}
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return data
    parsed: Optional[dict[str, Any]] = None
    try:
        import tomllib  # type: ignore

        parsed = tomllib.loads(text)
    except (ImportError, ValueError):
        try:
            import tomli  # type: ignore

            parsed = tomli.loads(text)
        except (ImportError, ValueError):
            parsed = None
    if parsed is None:
        def section(name: str) -> str:
            match = re.search(
                rf"(?ms)^\[{re.escape(name)}\]\s*$\n(.*?)(?=^\[|\Z)", text
            )
            return match.group(1) if match else ""

        project_text = section("project")
        poetry_text = section("tool.poetry")
        for field, key in (("name", "name"), ("requires_python", "requires-python")):
            match = re.search(rf'(?m)^\s*{re.escape(key)}\s*=\s*["\']([^"\']+)', project_text)
            if match:
                data[field] = match.group(1)
        if not data["name"]:
            match = re.search(r'(?m)^\s*name\s*=\s*["\']([^"\']+)', poetry_text)
            if match:
                data["name"] = match.group(1)
        dependency_match = re.search(r"(?ms)^\s*dependencies\s*=\s*\[(.*?)\]", project_text)
        if dependency_match:
            data["dependencies"] = re.findall(r'["\']([^"\']+)["\']', dependency_match.group(1))
        script_text = section("project.scripts") or section("tool.poetry.scripts")
        for match in re.finditer(r'(?m)^\s*["\']?([^="\']+?)["\']?\s*=\s*["\']([^"\']+)["\']', script_text):
            data["scripts"][match.group(1).strip()] = match.group(2)
        if not data["dependencies"]:
            for match in re.finditer(r'(?m)^\s*["\']?([^="\']+?)["\']?\s*=', section("tool.poetry.dependencies")):
                data["dependencies"].append(match.group(1).strip())
        return data
    project = parsed.get("project", {}) if isinstance(parsed, dict) else {}
    if isinstance(project, dict):
        data["name"] = project.get("name", "")
        data["requires_python"] = project.get("requires-python", "")
        data["dependencies"] = project.get("dependencies", []) if isinstance(project.get("dependencies", []), list) else []
        scripts = project.get("scripts", {})
        data["scripts"] = scripts if isinstance(scripts, dict) else {}
    poetry = parsed.get("tool", {}).get("poetry", {}) if isinstance(parsed, dict) else {}
    if isinstance(poetry, dict):
        data["name"] = data["name"] or poetry.get("name", "")
        poetry_scripts = poetry.get("scripts", {})
        if not data["scripts"] and isinstance(poetry_scripts, dict):
            data["scripts"] = poetry_scripts
        poetry_deps = poetry.get("dependencies", {})
        if not data["dependencies"] and isinstance(poetry_deps, dict):
            data["dependencies"] = list(poetry_deps)
    return data


def scan(root: Path, include_tests: bool) -> dict[str, Any]:
    all_files = list(walk_files(root))
    python_files = [path for path in all_files if path.suffix in {".py", ".pyi"}]
    result: dict[str, Any] = {
        "root": str(root), "project_files": [], "projects": [], "counts": {},
        "modules": [], "packages": [], "entry_points": [], "functions": [],
        "classes": [], "registrations": [], "imports": [], "frameworks": [],
        "syntax_errors": [], "notable_files": [],
    }
    import_counts: Counter[str] = Counter()
    module_files: dict[str, list[str]] = defaultdict(list)
    generated_count = 0
    test_count = 0
    migration_count = 0
    parsed_count = 0

    for path in all_files:
        relative = rel(path, root)
        if path.name in PROJECT_FILES or path.name.startswith("requirements") and path.suffix == ".txt":
            result["project_files"].append(relative)
        if path.name == "pyproject.toml":
            project = parse_pyproject(path, root)
            result["projects"].append(project)
            for command, target in project.get("scripts", {}).items():
                result["entry_points"].append({
                    "kind": "project-script", "symbol": str(command), "target": str(target),
                    "file": relative, "line": 1,
                })
        if path.name in NOTABLE_NAMES or path.suffix in NOTABLE_SUFFIXES:
            result["notable_files"].append(relative)

    for path in python_files:
        text = read_text(path)
        if text is None:
            continue
        relative = rel(path, root)
        test_file = is_test_file(path, root)
        generated = bool(GENERATED_RE.search(text[:4096]))
        migration = "migrations" in path.relative_to(root).parts
        test_count += int(test_file)
        generated_count += int(generated)
        migration_count += int(migration)
        module = module_name(path, root)
        module_files[module].append(relative)
        if generated:
            continue
        try:
            tree = ast.parse(text, filename=relative, type_comments=True)
        except SyntaxError as error:
            result["syntax_errors"].append({
                "file": relative, "line": error.lineno or 1, "message": error.msg,
            })
            continue
        parsed_count += 1
        visitor = InventoryVisitor(text, relative, module)
        visitor.visit(tree)
        import_counts.update(visitor.imports)
        result["entry_points"].extend(visitor.entry_points)
        if include_tests or not test_file:
            result["functions"].extend(visitor.functions)
            result["classes"].extend(visitor.classes)
            result["registrations"].extend(visitor.registrations)

    result["modules"] = [
        {"module": module, "files": files, "file_count": len(files)}
        for module, files in sorted(module_files.items())
    ]
    package_files: dict[str, list[str]] = defaultdict(list)
    for module, files in module_files.items():
        package_files[module.split(".", 1)[0]].extend(files)
    result["packages"] = [
        {"package": package, "files": sorted(files), "file_count": len(files)}
        for package, files in sorted(package_files.items())
    ]
    result["imports"] = [{"path": name, "count": count} for name, count in import_counts.most_common()]
    dependency_text = " ".join(
        str(dep).lower() for project in result["projects"] for dep in project.get("dependencies", [])
    )
    imported_roots = {name.lstrip(".").split(".", 1)[0].lower() for name in import_counts}
    result["frameworks"] = sorted(
        name for name in FRAMEWORK_NAMES if name in imported_roots or name.replace("_", "-") in dependency_text
    )
    result["counts"] = {
        "all_files": len(all_files), "python_files": len(python_files),
        "parsed_python_files": parsed_count, "test_python_files": test_count,
        "generated_python_files": generated_count, "migration_python_files": migration_count,
        "modules": len(module_files), "registration_candidates": len(result["registrations"]),
        "syntax_errors": len(result["syntax_errors"]),
    }
    return result


def md_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    if not rows:
        return ["_None found by the scanner._"]
    def safe(value: Any) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")
    return [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
        *["| " + " | ".join(safe(value) for value in row) + " |" for row in rows],
    ]


def evidence(item: dict[str, Any]) -> str:
    return f"`{item['file']}:L{item['line']}`"


def render_markdown(data: dict[str, Any], limit: int) -> str:
    lines = [
        "# Python repository inventory", "", f"Root: `{data['root']}`", "",
        "> Discovery output only. Verify registrations, reachability, final external identities, and call edges in source/configuration.",
        "", "## Summary", "",
    ]
    lines += md_table(["Metric", "Count"], [[key.replace("_", " "), value] for key, value in data["counts"].items()])
    lines += ["", "## Projects and tooling", ""]
    lines += md_table(
        ["Project file", "Distribution", "Requires Python", "Scripts"],
        [[item["path"], item["name"] or "-", item["requires_python"] or "-", ", ".join(item["scripts"]) or "-"] for item in data["projects"]],
    )
    if data["project_files"]:
        lines += ["", "Project/tool files: " + ", ".join(f"`{path}`" for path in data["project_files"][:limit])]
    lines += ["", "Detected frameworks/libraries: " + (", ".join(data["frameworks"]) or "_None detected._")]
    lines += ["", "## Runtime entry-point candidates", ""]
    lines += md_table(
        ["Kind", "Symbol", "Target/constructor", "Evidence"],
        [[item["kind"], item["symbol"], item.get("target") or item.get("constructor", "-"), evidence(item)] for item in data["entry_points"][:limit]],
    )
    lines += ["", "## Packages", ""]
    lines += md_table(["Import root", "Files"], [[item["package"], item["file_count"]] for item in data["packages"][:limit]])
    lines += ["", "## Registration candidates", ""]
    lines += md_table(
        ["Kind", "Target", "Evidence", "Expression"],
        [[item["kind"], item["target"], evidence(item), f"`{item['expression']}`"] for item in data["registrations"][:limit]],
    )
    lines += ["", "## Declared classes", ""]
    lines += md_table(
        ["Symbol", "Bases", "Evidence"],
        [[item["symbol"], ", ".join(item["bases"]) or "-", evidence(item)] for item in data["classes"][:limit]],
    )
    lines += ["", "## Declared functions and methods", ""]
    lines += md_table(
        ["Symbol", "Mode", "Decorators", "Evidence"],
        [[item["symbol"], "async" if item["async"] else "sync", ", ".join(item["decorators"]) or "-", evidence(item)] for item in data["functions"][:limit]],
    )
    lines += ["", "## Frequent imports", ""]
    lines += md_table(["Import", "Files/statements"], [[item["path"], item["count"]] for item in data["imports"][:limit]])
    lines += ["", "## Syntax errors", ""]
    lines += md_table(
        ["Evidence", "Message"],
        [[evidence(item), item["message"]] for item in data["syntax_errors"][:limit]],
    )
    lines += ["", "## Notable non-source files", ""]
    lines += [*(f"- `{item}`" for item in data["notable_files"][:limit])] if data["notable_files"] else ["_None found._"]
    lines += [
        "", "## Next investigation", "",
        "1. Verify application/worker composition roots and deployment-selected entry points.",
        "2. Build the complete inbound-interface ledger and resolve prefixes, mounts, discovery, and reachability.",
        "3. Trace every ledger row through validation, domain behavior, persistence/external effects, exception mapping, and tests.",
        "4. Reconcile registrations with schemas, settings, deployment metadata, and tests.", "",
    ]
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2
    data = scan(root, args.include_tests)
    output = (
        json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        if args.format == "json"
        else render_markdown(data, max(1, args.max_symbols))
    )
    if args.output:
        destination = Path(args.output).expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
