import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import register_guests_phase_a as rg  # noqa: E402


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def test_extract_name_candidates_from_title_ft_clause():
    title = "Ep #9 | WTF is Venture Capital? Ft. Nikhil, Nithin, Rajan A., Prashanth P. & Karthik R."
    names = dict(rg.extract_name_candidates_from_title(title))
    assert names.get("Nithin") == "likely"
    assert names.get("Rajan A.") == "likely"
    assert names.get("Prashanth P.") == "likely"
    assert names.get("Karthik R.") == "likely"


def test_extract_name_candidates_from_title_leading_name_before_colon():
    title = "Andrew Huberman: Become Mentally Dangerous With These Daily Habits | FO556 Raj Shamani"
    names = dict(rg.extract_name_candidates_from_title(title))
    assert names.get("Andrew Huberman") == "likely"
    assert "FO556 Raj Shamani" not in names
    assert "Become Mentally Dangerous With These Daily Habits" not in names


def test_extract_name_candidates_from_title_leading_name_before_on():
    title = "Sourav Ganguly on Leadership, Team Building, BCCI, Match-Fixing Era & Aggression | FO509 Raj Shamani"
    names = dict(rg.extract_name_candidates_from_title(title))
    assert names.get("Sourav Ganguly") == "likely"


def test_extract_name_candidates_from_title_pipe_segment_name_with_title_prefix():
    title = "President's Ex-ADC On Security Protocols & Mental Toughness | Major Rishabh Singh| FO560 Raj Shamani"
    names = dict(rg.extract_name_candidates_from_title(title))
    assert names.get("Major Rishabh Singh") == "uncertain"


def test_extract_name_candidates_from_title_rejects_headline_boilerplate():
    title = "Neuroscientist's Guide To 10X Your Focus & Memory | Dr Sahar Yousef | FO559 Raj Shamani"
    names = dict(rg.extract_name_candidates_from_title(title))
    assert "Neuroscientist's Guide To 10X Your Focus & Memory" not in names
    assert names.get("Dr Sahar Yousef") == "uncertain"
    assert "FO559 Raj Shamani" not in names


def test_extract_name_candidates_from_title_rejects_headline_false_positives():
    # Real examples that were previously mistaken for names via the
    # pipe-segment fallback or the leading-name-before-colon match.
    titles = [
        "Elon Musk: A Different Conversation w/ Nikhil Kamath | Full Episode | People by WTF Ep. 16",
        "Money Trap: Why More Money Won't Make You Rich & How to Escape | Alok Sama | FO540 Raj Shamani",
        "The $11B Bet That Voice Will Replace Everything | Mati Staniszewski x Nikhil Kamath | WTF Online",
        "People with The Prime Minister Shri Narendra Modi x Nikhil Kamath | Episode 6 | By WTF",
        "Nikhil Kamath ft. Police Comm'r & Traffic Police Comm'r of Bengaluru | WTF is Policing? | Special Ep",
        "17 Young Founders | 8 Startups | 20 Lakh Grants | Third WTFund Cohort",
        "Inside Silicon Valley's VC Playbook | WTF is Venture Capital? - 2025 Edition | Ep. 24",
        "Inside India's Next Gen Startups | Nikhil Kamath ft. WTFund C2/24 Founders",
    ]
    for title in titles:
        names = dict(rg.extract_name_candidates_from_title(title))
        for bogus in (
            "Full Episode", "Money Trap", "WTF Online", "By WTF",
            "Special Ep", "Third WTFund Cohort",
            "Inside Silicon Valley's VC Playbook",
            "Inside India's Next Gen Startups",
        ):
            assert bogus not in names, f"{bogus!r} wrongly extracted from {title!r}"


def test_extract_name_candidates_from_title_splits_company_possessive_prefix():
    # A "Company's Person Name" pipe segment should yield just the
    # person's name, not the company+person phrase fused together.
    title = "Founder Spotlight | Ather's Tarun Mehta | FO600 Raj Shamani"
    names = dict(rg.extract_name_candidates_from_title(title))
    assert names.get("Tarun Mehta") == "uncertain"
    assert "Ather's Tarun Mehta" not in names


def test_extract_name_candidates_from_title_leaves_real_possessive_headlines_alone():
    # A genuine headline possessive (not "Company's Person") must not be
    # stripped down into a bogus short "name".
    title = "India-US Relations, China Competition & India's Superpower Strategy | Dr. Samir | FO526 Raj Shamani"
    names = dict(rg.extract_name_candidates_from_title(title))
    assert "Superpower Strategy" not in names
    assert names.get("Dr. Samir") == "uncertain"


