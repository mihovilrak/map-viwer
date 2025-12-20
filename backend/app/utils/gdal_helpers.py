"""Helpers for calling GDAL/OGR utilities safely."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pathlib
    from collections.abc import Iterable


class CommandError(RuntimeError):
    """Exception raised when a GDAL/OGR subprocess command fails.

    Contains the error message from the failed command's stderr output.
    """


def run_command(
    command: Iterable[str | pathlib.Path],
    workdir: pathlib.Path | None = None,
) -> None:
    """Execute a command and raise on non-zero exit.

    Args:
        command: Iterable arguments to execute.
        workdir: Optional working directory for the command.

    Raises:
        CommandError: if the command exits with a non-zero status.
    """
    result = subprocess.run(
        list(command),
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise CommandError(result.stderr.strip() or "Unknown command failure")
