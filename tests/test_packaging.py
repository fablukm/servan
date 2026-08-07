"""S-11 packaging — template/ ships as wheel data, resolved via importlib.resources."""
import importlib.resources

from servan.scaffold import PackagedTemplateSource

RESOURCE = importlib.resources.files("servan").joinpath("template")


def test_template_is_a_package_resource():
    assert RESOURCE.is_dir()
    for rel in ("AGENTS.md", ".servan.toml", ".githooks", ".opencode", "wiki", "tools"):
        assert RESOURCE.joinpath(rel).exists(), f"missing packaged template entry: {rel}"


def test_copy_tree_materializes_every_resource_file(tmp_path):
    PackagedTemplateSource().copy_tree(tmp_path)
    with importlib.resources.as_file(RESOURCE) as root:
        expected = {p.relative_to(root) for p in root.rglob("*")}
    actual = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}
    assert actual == expected
    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == (
        RESOURCE.joinpath("AGENTS.md").read_text(encoding="utf-8")
    )
