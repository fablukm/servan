"""S-22 `servan check` — machine-checkable standards half: [forbidden].literals grep
(include/exclude_paths globs), [tooling] presence (lockfile, linter config);
findings -> exit 3, lint report shape; servan's own repo passes base+python."""
import pathlib

import pytest
from typer.testing import CliRunner

from servan.check import CheckService
from servan.cli.app import app
from servan.config import ConfigError, ConfigLoader

STANDARD = """\
schema = 1
name = "python"
[forbidden]
literals = ["print("]
include = ["*.py"]
exclude_paths = ["src/*/cli/*", "tests/*"]
[tooling]
lockfile = "uv.lock"
linter = "ruff"
"""


@pytest.fixture
def cfg_dir(tmp_path):
    d = tmp_path / "cfg"
    (d / "standards").mkdir(parents=True)
    (d / "standards" / "python.toml").write_text(STANDARD)
    return d


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "proj"
    (root / "src/pkg/config").mkdir(parents=True)
    (root / "src/pkg/cli").mkdir(parents=True)
    (root / ".servan.toml").write_text('standards = ["python"]\n')
    (root / "uv.lock").write_text("lock\n")
    (root / "pyproject.toml").write_text("[tool.ruff]\n")
    return root


def check(cfg_dir, project):
    return CheckService(ConfigLoader(cfg_dir)).check(project)


def test_forbidden_literal_flagged_only_outside_excludes(cfg_dir, project):
    (project / "src/pkg/config/c.py").write_text("x = 1\nprint('debug')\n")
    (project / "src/pkg/cli/c.py").write_text("print('ui is allowed')\n")
    (project / "README.md").write_text("mention print('x') in prose\n")  # not *.py: skipped
    findings = check(cfg_dir, project)
    assert [f.path.name for f in findings] == ["c.py"]
    assert findings[0].rule == "forbidden-literal" and "line 2" in findings[0].message
    assert "print(" in findings[0].message


def test_tooling_presence_lockfile_and_linter_config(cfg_dir, project):
    (project / "uv.lock").unlink()
    (project / "pyproject.toml").write_text("[project]\nname = \"x\"\n")
    findings = check(cfg_dir, project)
    messages = [f.message for f in findings]
    assert any("uv.lock" in m for m in messages)
    assert any("ruff" in m for m in messages)
    assert all(f.rule == "tooling-presence" for f in findings)
    (project / "uv.lock").write_text("lock\n")
    (project / "ruff.toml").write_text("")                            # standalone config also counts
    assert check(cfg_dir, project) == []


def test_no_standards_configured_is_a_config_error(cfg_dir, project):
    (project / ".servan.toml").write_text('profile = "test"\n')
    with pytest.raises(ConfigError, match="standards"):
        check(cfg_dir, project)
    result = CliRunner().invoke(
        app, ["--config-dir", str(cfg_dir), "check", "-p", str(project)])
    assert result.exit_code == 2


def test_cli_findings_exit_3_with_lint_report_shape(cfg_dir, project):
    (project / "src/pkg/config/c.py").write_text("print('debug')\n")
    result = CliRunner().invoke(
        app, ["--config-dir", str(cfg_dir), "check", "-p", str(project)])
    assert result.exit_code == 3
    assert "error: forbidden-literal:" in result.output
    (project / "src/pkg/config/c.py").write_text("x = 1\n")
    result = CliRunner().invoke(
        app, ["--config-dir", str(cfg_dir), "check", "-p", str(project)])
    assert result.exit_code == 0 and "check clean." in result.output


def test_servan_repo_passes_base_plus_python():
    root = pathlib.Path(__file__).resolve().parents[1]
    service = CheckService(ConfigLoader(root / "examples"))     # examples/standards as layer
    assert service.check(root) == []
