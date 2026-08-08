"""SurveyReport — the deterministic inventory model + its markdown rendering."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class GitStats(BaseModel):
    model_config = ConfigDict(frozen=True)

    commits: int
    contributors: int
    top_changed: list[str]


class FileSize(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    size: int


class SurveyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    root: str
    file_tree: list[str]
    loc_by_extension: dict[str, int]
    manifests: dict[str, list[str]]
    entry_points: list[str]
    test_dirs: list[str]
    test_files: int
    git: GitStats | None
    todos: int
    fixmes: int
    marker_files: dict[str, int]
    largest_files: list[FileSize]


def render_markdown(report: SurveyReport, generated_at: str) -> str:
    """Human-readable inventory; `generated_at` is the single timestamp line."""
    lines = [f"# Survey inventory — {report.root}", "",
             f"_Generated: {generated_at}_", "",
             "Machine facts from `servan survey` (deterministic, no LLM); re-run to refresh.", "",
             "## File tree (depth ≤ 3)", ""]
    lines += [f"- `{path}`" for path in report.file_tree]
    lines += ["", "## LOC by extension", "", "| extension | lines |", "|---|---|"]
    lines += [f"| {ext} | {count} |" for ext, count in sorted(
        report.loc_by_extension.items(), key=lambda kv: (-kv[1], kv[0]))]
    lines += ["", "## Dependency manifests", ""]
    for manifest, deps in sorted(report.manifests.items()):
        lines.append(f"### {manifest}")
        lines += [f"- {dep}" for dep in deps] or ["- (none)"]
        lines.append("")
    lines += ["## Entry points", ""]
    lines += [f"- {entry}" for entry in report.entry_points] or ["- (none found)"]
    lines += ["", "## Test layout", "",
              f"- test dirs: {', '.join(report.test_dirs) or 'none'}",
              f"- test files: {report.test_files}", ""]
    if report.git is None:
        lines += ["## Git stats", "", "_No git history._", ""]
    else:
        lines += ["## Git stats", "",
                  f"- commits: {report.git.commits}",
                  f"- contributors: {report.git.contributors}", "",
                  "Most-changed files (hot spots):"]
        lines += [f"- `{path}`" for path in report.git.top_changed] + [""]
    lines += ["## TODO/FIXME", "", f"- TODO: {report.todos} · FIXME: {report.fixmes}", ""]
    lines += [f"- `{path}`: {count}" for path, count in sorted(report.marker_files.items())]
    lines += ["", "## Largest files", "", "| file | bytes |", "|---|---|"]
    lines += [f"| {item.path} | {item.size} |" for item in report.largest_files]
    lines.append("")
    return "\n".join(lines)
