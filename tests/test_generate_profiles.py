import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import generate_profiles as gp  # noqa: E402


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
