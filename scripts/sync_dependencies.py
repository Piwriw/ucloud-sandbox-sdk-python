#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        print("Python 3.11+ or the 'tomli' package is required.", file=sys.stderr)
        raise SystemExit(1)


REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_PYPROJECT = REPO_ROOT / "pyproject.toml"

UPSTREAM_PYPROJECTS = [
    ("e2b", REPO_ROOT / "upstream/e2b/packages/python-sdk/pyproject.toml"),
    (
        "code-interpreter",
        REPO_ROOT / "upstream/e2b/packages/code-interpreter-python/pyproject.toml",
    ),
    (
        "desktop",
        REPO_ROOT / "upstream/e2b/packages/desktop-python/pyproject.toml",
    ),
]

SKIP_RUNTIME_DEPENDENCIES = {
    "e2b",
}

# Upstream dependency groups that only serve E2B's own code generation
# toolchain; this project never runs `make generate-*`.
SKIP_DEV_GROUPS = {
    "codegen",
}

RUNTIME_OVERRIDES = {
    "python": "^3.10",
    "httpx": ">=0.27.0,<1.0.0",
    "attrs": ">=23.2.0",
    "pillow": "^12.0.0",
}

DEV_OVERRIDES = {
    "pytest": "^9.0.3",
    "pytest-asyncio": "^1.3.0",
    "pytest-xdist": "^3.6.1",
    "ruff": "^0.15.0",
}

RUNTIME_ORDER = [
    "python",
    "python-dateutil",
    "wcmatch",
    "protobuf-py",
    "connectrpc",
    "pyqwest",
    "httpx",
    "h2",
    "attrs",
    "packaging",
    "typing-extensions",
    "dockerfile-parse",
    "rich",
    "requests",
    "pillow",
]

DEV_ORDER = [
    "pytest",
    "pytest-xdist",
    "python-dotenv",
    "pytest-dotenv",
    "pytest-asyncio",
    "ruff",
    "pytest-timeout",
    "ty",
    "matplotlib",
]


def load_pyproject(path: Path) -> dict[str, Any]:
    if not path.exists():
        print(f"Upstream pyproject not found: {path.relative_to(REPO_ROOT)}", file=sys.stderr)
        raise SystemExit(1)

    with path.open("rb") as file:
        return tomllib.load(file)


# PEP 508 requirement, e.g. `wcmatch>=10.1,<12` or `protobuf-py>=0.1.1,<0.2`.
# Upstream migrated to uv/PEP 621, so dependencies arrive as strings rather than
# the `name = constraint` tables Poetry uses.
REQUIREMENT_PATTERN = re.compile(
    r"""
    ^\s*
    (?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)
    (?:\[(?P<extras>[^\]]*)\])?
    \s*
    (?P<constraint>[^;]*?)
    \s*
    (?:;(?P<marker>.*))?
    $
    """,
    re.VERBOSE,
)


