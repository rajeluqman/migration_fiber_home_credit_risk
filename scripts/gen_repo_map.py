#!/usr/bin/env python3
"""Repo-map generator — the NAVIGATION half of the ANTI-SHORTCUT PROTOCOL (see CLAUDE.md).

Ported from the parent repo's `scripts/gen_repo_map.py`, retargeted to this Fabric-migration
repo's real layout (notebooks/, dbt_fabric/, pipelines/, migration/, docs/ADR/) instead of the
parent repo's (glue/, dbt_home_credit/, airflow/dags/, gx/).

Design rule (unchanged): the map is a POINTER, never a substitute for reading the file. It is
100% DERIVED — purpose extracted from the file's own docstring/heading/leading comment, edges
parsed with `ast` (.py imports) and `ref()` (.sql) — never hand-authored, so it cannot silently
drift from the code. `--check` is the CI gate: regenerate in memory, diff against the committed
REPO_MAP.md, fail if stale.

Stdlib only ($0, no deps). Exit 0 = map is fresh. Exit 1 (with --check) = stale, regenerate.

Run:  python scripts/gen_repo_map.py            # (re)write architecture/REPO_MAP.md
      python scripts/gen_repo_map.py --check    # CI gate: fail if committed map is stale
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MAP_PATH = REPO / "architecture" / "REPO_MAP.md"

EXCLUDE = {
    ".gitignore", ".env.example", "dbt_fabric/profiles.yml",
    ".claude/settings.json", "architecture/REPO_MAP.md",
}
EXCLUDE_PREFIX = (".github/",)

ROLE_LABELS = [
    ("adr", "Architecture Decision Records"),
    ("doc", "Top-level docs"),
    ("dbt:staging", "dbt — staging"),
    ("dbt:intermediate", "dbt — intermediate"),
    ("dbt:mart", "dbt — mart"),
    ("dbt:snapshot", "dbt — snapshots"),
    ("dbt:test", "dbt — tests"),
    ("dbt:macro", "dbt — macros"),
    ("dbt:model", "dbt — other"),
    ("notebook", "Fabric Spark Notebooks"),
    ("pipeline", "Data Factory pipelines"),
    ("migration", "Migration artefacts (benchmarks, validation, staging)"),
    ("test", "Tests / contracts"),
    ("hook", "Governance hooks"),
    ("agent", "Cabinet agents"),
    ("learning", "Learning"),
    ("config", "Config"),
    ("other", "Other"),
]

REF_RE = re.compile(r"\bref\(\s*['\"]([a-zA-Z0-9_]+)['\"]")


def working_set() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout
    files = []
    for raw in out.splitlines():
        rel = raw.strip()
        if not rel or rel in EXCLUDE or rel.startswith(EXCLUDE_PREFIX):
            continue
        if (REPO / rel).is_file():
            files.append(Path(rel))
    return sorted(files, key=lambda p: p.as_posix())


def role_of(rel: str) -> str:
    if rel.startswith("docs/ADR/"):
        return "adr"
    if rel.startswith("docs/"):
        return "doc"
    if rel.startswith("dbt_fabric/models/staging/"):
        return "dbt:staging"
    if rel.startswith("dbt_fabric/models/intermediate/"):
        return "dbt:intermediate"
    if rel.startswith("dbt_fabric/models/mart/"):
        return "dbt:mart"
    if rel.startswith("dbt_fabric/snapshots/"):
        return "dbt:snapshot"
    if rel.startswith("dbt_fabric/tests/"):
        return "dbt:test"
    if rel.startswith("dbt_fabric/macros/"):
        return "dbt:macro"
    if rel.startswith("dbt_fabric/"):
        return "dbt:model"
    if rel.startswith("notebooks/"):
        return "notebook"
    if rel.startswith("pipelines/"):
        return "pipeline"
    if rel.startswith("migration/"):
        return "migration"
    if rel.startswith("tests/"):
        return "test"
    if rel.startswith(".claude/hooks/"):
        return "hook"
    if rel.startswith(".claude/agents/"):
        return "agent"
    if rel.startswith("learning/"):
        return "learning"
    suf = Path(rel).suffix
    if suf == ".md":
        return "doc"
    if suf in (".yml", ".yaml", ".json"):
        return "config"
    if suf == ".sh":
        return "config"
    return "other"


def _clean(text: str, limit: int = 110) -> str:
    text = text.replace("`", "").replace("|", "/")
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def purpose_of(path: Path) -> str:
    suf = path.suffix
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return "—"

    if suf == ".py":
        try:
            doc = ast.get_docstring(ast.parse(text))
        except SyntaxError:
            doc = None
        if doc:
            return _clean(doc.strip().splitlines()[0])
        return "(no module docstring)"

    if suf == ".md":
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("#"):
                return _clean(s.lstrip("#").strip())
            if s and not s.startswith(("<!--", ">", "---")):
                return _clean(s)
        return "—"

    if suf == ".sql":
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("--"):
                return _clean(s.lstrip("-").strip())
            if s:
                break
        return "(no leading -- comment)"

    if suf in (".yml", ".yaml"):
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("#"):
                return _clean(s.lstrip("#").strip())
            if s:
                break
        return "—"

    return "—"


def py_deps(path: Path, local_py: dict[str, str]) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, OSError, UnicodeDecodeError):
        return set()
    deps: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                top = n.name.split(".")[0]
                if top in local_py:
                    deps.add(local_py[top])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                top = node.module.split(".")[0]
                if top in local_py:
                    deps.add(local_py[top])
    return deps


def sql_deps(path: Path, local_sql: dict[str, str]) -> set[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return set()
    deps: set[str] = set()
    for name in REF_RE.findall(text):
        if name in local_sql:
            deps.add(local_sql[name])
    return deps


def build_edges(files: list[Path]) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    local_py = {p.stem: p.as_posix() for p in files if p.suffix == ".py"}
    local_sql = {p.stem: p.as_posix() for p in files if p.suffix == ".sql"}
    uses: dict[str, set[str]] = {p.as_posix(): set() for p in files}
    for p in files:
        rel = p.as_posix()
        if p.suffix == ".py":
            uses[rel] |= py_deps(p, local_py)
        elif p.suffix == ".sql":
            uses[rel] |= sql_deps(p, local_sql)
        uses[rel].discard(rel)
    used_by: dict[str, set[str]] = {p.as_posix(): set() for p in files}
    for rel, targets in uses.items():
        for t in targets:
            used_by.setdefault(t, set()).add(rel)
    return uses, used_by


def _names(rels: set[str]) -> str:
    return ", ".join(sorted(Path(r).name for r in rels)) if rels else "—"


def render(files: list[Path]) -> str:
    uses, used_by = build_edges(files)
    by_role: dict[str, list[Path]] = {}
    for p in files:
        by_role.setdefault(role_of(p.as_posix()), []).append(p)

    lines: list[str] = [
        "# REPO_MAP — generated navigation index",
        "",
        "> **GENERATED — do not hand-edit.** `python scripts/gen_repo_map.py` rebuilds it from",
        "> ground truth; CI runs `--check` and fails if this file is stale. Purpose is extracted",
        "> from each file's own docstring / first heading / leading comment; *Uses* and *Used by*",
        "> are parsed (`ast` for Python, `ref()` for dbt), never authored.",
        ">",
        "> **This is a pointer, not a cache.** It tells you which file to open — then READ THAT",
        "> FILE FRESH before you edit or assert about it (ANTI-SHORTCUT PROTOCOL, CLAUDE.md).",
        "",
        f"**{len(files)} files mapped.**",
        "",
    ]

    for role, label in ROLE_LABELS:
        group = sorted(by_role.get(role, []), key=lambda p: p.as_posix())
        if not group:
            continue
        lines += [f"## {label}", "", "| File | Purpose | Uses | Used by |", "|------|---------|------|---------|"]
        for p in group:
            rel = p.as_posix()
            lines.append(
                f"| `{rel}` | {purpose_of(p)} | {_names(uses.get(rel, set()))} "
                f"| {_names(used_by.get(rel, set()))} |"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str]) -> int:
    files = working_set()
    content = render(files)

    if "--check" in argv[1:]:
        if not MAP_PATH.exists():
            print("REPO-MAP: architecture/REPO_MAP.md missing — run python scripts/gen_repo_map.py")
            return 1
        current = MAP_PATH.read_text(encoding="utf-8")
        if current != content:
            print("REPO-MAP: STALE — committed index does not match ground truth.")
            print("Regenerate: python scripts/gen_repo_map.py")
            return 1
        print(f"REPO-MAP: OK — {len(files)} files, index matches ground truth.")
        return 0

    MAP_PATH.write_text(content, encoding="utf-8")
    print(f"REPO-MAP: wrote {MAP_PATH.relative_to(REPO)} — {len(files)} files mapped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
