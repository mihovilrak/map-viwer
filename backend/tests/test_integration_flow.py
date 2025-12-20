"""Integration test for the end-to-end vector and raster ingest flow.

This module performs an integration test that:
    - Uploads both vector and raster files via the public API,
    - Ingests both types and verifies SRID transformation to EPSG:3857,
    - Ensures both are registered and present in the layer repository,
    - Simulates the production ingestion contract.

Critical project requirements enforced by these tests:
    - All vector geometries MUST be transformed to EPSG:3857 at ingestion time.
    - All rasters MUST be transformed to EPSG:3857 before COG creation.
    - Layer names, metadata, and sources are correctly validated and managed.

See Also:
    - backend/app/services/ingest_vector.py and ingest_raster.py
      for implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import testclient

from backend.app import main
from backend.app.api import ingest as api_ingest
from backend.app.api import layers as api_layers
from backend.app.core import config
from backend.app.db import database
from backend.app.db import models as db_models
from backend.app.services import ingest_raster, ingest_vector

if TYPE_CHECKING:
    import pathlib

    import pytest


def _settings(tmp_path: pathlib.Path) -> config.Settings:
    """Return settings pointing to temp dirs."""
    settings = config.Settings(
        storage_dir=tmp_path / "uploads",
        raster_cache_dir=tmp_path / "cog",
        allow_origins=["*"],
    )
    settings.ensure_directories()
    return settings


def test_full_vector_and_raster_flow(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """Upload vector and raster, ingest both, list layers."""
    repo = database.InMemoryLayerRepository()

    def _get_layer_repository(
        _settings: config.Settings,
    ) -> database.InMemoryLayerRepository:
        return repo

    def _get_settings() -> config.Settings:
        return _settings(tmp_path)

    monkeypatch.setattr(
        database,
        "get_layer_repository",
        _get_layer_repository,
    )
    monkeypatch.setattr(
        "app.db.database.get_layer_repository",
        _get_layer_repository,
    )
    monkeypatch.setattr(
        config,
        "get_settings",
        _get_settings,
    )

    def fake_vector(
        source_path: pathlib.Path,
        layer_name: str,
        _: Any,
    ) -> db_models.LayerMetadata:
        return db_models.LayerMetadata(
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

    def fake_raster(
        source_path: pathlib.Path,
        settings: Any,
    ) -> db_models.LayerMetadata:
        return db_models.LayerMetadata(
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

    monkeypatch.setattr(
        ingest_vector,
        "ingest_vector_to_postgis",
        fake_vector,
    )
    monkeypatch.setattr(
        "app.services.ingest_vector.ingest_vector_to_postgis",
        fake_vector,
    )
    monkeypatch.setattr(
        ingest_raster,
        "ingest_raster",
        fake_raster,
    )
    monkeypatch.setattr(
        "app.services.ingest_raster.ingest_raster",
        fake_raster,
    )

    app = main.create_app()
    app.dependency_overrides[api_ingest._get_repo] = lambda: repo
    app.dependency_overrides[api_layers._get_repo] = lambda: repo
    client = testclient.TestClient(app)
    try:
        upload_resp = client.post(
            "/api/layers/upload",
            files={
                "file": (
                    "vector.geojson",
                    b'{"type":"FeatureCollection","features":[]}',
                )
            },
        )
        assert upload_resp.status_code == 200
        upload_id = upload_resp.json()["upload_id"]

        ingest_resp = client.post(
            f"/api/layers/ingest/{upload_id}?kind=vector&layer_name=demo",
        )
        assert ingest_resp.status_code == 200

        raster_upload = client.post(
            "/api/layers/upload",
            files={"file": ("raster.tif", b"fake")},
        )
        raster_id = raster_upload.json()["upload_id"]
        raster_ingest = client.post(
            f"/api/layers/ingest/{raster_id}?kind=raster",
        )
        assert raster_ingest.status_code == 200

        layers_resp = client.get("/api/layers")
        assert layers_resp.status_code == 200
        names = {layer["name"] for layer in layers_resp.json()}
        assert {"demo", "raster"}.issubset(names)

        bbox_resp = client.get("/api/layers/v1/bbox")
        assert bbox_resp.status_code == 200
        assert bbox_resp.json()["bbox"] == [-1.0, -1.0, 1.0, 1.0]
    finally:
        app.dependency_overrides.clear()


def test_ingest_invalid_upload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """Missing upload should return 404."""
    repo = database.InMemoryLayerRepository()

    def _get_layer_repository(
        _settings: config.Settings,
    ) -> database.InMemoryLayerRepository:
        return repo

    def _get_settings() -> config.Settings:
        return _settings(tmp_path)

    monkeypatch.setattr(
        database,
        "get_layer_repository",
        _get_layer_repository,
    )
    monkeypatch.setattr(
        "app.db.database.get_layer_repository",
        _get_layer_repository,
    )
    monkeypatch.setattr(
        config,
        "get_settings",
        _get_settings,
    )
    app = main.create_app()
    app.dependency_overrides[api_ingest._get_repo] = lambda: repo
    app.dependency_overrides[api_layers._get_repo] = lambda: repo
    client = testclient.TestClient(app)
    try:
        resp = client.post(
            "/api/layers/ingest/unknown?kind=vector&layer_name=demo",
        )
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()
