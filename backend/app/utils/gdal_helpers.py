"""Helpers for calling GDAL/OGR utilities safely."""

import subprocess
from pathlib import Path
from typing import Iterable, List


class CommandError(RuntimeError):
    """Raised when a subprocess call fails."""


def run_command(command: Iterable[str], workdir: Path | None = None) -> None:
    """Execute a command and raise on non-zero exit.

    Args:
        command: Iterable arguments to execute.
        workdir: Optional working directory for the command.

    Raises:
        CommandError: if the command exits with a non-zero status.
    """
    result = subprocess.run(
        list(command), cwd=workdir, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise CommandError(result.stderr.strip() or "Unknown command failure")

