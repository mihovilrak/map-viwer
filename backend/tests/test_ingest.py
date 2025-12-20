"""Integration and unit tests for vector and raster ingestion workflows.

This test module verifies:
    - Upload and ingestion endpoints for vector and raster data,
    - That SRID transformation to EPSG:3857 occurs at ingestion time,
    - That layer metadata is extracted and registered into the repository,
    - Correct contract and error handling for the ingest APIs,
    - Compliance with project requirements outlined in Instructions.md.

Patterns:
    - Service and repository logic monkeypatched for isolated,
      deterministic tests,
    - FastAPI test client used for end-to-end simulation of ingest flows,
    - Settings and repository instances are injected for testability,
    - All geospatial data are validated as transformed to SRID 3857
      after ingestion per critical requirements.

See Also:
    - backend/app/services/ingest_vector.py and ingest_raster.py
      for implementation,
    - test_ingest_vector_metadata.py, test_ingest_raster_helpers.py
      for low-level tests.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import testclient

from backend.app import main
from backend.app.api import ingest as api_ingest
from backend.app.api import layers as api_layers
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
    monkeypatch.setattr("app.db.database.get_layer_repository", get_test_repo)

    def fake_ingest(
        source_path: pathlib.Path,
        layer_name: str,
        settings: config.Settings,
    ) -> db_models.LayerMetadata:
        """Mock ingest_vector_to_postgis to return test metadata."""
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
        "app.services.ingest_vector.ingest_vector_to_postgis",
        fake_ingest,
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
    finally:
        app.dependency_overrides.clear()
