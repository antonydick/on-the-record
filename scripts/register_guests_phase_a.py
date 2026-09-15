#!/usr/bin/env python3
"""Phase A guest discovery (see docs/superpowers/specs/2026-09-15-guest-profiles-design.md).

Sweeps every episode's title and every existing statement's `notes`
field for candidate guest names, resolves each candidate against
existing people/*.yaml (by name or alias, case/punctuation-insensitive),
and for unresolved candidates creates a new stub people/<slug>.yaml
(identity_confidence: likely/uncertain — never confirmed) plus a
sources/<guest-slug>/<episode-slug>/metadata.yaml appearance record
(role: guest, processing_status: pending).

Never touches statement content — that's Phase B, a separate, much
larger, ongoing effort. Safe to re-run: existing appearance files and
existing people are never overwritten.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

NAME_TOKEN_RE = re.compile(r"^[A-Z][a-zA-Z\.\']*$")
TITLE_PREFIX_RE = re.compile(r"^(Dr|Major|Prof|Mr|Ms|Mrs)\.?$")
BOILERPLATE_SEGMENT_RE = re.compile(r"(?i)^(raj shamani|nikhil( kamath)?|fo\s?\d+.*|ep\s*#?\d+.*)$")
LEADING_NAME_RE = re.compile(r"^([A-Z][a-zA-Z\.\']+(?:\s+[A-Z][a-zA-Z\.\']+){0,3})\s*(?::|\bon\b)")
FT_CLAUSE_RE = re.compile(r"\bFt\.?\s+(.+?)(?:\s*\||$)")
SPEAKER_ATTRIBUTION_RE = re.compile(r"SPEAKER ATTRIBUTION:(.+?)(?:\n\n|\Z)", re.DOTALL)
PAREN_LIST_RE = re.compile(r"\(([^()]+)\)")

HEADLINE_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "will", "why", "how",
    "what", "who", "this", "that", "these", "those", "your", "you",
    "with", "without", "from", "for", "and", "or", "but", "not", "no",
    "of", "on", "in", "at", "to", "into", "onto", "out", "up", "down",
    "than", "then", "so", "if", "it", "its", "his", "her", "their",
    "our", "my", "be", "do", "does", "did", "can", "could", "should",
    "would", "make", "makes", "made", "become", "becomes", "becoming",
}


def _looks_like_name(segment: str) -> bool:
    words = segment.strip().split()
    if not (1 <= len(words) <= 5):
        return False
    for w in words:
        bare = w.strip(".,'’").lower()
        if bare in HEADLINE_STOPWORDS:
            return False
        if not (NAME_TOKEN_RE.match(w) or TITLE_PREFIX_RE.match(w.rstrip("."))):
            return False
    return True


def extract_name_candidates_from_title(title: str) -> list[tuple[str, str]]:
    """Return (name, confidence) candidate pairs heuristically extracted
    from an episode title. confidence is 'likely' or 'uncertain' — a
    title alone is never sufficient to mark a person 'confirmed'."""
    candidates: list[tuple[str, str]] = []

    ft_match = FT_CLAUSE_RE.search(title)
    if ft_match:
        chunk = ft_match.group(1)
        chunk = re.sub(r"\s*&\s*", ",", chunk)
        chunk = re.sub(r"\s+and\s+", ",", chunk)
        for name in chunk.split(","):
            name = name.strip()
            if name.endswith("."):
                # Strip a trailing sentence-final period, but keep one
                # that belongs to a single-letter initial (e.g. "Rajan A.").
                last_word = name[:-1].rsplit(" ", 1)[-1]
                if len(last_word) > 1:
                    name = name[:-1]
            if name:
                candidates.append((name, "likely"))

    leading_match = LEADING_NAME_RE.match(title.strip())
    if leading_match:
        name = leading_match.group(1).strip()
        if _looks_like_name(name):
            candidates.append((name, "likely"))

    for segment in title.split("|"):
        segment = segment.strip()
        if not segment or BOILERPLATE_SEGMENT_RE.match(segment):
            continue
        if _looks_like_name(segment):
            candidates.append((segment, "uncertain"))

    best: dict[str, str] = {}
    for name, confidence in candidates:
        if name not in best or (best[name] == "uncertain" and confidence == "likely"):
            best[name] = confidence
    return sorted(best.items())


def extract_name_candidates_from_notes(notes: str) -> list[str]:
    """Return name candidates parsed out of a statement's `notes` field —
    specifically the parenthesized guest lists this corpus's own
    SPEAKER ATTRIBUTION convention already writes, e.g. '...panel
    (Nithin Kamath/Zerodha, Karthik Reddy/Blume Ventures, ...)'."""
    match = SPEAKER_ATTRIBUTION_RE.search(notes or "")
    if not match:
        return []
    block = match.group(1)
    # "Cross-reference:" is this corpus's own convention for citing a
    # *different* episode's guest for corroboration (e.g. "Cross-
    # reference: ... nikhil-kamath-005 (Sam Altman)") -- never a guest
    # of *this* episode. Drop it before scanning for parenthesized
    # names so those cross-episode mentions aren't misattributed here.
    block = block.split("Cross-reference:")[0]
    candidates: list[str] = []
    # Only the *first* parenthesized group in the block is ever the
    # guest-list convention (it always appears immediately after the
    # panel/interview framing, e.g. "...panel (Name/Org, Name/Org)"). Any
    # later parenthetical is just a prose aside -- scanning those too picks
    # up unrelated capitalized asides (a company name, a video chapter
    # title) as bogus name candidates.
    first_paren_match = PAREN_LIST_RE.search(block)
    if first_paren_match:
        paren_group = first_paren_match.group(1)
        for item in paren_group.split(","):
            name = item.split("/")[0].strip()
            words = name.split()
            if 1 <= len(words) <= 4 and all(
                NAME_TOKEN_RE.match(w) or TITLE_PREFIX_RE.match(w.rstrip("."))
                for w in words
            ):
                candidates.append(name)
    return sorted(set(candidates))


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def resolve_person(name: str, people_by_normalized_name: dict[str, str]) -> str | None:
    return people_by_normalized_name.get(normalize_name(name))


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def unique_slug(base_slug: str, existing_ids: set[str]) -> str:
    if base_slug not in existing_ids:
        return base_slug
    n = 2
    while f"{base_slug}-{n}" in existing_ids:
        n += 1
    return f"{base_slug}-{n}"


