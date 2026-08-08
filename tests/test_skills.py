"""S-18 skill library — verbatim folder copies (byte-identical round-trip, no header
injection), lockfile provenance, [team] skills, add/remove both kinds, import --claude,
new skill scaffold."""
import json
from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

from servan.cli.app import app
from servan.config import ConfigError
from servan.library import LibraryLoader, LibraryService
from servan.rendering import SyncService

SKILL_MD = "---\nname: react-quality\ndescription: React review checklist\n---\n# React\n"
LINT_SH = "#!/bin/sh\nnpx biome check .\n"
LOGO = b"\x89PNG\r\n\x1a\n\x00fake"  # binary payload: skills are not text-only


class FakeClock:
    def now(self):
        return datetime(2026, 8, 8, tzinfo=UTC)


@pytest.fixture
def library_dir(tmp_path, monkeypatch):
    d = tmp_path / "library"
    (d / "agents").mkdir(parents=True)
    (d / "agents" / "math-sme.md").write_text(
        "---\ndescription: m\nmode: subagent\nmodel: ollama/x\n---\nbody\n")
    skill = d / "skills" / "react-quality"
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text(SKILL_MD)
    (skill / "scripts" / "lint.sh").write_text(LINT_SH)
    (skill / "logo.png").write_bytes(LOGO)
    monkeypatch.setenv("SERVAN_LIBRARY_DIR", str(d))
    return d


@pytest.fixture
def skill_project(tmp_path):
    root = tmp_path / "proj"
    (root / ".opencode").mkdir(parents=True)
    (root / ".servan.toml").write_text(
        'profile = "test"\n\n[team]\nskills = ["react-quality"]\n')
    return root


def tree(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()}


def read_lock(root):
    return json.loads((root / ".servan/library.lock.json").read_text())


def test_skill_installs_byte_identical_no_injection(cfg_dir, library_dir, skill_project):
    SyncService(clock=FakeClock()).sync(skill_project)
    assert tree(skill_project / ".opencode/skills/react-quality") == \
        tree(library_dir / "skills/react-quality")                # verbatim, incl. binary
    entry = read_lock(skill_project)["installs"]["skill:react-quality"]
    assert entry["kind"] == "skill" and entry["date"] == "2026-08-08"
    assert entry["source"] == "skills/react-quality" and entry["sha256"]


def test_skill_local_edits_preserved_unless_force(cfg_dir, library_dir, skill_project):
    SyncService(clock=FakeClock()).sync(skill_project)
    installed = skill_project / ".opencode/skills/react-quality/SKILL.md"
    installed.write_text("my local rewrite\n")
    SyncService(clock=FakeClock()).sync(skill_project)
    assert installed.read_text() == "my local rewrite\n"          # not clobbered
    SyncService(clock=FakeClock()).sync(skill_project, force=True)
    assert installed.read_text() == SKILL_MD                      # force restores library


def test_library_skill_update_propagates_when_untouched(cfg_dir, library_dir, skill_project):
    SyncService(clock=FakeClock()).sync(skill_project)
    (library_dir / "skills/react-quality/SKILL.md").write_text(SKILL_MD + "v2\n")
    (library_dir / "skills/react-quality/scripts/lint.sh").unlink()
    (library_dir / "skills/react-quality/refs.md").write_text("refs\n")
    SyncService(clock=FakeClock()).sync(skill_project)
    assert tree(skill_project / ".opencode/skills/react-quality") == \
        tree(library_dir / "skills/react-quality")                # mirrors: added + removed


def test_check_mode_reports_skill_drift_without_writing(cfg_dir, library_dir, skill_project):
    SyncService(clock=FakeClock()).sync(skill_project)
    (library_dir / "skills/react-quality/SKILL.md").write_text(SKILL_MD + "v2\n")
    results = SyncService(clock=FakeClock()).sync(skill_project, check=True)
    drift = [r for r in results if "react-quality" in r.path.name and r.changed]
    assert len(drift) == 1
    assert (skill_project / ".opencode/skills/react-quality/SKILL.md").read_text() == SKILL_MD


def test_add_routes_agents_and_skills(library_dir, tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / ".servan.toml").write_text('profile = "test"\n')
    service = LibraryService(LibraryLoader())
    service.add(root, "react-quality")
    service.add(root, "math-sme")
    text = (root / ".servan.toml").read_text()
    assert 'skills = ["react-quality"]' in text
    assert 'extra_agents = ["math-sme"]' in text
    with pytest.raises(ConfigError, match="unknown library item 'nope'"):
        service.add(root, "nope")


def test_remove_skill_deletes_unmodified_install(cfg_dir, library_dir, skill_project):
    SyncService(clock=FakeClock()).sync(skill_project)
    LibraryService(LibraryLoader()).remove(skill_project, "react-quality")
    assert not (skill_project / ".opencode/skills/react-quality").exists()
    assert 'skills = []' in (skill_project / ".servan.toml").read_text()
    assert "skill:react-quality" not in read_lock(skill_project)["installs"]


def test_import_claude_copies_folder_unchanged(library_dir, tmp_path):
    source = tmp_path / "downloads" / "pdf-tools"
    (source / "refs").mkdir(parents=True)
    (source / "SKILL.md").write_text("---\nname: pdf-tools\ndescription: x\n---\n")
    (source / "refs" / "spec.pdf").write_bytes(b"%PDF-fake")
    target = LibraryService(LibraryLoader()).import_claude(source)
    assert target == library_dir / "skills" / "pdf-tools"
    assert tree(target) == tree(source)
    with pytest.raises(ConfigError, match="already exists"):
        LibraryService(LibraryLoader()).import_claude(source)
    with pytest.raises(ConfigError, match="no SKILL.md"):
        LibraryService(LibraryLoader()).import_claude(tmp_path / "downloads")


def test_new_skill_scaffolds_and_refuses_overwrite(library_dir):
    service = LibraryService(LibraryLoader())
    created = service.new_skill("data-quality")
    assert created == library_dir / "skills" / "data-quality" / "SKILL.md"
    assert "name: data-quality" in created.read_text()
    with pytest.raises(ConfigError, match="already exists"):
        service.new_skill("data-quality")


def test_cli_list_shows_skill_state(cfg_dir, library_dir, skill_project):
    result = CliRunner().invoke(app, ["library", "list", "-p", str(skill_project)])
    assert result.exit_code == 0
    assert "react-quality (installed)" in result.output
    assert "math-sme (available)" in result.output
