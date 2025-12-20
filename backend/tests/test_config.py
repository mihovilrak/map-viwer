"""Tests for application configuration and settings.

This module contains unit tests for the Settings Pydantic model and
application configuration logic in backend.app.core.config. It ensures
that default values, directory creation logic, and get_settings
caching work as expected.

All tests are safe to run in isolation. Temporary directories are used
to verify filesystem interactions where needed.
"""

from __future__ import annotations

import pathlib

from backend.app.core import config


def test_settings_defaults() -> None:
    """Test that Settings has expected default values."""
    settings = config.Settings()
    assert settings.database_url == "postgresql://gis:gis@localhost:5432/gis"
    assert settings.max_upload_size_bytes == 512 * 1024 * 1024
    assert settings.allow_origins == ["*"]


def test_settings_ensure_directories(tmp_path: pathlib.Path) -> None:
    """Test that ensure_directories creates required directories."""
    storage_dir = tmp_path / "uploads"
    cache_dir = tmp_path / "cog"
    settings = config.Settings(
        storage_dir=storage_dir,
        raster_cache_dir=cache_dir,
    )
    assert not storage_dir.exists()
    assert not cache_dir.exists()
    settings.ensure_directories()
    assert storage_dir.exists()
    assert cache_dir.exists()


def test_get_settings_cached() -> None:
    """Test that get_settings returns cached instance."""
    config.get_settings.cache_clear()
    settings1 = config.get_settings()
    settings2 = config.get_settings()
    assert settings1 is settings2
    config.get_settings.cache_clear()


def test_get_settings_creates_directories(tmp_path: pathlib.Path) -> None:
    """Test that get_settings ensures directories exist."""
    config.get_settings.cache_clear()
    storage_dir = tmp_path / "uploads"
    cache_dir = tmp_path / "cog"
    settings = config.Settings(
        storage_dir=storage_dir,
        raster_cache_dir=cache_dir,
    )
    original_settings = config.Settings
    config.Settings = lambda: settings  # type: ignore[misc, assignment]
    try:
        result = config.get_settings()
        assert result.storage_dir.exists()
        assert result.raster_cache_dir.exists()
    finally:
        config.Settings = original_settings  # type: ignore[misc, assignment]
        config.get_settings.cache_clear()


def test_settings_custom_values() -> None:
    """Test Settings with custom values."""
    settings = config.Settings(
        database_url="postgresql://test:test@localhost:5432/test",
        max_upload_size_bytes=1024,
        allow_origins=["http://localhost:3000"],
    )
    assert settings.database_url == "postgresql://test:test@localhost:5432/test"
    assert settings.max_upload_size_bytes == 1024
    assert settings.allow_origins == ["http://localhost:3000"]