def parse_requirement(source_name: str, requirement: str) -> tuple[str, str]:
    match = REQUIREMENT_PATTERN.match(requirement)
    if not match:
        print(
            f"Cannot parse {source_name} requirement: {requirement!r}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    # Poetry needs a table instead of a plain version string for these, so fail
    # loudly rather than silently dropping them.
    for field in ("extras", "marker"):
        if match.group(field):
            print(
                f"Unsupported {field} in {source_name} requirement: {requirement!r}",
                file=sys.stderr,
            )
            raise SystemExit(1)

    return match.group("name"), match.group("constraint") or "*"


def project_dependencies(
    source_name: str, pyproject: dict[str, Any]
) -> dict[str, Any]:
    project = pyproject.get("project", {})
    dependencies = {
        name: constraint
        for name, constraint in (
            parse_requirement(source_name, requirement)
            for requirement in project.get("dependencies", [])
        )
    }

    requires_python = project.get("requires-python")
    if requires_python:
        dependencies["python"] = requires_python

    return dependencies


def project_dev_dependencies(
    source_name: str, pyproject: dict[str, Any]
) -> dict[str, Any]:
    groups = pyproject.get("dependency-groups", {})
    return {
        name: constraint
        for group, requirements in groups.items()
        if group not in SKIP_DEV_GROUPS
        for name, constraint in (
            parse_requirement(source_name, requirement) for requirement in requirements
        )
    }


def merge_dependencies(
    sections: list[tuple[str, dict[str, Any]]],
    *,
    skip: set[str] | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    skip = skip or set()
    overrides = overrides or {}
    merged: dict[str, Any] = {}
    conflicts: dict[str, list[tuple[str, Any]]] = {}

    for source_name, dependencies in sections:
        for name, value in dependencies.items():
            if name in skip:
                continue

            value = overrides.get(name, value)
            if name not in merged:
                merged[name] = value
                continue

            if merged[name] == value:
                continue

            conflicts.setdefault(name, []).append((source_name, value))

    unresolved = [name for name in conflicts if name not in overrides]
    if unresolved:
        for name in unresolved:
            print(f"Unresolved dependency conflict for {name!r}:", file=sys.stderr)
            print(f"  selected: {merged[name]!r}", file=sys.stderr)
            for source_name, value in conflicts[name]:
                print(f"  {source_name}: {value!r}", file=sys.stderr)
        raise SystemExit(1)

    for name, value in overrides.items():
        if name in merged:
            merged[name] = value

    return merged


def ordered_items(dependencies: dict[str, Any], order: list[str]) -> list[tuple[str, Any]]:
    ordered = [(name, dependencies[name]) for name in order if name in dependencies]
    ordered_names = {name for name, _ in ordered}
    ordered.extend(
        (name, dependencies[name])
        for name in sorted(dependencies)
        if name not in ordered_names
    )
    return ordered


def format_value(value: Any) -> str:
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "[" + ", ".join(format_value(item) for item in value) + "]"
    if isinstance(value, dict):
        parts = [f"{key} = {format_value(item)}" for key, item in value.items()]
        return "{ " + ", ".join(parts) + " }"
    return str(value)


def render_dependencies(dependencies: dict[str, Any], order: list[str]) -> str:
    return "\n".join(
        f"{name} = {format_value(value)}" for name, value in ordered_items(dependencies, order)
    )


def replace_section(text: str, header: str, body: str) -> str:
    escaped_header = re.escape(header)
    pattern = re.compile(rf"(?ms)^{escaped_header}\n.*?(?=^\[|\Z)")
    replacement = f"{header}\n{body}\n\n"

    text, count = pattern.subn(replacement, text)
    if count != 1:
        print(f"Expected exactly one {header} section, found {count}.", file=sys.stderr)
        raise SystemExit(1)

    return text


def main() -> int:
    upstream = [
        (source_name, load_pyproject(path))
        for source_name, path in UPSTREAM_PYPROJECTS
    ]

    runtime_dependencies = merge_dependencies(
        [
            (source_name, project_dependencies(source_name, pyproject))
            for source_name, pyproject in upstream
        ],
        skip=SKIP_RUNTIME_DEPENDENCIES,
        overrides=RUNTIME_OVERRIDES,
    )
    dev_dependencies = merge_dependencies(
        [
            (source_name, project_dev_dependencies(source_name, pyproject))
            for source_name, pyproject in upstream
        ],
        overrides=DEV_OVERRIDES,
    )

    pyproject_text = ROOT_PYPROJECT.read_text()
    pyproject_text = replace_section(
        pyproject_text,
        "[tool.poetry.dependencies]",
        render_dependencies(runtime_dependencies, RUNTIME_ORDER),
    )
    pyproject_text = replace_section(
        pyproject_text,
        "[tool.poetry.group.dev.dependencies]",
        render_dependencies(dev_dependencies, DEV_ORDER),
    )
    ROOT_PYPROJECT.write_text(pyproject_text)

    print("Synced dependencies into pyproject.toml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
