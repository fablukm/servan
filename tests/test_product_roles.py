"""S-21 product + surveyor roles — template ships both agents and the vision/roadmap
stubs; sync assigns them models via project [roles] overrides; stubs lint clean."""
import importlib.resources

from servan.lint import LintEngine, Severity
from servan.rendering import SyncService
from servan.scaffold import PackagedTemplateSource

TEMPLATE = importlib.resources.files("servan").joinpath("template")


def test_template_ships_product_surveyor_and_stubs(tmp_path):
    root = tmp_path / "proj"
    PackagedTemplateSource().copy_tree(root)
    for rel in (".opencode/agent/product.md", ".opencode/agent/surveyor.md",
                "wiki/vision.md", "wiki/roadmap.md"):
        assert (root / rel).is_file(), f"missing template entry: {rel}"
    product = (root / ".opencode/agent/product.md").read_text(encoding="utf-8")
    surveyor = (root / ".opencode/agent/surveyor.md").read_text(encoding="utf-8")
    assert "mode: primary" in product        # subagents cannot interview the human
    assert "mode: subagent" in surveyor      # read-only analyst, invoked on demand


def test_sync_assigns_models_via_project_roles(cfg_dir, tmp_path):
    root = tmp_path / "proj"
    PackagedTemplateSource().copy_tree(root)
    (root / ".servan.toml").write_text(
        'profile = "test"\n[roles]\nproduct = "local/small"\nsurveyor = "local/small"\n')
    results = SyncService().sync(root)
    for role in ("product", "surveyor"):
        agent = (root / f".opencode/agent/{role}.md").read_text(encoding="utf-8")
        assert "model: ollama/qwen2.5-coder:7b" in agent
        assert any(r.summary.startswith(f"{role} ->") for r in results)


def test_vision_roadmap_stubs_lint_clean(tmp_path):
    root = tmp_path / "proj"
    PackagedTemplateSource().copy_tree(root)
    findings = LintEngine().run(root)
    assert not [f for f in findings if f.severity is Severity.ERROR]
    orphans = {f.path.name for f in findings if f.rule == "orphan-pages"}
    assert "vision.md" not in orphans and "roadmap.md" not in orphans
