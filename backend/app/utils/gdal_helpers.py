"""Safe execution wrapper for GDAL/OGR command-line utilities.

This module provides a safe interface for executing GDAL and OGR command-line
tools (ogr2ogr, gdalwarp, gdal_translate, etc.) as subprocesses. It handles
error checking and provides clear error messages when commands fail.

All commands are executed with proper error handling, and non-zero exit codes
result in CommandError exceptions with the command's stderr output.

Example:
    Execute ogr2ogr command:
        >>> from app.utils.gdal_helpers import run_command, CommandError

        >>> try:
        ...     run_command([
        ...         "ogr2ogr",
        ...         "-f", "PostgreSQL",
        ...         "postgresql://user:pass@localhost/db",
        ...         "data.shp",
        ...         "-t_srs", "EPSG:3857"
        ...     ])
        ... except CommandError as e:
        ...     print(f"Command failed: {e}")

    Execute gdalwarp command:
        >>> run_command([
        ...     "gdalwarp",
        ...     "-t_srs", "EPSG:3857",
        ...     "-r", "bilinear",
        ...     "input.tif",
        ...     "output.tif"
        ... ])
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pathlib
    from collections.abc import Iterable


class CommandError(RuntimeError):
    """Exception raised when a GDAL/OGR subprocess command fails.

    Contains the error message from the failed command's stderr output.
    This exception is raised when any GDAL/OGR command (ogr2ogr, gdalwarp,
    gdal_translate, etc.) exits with a non-zero status code.

    Example:
        Handle command failures:
            >>> from app.utils.gdal_helpers import run_command, CommandError

            >>> try:
            ...     run_command(["ogr2ogr", "-f", "PostgreSQL", ...])
            ... except CommandError as e:
            ...     print(f"GDAL command failed: {e}")
            ...     # e contains the stderr output from the failed command
    """


def run_command(
    command: Iterable[str | pathlib.Path],
    workdir: pathlib.Path | None = None,
) -> None:
    """Execute a command and raise on non-zero exit.

    Runs a GDAL/OGR command-line tool as a subprocess with proper error
    handling. Captures both stdout and stderr, and raises CommandError
    if the command fails. This provides a safe wrapper around subprocess
    execution for GDAL utilities.

    Args:
        command: Iterable arguments to execute (e.g., ["ogr2ogr", "-f", ...]).
        workdir: Optional working directory for the command execution.

    Raises:
        CommandError: if the command exits with a non-zero status code.
            The exception message contains the stderr output from the command.

    Example:
        Execute ogr2ogr command:
            >>> from app.utils.gdal_helpers import run_command, CommandError

            >>> try:
            ...     run_command([
            ...         "ogr2ogr",
            ...        "-f", "PostgreSQL",
            ...        "postgresql://user:pass@localhost/db",
            ...        "data.shp",
            ...        "-t_srs", "EPSG:3857"
            ...    ])
            ... except CommandError as e:
            ...     print(f"Import failed: {e}")

        Execute gdalwarp with working directory:
            >>> run_command(
            ...     ["gdalwarp", "-t_srs", "EPSG:3857", "in.tif", "out.tif"],
            ...     workdir=pathlib.Path("/tmp")
            ... )
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
