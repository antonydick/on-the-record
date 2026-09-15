#!/usr/bin/env python3
"""Regenerate profiles/<person-id>.md — a derived, categorized index of
each person's `verified` statements, grouped by topic and type. This is
a discovery/organization aid only: every line points back to a
statement id and its source appearance, never asserted as freestanding
fact. See SKILL.md's "Profiles are an index, not a source" section for
how an agent should use this file.

Deterministic and fully regeneratable from people/, sources/ — never
hand-edit an output file, and never let a stale one survive after the
statements it was built from change.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

ENTITY_TOKEN_RE = re.compile(r"^[A-Z][a-zA-Z&\.]*$")

TYPE_CATEGORY = {
    "experience": "Experiences & stories",
    "belief": "Beliefs & principles",
    "recommendation": "Opinions",
    "observation": "Beliefs & principles",
    "mechanism": "Beliefs & principles",
    "evidence": "Opinions",
    "qualification": "Opinions",
    "example": "Experiences & stories",
    "assertion": "Background",
}


def load_yaml(path: Path):
    with path.open() as f:
        return yaml.safe_load(f)


def filter_verified(statements: list[dict]) -> list[dict]:
    return [s for s in statements if (s.get("verification") or {}).get("status") == "verified"]


def group_by_topic(statements: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for statement in statements:
        topic = statement.get("topic") or "uncategorized"
        grouped[topic].append(statement)
    return dict(grouped)


def recurring_topics(grouped: dict[str, list[dict]]) -> set[str]:
    recurring = set()
    for topic, statements in grouped.items():
        sources = {s.get("source") for s in statements}
        if len(sources) >= 2:
            recurring.add(topic)
    return recurring


def evolving_topics(grouped: dict[str, list[dict]], episode_dates: dict[str, str]) -> dict[str, list[dict]]:
    """Return {topic: statements sorted chronologically} for topics where
    at least two statements share a topic but their appearances have
    different published dates. Ordering only — this says nothing about
    *why* anything differs; render callers must use cautious language
    ("later stated", never "changed his mind") per SKILL.md."""
    evolving: dict[str, list[dict]] = {}
    for topic, statements in grouped.items():
        dated = [(episode_dates.get(s.get("source")), s) for s in statements]
        dated = [(d, s) for d, s in dated if d]
        distinct_dates = {d for d, _ in dated}
        if len(distinct_dates) >= 2:
            evolving[topic] = [s for _, s in sorted(dated, key=lambda pair: pair[0])]
    return evolving


def extract_entity_mentions(text: str) -> list[str]:
    """Heuristically extract capitalized 2-4 word phrases (candidate
    person/company/book/event mentions) from statement text. Coarse on
    purpose — this feeds a discovery aid, not a citation, and false
    positives are far less harmful here than in guest-name resolution."""
    mentions: list[str] = []
    words = text.replace(",", " , ").replace(".", " . ").split()
    i = 0
    while i < len(words):
        if ENTITY_TOKEN_RE.match(words[i]):
            j = i + 1
            while j < len(words) and j < i + 4 and ENTITY_TOKEN_RE.match(words[j]):
                j += 1
            if j - i >= 2:
                mentions.append(" ".join(words[i:j]))
                i = j
                continue
        i += 1
    return mentions


def recurring_references(statements: list[dict]) -> dict[str, set[str]]:
    """Return {entity phrase: {statement ids mentioning it}} for phrases
    that appear in statements from at least two different appearances."""
    mentions_by_entity: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for statement in statements:
        for entity in set(extract_entity_mentions(statement.get("text", ""))):
            mentions_by_entity[entity].add((statement["id"], statement.get("source", "")))
    recurring: dict[str, set[str]] = {}
    for entity, pairs in mentions_by_entity.items():
        sources = {source for _, source in pairs}
        if len(sources) >= 2:
            recurring[entity] = {stmt_id for stmt_id, _ in pairs}
    return recurring


def render_profile_markdown(
    person: dict,
    verified_statements: list[dict],
    episode_titles: dict[str, str],
    episode_dates: dict[str, str],
) -> str:
    lines = [f'# {person["name"]}', ""]
    lines.append(
        "_Generated automatically from this repo's `verified` statements only. "
        "Every line below is a pointer to a statement id — never read a line "
        "here as an established fact on its own; follow it back to the "
        "statement and its source. See SKILL.md's \"Profiles are an index, "
        "not a source\" section._"
    )
    lines.append("")

    if not verified_statements:
        lines.append("_No verified statements yet for this person._")
        lines.append("")
        return "\n".join(lines)

    grouped_by_type: dict[str, list[dict]] = defaultdict(list)
    for statement in verified_statements:
        category = TYPE_CATEGORY.get(statement.get("type"), "Background")
        grouped_by_type[category].append(statement)

    for category in [
        "Background",
        "Beliefs & principles",
        "Experiences & stories",
        "Opinions",
    ]:
        statements = grouped_by_type.get(category)
        if not statements:
            continue
        lines.append(f"## {category}")
        lines.append("")
        for statement in statements:
            episode_title = episode_titles.get(statement.get("source"), statement.get("source"))
            lines.append(f'- {statement["text"]} — see `{statement["id"]}` ({episode_title})')
        lines.append("")

    topic_groups = group_by_topic(verified_statements)
    recurring = recurring_topics(topic_groups)
    if recurring:
        lines.append("## Recurring ideas")
        lines.append("")
        for topic in sorted(recurring):
            statement_ids = ", ".join(f'`{s["id"]}`' for s in topic_groups[topic])
            lines.append(f"- **{topic}**: {statement_ids}")
        lines.append("")

    evolving = evolving_topics(topic_groups, episode_dates)
    if evolving:
        lines.append("## Evolution")
        lines.append("")
        lines.append(
            "_Chronological ordering only — the sources do not establish "
            "**why** anything differs unless a statement itself says so._"
        )
        lines.append("")
        for topic, statements in sorted(evolving.items()):
            lines.append(f"**{topic}**")
            first = statements[0]
            first_episode = episode_titles.get(first.get("source"), first.get("source"))
            first_date = episode_dates.get(first.get("source"), "")
            lines.append(f'- `{first["id"]}` ({first_episode}, {first_date}): {first["text"]}')
            for statement in statements[1:]:
                episode_title = episode_titles.get(statement.get("source"), statement.get("source"))
                date = episode_dates.get(statement.get("source"), "")
                lines.append(
                    f'- Later stated in `{statement["id"]}` ({episode_title}, {date}): {statement["text"]}'
                )
            lines.append("")

    references = recurring_references(verified_statements)
    if references:
        lines.append("## Relationships & references")
        lines.append("")
        for entity in sorted(references):
            statement_ids = ", ".join(f"`{sid}`" for sid in sorted(references[entity]))
            lines.append(f"- **{entity}**: {statement_ids}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    people_dir = REPO_ROOT / "people"
    sources_dir = REPO_ROOT / "sources"
    profiles_dir = REPO_ROOT / "profiles"
    profiles_dir.mkdir(exist_ok=True)

    episode_titles: dict[str, str] = {}
    episode_dates: dict[str, str] = {}
    for path in sorted((sources_dir / "episodes").glob("*.yaml")):
        data = load_yaml(path) or {}
        if data.get("id") and data.get("title"):
            episode_titles[data["id"]] = data["title"]
        if data.get("id") and data.get("published_date"):
            episode_dates[data["id"]] = data["published_date"]

    statements_by_person: dict[str, list[dict]] = defaultdict(list)
    for path in sorted(sources_dir.glob("*/*/statements.yaml")):
        data = load_yaml(path) or {}
        for statement in data.get("statements") or []:
            person_id = statement.get("person")
            if person_id:
                statements_by_person[person_id].append(statement)

    for person_path in sorted(people_dir.glob("*.yaml")):
        person = load_yaml(person_path) or {}
        person_id = person.get("id")
        if not person_id:
            continue
        verified = filter_verified(statements_by_person.get(person_id, []))
        markdown = render_profile_markdown(person, verified, episode_titles, episode_dates)
        (profiles_dir / f"{person_id}.md").write_text(markdown)

    print(f"Wrote {len(list(people_dir.glob('*.yaml')))} profile(s) to profiles/.")


if __name__ == "__main__":
    main()
