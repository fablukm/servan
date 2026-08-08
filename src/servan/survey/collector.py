"""SurveyCollector — deterministic repo inventory. No LLM, no network, git optional."""
from __future__ import annotations

import json
import pathlib
import re
import tomllib
from collections import Counter

from ..abstractions import Clock, ProcessRunner
from ..errors import ProcessError
from ..logging_setup import get_logger
from .report import FileSize, GitStats, SurveyReport, render_markdown

_log = get_logger("survey.collector")

MAX_TREE_DEPTH = 3
TOP_CHANGED = 20
LARGEST = 10
SKIP_DIRS = frozenset({".git", ".venv", "node_modules", "__pycache__",
                       ".pytest_cache", ".ruff_cache", "dist", "build"})
KNOWN_MANIFESTS = ("pyproject.toml", "package.json", "requirements.txt",
                   "Cargo.toml", "go.mod")
_MARKERS = re.compile(r"\b(TODO|FIXME)\b")
_DEP_NAME = re.compile(r"[<>=!~;\[ ]")
_TEST_FILE = re.compile(r"(^test_.+|.+(_test\.(py|go)|\.test\.(ts|tsx|js|jsx)))$")
_GO_REQUIRE = re.compile(r"^\s*(?:require\s+)?(\S+)\s+v\S+")


class SurveyCollector:
    def __init__(self, runner: ProcessRunner, clock: Clock) -> None:
        self._runner = runner
        self._clock = clock

    def collect(self, root: pathlib.Path) -> SurveyReport:
        root = root.resolve()
        files = self._list_files(root)
        texts = {rel: text for rel in files if (text := self._text(root, rel)) is not None}
        loc: Counter[str] = Counter()
        for rel, text in texts.items():
            loc[pathlib.PurePosixPath(rel).suffix.lower() or "(none)"] += len(text.splitlines())
        markers: Counter[str] = Counter()
        marker_files: dict[str, int] = {}
        for rel, text in texts.items():
            hits = Counter(m.group(1) for m in _MARKERS.finditer(text))
            if hits:
                markers.update(hits)
                marker_files[rel] = sum(hits.values())
        manifests: dict[str, list[str]] = {}
        entry_points: list[str] = []
        for rel in files:
            if pathlib.PurePosixPath(rel).name in KNOWN_MANIFESTS:
                deps, entries = self._parse_manifest(root, rel)
                manifests[rel] = deps
                entry_points.extend(entries)
        entry_points.extend(f"{rel} (__main__ module)" for rel in files
                            if rel.endswith("__main__.py"))
        test_dirs: set[str] = set()
        for rel in files:
            parts = pathlib.PurePosixPath(rel).parts
            test_dirs.update(pathlib.PurePosixPath(*parts[:i + 1]).as_posix()
                             for i, part in enumerate(parts) if part in ("tests", "test"))
        sizes = sorted(((rel, (root / rel).stat().st_size) for rel in files),
                       key=lambda item: (-item[1], item[0]))
        report = SurveyReport(
            root=root.name,
            file_tree=[rel for rel in files
                       if len(pathlib.PurePosixPath(rel).parts) <= MAX_TREE_DEPTH],
            loc_by_extension=dict(sorted(loc.items(), key=lambda kv: (-kv[1], kv[0]))),
            manifests=manifests,
            entry_points=sorted(entry_points),
            test_dirs=sorted(test_dirs),
            test_files=sum(1 for rel in files if _TEST_FILE.match(
                pathlib.PurePosixPath(rel).name)),
            git=self._git_stats(root),
            todos=markers.get("TODO", 0),
            fixmes=markers.get("FIXME", 0),
            marker_files=dict(sorted(marker_files.items())),
            largest_files=[FileSize(path=rel, size=size) for rel, size in sizes[:LARGEST]],
        )
        _log.info("surveyed %s: %d files, git=%s", root, len(files), report.git is not None)
        return report

    def write(self, report: SurveyReport, out_dir: pathlib.Path,
              ) -> tuple[pathlib.Path, pathlib.Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        md = out_dir / "inventory.md"
        js = out_dir / "inventory.json"
        md.write_text(render_markdown(report, self._clock.now().isoformat()),
                      encoding="utf-8")
        js.write_text(json.dumps(report.model_dump(), indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
        _log.info("wrote %s and %s", md, js)
        return md, js

    def _list_files(self, root: pathlib.Path) -> list[str]:
        try:  # git ls-files is gitignore-aware by construction
            out = self._runner.run("git", "ls-files", "-co", "--exclude-standard", cwd=root)
            return sorted(line for line in out.splitlines() if line.strip())
        except ProcessError:  # not a git repo at all: walk, skipping the usual junk
            _log.info("no git repo under %s — falling back to directory walk", root)
            return sorted(path.relative_to(root).as_posix() for path in root.rglob("*")
                          if path.is_file()
                          and not any(part in SKIP_DIRS
                                      for part in path.relative_to(root).parts))

    @staticmethod
    def _text(root: pathlib.Path, rel: str) -> str | None:
        try:
            return (root / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            return None  # binary or unreadable: excluded from LOC/markers

    def _git_stats(self, root: pathlib.Path) -> GitStats | None:
        try:
            commits = int(self._runner.run("git", "rev-list", "--count", "HEAD",
                                           cwd=root).strip())
            emails = self._runner.run("git", "log", "--format=%ae", cwd=root).split()
            changed = Counter(line.strip() for line in self._runner.run(
                "git", "log", "--format=", "--name-only", cwd=root).splitlines()
                if line.strip())
        except (ProcessError, ValueError):
            return None  # repo with no history: stats are optional by contract
        top = [name for name, _ in sorted(changed.items(), key=lambda kv: (-kv[1], kv[0]))]
        return GitStats(commits=commits, contributors=len(set(emails)),
                        top_changed=top[:TOP_CHANGED])

    def _parse_manifest(self, root: pathlib.Path,
                        rel: str) -> tuple[list[str], list[str]]:
        text = self._text(root, rel) or ""
        name = pathlib.PurePosixPath(rel).name
        deps: list[str] = []
        entries: list[str] = []
        if name == "pyproject.toml":
            data = tomllib.loads(text)
            project = data.get("project", {})
            deps = [_DEP_NAME.split(dep)[0].strip() for dep in project.get("dependencies", [])]
            entries = [f"{script} ({rel} [project.scripts])"
                       for script in sorted(project.get("scripts", {}))]
        elif name == "package.json":
            data = json.loads(text)
            deps = sorted({*data.get("dependencies", {}), *data.get("devDependencies", {})})
            if main := data.get("main"):
                entries.append(f"{main} ({rel} main)")
            bin_field = data.get("bin")
            if isinstance(bin_field, dict):
                entries += [f"{tool} ({rel} bin)" for tool in sorted(bin_field)]
            elif bin_field:
                entries.append(f"{bin_field} ({rel} bin)")
        elif name == "requirements.txt":
            deps = sorted({_DEP_NAME.split(line)[0].strip() for line in text.splitlines()
                           if line.strip() and not line.startswith(("#", "-"))} - {""})
        elif name == "Cargo.toml":
            deps = sorted(tomllib.loads(text).get("dependencies", {}))
        elif name == "go.mod":
            deps = sorted({match.group(1) for line in text.splitlines()
                           if (match := _GO_REQUIRE.match(line))})
        return sorted(set(deps)), entries