def render_person_yaml(person: dict) -> str:
    lines = [f'id: {person["id"]}', f'name: "{person["name"]}"']
    lines.append(f'credentials: "{person["credentials"]}"')
    lines.append("bio: >")
    lines.append(f'  {person["bio"]}')
    lines.append(f'identity_confidence: {person["identity_confidence"]}')
    return "\n".join(lines) + "\n"


def render_guest_appearance_yaml(appearance: dict) -> str:
    return (
        f'id: {appearance["id"]}\n'
        f'person: {appearance["person"]}\n'
        f'episode: {appearance["episode"]}\n'
        f'role: {appearance["role"]}\n'
        f'processing_status: {appearance["processing_status"]}\n'
    )


def build_person_index(people_dir: Path) -> tuple[dict[str, str], set[str]]:
    index: dict[str, str] = {}
    ids: set[str] = set()
    for path in sorted(people_dir.glob("*.yaml")):
        with path.open() as f:
            data = yaml.safe_load(f) or {}
        person_id = data.get("id")
        if not person_id:
            continue
        ids.add(person_id)
        if data.get("name"):
            index[normalize_name(data["name"])] = person_id
        for alias in data.get("aliases") or []:
            index[normalize_name(alias)] = person_id
    return index, ids


def main(repo_root: Path | None = None) -> int:
    repo_root = repo_root or REPO_ROOT
    people_dir = repo_root / "people"
    sources_dir = repo_root / "sources"
    episodes_dir = sources_dir / "episodes"

    name_index, person_ids = build_person_index(people_dir)
    people_by_id: dict[str, dict] = {}
    for path in sorted(people_dir.glob("*.yaml")):
        with path.open() as f:
            data = yaml.safe_load(f) or {}
        if data.get("id"):
            people_by_id[data["id"]] = data

    episode_titles: dict[str, str] = {}
    for path in sorted(episodes_dir.glob("*.yaml")):
        with path.open() as f:
            data = yaml.safe_load(f) or {}
        if data.get("id") and data.get("title"):
            episode_titles[data["id"]] = data["title"]

    episode_people: dict[str, dict[str, str]] = {}
    for path in sorted(sources_dir.glob("*/*/metadata.yaml")):
        with path.open() as f:
            data = yaml.safe_load(f) or {}
        episode_id = data.get("episode")
        person_id = data.get("person")
        role = data.get("role")
        if episode_id and person_id:
            episode_people.setdefault(episode_id, {})[person_id] = role

    new_people = 0
    new_appearances = 0
    matched_existing = 0

    for episode_id, title in episode_titles.items():
        registered = episode_people.get(episode_id, {})
        host_ids = {pid for pid, role in registered.items() if role == "host"}
        # Match against each host's actual name/aliases (and the individual
        # words within them), not just their person-id slug -- a title's
        # Ft. clause often refers to the host by a bare first name (e.g.
        # "Nikhil" for host "Nikhil Kamath"), which would never match the
        # host's full slug/name as a whole string.
        host_full_forms: set[str] = set()
        host_token_sets: list[set[str]] = []
        for pid in host_ids:
            host_person = people_by_id.get(pid, {})
            name_forms = []
            if host_person.get("name"):
                name_forms.append(host_person["name"])
            for alias in host_person.get("aliases") or []:
                name_forms.append(alias)
            if not name_forms:
                # No person record (or no name) found for this host id --
                # fall back to the slug so we don't silently stop excluding.
                name_forms.append(pid)
            for form in name_forms:
                normalized_form = normalize_name(form)
                if not normalized_form:
                    continue
                host_full_forms.add(normalized_form)
                host_token_sets.append(set(normalized_form.split()))
        candidates: list[tuple[str, str]] = list(extract_name_candidates_from_title(title))

        for person_dir in sorted(sources_dir.glob(f"*/{episode_id}")):
            statements_path = person_dir / "statements.yaml"
            if not statements_path.exists():
                continue
            with statements_path.open() as f:
                statements_data = yaml.safe_load(f) or {}
            for statement in statements_data.get("statements") or []:
                for name in extract_name_candidates_from_notes(statement.get("notes", "")):
                    candidates.append((name, "likely"))

        for name, confidence in candidates:
            normalized = normalize_name(name)
            if not normalized:
                continue
            normalized_words = set(normalized.split())
            if normalized in host_full_forms or any(
                normalized_words and normalized_words <= host_tokens
                for host_tokens in host_token_sets
            ):
                continue

            existing_person_id = resolve_person(name, name_index)
            resolved_to_existing = existing_person_id is not None

            if existing_person_id is not None:
                if existing_person_id in registered:
                    continue
                person_id = existing_person_id
            else:
                base_slug = slugify(name)
                if not base_slug:
                    continue
                person_id = unique_slug(base_slug, person_ids)
                person_path = people_dir / f"{person_id}.yaml"
                person_path.write_text(
                    render_person_yaml(
                        {
                            "id": person_id,
                            "name": name,
                            "credentials": "TBD — identity not yet confirmed.",
                            "bio": "TBD — auto-registered from episode title/notes, not yet researched.",
                            "identity_confidence": confidence,
                        }
                    )
                )
                person_ids.add(person_id)
                name_index[normalized] = person_id
                new_people += 1

            appearance_dir = sources_dir / person_id / episode_id
            appearance_path = appearance_dir / "metadata.yaml"
            if appearance_path.exists():
                continue
            appearance_dir.mkdir(parents=True, exist_ok=True)
            appearance_path.write_text(
                render_guest_appearance_yaml(
                    {
                        "id": f"{person_id}-{episode_id}",
                        "person": person_id,
                        "episode": episode_id,
                        "role": "guest",
                        "processing_status": "pending",
                    }
                )
            )
            registered[person_id] = "guest"
            new_appearances += 1
            if resolved_to_existing:
                matched_existing += 1

    print(
        f"Phase A complete: {new_people} new stub people, {new_appearances} new "
        f"guest appearances, {matched_existing} candidates resolved to existing people."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
