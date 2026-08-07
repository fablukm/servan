"""S-06 CI — GitHub Actions workflow (uv, pytest, ruff) + README badge."""
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"


def test_workflow_exists_and_covers_uv_pytest_ruff():
    assert WORKFLOW.is_file(), "missing .github/workflows/ci.yml"
    text = WORKFLOW.read_text()
    assert "astral-sh/setup-uv" in text          # uv is the toolchain
    assert "uv run pytest" in text
    assert "uv run ruff check" in text
    assert "pull_request" in text and "push" in text


def test_readme_has_ci_badge():
    readme = (REPO / "README.md").read_text()
    assert "actions/workflows/ci.yml/badge.svg" in readme


def test_ruff_is_a_dev_dependency():
    pyproject = (REPO / "pyproject.toml").read_text()
    assert "ruff" in pyproject
