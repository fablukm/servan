"""CanaryRunner — golden-bead regression check before a model swap (S-10).
Runs each side in a scratch git worktree; compares pass rates."""
from __future__ import annotations

import pathlib
import shutil
import tempfile
from dataclasses import dataclass

from ..abstractions import ProcessRunner
from ..config.errors import ConfigError
from ..config.global_config import GlobalConfig
from ..config.project_config import ProjectConfig
from ..logging_setup import get_logger
from ..team.resolved_model import ResolvedModel
from ..team.resolver import TeamResolver
from .trial import BeadTrial

_log = get_logger("canary.runner")


@dataclass(frozen=True, slots=True)
class CanaryReport:
    role: str
    incumbent: str
    candidate: str
    incumbent_pass_rate: float
    candidate_pass_rate: float

    @property
    def regressed(self) -> bool:
        return self.candidate_pass_rate < self.incumbent_pass_rate


class CanaryRunner:
    def __init__(self, config: GlobalConfig, trial: BeadTrial, runner: ProcessRunner) -> None:
        self._config = config
        self._trial = trial
        self._runner = runner

    def run(self, root: pathlib.Path, project: ProjectConfig,
            role: str, candidate_alias: str) -> CanaryReport:
        team = TeamResolver(self._config).resolve(project)
        incumbent = team.get(role)
        if incumbent is None:
            raise ConfigError(f"role '{role}' not in profile — defined: {sorted(team)}")
        candidate = self._resolve_alias(candidate_alias)
        beads = self._golden_beads(root)
        incumbent_rate = self._pass_rate(root, beads, "incumbent", incumbent)
        candidate_rate = self._pass_rate(root, beads, "candidate", candidate)
        return CanaryReport(role, incumbent.alias, candidate.alias,
                            incumbent_rate, candidate_rate)

    def _resolve_alias(self, alias: str) -> ResolvedModel:
        spec = self._config.models.get(alias)
        if spec is None:
            raise ConfigError(f"unknown model alias '{alias}' — not in models.toml")
        return ResolvedModel.from_spec(alias, spec, self._config.providers[spec.provider])

    @staticmethod
    def _golden_beads(root: pathlib.Path) -> list[pathlib.Path]:
        golden = root / "tasks" / "golden"
        beads = sorted(golden.glob("*.md")) if golden.is_dir() else []
        if not beads:
            raise ConfigError(f"no golden beads at {golden} — add tasks/golden/*.md")
        return beads

    def _pass_rate(self, root: pathlib.Path, beads: list[pathlib.Path],
                   label: str, model: ResolvedModel) -> float:
        scratch = pathlib.Path(tempfile.mkdtemp(prefix=f"servan-canary-{label}-"))
        self._runner.run("git", "worktree", "add", "--detach", str(scratch), "HEAD", cwd=root)
        try:
            passed = sum(1 for bead in beads if self._trial.trial(scratch, bead, model))
        finally:
            self._runner.run("git", "worktree", "remove", "--force", str(scratch), cwd=root)
            shutil.rmtree(scratch, ignore_errors=True)
        _log.info("canary %s (%s): %d/%d passed", label, model.alias, passed, len(beads))
        return passed / len(beads)
