"""Tests for GDAL helper utilities."""

from subprocess import CompletedProcess

import pytest

from app.utils import gdal_helpers


def test_run_command_success(monkeypatch):
    """Command with zero return code should pass."""

    def fake_run(*args, **kwargs):
        return CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(gdal_helpers.subprocess, "run", fake_run)
    gdal_helpers.run_command(["echo", "ok"])


def test_run_command_failure(monkeypatch):
    """Command errors raise CommandError with message."""

    def fake_run(*args, **kwargs):
        return CompletedProcess(args=[], returncode=1, stdout="", stderr="fail")

    monkeypatch.setattr(gdal_helpers.subprocess, "run", fake_run)
    with pytest.raises(gdal_helpers.CommandError):
        gdal_helpers.run_command(["false"])

