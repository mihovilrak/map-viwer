"""Tests for upload and ingest routes."""

from pathlib import Path

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from backend.app import main
from backend.app.api import ingest as ingest_api
from backend.app.core import config
from backend.app.db import database
from backend.app.db.database import InMemoryLayerRepository, LayerRepositoryProtocol
from backend.app.db.models import LayerMetadata


def _test_settings(tmp_path: Path) -> config.Settings:
    settings = config.Settings(
        storage_dir=tmp_path / "uploads",
        raster_cache_dir=tmp_path / "cog",
        allow_origins=["*"],
    )
    settings.ensure_directories()
    return settings


def test_upload_and_ingest_vector(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Uploading then ingesting a vector should store metadata."""
    repo = InMemoryLayerRepository()
    
    def get_test_settings() -> config.Settings:
        return _test_settings(tmp_path)
    
    def get_test_repo(settings: config.Settings) -> LayerRepositoryProtocol:
        return repo
    
    monkeypatch.setattr(config, "get_settings", get_test_settings)
    monkeypatch.setattr(database, "get_layer_repository", get_test_repo)

    def fake_ingest(source_path: Path, layer_name: str, settings: config.Settings) -> LayerMetadata:
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

