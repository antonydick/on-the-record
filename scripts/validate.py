#!/usr/bin/env python3
"""Validate people/*.yaml, sources/episodes/*.yaml,
sources/*/*/metadata.yaml, and sources/*/*/statements.yaml against
schema/*.schema.yaml, plus cross-file rules that JSON Schema alone
can't express (id uniqueness, references that must resolve, and extra
fields required once a statement is verified).

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
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.items: list[str] = []

    def add(self, path: Path, message: str) -> None:
        self.items.append(f"{path.relative_to(self.repo_root)}: {message}")

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


def check_episode_data(data: dict, filename_stem: str) -> list[str]:
    """Structural error messages for one sources/episodes/<id>.yaml record."""
    messages: list[str] = []
    if not isinstance(data, dict):
        return messages
    episode_id = data.get("id")
    if episode_id and episode_id != filename_stem:
        messages.append(f"id '{episode_id}' does not match filename '{filename_stem}.yaml'")
    return messages


def check_appearance_against_dirs(data: dict, person_dir: str, episode_dir: str) -> list[str]:
    """Structural error messages for one appearance (source) record, given
    the <person-slug> and <episode-slug> directory segments it lives under."""
    messages: list[str] = []
    if not isinstance(data, dict):
        return messages
    if data.get("person") and data["person"] != person_dir:
        messages.append(f"person '{data['person']}' does not match directory '{person_dir}'")
    if data.get("episode") and data["episode"] != episode_dir:
        messages.append(f"episode '{data['episode']}' does not match directory '{episode_dir}'")
    return messages


def main(repo_root: Path | None = None) -> int:
    repo_root = repo_root or REPO_ROOT
    errors = Errors(repo_root)

    person_validator = load_schema("person.schema.yaml")
    episode_validator = load_schema("episode.schema.yaml")
    source_validator = load_schema("source.schema.yaml")
    statement_validator = load_schema("statement.schema.yaml")

    person_ids: dict[str, Path] = {}
    episode_ids: dict[str, Path] = {}
    source_ids: dict[str, Path] = {}
    statement_ids: dict[str, Path] = {}

    # --- people/*.yaml ---
    for path in sorted((repo_root / "people").glob("*.yaml")):
        data = load_yaml(path, errors)
        if data is None:
            continue
        validate_against_schema(path, data, person_validator, errors)
        person_id = data.get("id") if isinstance(data, dict) else None
        if person_id:
            if person_id != path.stem:
                errors.add(path, f"id '{person_id}' does not match filename '{path.stem}.yaml'")
            if person_id in person_ids:
                errors.add(path, f"duplicate person id '{person_id}' (also in {person_ids[person_id].relative_to(repo_root)})")
            else:
                person_ids[person_id] = path

    # --- sources/episodes/*.yaml ---
    episodes_dir = repo_root / "sources" / "episodes"
    if episodes_dir.is_dir():
        for path in sorted(episodes_dir.glob("*.yaml")):
            data = load_yaml(path, errors)
            if data is None:
                continue
            validate_against_schema(path, data, episode_validator, errors)
            for message in check_episode_data(data, path.stem):
                errors.add(path, message)
            episode_id = data.get("id") if isinstance(data, dict) else None
            if episode_id:
                if episode_id in episode_ids:
                    errors.add(path, f"duplicate episode id '{episode_id}' (also in {episode_ids[episode_id].relative_to(repo_root)})")
                else:
                    episode_ids[episode_id] = path

    # --- sources/<person>/<episode>/metadata.yaml ---
    for path in sorted((repo_root / "sources").glob("*/*/metadata.yaml")):
        data = load_yaml(path, errors)
        if data is None:
            continue
        validate_against_schema(path, data, source_validator, errors)
        if not isinstance(data, dict):
            continue

        person_dir, episode_dir = path.parent.parts[-2], path.parent.parts[-1]
        for message in check_appearance_against_dirs(data, person_dir, episode_dir):
            errors.add(path, message)

        source_id = data.get("id")
        if source_id:
            if source_id in source_ids:
                errors.add(path, f"duplicate source id '{source_id}' (also in {source_ids[source_id].relative_to(repo_root)})")
            else:
                source_ids[source_id] = path

        person_ref = data.get("person")
        if person_ref and person_ref not in person_ids:
            errors.add(path, f"person '{person_ref}' does not match any people/*.yaml id")

        episode_ref = data.get("episode")
        if episode_ref and episode_ref not in episode_ids:
            errors.add(path, f"episode '{episode_ref}' does not match any sources/episodes/*.yaml id")

    # --- sources/<person>/<episode>/statements.yaml ---
    for path in sorted((repo_root / "sources").glob("*/*/statements.yaml")):
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
                    errors.add(path, f"duplicate statement id '{statement_id}' (also in {statement_ids[statement_id].relative_to(repo_root)})")
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
        print(
            f"OK: {len(person_ids)} people, {len(episode_ids)} episodes, "
            f"{len(source_ids)} appearances, {len(statement_ids)} statements — all valid."
        )
        return 0

    print(f"FAILED: {len(errors.items)} error(s)\n")
    for item in errors.items:
        print(f"  - {item}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
