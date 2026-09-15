import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import register_guests_phase_a as rg  # noqa: E402


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


def test_extract_name_candidates_from_notes_no_attribution_block():
    assert rg.extract_name_candidates_from_notes("Just some ordinary notes.") == []


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
