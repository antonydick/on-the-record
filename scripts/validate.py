#!/usr/bin/env python3
"""Validate people/*.yaml, sources/*/*/metadata.yaml, and
sources/*/*/statements.yaml against schema/*.schema.yaml, plus
cross-file rules that JSON Schema alone can't express (id uniqueness,
references that must resolve, and extra fields required once a
statement is verified).

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

    person_validator = load_schema("person.schema.yaml")
    source_validator = load_schema("source.schema.yaml")
    statement_validator = load_schema("statement.schema.yaml")

    person_ids: dict[str, Path] = {}
    source_ids: dict[str, Path] = {}
    statement_ids: dict[str, Path] = {}

    # --- people/*.yaml ---
    for path in sorted((REPO_ROOT / "people").glob("*.yaml")):
        data = load_yaml(path, errors)
        if data is None:
            continue
        validate_against_schema(path, data, person_validator, errors)
        person_id = data.get("id") if isinstance(data, dict) else None
        if person_id:
            if person_id != path.stem:
                errors.add(path, f"id '{person_id}' does not match filename '{path.stem}.yaml'")
            if person_id in person_ids:
                errors.add(path, f"duplicate person id '{person_id}' (also in {person_ids[person_id].relative_to(REPO_ROOT)})")
            else:
                person_ids[person_id] = path

    # --- sources/<person>/<interviewer>/metadata.yaml ---
    for path in sorted((REPO_ROOT / "sources").glob("*/*/metadata.yaml")):
        data = load_yaml(path, errors)
        if data is None:
            continue
        validate_against_schema(path, data, source_validator, errors)
        if not isinstance(data, dict):
            continue

        person_dir, interviewer_dir = path.parent.parts[-2], path.parent.parts[-1]
        if data.get("person") and data["person"] != person_dir:
            errors.add(path, f"person '{data['person']}' does not match directory '{person_dir}'")
        if data.get("interviewer_slug") and data["interviewer_slug"] != interviewer_dir:
            errors.add(path, f"interviewer_slug '{data['interviewer_slug']}' does not match directory '{interviewer_dir}'")

        source_id = data.get("id")
        if source_id:
            if source_id in source_ids:
                errors.add(path, f"duplicate source id '{source_id}' (also in {source_ids[source_id].relative_to(REPO_ROOT)})")
            else:
                source_ids[source_id] = path

        person_ref = data.get("person")
        if person_ref and person_ref not in person_ids:
            errors.add(path, f"person '{person_ref}' does not match any people/*.yaml id")

    # --- sources/<person>/<interviewer>/statements.yaml ---
    for path in sorted((REPO_ROOT / "sources").glob("*/*/statements.yaml")):
        data = load_yaml(path, errors)
        if data is None:
            continue
        if not isinstance(data, dict) or not isinstance(data.get("statements"), list):
            errors.add(path, "must be a mapping with a top-level 'statements' list")
            continue

        for statement in data["statements"]:
            validate_against_schema(path, statement, statement_validator, errors)
            if not isinstance(statement, dict):
                continue

            statement_id = statement.get("id")
            if statement_id:
                if statement_id in statement_ids:
                    errors.add(path, f"duplicate statement id '{statement_id}' (also in {statement_ids[statement_id].relative_to(REPO_ROOT)})")
                else:
                    statement_ids[statement_id] = path

            person_ref = statement.get("person")
            if person_ref and person_ref not in person_ids:
                errors.add(path, f"statement '{statement_id}': person '{person_ref}' does not match any people/*.yaml id")

            source_ref = statement.get("source")
            if source_ref and source_ref not in source_ids:
                errors.add(path, f"statement '{statement_id}': source '{source_ref}' does not match any source metadata id")

            verification = statement.get("verification") or {}
            if verification.get("status") == "verified":
                missing = [f for f in VERIFIED_REQUIRED_FIELDS if not verification.get(f)]
                if missing:
                    errors.add(
                        path,
                        f"statement '{statement_id}': status is 'verified' but missing required field(s): {', '.join(missing)}",
                    )

    if errors.ok:
        print(f"OK: {len(person_ids)} people, {len(source_ids)} sources, {len(statement_ids)} statements — all valid.")
        return 0

    print(f"FAILED: {len(errors.items)} error(s)\n")
    for item in errors.items:
        print(f"  - {item}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
