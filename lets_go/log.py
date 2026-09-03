"""Small logging setup so our own log lines reach the Streamlit Cloud log pane.

We attach one stderr handler to the `lets_go` package logger at INFO and stop it
propagating to the root logger (avoids duplicate lines). Modules get a child
logger via `get_logger(__name__)`. We log milestones (info) and problems
(warning/error) — real exceptions still surface loudly (CLAUDE.md)."""

import logging
import sys

_ROOT = "lets_go"
_configured = False


def get_logger(name: str = _ROOT) -> logging.Logger:
    global _configured
    if not _configured:
        pkg = logging.getLogger(_ROOT)
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        pkg.addHandler(handler)
        pkg.setLevel(logging.INFO)
        pkg.propagate = False
        _configured = True
    return logging.getLogger(name)
