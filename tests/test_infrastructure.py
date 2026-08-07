"""SubprocessRunner — the single choke point for external commands (e2e-found:
Windows npm shims are .cmd, unfindable by CreateProcess without which-resolution;
a missing exe must be a fail-loud ProcessError, not a raw FileNotFoundError)."""
import sys

import pytest

from servan.errors import ProcessError
from servan.infrastructure import SubprocessRunner


def test_missing_executable_is_a_fail_loud_process_error():
    with pytest.raises(ProcessError, match="not found"):
        SubprocessRunner().run("definitely-not-a-real-exe-servan-e2e", "--version")


def test_runs_and_returns_stdout():
    out = SubprocessRunner().run(sys.executable, "-c", "print('ok')")
    assert out.strip() == "ok"


def test_nonzero_exit_raises_with_stderr():
    with pytest.raises(ProcessError, match="boom"):
        SubprocessRunner().run(sys.executable, "-c",
                               "import sys; sys.stderr.write('boom'); sys.exit(3)")
