from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import validate  # noqa: E402


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def make_minimal_valid_repo(tmp_path: Path) -> Path:
    write(
        tmp_path / "people" / "nikhil-kamath.yaml",
        'id: nikhil-kamath\nname: "Nikhil Kamath"\ncredentials: "Host"\nbio: "Bio."\n',
    )
    write(
        tmp_path / "sources" / "episodes" / "ep1.yaml",
        'id: ep1\ntitle: "Ep 1"\nurl: "https://example.com/1"\nplatform: youtube\n'
        'published_date: "2026-01-01"\nformat: video\n',
    )
    write(
        tmp_path / "sources" / "nikhil-kamath" / "ep1" / "metadata.yaml",
        'id: nikhil-kamath-ep1\nperson: nikhil-kamath\nepisode: ep1\nrole: host\n'
        'processing_status: extracted\n',
    )
    write(
        tmp_path / "sources" / "nikhil-kamath" / "ep1" / "statements.yaml",
        "statements:\n"
        "  - id: nikhil-kamath-1\n"
        "    person: nikhil-kamath\n"
        "    source: nikhil-kamath-ep1\n"
        "    type: experience\n"
        "    text: Some text.\n"
        "    speaker_confidence: high\n"
        "    verification:\n"
        "      status: draft\n",
    )
    return tmp_path


def test_valid_minimal_repo_passes(tmp_path, capsys):
    make_minimal_valid_repo(tmp_path)
    exit_code = validate.main(repo_root=tmp_path)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "1 people, 1 episodes, 1 appearances, 1 statements" in out


def test_appearance_episode_id_mismatched_with_directory_fails(tmp_path, capsys):
    repo = make_minimal_valid_repo(tmp_path)
    write(
        repo / "sources" / "nikhil-kamath" / "ep1" / "metadata.yaml",
        'id: nikhil-kamath-ep1\nperson: nikhil-kamath\nepisode: wrong-slug\nrole: host\n'
        'processing_status: extracted\n',
    )
    exit_code = validate.main(repo_root=repo)
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "does not match directory" in out


def test_appearance_referencing_unknown_episode_fails(tmp_path, capsys):
    repo = make_minimal_valid_repo(tmp_path)
    write(
        repo / "sources" / "nikhil-kamath" / "ep1" / "metadata.yaml",
        'id: nikhil-kamath-ep1\nperson: nikhil-kamath\nepisode: ep1\nrole: host\n'
        'processing_status: extracted\n',
    )
    (repo / "sources" / "episodes" / "ep1.yaml").unlink()
    exit_code = validate.main(repo_root=repo)
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "does not match any sources/episodes" in out


def test_duplicate_episode_id_fails(tmp_path, capsys):
    repo = make_minimal_valid_repo(tmp_path)
    write(
        repo / "sources" / "episodes" / "ep1-dup.yaml",
        'id: ep1\ntitle: "Dup"\nurl: "https://example.com/dup"\nplatform: youtube\n'
        'published_date: "2026-01-02"\nformat: video\n',
    )
    exit_code = validate.main(repo_root=repo)
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "duplicate episode id" in out


def test_episode_id_not_matching_filename_fails(tmp_path, capsys):
    repo = make_minimal_valid_repo(tmp_path)
    write(
        repo / "sources" / "episodes" / "ep1.yaml",
        'id: not-ep1\ntitle: "Ep 1"\nurl: "https://example.com/1"\nplatform: youtube\n'
        'published_date: "2026-01-01"\nformat: video\n',
    )
    exit_code = validate.main(repo_root=repo)
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "does not match filename" in out


def test_check_appearance_against_dirs_pure_function():
    errors = validate.check_appearance_against_dirs(
        {"person": "nikhil-kamath", "episode": "ep1"}, "nikhil-kamath", "ep1"
    )
    assert errors == []

    errors = validate.check_appearance_against_dirs(
        {"person": "wrong-person", "episode": "ep1"}, "nikhil-kamath", "ep1"
    )
    assert len(errors) == 1
    assert "does not match directory 'nikhil-kamath'" in errors[0]


def test_check_episode_data_pure_function():
    assert validate.check_episode_data({"id": "ep1"}, "ep1") == []
    errors = validate.check_episode_data({"id": "ep1"}, "other")
    assert len(errors) == 1
    assert "does not match filename" in errors[0]
