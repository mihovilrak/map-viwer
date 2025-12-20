"""Validation tests for ingest endpoints and helpers.

This module provides unit tests that verify validation logic for
the backend ingestion APIs, including:
  - Layer name validation rules,
  - File size enforcement during upload,
  - BBox setting/checking after raster ingestion.

Critical requirements are enforced, including proper error handling for
invalid input and file size, ensuring robustness and contract adherence
to project Instructions.md.

See Also:
    - backend/app/api/ingest.py for API and validation implementation.
    - backend/app/services/ingest_raster.py for raster ingest logic.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, Any

import fastapi
import pytest

from backend.app.api import ingest
from backend.app.core import config
from backend.app.services import ingest_raster, ingest_vector

if TYPE_CHECKING:
    import pathlib
    import types


def test_validate_layer_name_rejects_invalid() -> None:
    with pytest.raises(fastapi.HTTPException):
        ingest._validate_layer_name(
            "bad-name!",
        )


def test_save_upload_respects_size(tmp_path: pathlib.Path) -> None:
    file = fastapi.UploadFile(filename="big.bin", file=io.BytesIO(b"a" * 5))
    with pytest.raises(fastapi.HTTPException):
        ingest._save_upload(
            file,
            tmp_path,
            max_size=4,
        )


def test_ingest_raster_sets_bbox(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    cog: pathlib.Path = tmp_path / "in.tif"
    cog.write_bytes(b"tif")

    class FakeCOGReader:
        """Mock COGReader for testing."""

        def __init__(self, input: str, options: dict[str, Any]):
            self.path = input

        def __enter__(self) -> FakeCOGReader:
            class Bounds:
                left, bottom, right, top = (1.0, 2.0, 3.0, 4.0)

            self.bounds = Bounds()
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: types.TracebackType | None,
        ) -> None:
            return None

    def fake_convert_to_cog(
        source_path: pathlib.Path,
        output_dir: pathlib.Path,
    ) -> pathlib.Path:
        """Mock convert_to_cog to avoid running gdal_translate on fake file."""
        output_dir.mkdir(parents=True, exist_ok=True)
        cog_path = output_dir / f"{source_path.stem}_cog.tif"
        cog_path.write_bytes(b"fake_cog")
        return cog_path

    monkeypatch.setattr("rio_tiler.io.COGReader", FakeCOGReader)
    monkeypatch.setattr(ingest_raster, "convert_to_cog", fake_convert_to_cog)
    settings = config.Settings(raster_cache_dir=tmp_path, storage_dir=tmp_path)
    settings.ensure_directories()
    meta = ingest_raster.ingest_raster(cog, settings)
    assert meta.bbox == (1.0, 2.0, 3.0, 4.0)


def test_ingest_vector_calls_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """Test ingest_vector_to_postgis calls metadata extraction."""
    src: pathlib.Path = tmp_path / "vec.geojson"
    src.write_text("{}")
    called: dict[str, Any] = {}

    def fake_run(cmd: Any, workdir: pathlib.Path | None = None) -> None:
        """Mock run_command to capture command execution."""
        called["run_command"] = True

    def fake_fetch(
        table_name: str,
        settings: config.Settings,
    ) -> ingest_vector.VectorMetadata:
        """Mock _fetch_metadata to return test metadata."""
        return ingest_vector.VectorMetadata(
            geom_type="Polygon",
            srid=4326,
            bbox=(0.0, 0.0, 1.0, 1.0),
        )

    monkeypatch.setattr("app.utils.gdal_helpers.run_command", fake_run)
    monkeypatch.setattr(ingest_vector, "_fetch_metadata", fake_fetch)
    settings = config.Settings(storage_dir=tmp_path, raster_cache_dir=tmp_path)
    settings.ensure_directories()
    meta = ingest_vector.ingest_vector_to_postgis(src, "demo", settings)

    assert called.get("run_command") is True
    assert meta.geom_type == "Polygon"
    assert meta.srid == 4326
    assert meta.bbox == (0.0, 0.0, 1.0, 1.0)
