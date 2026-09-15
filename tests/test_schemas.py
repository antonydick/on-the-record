from pathlib import Path

import pytest
import yaml
from jsonschema import Draft7Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = REPO_ROOT / "schema"


def load_validator(name: str) -> Draft7Validator:
    with (SCHEMA_DIR / name).open() as f:
        return Draft7Validator(yaml.safe_load(f))


def test_episode_schema_accepts_minimal_valid_episode():
    validator = load_validator("episode.schema.yaml")
    episode = {
        "id": "fo561-smriti-mandhana",
        "title": "Smriti Mandhana On Anger, Sadness, Silence & The Emotions She Hides | FO561 Raj Shamani",
        "url": "https://www.youtube.com/watch?v=46P1rL0rzPE",
        "platform": "youtube",
        "published_date": "2026-09-12",
        "format": "video",
    }
    assert list(validator.iter_errors(episode)) == []


def test_episode_schema_rejects_missing_required_field():
    validator = load_validator("episode.schema.yaml")
    episode = {
        "id": "fo561-smriti-mandhana",
        "title": "Some title",
        "url": "https://example.com",
        "platform": "youtube",
        # missing published_date, format
    }
    errors = list(validator.iter_errors(episode))
    assert len(errors) > 0


def test_episode_schema_rejects_unknown_field():
    validator = load_validator("episode.schema.yaml")
    episode = {
        "id": "x",
        "title": "t",
        "url": "https://example.com",
        "platform": "youtube",
        "published_date": "2026-01-01",
        "format": "video",
        "unexpected_field": "nope",
    }
    errors = list(validator.iter_errors(episode))
    assert len(errors) == 1


def test_source_schema_accepts_minimal_valid_appearance():
    validator = load_validator("source.schema.yaml")
    appearance = {
        "id": "raj-shamani-fo561-smriti-mandhana",
        "person": "raj-shamani",
        "episode": "fo561-smriti-mandhana",
        "role": "host",
        "processing_status": "pending",
    }
    assert list(validator.iter_errors(appearance)) == []


def test_source_schema_rejects_old_interviewer_slug_shape():
    validator = load_validator("source.schema.yaml")
    old_shape = {
        "id": "x",
        "person": "raj-shamani",
        "interviewer_slug": "fo561-smriti-mandhana",
        "title": "t",
        "url": "https://example.com",
        "platform": "youtube",
        "published_date": "2026-01-01",
        "format": "video",
        "processing_status": "pending",
    }
    errors = list(validator.iter_errors(old_shape))
    assert len(errors) > 0


def test_source_schema_accepts_guest_role():
    validator = load_validator("source.schema.yaml")
    appearance = {
        "id": "nithin-kamath-wtf-is-venture-capital-ep9",
        "person": "nithin-kamath",
        "episode": "wtf-is-venture-capital-ep9",
        "role": "guest",
        "processing_status": "pending",
    }
    assert list(validator.iter_errors(appearance)) == []


def test_person_schema_still_accepts_existing_minimal_shape():
    validator = load_validator("person.schema.yaml")
    person = {
        "id": "nikhil-kamath",
        "name": "Nikhil Kamath",
        "credentials": "Co-founder, Zerodha and True Beacon; host, WTF is",
        "bio": "Indian entrepreneur and investor.",
    }
    assert list(validator.iter_errors(person)) == []


def test_person_schema_accepts_new_optional_fields():
    validator = load_validator("person.schema.yaml")
    person = {
        "id": "nithin-kamath",
        "name": "Nithin Kamath",
        "aliases": ["Nithin", "Nikhil's brother Nithin"],
        "credentials": "Founder and CEO, Zerodha",
        "organization": "Zerodha",
        "bio": "Indian entrepreneur.",
        "identity_confidence": "likely",
    }
    assert list(validator.iter_errors(person)) == []


def test_person_schema_rejects_bad_identity_confidence_value():
    validator = load_validator("person.schema.yaml")
    person = {
        "id": "x",
        "name": "X",
        "credentials": "c",
        "bio": "b",
        "identity_confidence": "definitely",
    }
    errors = list(validator.iter_errors(person))
    assert len(errors) == 1


def test_statement_schema_accepts_statement_without_speaker_confidence():
    validator = load_validator("statement.schema.yaml")
    statement = {
        "id": "nikhil-kamath-1",
        "person": "nikhil-kamath",
        "source": "nikhil-kamath-wtf-is-chatgpt-ep4",
        "type": "experience",
        "text": "Some text.",
        "verification": {"status": "draft"},
    }
    assert list(validator.iter_errors(statement)) == []


def test_statement_schema_accepts_speaker_confidence():
    validator = load_validator("statement.schema.yaml")
    statement = {
        "id": "nithin-kamath-1",
        "person": "nithin-kamath",
        "source": "nithin-kamath-wtf-is-venture-capital-ep9",
        "type": "experience",
        "text": "Some text.",
        "speaker_confidence": "medium",
        "verification": {"status": "draft"},
    }
    assert list(validator.iter_errors(statement)) == []


def test_statement_schema_rejects_bad_speaker_confidence_value():
    validator = load_validator("statement.schema.yaml")
    statement = {
        "id": "x",
        "person": "x",
        "source": "x",
        "type": "experience",
        "text": "t",
        "speaker_confidence": "certain",
        "verification": {"status": "draft"},
    }
    errors = list(validator.iter_errors(statement))
    assert len(errors) == 1
