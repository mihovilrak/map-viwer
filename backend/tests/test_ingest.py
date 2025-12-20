"""Tests for upload and ingest routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import testclient

from backend.app import main
from backend.app.core import config
from backend.app.db import database
from backend.app.db import models as db_models

if TYPE_CHECKING:
    import pathlib

    import pytest


def _test_settings(tmp_path: pathlib.Path) -> config.Settings:
    settings = config.Settings(
        storage_dir=tmp_path / "uploads",
        raster_cache_dir=tmp_path / "cog",
        allow_origins=["*"],
    )
    settings.ensure_directories()
    return settings


def test_upload_and_ingest_vector(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """Uploading then ingesting a vector should store metadata."""
    repo = database.InMemoryLayerRepository()

    def get_test_settings() -> config.Settings:
        return _test_settings(tmp_path)

    def get_test_repo(
        settings: config.Settings,
    ) -> database.LayerRepositoryProtocol:
        return repo

    monkeypatch.setattr(config, "get_settings", get_test_settings)
    monkeypatch.setattr(database, "get_layer_repository", get_test_repo)
    monkeypatch.setattr("app.api.ingest.get_layer_repository", get_test_repo)
    monkeypatch.setattr("app.api.layers.get_layer_repository", get_test_repo)

    def fake_ingest(
        source_path: pathlib.Path,
        layer_name: str,
        settings: config.Settings,
    ) -> db_models.LayerMetadata:
        return db_models.LayerMetadata(
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

    monkeypatch.setattr(
        "app.api.ingest.ingest_vector_to_postgis",
        fake_ingest,
    )
    app = main.create_app()
    client = testclient.TestClient(app)

    upload_resp = client.post(
        "/api/layers/upload",
        files={
            "file": (
                "test.geojson",
                b'{"type":"FeatureCollection","features":[]}',
            )
        },
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