def test_extract_name_candidates_from_notes_parses_speaker_attribution_parens():
    notes = (
        "SPEAKER ATTRIBUTION: four-guest panel (Nikhil's brother Nithin "
        "Kamath/Zerodha, Karthik Reddy/Blume Ventures, Rajan Anandan/Peak "
        "XV-Sequoia, Prashanth Prakash/Accel), no diarization in the "
        "auto-transcript."
    )
    names = rg.extract_name_candidates_from_notes(notes)
    assert "Karthik Reddy" in names
    assert "Rajan Anandan" in names
    assert "Prashanth Prakash" in names


def test_extract_name_candidates_from_notes_splits_company_possessive_prefix():
    # Real example shape (ather-s-tarun-mehta's original source text):
    # free-text attribution names the company right before the guest's
    # name ("Ather's Tarun Mehta"), unlike the corpus's own "Name/Company"
    # convention -- the company must not be fused into the candidate name.
    notes = (
        "SPEAKER ATTRIBUTION: four-person panel (Nikhil hosting Blusmart's "
        "Punit Goyal, Ather's Tarun Mehta, and Ossus Biorenewables' Suruchi "
        "Rao), no diarization in the auto-transcript."
    )
    names = rg.extract_name_candidates_from_notes(notes)
    assert "Tarun Mehta" in names
    assert "Punit Goyal" in names
    assert "Suruchi Rao" in names
    assert "Ather's Tarun Mehta" not in names
    assert "Blusmart's Punit Goyal" not in names


def test_extract_name_candidates_from_notes_no_attribution_block():
    assert rg.extract_name_candidates_from_notes("Just some ordinary notes.") == []


def test_extract_name_candidates_from_title_rejects_headline_noun_phrase_before_colon():
    # Real example shape (fo545-ian-bremmer): the leading-name-before-colon
    # heuristic must not treat a capitalized headline noun phrase as a
    # person's name -- only the pipe-segment "Ian Bremmer" is a real guest.
    title = (
        "Top Geopolitical Expert: Why America Is No Longer The World's "
        "Leader | Ian Bremmer | FO545 Raj Shamani"
    )
    names = dict(rg.extract_name_candidates_from_title(title))
    assert "Top Geopolitical Expert" not in names
    assert names.get("Ian Bremmer") == "uncertain"


def test_extract_name_candidates_from_title_rejects_bogus_headline_stub_people():
    # Each of these headline-before-colon prefixes previously produced a
    # bogus stub person when the corpus was re-run.
    bogus_titles = [
        "Bureaucracy: How India's Babus Are Killing Innovation | FO1 Raj Shamani",
        "Russian Spy: The Untold Story | FO2 Raj Shamani",
        "Supreme Court: Inside The Verdict | FO3 Raj Shamani",
        "Warning: This Will Change Your Mind | FO4 Raj Shamani",
        "Advice: What Nobody Tells You | FO5 Raj Shamani",
        "Champion Mindset Explained: How To Win | FO6 Raj Shamani",
        "Foreign Affairs Expert: Geopolitics 101 | FO7 Raj Shamani",
        "Psychiatrist Explains: Why We Break | FO8 Raj Shamani",
        "Top Brain Scientist: Memory Secrets | FO9 Raj Shamani",
    ]
    for title in bogus_titles:
        names = dict(rg.extract_name_candidates_from_title(title))
        headline = title.split(":")[0].strip()
        assert headline not in names, f"{headline!r} wrongly extracted from {title!r}"


def test_extract_name_candidates_from_notes_ignores_cross_reference_mentions():
    # Real example shape (nikhil-kamath/nandan-nilekani statements.yaml):
    # a "Cross-reference:" clause cites *other* episodes' guests for
    # corroboration -- those aren't guests of *this* episode and must
    # not be extracted as candidates here.
    notes = (
        "SPEAKER ATTRIBUTION: same caveat as nikhil-kamath-029. "
        "Cross-reference: extends the pattern seen in nikhil-kamath-005 "
        "(Sam Altman) and nikhil-kamath-009 (Vinod Khosla), where he "
        "describes ongoing, sustained research into specific investment "
        "sectors/themes."
    )
    assert rg.extract_name_candidates_from_notes(notes) == []


def test_extract_name_candidates_from_notes_handles_slash_joined_companies_before_name():
    # Real example shape (nikhil-kamath/wtf-is-ev-ep14): when a SPEAKER
    # ATTRIBUTION mention reads "Company/Company founder Name" -- two
    # companies joined by slash, with the person's name trailing after a
    # founder/co-founder/CEO role word -- the name must still be extracted,
    # not the first company.
    notes = (
        "SPEAKER ATTRIBUTION: four-person panel (Nikhil hosting Blusmart's "
        "Punit Goyal, Reva/Sun Mobility founder Chetan Maini, and Ossus "
        "Biorenewables' Suruchi Rao), no diarization in the auto-transcript."
    )
    names = rg.extract_name_candidates_from_notes(notes)
    assert "Chetan Maini" in names
    assert "Reva" not in names


