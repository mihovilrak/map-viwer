"""Tests for GDAL helper utilities."""

from subprocess import CompletedProcess
from typing import Any

import pytest
from pytest import MonkeyPatch

from backend.app.utils import gdal_helpers


def test_run_command_success(monkeypatch: MonkeyPatch) -> None:
    """Command with zero return code should pass."""

    def fake_run(*args: Any, **kwargs: Any) -> CompletedProcess[str]:
        return CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(gdal_helpers.subprocess, "run", fake_run)
    gdal_helpers.run_command(["echo", "ok"])


def test_run_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Command errors raise CommandError with message."""

    def fake_run(*args: Any, **kwargs: Any) -> CompletedProcess[str]:
        return CompletedProcess(args=[], returncode=1, stdout="", stderr="fail")

    monkeypatch.setattr(gdal_helpers.subprocess, "run", fake_run)
    with pytest.raises(gdal_helpers.CommandError):
        gdal_helpers.run_command(["false"])

