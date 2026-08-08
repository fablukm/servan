"""S-20 `servan survey` — deterministic repo inventory: tree (depth<=3, gitignore-aware),
LOC by extension, manifests + top-level deps, entry points, test layout, git stats,
TODO/FIXME counts, 10 largest files; re-run differs only in the timestamp line."""
import json
import pathlib
import time
from datetime import datetime

import pytest
from typer.testing import CliRunner

from servan.cli.app import app
from servan.errors import ProcessError
from servan.infrastructure import SubprocessRunner
from servan.survey import SurveyCollector, SurveyReport


class FakeClock:
    def __init__(self, stamp="2026-08-08T12:00:00+00:00"):
        self._stamp = stamp

    def now(self):
        return datetime.fromisoformat(self._stamp)


class FakeRunner:
    """Routes git argv to canned stdout; unknown commands fail like a missing repo."""

    def __init__(self, files: str, *, git_stats: bool = True):
        self._files = files
        self._git_stats = git_stats

    def run(self, *argv: str, cwd: pathlib.Path | None = None) -> str:
        if argv[:2] == ("git", "ls-files"):
            return self._files
        if not self._git_stats:
            raise ProcessError("git: no commits yet")
        if argv[1] == "rev-list":
            return "42\n"
        if argv[1] == "log" and "--format=%ae" in argv:
            return "a@x.dev\nb@y.dev\na@x.dev\n"
        if argv[1] == "log":
            return "\nsrc/a.py\nsrc/b.py\n\nsrc/a.py\n"
        raise ProcessError(f"unexpected argv: {argv}")


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    (root / "src/pkg").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / ".venv/junk").mkdir(parents=True)          # fallback walker must skip this
    (root / "src/pkg/__init__.py").write_text("")
    (root / "src/pkg/__main__.py").write_text("print('hi')\n")
    (root / "src/pkg/core.py").write_text("# TODO: rethink\n" * 3 + "# FIXME: bug\n")
    (root / "tests/conftest.py").write_text("")
    (root / "tests/test_core.py").write_text("def test_x():\n    pass\n")
    (root / "README.md").write_text("# repo\n")
    (root / "big.bin").write_bytes(b"\0" * 2048)
    (root / ".venv/junk/ignored.py").write_text("junk\n")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "repo"\ndependencies = ["typer>=0.12", "pydantic[email]"]\n'
        '[project.scripts]\nrepo = "pkg.__main__:main"\n')
    (root / "package.json").write_text(json.dumps(
        {"name": "repo", "main": "dist/index.js",
         "dependencies": {"react": "^19"}, "devDependencies": {"vitest": "*"}}))
    return root


def collect(root, runner):
    return SurveyCollector(runner, FakeClock()).collect(root)


def test_collects_every_section_without_git(repo):
    runner = FakeRunner("src/pkg/__init__.py\nsrc/pkg/__main__.py\nsrc/pkg/core.py\n"
                        "tests/conftest.py\ntests/test_core.py\nREADME.md\nbig.bin\n"
                        "pyproject.toml\npackage.json\n", git_stats=False)
    report = collect(repo, runner)
    assert report.git is None                                   # no history: still works
    assert "src/pkg/core.py" in report.file_tree
    assert all(len(pathlib.PurePosixPath(p).parts) <= 3 for p in report.file_tree)
    assert report.loc_by_extension[".py"] == 7                  # 3 TODO + 1 FIXME + test + main
    assert report.manifests["pyproject.toml"] == ["pydantic", "typer"]
    assert report.manifests["package.json"] == ["react", "vitest"]
    assert any("repo" in e and "pyproject.toml" in e for e in report.entry_points)
    assert any("__main__.py" in e for e in report.entry_points)
    assert "dist/index.js" in report.entry_points[0] or any(
        "dist/index.js" in e for e in report.entry_points)
    assert report.test_dirs == ["tests"] and report.test_files == 1
    assert report.todos == 3 and report.fixmes == 1
    assert report.marker_files == {"src/pkg/core.py": 4}
    assert report.largest_files[0].path == "big.bin"
    assert report.largest_files[0].size == 2048
    assert len(report.largest_files) <= 10


def test_fallback_walker_skips_junk_dirs(repo):
    class NoGit:
        def run(self, *argv, cwd=None):
            raise ProcessError("not a git repo")

    report = collect(repo, NoGit())
    assert report.git is None
    assert not any(".venv" in p for p in report.file_tree)
    assert "src/pkg/core.py" in report.file_tree


def test_manifest_parsers_cover_requirements_cargo_go(repo):
    (repo / "requirements.txt").write_text("flask>=3\n# comment\n-r other.txt\nrequests\n")
    (repo / "Cargo.toml").write_text('[dependencies]\nserde = "1"\ntokio = { version = "1" }\n')
    (repo / "go.mod").write_text("module example.com/x\n\nrequire github.com/a/b v1.2.3\n\n"
                                 "require (\n\tgithub.com/c/d v2.0.0\n)\n")
    report = collect(repo, FakeRunner("requirements.txt\nCargo.toml\ngo.mod\n",
                                      git_stats=False))
    assert report.manifests["requirements.txt"] == ["flask", "requests"]
    assert report.manifests["Cargo.toml"] == ["serde", "tokio"]
    assert report.manifests["go.mod"] == ["github.com/a/b", "github.com/c/d"]


def test_git_stats_parsed_and_capped(repo):
    (repo / "src/a.py").write_text("a\n")
    (repo / "src/b.py").write_text("b\n")
    report = collect(repo, FakeRunner("src/a.py\nsrc/b.py\n"))
    assert report.git is not None
    assert report.git.commits == 42 and report.git.contributors == 2
    assert report.git.top_changed == ["src/a.py", "src/b.py"]     # count desc, then name


def test_rerun_differs_only_in_timestamp(repo, tmp_path):
    runner = FakeRunner("src/pkg/core.py\n", git_stats=False)
    collector = SurveyCollector(runner, FakeClock())
    report = collector.collect(repo)
    out = tmp_path / "out"
    collector.write(report, out)
    md1 = (out / "inventory.md").read_text()
    json1 = (out / "inventory.json").read_bytes()
    later = SurveyCollector(runner, FakeClock("2026-08-09T09:30:00+00:00"))
    later.write(later.collect(repo), out)
    md2 = (out / "inventory.md").read_text()
    assert md1 != md2
    assert [l for l in md1.splitlines() if l not in md2.splitlines()] == \
        ["_Generated: 2026-08-08T12:00:00+00:00_"]                # the single timestamp line
    assert (out / "inventory.json").read_bytes() == json1         # JSON fully deterministic
    SurveyReport.model_validate_json(json1)                       # round-trips the model


def test_cli_writes_both_files(repo):
    result = CliRunner().invoke(app, ["survey", "-p", str(repo)])
    assert result.exit_code == 0, result.output
    assert (repo / "raw/survey/inventory.md").is_file()
    assert (repo / "raw/survey/inventory.json").is_file()


def test_runs_on_servan_itself_under_5_seconds():
    root = pathlib.Path(__file__).resolve().parents[1]
    start = time.monotonic()
    report = SurveyCollector(SubprocessRunner(), FakeClock()).collect(root)
    assert time.monotonic() - start < 5
    assert "pyproject.toml" in report.manifests
    assert report.git is not None and report.git.commits > 0
