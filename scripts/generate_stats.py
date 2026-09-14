#!/usr/bin/env python3
"""Regenerate STATS.md from the repo's own YAML content — counts of
experts, sources, and claims by verification status. No external
telemetry; purely computed from experts/, sources/. Deterministic: no
timestamps, so it only produces a diff when the underlying content
actually changes.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

CLAIM_STATUSES = ["draft", "unverified", "reviewed", "verified", "rejected"]
SOURCE_STATUSES = ["pending", "extracted", "in_review", "complete"]


def load_yaml(path: Path):
    with path.open() as f:
        return yaml.safe_load(f)


def main() -> None:
    expert_paths = sorted((REPO_ROOT / "experts").glob("*.yaml"))

    source_paths = sorted((REPO_ROOT / "sources").glob("*/*/metadata.yaml"))
    source_status_counts: Counter[str] = Counter()
    for path in source_paths:
        data = load_yaml(path) or {}
        source_status_counts[data.get("processing_status", "unknown")] += 1

    claim_paths = sorted((REPO_ROOT / "sources").glob("*/*/claims.yaml"))
    claim_status_counts: Counter[str] = Counter()
    total_claims = 0
    for path in claim_paths:
        data = load_yaml(path) or {}
        for claim in data.get("claims", []) or []:
            total_claims += 1
            status = (claim.get("verification") or {}).get("status", "unknown")
            claim_status_counts[status] += 1

    lines = [
        "# Repository Statistics",
        "",
        "_Generated automatically from repository content by CI. Do not edit",
        "by hand — changes will be overwritten on the next push to main._",
        "",
        "## Experts",
        "",
        f"- Total: {len(expert_paths)}",
        "",
        "## Sources (interviews)",
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
        "## Claims",
        "",
        f"- Total: {total_claims}",
    ]
    for status in CLAIM_STATUSES:
        lines.append(f"  - {status}: {claim_status_counts.get(status, 0)}")
    extra_claim_statuses = sorted(set(claim_status_counts) - set(CLAIM_STATUSES))
    for status in extra_claim_statuses:
        lines.append(f"  - {status}: {claim_status_counts[status]}")

    lines.append("")

    (REPO_ROOT / "STATS.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