def test_extract_name_candidates_from_notes_still_handles_name_before_slash_company():
    # The existing "Name/Company" convention (name first) must keep working.
    notes = (
        "SPEAKER ATTRIBUTION: panel (Nithin Kamath/Zerodha, Chetan "
        "Maini/Reva-Sun Mobility), no diarization in the auto-transcript."
    )
    names = rg.extract_name_candidates_from_notes(notes)
    assert "Nithin Kamath" in names
    assert "Chetan Maini" in names


def test_normalize_name():
    assert rg.normalize_name("Nikhil Kamath") == "nikhil kamath"
    assert rg.normalize_name("Nikhil  Kamath (WTF)") == "nikhil kamath wtf"
    assert rg.normalize_name("Dr. Sahar Yousef") == "dr sahar yousef"


def test_resolve_person_matches_name_and_alias():
    index = {"nikhil kamath": "nikhil-kamath", "nikhil": "nikhil-kamath"}
    assert rg.resolve_person("Nikhil Kamath", index) == "nikhil-kamath"
    assert rg.resolve_person("Nikhil", index) == "nikhil-kamath"
    assert rg.resolve_person("Someone Else", index) is None


def test_slugify():
    assert rg.slugify("Nithin Kamath") == "nithin-kamath"
    assert rg.slugify("Dr. Sahar Yousef") == "dr-sahar-yousef"


def test_unique_slug_appends_suffix_on_collision():
    existing = {"john-smith"}
    assert rg.unique_slug("john-smith", existing) == "john-smith-2"
    assert rg.unique_slug("jane-doe", existing) == "jane-doe"


def test_render_person_yaml_round_trips():
    import yaml

    person = {
        "id": "nithin-kamath",
        "name": "Nithin Kamath",
        "credentials": "TBD — identity not yet confirmed.",
        "bio": "TBD — auto-registered from episode title/notes, not yet researched.",
        "identity_confidence": "likely",
    }
    parsed = yaml.safe_load(rg.render_person_yaml(person))
    assert parsed["id"] == "nithin-kamath"
    assert parsed["identity_confidence"] == "likely"


def test_render_guest_appearance_yaml_round_trips():
    import yaml

    appearance = {
        "id": "nithin-kamath-wtf-is-venture-capital-ep9",
        "person": "nithin-kamath",
        "episode": "wtf-is-venture-capital-ep9",
        "role": "guest",
        "processing_status": "pending",
    }
    parsed = yaml.safe_load(rg.render_guest_appearance_yaml(appearance))
    assert parsed == appearance


def test_main_registers_guest_from_title_and_is_idempotent(tmp_path):
    # Build a small fixture repo: one host person, one episode whose title
    # has a "Ft. Someone Real" clause, and the host's own appearance record.
    _write_yaml(
        tmp_path / "people" / "host-person.yaml",
        {
            "id": "host-person",
            "name": "Host Person",
            "credentials": "Show host.",
            "bio": "Hosts the show.",
        },
    )
    _write_yaml(
        tmp_path / "sources" / "episodes" / "ep1.yaml",
        {
            "id": "ep1",
            "title": "Some Interesting Topic Ft. Someone Real | EP1 Host Person",
            "url": "https://example.com/ep1",
            "platform": "youtube",
            "published_date": "2024-01-01",
            "format": "video",
        },
    )
    _write_yaml(
        tmp_path / "sources" / "host-person" / "ep1" / "metadata.yaml",
        {
            "id": "host-person-ep1",
            "person": "host-person",
            "episode": "ep1",
            "role": "host",
            "processing_status": "pending",
        },
    )

    result = rg.main(repo_root=tmp_path)
    assert result == 0

    person_files = {p.stem for p in (tmp_path / "people").glob("*.yaml")}
    new_people = person_files - {"host-person"}
    assert len(new_people) == 1
    new_person_id = next(iter(new_people))

    new_person = yaml.safe_load((tmp_path / "people" / f"{new_person_id}.yaml").read_text())
    assert new_person["name"] == "Someone Real"
    assert new_person["identity_confidence"] in {"likely", "uncertain"}

    appearance_count_before = len(list((tmp_path / "sources").glob("*/*/metadata.yaml")))
    people_count_before = len(list((tmp_path / "people").glob("*.yaml")))

    # Re-running must be a no-op: no additional people or appearances.
    rg.main(repo_root=tmp_path)

    appearance_count_after = len(list((tmp_path / "sources").glob("*/*/metadata.yaml")))
    people_count_after = len(list((tmp_path / "people").glob("*.yaml")))
    assert appearance_count_after == appearance_count_before
    assert people_count_after == people_count_before
