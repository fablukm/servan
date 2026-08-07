"""S-07 `servan lint` — OKF conformance, link resolution, servan extension, orphans.
Pure core: files-in -> findings-out; one CLI test for the exit-3 contract."""
from typer.testing import CliRunner

from servan.cli.app import app
from servan.lint import LintEngine, Severity


def write_page(root, rel, frontmatter: str | None, body: str = ""):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    text = body if frontmatter is None else f"---\n{frontmatter}\n---\n{body}"
    path.write_text(text)
    return path


def test_valid_page_passes(tmp_path):
    write_page(tmp_path, "wiki/index.md", "type: overview", "[A](modules/a.md)")
    write_page(tmp_path, "wiki/modules/a.md", "type: module\ntitle: A\ntimestamp: 2026-07-29")
    assert LintEngine().run(tmp_path) == []


def test_missing_okf_key_fails(tmp_path):
    page = write_page(tmp_path, "wiki/index.md", "title: no type here")
    findings = LintEngine().run(tmp_path)
    errors = [f for f in findings
              if f.rule == "okf-conformance" and f.severity is Severity.ERROR]
    assert [f.path for f in errors] == [page]


def test_broken_link_target_exit3(tmp_path):
    write_page(tmp_path, "wiki/index.md", "type: overview", "[ghost](modules/ghost.md)")
    write_page(tmp_path, "wiki/modules/a.md",
               "type: module\nlinks: [{rel: relates, target: specs/nope}]")
    findings = LintEngine().run(tmp_path)
    broken = [f for f in findings
              if f.rule == "link-resolution" and f.severity is Severity.ERROR]
    assert len(broken) == 2                      # markdown ghost + typed specs/nope
    result = CliRunner().invoke(app, ["lint", "-p", str(tmp_path)])
    assert result.exit_code == 3
    assert "link-resolution" in result.output


def test_orphan_detection_excludes_index_log_status(tmp_path):
    for name in ("index", "log", "status"):
        write_page(tmp_path, f"wiki/{name}.md", "type: overview")
    lonely = write_page(tmp_path, "wiki/modules/lonely.md", "type: module")
    findings = LintEngine().run(tmp_path)
    orphans = {f.path for f in findings if f.rule == "orphan-pages"}
    assert orphans == {lonely}
    assert all(f.severity is Severity.WARNING for f in findings)


def test_superseded_still_linked_as_current(tmp_path):
    write_page(tmp_path, "wiki/index.md", "type: overview",
               "[new](modules/new.md) [old](modules/old.md)")
    write_page(tmp_path, "wiki/modules/old.md", "type: module\nstatus: superseded")
    page = write_page(tmp_path, "wiki/modules/new.md",
                      "type: module\nlinks: [{rel: relates, target: wiki/modules/old}]")
    findings = LintEngine().run(tmp_path)
    ext = [f for f in findings if f.rule == "extension-validity"]
    assert len(ext) == 1
    assert ext[0].severity is Severity.WARNING and ext[0].path == page
    assert "wiki/modules/old" in ext[0].message

    page.write_text("---\ntype: module\nlinks: [{rel: supersedes, target: wiki/modules/old}]\n---\n")
    findings = LintEngine().run(tmp_path)
    assert [f for f in findings if f.rule == "extension-validity"] == []
