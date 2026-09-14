#!/usr/bin/env python3
"""Regenerate STATS.md from the repo's own YAML content — counts of
people, sources, and statements by verification status. No external
telemetry; purely computed from people/, sources/. Deterministic: no
timestamps, so it only produces a diff when the underlying content
actually changes.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

STATEMENT_STATUSES = ["draft", "unverified", "reviewed", "verified", "rejected"]
SOURCE_STATUSES = ["pending", "extracted", "in_review", "complete"]


def load_yaml(path: Path):
    with path.open() as f:
        return yaml.safe_load(f)


def main() -> None:
    person_paths = sorted((REPO_ROOT / "people").glob("*.yaml"))

    source_paths = sorted((REPO_ROOT / "sources").glob("*/*/metadata.yaml"))
    source_status_counts: Counter[str] = Counter()
    for path in source_paths:
        data = load_yaml(path) or {}
        source_status_counts[data.get("processing_status", "unknown")] += 1

    statement_paths = sorted((REPO_ROOT / "sources").glob("*/*/statements.yaml"))
    statement_status_counts: Counter[str] = Counter()
    total_statements = 0
    for path in statement_paths:
        data = load_yaml(path) or {}
        for statement in data.get("statements", []) or []:
            total_statements += 1
            status = (statement.get("verification") or {}).get("status", "unknown")
            statement_status_counts[status] += 1

    lines = [
        "# Repository Statistics",
        "",
        "_Generated automatically from repository content by CI. Do not edit",
        "by hand — changes will be overwritten on the next push to main._",
        "",
        "## People",
        "",
        f"- Total: {len(person_paths)}",
        "",
        "## Sources (appearances)",
        "",
        f"- Total: {len(source_paths)}",
    ]
    for status in SOURCE_STATUSES:
        lines.append(f"  - {status}: {source_status_counts.get(status, 0)}")
    extra_source_statuses = sorted(set(source_status_counts) - set(SOURCE_STATUSES))
    for status in extra_source_statuses:
        lines.append(f"  - {status}: {source_status_counts[status]}")

    lines += [
        "",
        "## Statements",
        "",
        f"- Total: {total_statements}",
    ]
    for status in STATEMENT_STATUSES:
        lines.append(f"  - {status}: {statement_status_counts.get(status, 0)}")
    extra_statement_statuses = sorted(set(statement_status_counts) - set(STATEMENT_STATUSES))
    for status in extra_statement_statuses:
        lines.append(f"  - {status}: {statement_status_counts[status]}")

    lines.append("")

    (REPO_ROOT / "STATS.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
