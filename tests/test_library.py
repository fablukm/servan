"""S-17 agent library — loader enumeration + env override, sync install with provenance +
profile model, missing model mapping -> exit 2 naming the fix, idempotent add, local edits
preserved unless --force, remove, new agent scaffold."""
import hashlib
import json
from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

from servan.cli.app import app
from servan.config import ConfigError
from servan.library import LibraryLoader, LibraryService
from servan.rendering import SyncService

MATH_SME = """\
---
description: Math SME
mode: subagent
model: ollama/deepseek-r1:32b
---
You are the math SME.
"""


class FakeClock:
    def now(self):
        return datetime(2026, 8, 8, tzinfo=UTC)


@pytest.fixture
def library_dir(tmp_path, monkeypatch):
    d = tmp_path / "library"
    (d / "agents").mkdir(parents=True)
    (d / "agents" / "math-sme.md").write_text(MATH_SME)
    skill = d / "skills" / "react-quality"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: react-quality\n---\n")
    monkeypatch.setenv("SERVAN_LIBRARY_DIR", str(d))
    return d


@pytest.fixture
def lib_project(tmp_path):
    root = tmp_path / "proj"
    (root / ".opencode/agent").mkdir(parents=True)
    (root / ".servan.toml").write_text(
        'profile = "test"\n\n[roles]\nmath-sme = "local/small"\n\n'
        '[team]\nextra_agents = ["math-sme"]\n')
    return root


def read_lock(root):
    return json.loads((root / ".servan/library.lock.json").read_text())


def test_loader_enumerates_agents_and_skills(library_dir):
    loader = LibraryLoader()  # SERVAN_LIBRARY_DIR override
    assert list(loader.agents()) == ["math-sme"]
    assert list(loader.skills()) == ["react-quality"]


def test_sync_installs_agent_with_provenance_model_and_lock(cfg_dir, library_dir, lib_project):
    SyncService(clock=FakeClock()).sync(lib_project)
    installed = (lib_project / ".opencode/agent/math-sme.md").read_text()
    assert "<!-- installed by servan from library:math-sme -->" in installed
    assert "model: ollama/qwen2.5-coder:7b" in installed          # profile model, not source
    assert "You are the math SME." in installed
    entry = read_lock(lib_project)["installs"]["agent:math-sme"]
    assert entry["kind"] == "agent" and entry["date"] == "2026-08-08"
    assert entry["sha256"] == hashlib.sha256(installed.encode()).hexdigest()
    first = (lib_project / ".servan/library.lock.json").read_bytes()
    SyncService(clock=FakeClock()).sync(lib_project)              # re-run: no rewrite
    assert (lib_project / ".servan/library.lock.json").read_bytes() == first


def test_extra_agent_without_model_mapping_names_the_fix(cfg_dir, library_dir, tmp_path):
    root = tmp_path / "proj"
    (root / ".opencode/agent").mkdir(parents=True)
    (root / ".servan.toml").write_text(
        'profile = "test"\n\n[team]\nextra_agents = ["math-sme"]\n')
    with pytest.raises(ConfigError, match=r"\[roles\] math-sme = \"<alias>\""):
        SyncService().sync(root)


def test_local_edits_preserved_unless_force(cfg_dir, library_dir, lib_project):
    SyncService(clock=FakeClock()).sync(lib_project)
    path = lib_project / ".opencode/agent/math-sme.md"
    original = path.read_text()
    path.write_text(original + "\nlocal tweak\n")
    SyncService(clock=FakeClock()).sync(lib_project)
    assert path.read_text().endswith("local tweak\n")              # not clobbered
    SyncService(clock=FakeClock()).sync(lib_project, force=True)
    assert path.read_text() == original                           # force restores library


def test_library_source_update_propagates_when_untouched(cfg_dir, library_dir, lib_project):
    SyncService(clock=FakeClock()).sync(lib_project)
    (library_dir / "agents/math-sme.md").write_text(MATH_SME + "\nNew guidance.\n")
    SyncService(clock=FakeClock()).sync(lib_project)
    assert "New guidance." in (lib_project / ".opencode/agent/math-sme.md").read_text()


def test_foreign_agent_file_is_never_adopted(cfg_dir, library_dir, lib_project):
    path = lib_project / ".opencode/agent/math-sme.md"
    path.write_text("hand-written, no lock entry\n")
    SyncService(clock=FakeClock()).sync(lib_project)
    assert path.read_text() == "hand-written, no lock entry\n"


def test_check_mode_reports_drift_and_writes_nothing(cfg_dir, library_dir, lib_project):
    SyncService(clock=FakeClock()).sync(lib_project)
    (library_dir / "agents/math-sme.md").write_text(MATH_SME + "\nNew guidance.\n")
    results = SyncService(clock=FakeClock()).sync(lib_project, check=True)
    drift = [r for r in results if r.path.name == "math-sme.md" and r.changed]
    assert len(drift) == 1 and drift[0].summary.startswith("library agent")
    assert "New guidance." not in (lib_project / ".opencode/agent/math-sme.md").read_text()


def test_add_is_idempotent_and_validates(library_dir, tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / ".servan.toml").write_text('profile = "test"\n')
    service = LibraryService(LibraryLoader())
    service.add(root, "math-sme")
    first = (root / ".servan.toml").read_text()
    assert 'extra_agents = ["math-sme"]' in first
    service.add(root, "math-sme")
    assert (root / ".servan.toml").read_text() == first           # idempotent
    with pytest.raises(ConfigError, match="unknown library agent 'nope'"):
        service.add(root, "nope")


def test_remove_deletes_unmodified_install_keeps_modified(cfg_dir, library_dir, lib_project):
    service = LibraryService(LibraryLoader())
    SyncService(clock=FakeClock()).sync(lib_project)
    path = lib_project / ".opencode/agent/math-sme.md"
    path.write_text(path.read_text() + "\nlocal tweak\n")
    service.remove(lib_project, "math-sme")
    assert path.is_file()                                         # local edits survive
    assert 'extra_agents = []' in (lib_project / ".servan.toml").read_text()
    service.add(lib_project, "math-sme")
    SyncService(clock=FakeClock()).sync(lib_project, force=True)  # overwrite the kept copy
    service.remove(lib_project, "math-sme")
    assert not path.exists()                                      # unmodified -> deleted
    assert "agent:math-sme" not in read_lock(lib_project)["installs"]


def test_new_agent_scaffolds_and_refuses_overwrite(library_dir):
    service = LibraryService(LibraryLoader())
    created = service.new_agent("qa-sme")
    assert created == library_dir / "agents/qa-sme.md"
    assert "mode: subagent" in created.read_text()
    with pytest.raises(ConfigError, match="already exists"):
        service.new_agent("qa-sme")


def test_cli_library_list_and_add_exit_codes(cfg_dir, library_dir, lib_project):
    runner = CliRunner()
    result = runner.invoke(app, ["library", "list", "-p", str(lib_project)])
    assert result.exit_code == 0
    assert "agents:" in result.output and "skills:" in result.output
    assert "math-sme (installed)" in result.output
    assert "react-quality (available)" in result.output
    result = runner.invoke(app, ["library", "add", "nope", "-p", str(lib_project)])
    assert result.exit_code == 2
