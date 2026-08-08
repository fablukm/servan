"""S-23 template + docs wiring — template AGENTS.md references STANDARDS.md + the skills
mechanism; template .servan.toml carries commented standards/[team] examples and still
validates; examples/standards + examples/library stay loadable (shipped starting points)."""
import importlib.resources
import pathlib
import tomllib

from servan.config import ProjectConfig, StandardsLoader
from servan.library import LibraryLoader

TEMPLATE = importlib.resources.files("servan").joinpath("template")
EXAMPLES = pathlib.Path(__file__).resolve().parents[1] / "examples"


def test_template_agents_md_references_standards_and_skills():
    text = TEMPLATE.joinpath("AGENTS.md").read_text(encoding="utf-8")
    assert "STANDARDS.md" in text
    assert ".opencode/skills" in text
    assert ".claude/skills" in text                      # third-party compatibility note


def test_template_servan_toml_validates_with_commented_examples():
    raw = TEMPLATE.joinpath(".servan.toml").read_bytes()
    text = raw.decode()
    assert "# standards = [" in text                     # commented opt-in example
    assert "# [team]" in text and "# extra_agents" in text and "# skills" in text
    config = ProjectConfig.model_validate(tomllib.loads(text))
    assert config.standards == () and config.team.extra_agents == ()


def test_examples_standards_all_load():
    loader = StandardsLoader(EXAMPLES / "standards")
    assert loader.available() == ["base", "python", "react-typescript"]
    for name in loader.available():
        merged = loader.load(name)                       # extends resolve, no cycles
        assert merged.sections, name


def test_examples_library_seeds_are_valid():
    loader = LibraryLoader(EXAMPLES)
    assert "math-sme" in loader.agents()
    assert "react-quality" in loader.skills()
    source = loader.agent_source("math-sme")
    assert "\nmodel:" in source                            # sync requires a model: line
    assert "name: react-quality" in loader.skills()["react-quality"].read_text()


def test_readme_documents_v05_commands_and_walkthroughs():
    readme = (pathlib.Path(__file__).resolve().parents[1] / "README.md").read_text()
    for command in ("servan init", "servan survey", "servan standards",
                    "servan check", "servan library"):
        assert command in readme, command
    assert "--dry-run" in readme                           # brownfield walkthrough
    assert "@product" in readme                            # greenfield interview walkthrough
    assert ".claude/skills" in readme                      # skills compatibility note
    assert "## How it works" in readme                     # agent roster + the loop
    assert "## Where you interact" in readme              # human/servan touchpoints
    assert "## Scenarios" in readme and "@surveyor" in readme
    assert "git config --unset core.hooksPath" in readme   # leave-no-trace removal
