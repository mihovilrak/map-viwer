"""Additional ingestion and validation tests."""

import io
from pathlib import Path
from types import TracebackType
from typing import Any, Optional, Type

import pytest
from fastapi import HTTPException, UploadFile
from pytest import MonkeyPatch

from backend.app.api.ingest import (
    _save_upload,  # type: ignore[reportPrivateUsage]
    _validate_layer_name,  # type: ignore[reportPrivateUsage]
)
from backend.app.core import config
from backend.app.services import ingest_raster, ingest_vector


def test_validate_layer_name_rejects_invalid() -> None:
    with pytest.raises(HTTPException):
        _validate_layer_name("bad-name!")


def test_save_upload_respects_size(tmp_path: Path) -> None:
    file = UploadFile(filename="big.bin", file=io.BytesIO(b"a" * 5))
    with pytest.raises(HTTPException):
        _save_upload(file, tmp_path, max_size=4)


def test_ingest_raster_sets_bbox(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    cog: Path = tmp_path / "in.tif"
    cog.write_bytes(b"tif")

    class FakeCOGReader:
        def __init__(self, path: Path) -> None:
            self.path = path

        def __enter__(self) -> "FakeCOGReader":
            class Bounds:
                left, bottom, right, top = (1.0, 2.0, 3.0, 4.0)

            self.bounds = Bounds()
            return self

        def __exit__(
            self,
            exc_type: Optional[Type[BaseException]],
            exc: Optional[BaseException],
            tb: Optional[TracebackType],
        ) -> None:
            return None

    def fake_convert_to_cog(source_path: Path, output_dir: Path) -> Path:
        """Mock convert_to_cog to avoid running gdal_translate on fake file."""
        output_dir.mkdir(parents=True, exist_ok=True)
        cog_path = output_dir / f"{source_path.stem}_cog.tif"
        cog_path.write_bytes(b"fake_cog")
        return cog_path

    monkeypatch.setattr(ingest_raster, "COGReader", FakeCOGReader)
    monkeypatch.setattr(ingest_raster, "convert_to_cog", fake_convert_to_cog)
    settings = config.Settings(raster_cache_dir=tmp_path, storage_dir=tmp_path)
    settings.ensure_directories()
    meta = ingest_raster.ingest_raster(cog, settings)
    assert meta.bbox == (1.0, 2.0, 3.0, 4.0)


def test_ingest_vector_calls_metadata(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    src: Path = tmp_path / "vec.geojson"
    src.write_text("{}")
    called: dict[str, Any] = {}

    def fake_run(cmd: Any, workdir: Path | None = None) -> None:
        called["run_command"] = True

    def fake_fetch(
        table_name: str, settings: config.Settings
    ) -> tuple[str, int, tuple[float, float, float, float]]:
        return "Polygon", 4326, (0.0, 0.0, 1.0, 1.0)

    monkeypatch.setattr(ingest_vector, "run_command", fake_run)
    monkeypatch.setattr(ingest_vector, "_fetch_metadata", fake_fetch)
    settings = config.Settings(storage_dir=tmp_path, raster_cache_dir=tmp_path)
    settings.ensure_directories()
    meta = ingest_vector.ingest_vector_to_postgis(src, "demo", settings)

    assert called.get("run_command") is True
    assert meta.geom_type == "Polygon"
    assert meta.srid == 4326
    assert meta.bbox == (0.0, 0.0, 1.0, 1.0)

