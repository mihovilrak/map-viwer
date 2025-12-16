"""Additional ingestion and validation tests."""

import io
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile

from app.api.ingest import _save_upload, _validate_layer_name
from app.services import ingest_raster, ingest_vector


def test_validate_layer_name_rejects_invalid():
    with pytest.raises(HTTPException):
        _validate_layer_name("bad-name!")


def test_save_upload_respects_size(tmp_path):
    file = UploadFile(filename="big.bin", file=io.BytesIO(b"a" * 5))
    with pytest.raises(HTTPException):
        _save_upload(file, tmp_path, max_size=4)


def test_ingest_raster_sets_bbox(monkeypatch, tmp_path):
    cog = tmp_path / "in.tif"
    cog.write_bytes(b"tif")

    class FakeCOGReader:
        def __init__(self, path):
            self.path = path

        def __enter__(self):
            class Bounds:
                left, bottom, right, top = (1.0, 2.0, 3.0, 4.0)

            self.bounds = Bounds()
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(ingest_raster, "COGReader", FakeCOGReader)
    settings = ingest_raster.Settings(raster_cache_dir=tmp_path, storage_dir=tmp_path)
    settings.ensure_directories()
    meta = ingest_raster.ingest_raster(cog, settings)
    assert meta.bbox == (1.0, 2.0, 3.0, 4.0)


def test_ingest_vector_calls_metadata(monkeypatch, tmp_path):
    src = tmp_path / "vec.geojson"
    src.write_text("{}")
    called = {}

    def fake_run(cmd, workdir=None):
        called["run_command"] = True

    def fake_fetch(table_name, settings):
        return "Polygon", 4326, (0.0, 0.0, 1.0, 1.0)

    monkeypatch.setattr(ingest_vector, "run_command", fake_run)
    monkeypatch.setattr(ingest_vector, "_fetch_metadata", fake_fetch)
    settings = ingest_vector.Settings(storage_dir=tmp_path, raster_cache_dir=tmp_path)
    settings.ensure_directories()
    meta = ingest_vector.ingest_vector_to_postgis(src, "demo", settings)

    assert called.get("run_command") is True
    assert meta.geom_type == "Polygon"
    assert meta.srid == 4326
    assert meta.bbox == (0.0, 0.0, 1.0, 1.0)

