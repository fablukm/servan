"""File-only logging. No console handlers anywhere; `typer.echo` in cli/ is the sole UI channel."""
from __future__ import annotations

import logging
import logging.handlers
import os
import pathlib

_FORMAT = "%(asctime)s %(levelname)-7s %(name)s :: %(message)s"


def configure_logging(project_root: pathlib.Path | None = None) -> pathlib.Path:
    """Attach a rotating file handler to the 'servan' logger tree. Returns the log path."""
    if project_root is not None and (project_root / ".servan").exists():
        log_dir = project_root / ".servan" / "logs"
    else:
        state = pathlib.Path(os.environ.get("XDG_STATE_HOME", pathlib.Path.home() / ".local/state"))
        log_dir = state / "servan"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "servan.log"

    root = logging.getLogger("servan")
    root.setLevel(os.environ.get("SERVAN_LOG_LEVEL", "INFO").upper())
    root.propagate = False
    if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in root.handlers):
        handler = logging.handlers.RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3)
        handler.setFormatter(logging.Formatter(_FORMAT))
        root.addHandler(handler)
    return log_path


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"servan.{name}")
