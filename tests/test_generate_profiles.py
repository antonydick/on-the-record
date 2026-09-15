import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import generate_profiles as gp  # noqa: E402


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def _write_person(repo_root: Path, person_id: str, name: str) -> None:
    _write_yaml(
        repo_root / "people" / f"{person_id}.yaml",
        {
            "id": person_id,
            "name": name,
            "credentials": "Some credentials.",
            "bio": "Some bio.",
        },
    )


def _write_episode(repo_root: Path, episode_id: str, title: str, published_date: str) -> None:
    _write_yaml(
        repo_root / "sources" / "episodes" / f"{episode_id}.yaml",
        {
            "id": episode_id,
            "title": title,
            "url": f"https://example.com/{episode_id}",
            "platform": "youtube",
            "published_date": published_date,
            "format": "video",
        },
    )


def _write_appearance(repo_root: Path, person_id: str, episode_id: str, role: str = "guest") -> str:
    appearance_id = f"{person_id}-{episode_id}"
    _write_yaml(
        repo_root / "sources" / person_id / episode_id / "metadata.yaml",
        {
            "id": appearance_id,
            "person": person_id,
            "episode": episode_id,
            "role": role,
            "processing_status": "complete",
        },
    )
    return appearance_id


def _write_statements(repo_root: Path, person_id: str, episode_id: str, statements: list[dict]) -> None:
    _write_yaml(
        repo_root / "sources" / person_id / episode_id / "statements.yaml",
        {"statements": statements},
    )


def _verified_verification() -> dict:
    return {
        "status": "verified",
        "verified_at": "2026-01-01",
        "verified_by": "someone",
        "source_url": "https://example.com/clip",
        "start_timestamp": "00:01:00",
        "end_timestamp": "00:01:30",
    }


def make_statement(**overrides):
    base = {
        "id": "p-1",
        "person": "p",
        "source": "p-ep1",
        "type": "experience",
        "text": "Some text.",
        "topic": "trading",
        "verification": {"status": "draft"},
    }
    base.update(overrides)
    return base


def test_filter_verified_keeps_only_verified():
    statements = [
        make_statement(id="a", verification={"status": "draft"}),
        make_statement(
            id="b",
            verification={
                "status": "verified",
                "verified_at": "2026-01-01",
                "verified_by": "someone",
                "source_url": "https://example.com/b",
                "start_timestamp": "00:01:00",
                "end_timestamp": "00:01:30",
            },
        ),
        make_statement(id="c", verification={"status": "rejected"}),
    ]
    result = gp.filter_verified(statements)
    assert [s["id"] for s in result] == ["b"]


def test_group_by_topic_groups_multiple_appearances():
    statements = [
        make_statement(id="a", topic="trading", source="p-ep1"),
        make_statement(id="b", topic="trading", source="p-ep2"),
        make_statement(id="c", topic="investing", source="p-ep1"),
    ]
    grouped = gp.group_by_topic(statements)
    assert set(grouped.keys()) == {"trading", "investing"}
    assert {s["id"] for s in grouped["trading"]} == {"a", "b"}


def test_recurring_topics_requires_two_different_appearances():
    statements = [
        make_statement(id="a", topic="trading", source="p-ep1"),
        make_statement(id="b", topic="trading", source="p-ep1"),
    ]
    grouped = gp.group_by_topic(statements)
    recurring = gp.recurring_topics(grouped)
    assert "trading" not in recurring

    statements.append(make_statement(id="c", topic="trading", source="p-ep2"))
    grouped = gp.group_by_topic(statements)
    recurring = gp.recurring_topics(grouped)
    assert "trading" in recurring


def test_render_profile_markdown_includes_statement_ids_not_prose_assertions():
    person = {"id": "p", "name": "Person P"}
    statements = [
        make_statement(
            id="p-1",
            type="belief",
            topic="trading",
            text="Trading is mostly about emotional control.",
        )
    ]
    episode_titles = {"p-ep1": "Some Episode"}
    episode_dates = {"p-ep1": "2024-01-01"}
    md = gp.render_profile_markdown(person, statements, episode_titles, episode_dates)
    assert "p-1" in md
    assert "Some Episode" in md
    assert "Trading is mostly about emotional control." in md


def test_render_profile_markdown_empty_when_no_verified_statements():
    person = {"id": "p", "name": "Person P"}
    md = gp.render_profile_markdown(person, [], {}, {})
    assert "no verified statements yet" in md.lower()


def test_evolving_topics_requires_two_distinct_dates():
    statements = [
        make_statement(id="a", topic="trading", source="p-ep1"),
        make_statement(id="b", topic="trading", source="p-ep2"),
    ]
    grouped = gp.group_by_topic(statements)

    same_date = {"p-ep1": "2024-01-01", "p-ep2": "2024-01-01"}
    assert gp.evolving_topics(grouped, same_date) == {}

    different_dates = {"p-ep1": "2023-01-01", "p-ep2": "2024-01-01"}
    evolving = gp.evolving_topics(grouped, different_dates)
    assert list(evolving.keys()) == ["trading"]
    assert [s["id"] for s in evolving["trading"]] == ["a", "b"]


