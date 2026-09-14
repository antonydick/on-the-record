#!/usr/bin/env python3
"""Validate experts/*.yaml, sources/*/*/metadata.yaml, and
sources/*/*/claims.yaml against schema/*.schema.yaml, plus cross-file
rules that JSON Schema alone can't express (id uniqueness, references
that must resolve, and extra fields required once a claim is verified).

Collects every error before exiting, so a single run reports everything
wrong across the repo rather than stopping at the first problem.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = REPO_ROOT / "schema"

VERIFIED_REQUIRED_FIELDS = ["source_url", "start_timestamp", "end_timestamp", "verified_at"]


class Errors:
    def __init__(self) -> None:
        self.items: list[str] = []

    def add(self, path: Path, message: str) -> None:
        self.items.append(f"{path.relative_to(REPO_ROOT)}: {message}")

    @property
    def ok(self) -> bool:
        return not self.items


def load_yaml(path: Path, errors: Errors):
    try:
        with path.open() as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        errors.add(path, f"invalid YAML: {e}")
        return None


def load_schema(name: str) -> Draft7Validator:
    with (SCHEMA_DIR / name).open() as f:
        schema = yaml.safe_load(f)
    return Draft7Validator(schema)


def validate_against_schema(path: Path, data, validator: Draft7Validator, errors: Errors) -> None:
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path) or "<root>"
        errors.add(path, f"{loc}: {err.message}")


def main() -> int:
    errors = Errors()

    expert_validator = load_schema("expert.schema.yaml")
    source_validator = load_schema("source.schema.yaml")
    claim_validator = load_schema("claim.schema.yaml")

    expert_ids: dict[str, Path] = {}
    source_ids: dict[str, Path] = {}
    claim_ids: dict[str, Path] = {}

    # --- experts/*.yaml ---
    for path in sorted((REPO_ROOT / "experts").glob("*.yaml")):
        data = load_yaml(path, errors)
        if data is None:
            continue
        validate_against_schema(path, data, expert_validator, errors)
        expert_id = data.get("id") if isinstance(data, dict) else None
        if expert_id:
            if expert_id != path.stem:
                errors.add(path, f"id '{expert_id}' does not match filename '{path.stem}.yaml'")
            if expert_id in expert_ids:
                errors.add(path, f"duplicate expert id '{expert_id}' (also in {expert_ids[expert_id].relative_to(REPO_ROOT)})")
            else:
                expert_ids[expert_id] = path

    # --- sources/*/*/metadata.yaml ---
    source_expert: dict[str, str] = {}
    for path in sorted((REPO_ROOT / "sources").glob("*/*/metadata.yaml")):
        data = load_yaml(path, errors)
        if data is None:
            continue
        validate_against_schema(path, data, source_validator, errors)
        if not isinstance(data, dict):
            continue

        show_slug_dir, expert_dir = path.parent.parts[-2], path.parent.parts[-1]
        if data.get("show_slug") and data["show_slug"] != show_slug_dir:
            errors.add(path, f"show_slug '{data['show_slug']}' does not match directory '{show_slug_dir}'")
        if data.get("expert") and data["expert"] != expert_dir:
            errors.add(path, f"expert '{data['expert']}' does not match directory '{expert_dir}'")

        source_id = data.get("id")
        if source_id:
            if source_id in source_ids:
                errors.add(path, f"duplicate source id '{source_id}' (also in {source_ids[source_id].relative_to(REPO_ROOT)})")
            else:
                source_ids[source_id] = path
                source_expert[source_id] = data.get("expert")

        expert_ref = data.get("expert")
        if expert_ref and expert_ref not in expert_ids:
            errors.add(path, f"expert '{expert_ref}' does not match any experts/*.yaml id")

    # --- sources/*/*/claims.yaml ---
    for path in sorted((REPO_ROOT / "sources").glob("*/*/claims.yaml")):
        data = load_yaml(path, errors)
        if data is None:
            continue
        if not isinstance(data, dict) or not isinstance(data.get("claims"), list):
            errors.add(path, "must be a mapping with a top-level 'claims' list")
            continue

        for i, claim in enumerate(data["claims"]):
            claim_path_label = f"{path}[{i}]"
            validate_against_schema(path, claim, claim_validator, errors)
            if not isinstance(claim, dict):
                continue

            claim_id = claim.get("id")
            if claim_id:
                if claim_id in claim_ids:
                    errors.add(path, f"duplicate claim id '{claim_id}' (also in {claim_ids[claim_id].relative_to(REPO_ROOT)})")
                else:
                    claim_ids[claim_id] = path

            expert_ref = claim.get("expert")
            if expert_ref and expert_ref not in expert_ids:
                errors.add(path, f"claim '{claim_id}': expert '{expert_ref}' does not match any experts/*.yaml id")

            source_ref = claim.get("source")
            if source_ref and source_ref not in source_ids:
                errors.add(path, f"claim '{claim_id}': source '{source_ref}' does not match any source metadata id")

            verification = claim.get("verification") or {}
            if verification.get("status") == "verified":
                missing = [f for f in VERIFIED_REQUIRED_FIELDS if not verification.get(f)]
                if missing:
                    errors.add(
                        path,
                        f"claim '{claim_id}': status is 'verified' but missing required field(s): {', '.join(missing)}",
                    )

    if errors.ok:
        print(f"OK: {len(expert_ids)} experts, {len(source_ids)} sources, {len(claim_ids)} claims — all valid.")
        return 0

    print(f"FAILED: {len(errors.items)} error(s)\n")
    for item in errors.items:
        print(f"  - {item}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
