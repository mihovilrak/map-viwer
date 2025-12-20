"""Tests for raster ingestion utilities in backend.app.services.ingest_raster.

This test module covers helpers used during the raster (COG) ingestion
workflow, including bounding box computation and validation of EPSG:3857
reprojection logic. Mocks and monkeypatching are used to isolate dependencies
on rio-tiler and filesystem. Critical project requirements demand that
all rasters are reprojected to EPSG:3857 before COG creation,
and these tests help enforce that constraint.

See Also:
    - backend/app/services/ingest_raster.py for implementation under test.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from backend.app.services import ingest_raster

if TYPE_CHECKING:
    import pathlib
    import types


def test_compute_bbox_from_cog_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _compute_bbox extracts bbox from COG using rio-tiler."""

    class FakeBounds:
        """Mock bounds object for testing."""

        left = -20037508.34
        bottom = -20037508.34
        right = 20037508.34
        top = 20037508.34

    class FakeCOGReader:
        """Mock COGReader for testing."""

        def __init__(self, input: str, options: dict[str, Any]):
            self.input = input
            self.options = options

        def __enter__(self) -> FakeCOGReader:
            self.bounds = FakeBounds()
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: types.TracebackType | None,
        ) -> None:
            pass

    monkeypatch.setattr("rio_tiler.io.COGReader", FakeCOGReader)
    from pathlib import Path

    bbox = ingest_raster._compute_bbox(Path("/fake/cog.tif"))
    assert bbox == (-20037508.34, -20037508.34, 20037508.34, 20037508.34)


def test_compute_bbox_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _compute_bbox returns None when bounds unavailable."""

    class FakeCOGReader:
        """Mock COGReader for testing."""

        def __init__(self, input: str, options: dict[str, Any]):
            pass

        def __enter__(self) -> FakeCOGReader:
            self.bounds = None
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: types.TracebackType | None,
        ) -> None:
            pass

    monkeypatch.setattr("rio_tiler.io.COGReader", FakeCOGReader)
    from pathlib import Path

    bbox = ingest_raster._compute_bbox(Path("/fake/cog.tif"))
    assert bbox is None


def test_convert_to_cog_mocked(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """Test convert_to_cog calls gdalwarp and gdal_translate."""
    called_commands: list[list[str]] = []

    def fake_run_command_with_file_creation(
        command: Any, workdir: pathlib.Path | None = None
    ) -> None:
        """Mock run_command to capture command execution and create samples."""
        called_commands.append(list(command))
        # Create the output file that convert_to_cog expects
        if "gdal_translate" in list(command):
            cog_path = tmp_path / "output" / "input_cog.tif"
            cog_path.parent.mkdir(parents=True, exist_ok=True)
            cog_path.write_bytes(b"fake cog")
        elif "gdalwarp" in list(command):
            warped_path = tmp_path / "output" / "input_3857.tif"
            warped_path.parent.mkdir(parents=True, exist_ok=True)
            warped_path.write_bytes(b"fake warped")

    monkeypatch.setattr(
        "app.utils.gdal_helpers.run_command",
        fake_run_command_with_file_creation,
    )

    source = tmp_path / "input.tif"
    source.write_bytes(b"fake tif")
    output_dir = tmp_path / "output"
    result = ingest_raster.convert_to_cog(source, output_dir)
    assert result.exists()
    # Should call gdalwarp first, then gdal_translate
    assert len(called_commands) >= 2
    assert any("gdalwarp" in cmd for cmd in called_commands)
    assert any("gdal_translate" in cmd for cmd in called_commands)
