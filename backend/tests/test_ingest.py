"""Tests for upload and ingest routes."""

from pathlib import Path

from fastapi.testclient import TestClient

from app import main
from app.api import ingest as ingest_api
from app.core import config
from app.db import database
from app.db.database import InMemoryLayerRepository
from app.db.models import LayerMetadata


def _test_settings(tmp_path: Path) -> config.Settings:
    settings = config.Settings(
        storage_dir=tmp_path / "uploads",
        raster_cache_dir=tmp_path / "cog",
        allow_origins=["*"],
    )
    settings.ensure_directories()
    return settings


def test_upload_and_ingest_vector(monkeypatch, tmp_path):
    """Uploading then ingesting a vector should store metadata."""
    repo = InMemoryLayerRepository()
    monkeypatch.setattr(config, "get_settings", lambda: _test_settings(tmp_path))
    monkeypatch.setattr(database, "get_layer_repository", lambda settings: repo)

    def fake_ingest(source_path, layer_name, settings):
        return LayerMetadata(
            id="123",
            name=layer_name,
            source=str(source_path),
            provider="postgis",
            table_name=layer_name,
            geom_type="Polygon",
            srid=4326,
            bbox=None,
            local_path=None,
        )

    monkeypatch.setattr(ingest_api, "ingest_vector_to_postgis", fake_ingest)
    app = main.create_app()
    client = TestClient(app)

    upload_resp = client.post(
        "/api/layers/upload",
        files={"file": ("test.geojson", b"{\"type\":\"FeatureCollection\",\"features\":[]}")},
    )
    assert upload_resp.status_code == 200
    upload_id = upload_resp.json()["upload_id"]

    ingest_resp = client.post(
        f"/api/layers/ingest/{upload_id}?kind=vector&layer_name=demo"
    )
    assert ingest_resp.status_code == 200
    body = ingest_resp.json()
    assert body["name"] == "demo"
    assert body["provider"] == "postgis"

    layers_resp = client.get("/api/layers")
    assert layers_resp.status_code == 200
    assert len(layers_resp.json()) == 1