def test_evolving_topics_sorts_chronologically_regardless_of_input_order():
    statements = [
        make_statement(id="later", topic="trading", source="p-ep2"),
        make_statement(id="earlier", topic="trading", source="p-ep1"),
    ]
    grouped = gp.group_by_topic(statements)
    dates = {"p-ep1": "2020-01-01", "p-ep2": "2025-01-01"}
    evolving = gp.evolving_topics(grouped, dates)
    assert [s["id"] for s in evolving["trading"]] == ["earlier", "later"]


def test_extract_entity_mentions_finds_multiword_capitalized_phrases():
    text = "He talked about True Beacon and also mentioned Zerodha's culture."
    mentions = gp.extract_entity_mentions(text)
    assert "True Beacon" in mentions


def test_extract_entity_mentions_ignores_single_capitalized_words():
    text = "He said Trading is hard."
    mentions = gp.extract_entity_mentions(text)
    assert mentions == []


def test_recurring_references_requires_two_different_sources():
    statements = [
        make_statement(id="a", source="p-ep1", text="He praised True Beacon a lot."),
        make_statement(id="b", source="p-ep1", text="True Beacon again came up."),
    ]
    assert gp.recurring_references(statements) == {}

    statements.append(make_statement(id="c", source="p-ep2", text="True Beacon strategy explained."))
    recurring = gp.recurring_references(statements)
    assert "True Beacon" in recurring
    assert recurring["True Beacon"] == {"a", "b", "c"}


def test_render_profile_markdown_includes_evolution_and_references_sections():
    person = {"id": "p", "name": "Person P"}
    statements = [
        make_statement(
            id="p-1", topic="trading", source="p-ep1",
            text="I traded full-time for many years, mostly at True Beacon.",
        ),
        make_statement(
            id="p-2", topic="trading", source="p-ep2",
            text="These days I barely trade myself, True Beacon runs on its own team now.",
        ),
    ]
    episode_titles = {"p-ep1": "Episode One", "p-ep2": "Episode Two"}
    episode_dates = {"p-ep1": "2020-01-01", "p-ep2": "2025-01-01"}
    md = gp.render_profile_markdown(person, statements, episode_titles, episode_dates)
    assert "## Evolution" in md
    assert "Later stated" in md
    assert "## Relationships & references" in md
    assert "True Beacon" in md


def test_main_renders_real_episode_title_not_appearance_id(tmp_path):
    # Regression test for the bug where main() built episode_titles/
    # episode_dates keyed by *episode id* while every lookup site keys by
    # *appearance id* (statement["source"]), so titles/dates never resolved.
    _write_person(tmp_path, "guest-one", "Guest One")
    _write_episode(tmp_path, "episode-one", "The Real Episode Title", "2024-03-01")
    _write_appearance(tmp_path, "guest-one", "episode-one")
    _write_statements(
        tmp_path,
        "guest-one",
        "episode-one",
        [
            {
                "id": "guest-one-1",
                "person": "guest-one",
                "source": "guest-one-episode-one",
                "type": "belief",
                "text": "Some verified thing they said.",
                "topic": "life",
                "verification": _verified_verification(),
            }
        ],
    )

    gp.main(repo_root=tmp_path)

    profile = (tmp_path / "profiles" / "guest-one.md").read_text()
    assert "The Real Episode Title" in profile
    assert "guest-one-episode-one" not in profile


def test_main_renders_evolution_section_from_real_fixture_files(tmp_path):
    # A second fixture proving evolving_topics() actually fires when data
    # comes through main()'s real file-loading path (appearance id -> episode
    # id -> title/date), not just the unit-level fixtures above which never
    # exercise that join.
    _write_person(tmp_path, "guest-two", "Guest Two")
    _write_episode(tmp_path, "episode-a", "Episode A Title", "2020-01-01")
    _write_episode(tmp_path, "episode-b", "Episode B Title", "2025-01-01")
    _write_appearance(tmp_path, "guest-two", "episode-a")
    _write_appearance(tmp_path, "guest-two", "episode-b")
    _write_statements(
        tmp_path,
        "guest-two",
        "episode-a",
        [
            {
                "id": "guest-two-1",
                "person": "guest-two",
                "source": "guest-two-episode-a",
                "type": "belief",
                "text": "Early view on the topic.",
                "topic": "careers",
                "verification": _verified_verification(),
            }
        ],
    )
    _write_statements(
        tmp_path,
        "guest-two",
        "episode-b",
        [
            {
                "id": "guest-two-2",
                "person": "guest-two",
                "source": "guest-two-episode-b",
                "type": "belief",
                "text": "Later view on the topic.",
                "topic": "careers",
                "verification": _verified_verification(),
            }
        ],
    )

    gp.main(repo_root=tmp_path)

    profile = (tmp_path / "profiles" / "guest-two.md").read_text()
    assert "## Evolution" in profile
    assert "Episode A Title" in profile
    assert "Episode B Title" in profile
