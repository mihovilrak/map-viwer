"""API endpoint tests for the layers management endpoints.

This module provides tests for the /api/layers endpoints in the FastAPI
application, covering:
    - Listing all available vector and raster layers,
    - Ensuring correct contract for the empty and non-empty layer repository.

All repository operations are monkeypatched for isolation and deterministic
results. These tests validate that the layer listing API contract remains
consistent, including with real and mocked layer metadata. Layer repository
and settings are always injected using dependency overrides
per project testability standards.

See Also:
    - backend/app/api/layers.py for API implementation,
    - backend/app/db/database.py for repository protocol.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import testclient

from backend.app import main
from backend.app.api import layers as api_layers
from backend.app.core import config
from backend.app.db import database
from backend.app.db import models as db_models

if TYPE_CHECKING:
    import pytest


def test_list_layers_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test listing layers when repository is empty."""
    repo = database.InMemoryLayerRepository()

    def get_repo(
        _settings: config.Settings,
    ) -> database.LayerRepositoryProtocol:
        return repo

    monkeypatch.setattr(database, "get_layer_repository", get_repo)
    monkeypatch.setattr("app.db.database.get_layer_repository", get_repo)

    app = main.create_app()
    app.dependency_overrides[api_layers._get_repo] = lambda: repo
    client = testclient.TestClient(app)
    try:
        response = client.get("/api/layers")
        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides.clear()


def test_list_layers_multiple(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test listing multiple layers."""
    repo = database.InMemoryLayerRepository()
    layer1 = db_models.LayerMetadata(
        id="layer1",
        name="cities",
        source="/path1",
        provider="postgis",
        table_name="cities",
        geom_type="Point",
        srid=3857,
        bbox=None,
        local_path=None,
    )
    layer2 = db_models.LayerMetadata(
        id="layer2",
        name="rivers",
        source="/path2",
        provider="postgis",
        table_name="rivers",
        geom_type="LineString",
        srid=3857,
        bbox=None,
        local_path=None,
    )
    repo.add(layer1)
    repo.add(layer2)

    monkeypatch.setattr(database, "get_layer_repository", lambda _: repo)

    app = main.create_app()
    from app.api import layers

    app.dependency_overrides[layers._get_repo] = lambda: repo
    client = testclient.TestClient(app)
    try:
        response = client.get("/api/layers")
        assert response.status_code == 200
        layers_data = response.json()
        assert len(layers_data) == 2
        names = {layer["name"] for layer in layers_data}
        assert names == {"cities", "rivers"}
    finally:
        app.dependency_overrides.clear()


def test_get_layer_bbox_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test getting bbox for non-existent layer returns 404."""
    repo = database.InMemoryLayerRepository()

    monkeypatch.setattr(database, "get_layer_repository", lambda _: repo)

    app = main.create_app()
    from app.api import layers

    app.dependency_overrides[layers._get_repo] = lambda: repo
    client = testclient.TestClient(app)
    try:
        response = client.get("/api/layers/nonexistent/bbox")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_get_layer_bbox_with_bbox(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test getting bbox for layer with bounding box."""
    repo = database.InMemoryLayerRepository()
    layer = db_models.LayerMetadata(
        id="layer1",
        name="test",
        source="/path",
        provider="postgis",
        table_name="test",
        geom_type="Point",
        srid=3857,
        bbox=(-20037508.34, -20037508.34, 20037508.34, 20037508.34),
        local_path=None,
    )
    repo.add(layer)

    monkeypatch.setattr(database, "get_layer_repository", lambda _: repo)

    app = main.create_app()
    from app.api import layers

    app.dependency_overrides[layers._get_repo] = lambda: repo
    client = testclient.TestClient(app)
    try:
        response = client.get("/api/layers/layer1/bbox")
        assert response.status_code == 200
        assert response.json()["bbox"] == [
            -20037508.34,
            -20037508.34,
            20037508.34,
            20037508.34,
        ]
    finally:
        app.dependency_overrides.clear()


def test_get_layer_bbox_none_bbox(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test getting bbox for layer with None bbox."""
    repo = database.InMemoryLayerRepository()
    layer = db_models.LayerMetadata(
        id="layer2",
        name="test",
        source="/path",
        provider="postgis",
        table_name="test",
        geom_type="Point",
        srid=3857,
        bbox=None,
        local_path=None,
    )
    repo.add(layer)

    monkeypatch.setattr(database, "get_layer_repository", lambda _: repo)

    app = main.create_app()
    from app.api import layers

    app.dependency_overrides[layers._get_repo] = lambda: repo
    client = testclient.TestClient(app)
    try:
        response = client.get("/api/layers/layer2/bbox")
        assert response.status_code == 200
        assert response.json()["bbox"] is None
    finally:
        app.dependency_overrides.clear()
