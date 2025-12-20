"""Additional ingestion and validation tests."""

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
        ingest._validate_layer_name(  # type: ignore[reportPrivateUsage]
            "bad-name!",
        )


def test_save_upload_respects_size(tmp_path: pathlib.Path) -> None:
    file = fastapi.UploadFile(filename="big.bin", file=io.BytesIO(b"a" * 5))
    with pytest.raises(fastapi.HTTPException):
        ingest._save_upload(  # type: ignore[reportPrivateUsage]
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
        def __init__(self, path: pathlib.Path) -> None:
            self.path = path

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

    monkeypatch.setattr(ingest_raster, "COGReader", FakeCOGReader)
    monkeypatch.setattr(ingest_raster, "convert_to_cog", fake_convert_to_cog)
    settings = config.Settings(raster_cache_dir=tmp_path, storage_dir=tmp_path)
    settings.ensure_directories()
    meta = ingest_raster.ingest_raster(cog, settings)
    assert meta.bbox == (1.0, 2.0, 3.0, 4.0)


def test_ingest_vector_calls_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    src: pathlib.Path = tmp_path / "vec.geojson"
    src.write_text("{}")
    called: dict[str, Any] = {}

    def fake_run(cmd: Any, workdir: pathlib.Path | None = None) -> None:
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
