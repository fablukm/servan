"""S-03 `servan new` — acceptance: creates tree, hooksPath set, hook executable,
refuses non-empty dir, --no-bd skips ledger, works from any cwd."""
import importlib.resources
import os
import pathlib
import stat

import pytest

from servan.scaffold import PackagedTemplateSource, ScaffoldError, ScaffoldService

TEMPLATE = importlib.resources.files("servan").joinpath("template")


class FakeRunner:
    """ProcessRunner double: records (argv, cwd), never touches a real process."""

    def __init__(self) -> None:
        self.calls: list[tuple[tuple[str, ...], pathlib.Path | None]] = []

    def run(self, *argv: str, cwd: pathlib.Path | None = None) -> str:
        self.calls.append((argv, cwd))
        return ""


@pytest.fixture
def runner():
    return FakeRunner()


@pytest.fixture
def service(runner):
    return ScaffoldService(PackagedTemplateSource(), runner)


def test_creates_tree(tmp_path, service, runner):
    target = tmp_path / "proj"
    assert service.create(target) == target
    expected = {p.relative_to(TEMPLATE) for p in TEMPLATE.rglob("*")}
    actual = {p.relative_to(target) for p in target.rglob("*")}
    assert actual == expected
    argv_seq = [argv for argv, _ in runner.calls]
    assert argv_seq[0] == ("git", "init")
    assert argv_seq[-2] == ("git", "add", "-A")
    assert argv_seq[-1] == ("git", "commit", "-m", "[init] servan scaffold")
    assert all(cwd == target for _, cwd in runner.calls)


def test_refuses_non_empty(tmp_path, service, runner):
    target = tmp_path / "proj"
    target.mkdir()
    (target / "keep.txt").write_text("precious")
    with pytest.raises(ScaffoldError, match="not empty"):
        service.create(target)
    assert runner.calls == []                      # fail before any side effect
    assert (target / "keep.txt").read_text() == "precious"  # no partial writes


def test_allows_empty_existing_dir(tmp_path, service):
    target = tmp_path / "proj"
    target.mkdir()
    service.create(target)
    assert (target / "AGENTS.md").is_file()


def test_hookspath_and_exec_bits(tmp_path, service, runner):
    target = service.create(tmp_path / "proj")
    assert (("git", "config", "core.hooksPath", ".githooks"), target) in runner.calls
    hook = target / ".githooks" / "pre-commit"
    tool = target / "tools" / "wiki-status.sh"
    assert hook.is_file() and tool.is_file()
    if os.name == "posix":  # exec bits are not representable on Windows
        assert hook.stat().st_mode & stat.S_IXUSR
        assert tool.stat().st_mode & stat.S_IXUSR


def test_no_bd_flag(tmp_path, service, runner):
    service.create(tmp_path / "proj", with_ledger=False)
    assert all(argv[0] != "bd" for argv, _ in runner.calls)


def test_bd_init_by_default_before_commit(tmp_path, service, runner):
    service.create(tmp_path / "proj")
    argv_seq = [argv for argv, _ in runner.calls]
    assert ("bd", "init") in argv_seq
    assert argv_seq.index(("bd", "init")) < argv_seq.index(("git", "add", "-A"))


def test_works_from_any_cwd(tmp_path, monkeypatch, service, runner):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    target = service.create(pathlib.Path("proj"))
    assert target == elsewhere / "proj"
    assert (target / "AGENTS.md").is_file()        # template found independent of cwd
    assert all(cwd == target for _, cwd in runner.calls)
