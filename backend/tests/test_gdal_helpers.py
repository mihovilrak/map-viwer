"""Unit tests for utilities in backend.app.utils.gdal_helpers.

This module tests the low-level GDAL/ogr command execution helpers,
specifically the `run_command` function and CommandError handling.
Tests cover:
    - Successful command execution (zero exit code)
    - Failure handling and error message propagation (nonzero exit code)

Monkeypatching is used to avoid actual subprocess execution, ensuring tests
are isolated, fast, and reliable.

See Also:
    - backend/app/utils/gdal_helpers.py for implementation details.
"""

import subprocess
from typing import Any

import pytest

from backend.app.utils import gdal_helpers


def test_run_command_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Command with zero return code should pass."""

    def fake_run(
        *args: Any,
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        """Mock subprocess.run to return a successful CompletedProcess."""
        return subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="ok",
            stderr="",
        )

    monkeypatch.setattr(gdal_helpers.subprocess, "run", fake_run)
    gdal_helpers.run_command(["echo", "ok"])


def test_run_command_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Command errors raise CommandError with message."""

    def fake_run(
        *args: Any,
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr="fail",
        )

    monkeypatch.setattr(gdal_helpers.subprocess, "run", fake_run)
    with pytest.raises(gdal_helpers.CommandError):
        gdal_helpers.run_command(["false"])
