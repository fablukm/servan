"""CheckService — the `servan check` use-case: the machine-checkable half of standards.
[forbidden].literals grep (include/exclude_paths globs) + [tooling] presence checks.
Findings reuse lint's Finding/Severity so the report shape is identical."""
from __future__ import annotations

import fnmatch
import pathlib

from ..config.errors import ConfigError
from ..config.loader import ConfigLoader
from ..config.standards_loader import StandardsLoader
from ..config.standards_set import SectionValue
from ..lint import Finding, Severity
from ..logging_setup import get_logger
from ..survey.collector import SKIP_DIRS

_log = get_logger("check.checker")


def find_forbidden_literals(root: pathlib.Path,
                            forbidden: dict[str, SectionValue]) -> list[Finding]:
    literals = forbidden.get("literals", [])
    if not literals:
        return []
    includes = forbidden.get("include", [])       # empty = all text files
    excludes = forbidden.get("exclude_paths", [])
    findings: list[Finding] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        rel = relative.as_posix()
        if includes and not any(fnmatch.fnmatch(rel, pat) for pat in includes):
            continue
        if any(fnmatch.fnmatch(rel, pat) for pat in excludes):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue                            # binary/unreadable: not greppable
        for lineno, line in enumerate(text.splitlines(), 1):
            for literal in literals:
                if literal in line:
                    findings.append(Finding(
                        rule="forbidden-literal", path=path, severity=Severity.ERROR,
                        message=f"line {lineno}: forbidden literal '{literal}'"))
    return findings


def check_tooling(root: pathlib.Path, tooling: dict[str, SectionValue]) -> list[Finding]:
    findings: list[Finding] = []
    lockfile = tooling.get("lockfile")
    if isinstance(lockfile, str) and lockfile and not (root / lockfile).is_file():
        findings.append(Finding(rule="tooling-presence", path=root / lockfile,
                                severity=Severity.ERROR,
                                message=f"missing lockfile '{lockfile}' required by standards"))
    linter = tooling.get("linter")
    if isinstance(linter, str) and linter and not _linter_configured(root, linter):
        findings.append(Finding(rule="tooling-presence", path=root / "pyproject.toml",
                                severity=Severity.ERROR,
                                message=f"linter '{linter}' has no config ({linter}.toml, "
                                        f".{linter}.toml, or [tool.{linter}…] in pyproject.toml)"))
    return findings


def _linter_configured(root: pathlib.Path, linter: str) -> bool:
    if (root / f"{linter}.toml").is_file() or (root / f".{linter}.toml").is_file():
        return True
    pyproject = root / "pyproject.toml"
    return pyproject.is_file() and f"[tool.{linter}" in pyproject.read_text(encoding="utf-8")


class CheckService:
    def __init__(self, loader: ConfigLoader) -> None:
        self._loader = loader
        self._standards = StandardsLoader(loader.standards_dir)

    def check(self, root: pathlib.Path) -> list[Finding]:
        project = self._loader.load_project(root)
        if not project.standards:
            raise ConfigError(
                "no standards configured — set standards = [...] in .servan.toml")
        merged = self._standards.load_all(project.standards)
        findings = find_forbidden_literals(root, merged.sections.get("forbidden", {}))
        findings += check_tooling(root, merged.sections.get("tooling", {}))
        _log.info("check %s: %d findings", root, len(findings))
        return findings
