"""Integration-style tests covering happy-path ingest and error handling."""

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app import main
from app.api import ingest as ingest_api
from app.core import config
from app.db import database
from app.db.database import InMemoryLayerRepository
from app.db.models import LayerMetadata


def _settings(tmp_path: Path) -> config.Settings:
    """Return settings pointing to temp dirs."""
    settings = config.Settings(
        storage_dir=tmp_path / "uploads",
        raster_cache_dir=tmp_path / "cog",
        allow_origins=["*"],
    )
    settings.ensure_directories()
    return settings


def test_full_vector_and_raster_flow(monkeypatch, tmp_path):
    """Upload vector and raster, ingest both, list layers."""
    repo = InMemoryLayerRepository()
    monkeypatch.setattr(database, "get_layer_repository", lambda settings: repo)
    monkeypatch.setattr(config, "get_settings", lambda: _settings(tmp_path))

    def fake_vector(source_path: Path, layer_name: str, settings: Any) -> LayerMetadata:
        return LayerMetadata(
            id="v1",
            name=layer_name,
            source=str(source_path),
            provider="postgis",
            table_name=layer_name,
            geom_type="Polygon",
            srid=4326,
            bbox=(-1.0, -1.0, 1.0, 1.0),
            local_path=None,
        )

    def fake_raster(source_path: Path, settings: Any) -> LayerMetadata:
        return LayerMetadata(
            id="r1",
            name=source_path.stem,
            source=str(source_path),
            provider="cog",
            table_name=None,
            geom_type="raster",
            srid=None,
            bbox=(0.0, 0.0, 10.0, 10.0),
            local_path=str(settings.raster_cache_dir / "mock.tif"),
        )

    monkeypatch.setattr(ingest_api, "ingest_vector_to_postgis", fake_vector)
    monkeypatch.setattr(ingest_api, "ingest_raster", fake_raster)

    app = main.create_app()
    client = TestClient(app)

    upload_resp = client.post(
        "/api/layers/upload",
        files={"file": ("vector.geojson", b"{\"type\":\"FeatureCollection\",\"features\":[]}")},
    )
    assert upload_resp.status_code == 200
    upload_id = upload_resp.json()["upload_id"]

    ingest_resp = client.post(f"/api/layers/ingest/{upload_id}?kind=vector&layer_name=demo")
    assert ingest_resp.status_code == 200

    raster_upload = client.post(
        "/api/layers/upload",
        files={"file": ("raster.tif", b"fake")},
    )
    raster_id = raster_upload.json()["upload_id"]
    raster_ingest = client.post(f"/api/layers/ingest/{raster_id}?kind=raster")
    assert raster_ingest.status_code == 200

    layers_resp = client.get("/api/layers")
    assert layers_resp.status_code == 200
    names = {layer["name"] for layer in layers_resp.json()}
    assert {"demo", "raster"}.issubset(names)

    bbox_resp = client.get("/api/layers/v1/bbox")
    assert bbox_resp.status_code == 200
    assert bbox_resp.json()["bbox"] == [-1.0, -1.0, 1.0, 1.0]


def test_ingest_invalid_upload(monkeypatch, tmp_path):
    """Missing upload should return 404."""
    repo = InMemoryLayerRepository()
    monkeypatch.setattr(database, "get_layer_repository", lambda settings: repo)
    monkeypatch.setattr(config, "get_settings", lambda: _settings(tmp_path))
    app = main.create_app()
    client = TestClient(app)
    resp = client.post("/api/layers/ingest/unknown?kind=vector&layer_name=demo")
    assert resp.status_code == 404

