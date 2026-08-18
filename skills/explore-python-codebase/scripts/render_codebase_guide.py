#!/usr/bin/env python3
"""Validate codebase-guide data and render a self-contained offline HTML report."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


STATUS_VALUES = {"traced", "partial", "unresolved"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
REMOTE_RE = re.compile(r"(?i)(?:https?:)?//[a-z0-9]")
ABSOLUTE_WINDOWS_RE = re.compile(r"^[A-Za-z]:[\\/]")
SECRET_PATTERNS = {
    "private key material": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "bearer token value": re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~-]{24,}"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render an evidence-backed Python codebase guide as one offline HTML file."
    )
    parser.add_argument("--input", "-i", required=True, help="analysis data JSON")
    parser.add_argument("--output", "-o", help="destination HTML file")
    parser.add_argument(
        "--template",
        help="HTML template; defaults to the bundled codebase-guide.template.html",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate data and template without writing HTML",
    )
    return parser.parse_args()


def is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def walk_strings(value: Any, path: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk_strings(item, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from walk_strings(item, f"{path}.{key}")


def require_fields(item: dict[str, Any], fields: Iterable[str], path: str, errors: list[str]) -> None:
    for field in fields:
        if field not in item:
            errors.append(f"{path}.{field}: required field is missing")


def validate_evidence(evidence: Any, path: str, errors: list[str], required: bool = False) -> None:
    if not isinstance(evidence, list):
        errors.append(f"{path}: evidence must be an array")
        return
    if required and not evidence:
        errors.append(f"{path}: at least one source citation is required")
    for index, citation in enumerate(evidence):
        citation_path = f"{path}[{index}]"
        if not is_nonempty_string(citation):
            errors.append(f"{citation_path}: citation must be a non-empty string")
            continue
        if citation.startswith(("/", "~")) or ABSOLUTE_WINDOWS_RE.match(citation):
            errors.append(f"{citation_path}: use a repository-relative source path")
        if "://" in citation:
            errors.append(f"{citation_path}: URLs are not valid source citations")


def validate_symbol_record(record: Any, path: str, errors: list[str]) -> None:
    if not isinstance(record, dict):
        errors.append(f"{path}: expected an object")
        return
    require_fields(record, ("symbol", "evidence"), path, errors)
    if "symbol" in record and not is_nonempty_string(record["symbol"]):
        errors.append(f"{path}.symbol: must be a non-empty string")
    if "evidence" in record:
        validate_evidence(record["evidence"], f"{path}.evidence", errors, required=True)


def validate_steps(steps: Any, path: str, errors: list[str], required: bool) -> None:
    if not isinstance(steps, list):
        errors.append(f"{path}: steps must be an array")
        return
    if required and not steps:
        errors.append(f"{path}: a traced interface needs at least one ordered step")
    for index, step in enumerate(steps):
        step_path = f"{path}[{index}]"
        if not isinstance(step, dict):
            errors.append(f"{step_path}: expected an object")
            continue
        require_fields(step, ("stage", "symbol", "action", "evidence"), step_path, errors)
        for field in ("stage", "symbol", "action"):
            if field in step and not is_nonempty_string(step[field]):
                errors.append(f"{step_path}.{field}: must be a non-empty string")
        if "evidence" in step:
            validate_evidence(step["evidence"], f"{step_path}.evidence", errors, required=True)


def validate_interface(item: Any, index: int, shared_ids: set[str], errors: list[str]) -> None:
    path = f"$.interfaces[{index}]"
    if not isinstance(item, dict):
        errors.append(f"{path}: expected an object")
        return
    require_fields(
        item,
        (
            "id", "protocol", "external", "title", "status", "registration", "handler",
            "request", "response", "steps", "branches", "errors", "effects", "tests", "unresolved",
        ),
        path,
        errors,
    )
    for field in ("id", "protocol", "external", "title", "status"):
        if field in item and not is_nonempty_string(item[field]):
            errors.append(f"{path}.{field}: must be a non-empty string")
    if is_nonempty_string(item.get("id")) and not ID_RE.fullmatch(item["id"]):
        errors.append(f"{path}.id: use lowercase letters, digits, and hyphens")
    status = item.get("status")
    if status not in STATUS_VALUES:
        errors.append(f"{path}.status: expected one of {sorted(STATUS_VALUES)}")
    if "registration" in item:
        validate_symbol_record(item["registration"], f"{path}.registration", errors)
    if "handler" in item:
        validate_symbol_record(item["handler"], f"{path}.handler", errors)
    for field in ("request", "response"):
        if field in item and not isinstance(item[field], dict):
            errors.append(f"{path}.{field}: expected an object")
    if "steps" in item:
        validate_steps(item["steps"], f"{path}.steps", errors, required=status == "traced")
    for field in ("branches", "errors", "effects", "tests", "unresolved"):
        if field in item and not isinstance(item[field], list):
            errors.append(f"{path}.{field}: expected an array")
    unresolved = item.get("unresolved")
    if status in {"partial", "unresolved"} and isinstance(unresolved, list) and not unresolved:
        errors.append(f"{path}.unresolved: explain the gap and how to verify it")
    if status == "traced" and isinstance(unresolved, list) and unresolved:
        errors.append(f"{path}: status cannot be traced while unresolved gaps remain")
    refs = item.get("shared_chain_refs", [])
    if not isinstance(refs, list):
        errors.append(f"{path}.shared_chain_refs: expected an array")
    else:
        for ref_index, ref in enumerate(refs):
            if ref not in shared_ids:
                errors.append(f"{path}.shared_chain_refs[{ref_index}]: unknown shared chain {ref!r}")


def validate_data(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["$: top-level JSON value must be an object"]

    require_fields(
        data,
        (
            "repository", "scope", "revision", "generated_at", "confidence", "summary",
            "run", "architecture", "interfaces", "shared_chains", "system_sections", "risks",
            "reading_order",
        ),
        "$",
        errors,
    )
    for field in ("repository", "scope", "revision", "generated_at", "confidence", "summary"):
        if field in data and not is_nonempty_string(data[field]):
            errors.append(f"$.{field}: must be a non-empty string")
    for field in ("run", "architecture", "interfaces", "shared_chains", "system_sections", "risks", "reading_order"):
        if field in data and not isinstance(data[field], list):
            errors.append(f"$.{field}: expected an array")

    shared_ids: set[str] = set()
    shared_chains = data.get("shared_chains", [])
    if isinstance(shared_chains, list):
        for index, chain in enumerate(shared_chains):
            path = f"$.shared_chains[{index}]"
            if not isinstance(chain, dict):
                errors.append(f"{path}: expected an object")
                continue
            require_fields(chain, ("id", "title", "steps"), path, errors)
            chain_id = chain.get("id")
            if is_nonempty_string(chain_id):
                if not ID_RE.fullmatch(chain_id):
                    errors.append(f"{path}.id: use lowercase letters, digits, and hyphens")
                if chain_id in shared_ids:
                    errors.append(f"{path}.id: duplicate ID {chain_id!r}")
                shared_ids.add(chain_id)
            if "steps" in chain:
                validate_steps(chain["steps"], f"{path}.steps", errors, required=True)

    interfaces = data.get("interfaces", [])
    interface_ids: set[str] = set()
    if isinstance(interfaces, list):
        for index, item in enumerate(interfaces):
            validate_interface(item, index, shared_ids, errors)
            if isinstance(item, dict) and is_nonempty_string(item.get("id")):
                if item["id"] in interface_ids:
                    errors.append(f"$.interfaces[{index}].id: duplicate ID {item['id']!r}")
                interface_ids.add(item["id"])

    for path, value in walk_strings(data):
        if REMOTE_RE.search(value):
            errors.append(f"{path}: remote/protocol-relative URL is not allowed in the offline report")
        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(value):
                errors.append(f"{path}: possible {name}; redact the value")

    def visit_evidence(value: Any, path: str = "$") -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                child_path = f"{path}.{key}"
                if key == "evidence":
                    validate_evidence(item, child_path, errors, required=False)
                else:
                    visit_evidence(item, child_path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit_evidence(item, f"{path}[{index}]")

    visit_evidence(data)
    return errors


def validate_template(template: str) -> list[str]:
    errors: list[str] = []
    if template.count("__GUIDE_DATA__") != 1:
        errors.append("template: expected exactly one __GUIDE_DATA__ placeholder")
    forbidden_patterns = {
        "remote script": re.compile(r"(?is)<script[^>]+src\s*="),
        "external stylesheet": re.compile(r"(?is)<link[^>]+href\s*="),
        "remote iframe": re.compile(r"(?is)<iframe\b"),
        "network request API": re.compile(r"\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\("),
        "service worker": re.compile(r"\bserviceWorker\b"),
        "remote URL": REMOTE_RE,
    }
    for name, pattern in forbidden_patterns.items():
        if pattern.search(template):
            errors.append(f"template: contains forbidden {name}")
    return errors


def render(template: str, data: dict[str, Any]) -> str:
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    encoded = encoded.replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return template.replace("__GUIDE_DATA__", encoded)


def coverage(data: dict[str, Any]) -> dict[str, int]:
    interfaces = data.get("interfaces", [])
    return {
        "discovered": len(interfaces),
        "traced": sum(item.get("status") == "traced" for item in interfaces if isinstance(item, dict)),
        "partial": sum(item.get("status") == "partial" for item in interfaces if isinstance(item, dict)),
        "unresolved": sum(item.get("status") == "unresolved" for item in interfaces if isinstance(item, dict)),
    }


def main() -> int:
    args = parse_args()
    if not args.check and not args.output:
        print("error: --output is required unless --check is used", file=sys.stderr)
        return 2

    input_path = Path(args.input).expanduser().resolve()
    template_path = (
        Path(args.template).expanduser().resolve()
        if args.template
        else Path(__file__).resolve().parent.parent / "assets" / "codebase-guide.template.html"
    )
    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"error: cannot read analysis data: {error}", file=sys.stderr)
        return 2
    try:
        template = template_path.read_text(encoding="utf-8")
    except OSError as error:
        print(f"error: cannot read HTML template: {error}", file=sys.stderr)
        return 2

    errors = validate_data(data) + validate_template(template)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    counts = coverage(data)
    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(render(template, data), encoding="utf-8")
        print(f"wrote {output_path}")
    print(
        "coverage: "
        f"{counts['discovered']} discovered = {counts['traced']} traced + "
        f"{counts['partial']} partial + {counts['unresolved']} unresolved"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
