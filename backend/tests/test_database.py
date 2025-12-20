"""Tests for geospatial database layer repositories and models.

This module contains unit tests for the core geospatial database abstractions:
- InMemoryLayerRepository: Used for isolated/testing environments to verify
  repository logic.
- PostgresLayerRepository: (Not covered in these tests, but would be tested
  for real DB interactions.)

The tests cover CRUD operations on the in-memory repository and verify
the integrity of LayerMetadata objects relevant to the application.

All tests are self-contained and do not require a running database.
"""

from __future__ import annotations

import datetime

import pytest

from backend.app.core import config
from backend.app.db import database
from backend.app.db import models as db_models


def test_in_memory_repository_add() -> None:
    """Test adding a layer to in-memory repository."""
    repo = database.InMemoryLayerRepository()
    layer = db_models.LayerMetadata(
        id="test-1",
        name="test",
        source="/path",
        provider="postgis",
        table_name="test",
        geom_type="Point",
        srid=3857,
        bbox=None,
        local_path=None,
    )
    result = repo.add(layer)
    assert result.id == "test-1"
    assert repo.get("test-1") == layer


def test_in_memory_repository_get() -> None:
    """Test retrieving a layer from in-memory repository."""
    repo = database.InMemoryLayerRepository()
    layer = db_models.LayerMetadata(
        id="test-2",
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
    found = repo.get("test-2")
    assert found == layer
    assert repo.get("nonexistent") is None


def test_in_memory_repository_all() -> None:
    """Test listing all layers from in-memory repository."""
    repo = database.InMemoryLayerRepository()
    layer1 = db_models.LayerMetadata(
        id="test-3",
        name="layer1",
        source="/path1",
        provider="postgis",
        table_name="layer1",
        geom_type="Point",
        srid=3857,
        bbox=None,
        local_path=None,
    )
    layer2 = db_models.LayerMetadata(
        id="test-4",
        name="layer2",
        source="/path2",
        provider="cog",
        table_name=None,
        geom_type="raster",
        srid=None,
        bbox=None,
        local_path="/cache/layer2.tif",
    )
    repo.add(layer1)
    repo.add(layer2)
    all_layers = list(repo.all())
    assert len(all_layers) == 2
    assert {layer.id for layer in all_layers} == {"test-3", "test-4"}


def test_postgres_repository_to_row() -> None:
    """Test converting LayerMetadata to database row dictionary."""
    layer = db_models.LayerMetadata(
        id="test-5",
        name="test",
        source="/path",
        provider="postgis",
        table_name="test_table",
        geom_type="Point",
        srid=3857,
        bbox=(-1.0, -2.0, 3.0, 4.0),
        local_path=None,
        created_at=datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC),
    )
    row = database.PostgresLayerRepository._to_row(layer)
    assert row["id"] == "test-5"
    assert row["name"] == "test"
    assert row["bbox_minx"] == -1.0
    assert row["bbox_maxy"] == 4.0
    assert row["srid"] == 3857


def test_postgres_repository_to_row_none_bbox() -> None:
    """Test converting LayerMetadata with None bbox to row."""
    layer = db_models.LayerMetadata(
        id="test-6",
        name="test",
        source="/path",
        provider="postgis",
        table_name="test",
        geom_type="Point",
        srid=3857,
        bbox=None,
        local_path=None,
    )
    row = database.PostgresLayerRepository._to_row(layer)
    assert row["bbox_minx"] is None
    assert row["bbox_miny"] is None
    assert row["bbox_maxx"] is None
    assert row["bbox_maxy"] is None


def test_postgres_repository_from_row() -> None:
    """Test converting database row to LayerMetadata."""
    row = {
        "id": "test-7",
        "name": "test",
        "source": "/path",
        "provider": "postgis",
        "table_name": "test_table",
        "geom_type": "Point",
        "srid": 3857,
        "bbox_minx": -1.0,
        "bbox_miny": -2.0,
        "bbox_maxx": 3.0,
        "bbox_maxy": 4.0,
        "local_path": None,
        "created_at": datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC),
    }
    layer = database.PostgresLayerRepository._from_row(row)
    assert layer.id == "test-7"
    assert layer.bbox == (-1.0, -2.0, 3.0, 4.0)
    assert layer.srid == 3857


def test_postgres_repository_from_row_none_bbox() -> None:
    """Test converting row with None bbox to LayerMetadata."""
    row = {
        "id": "test-8",
        "name": "test",
        "source": "/path",
        "provider": "postgis",
        "table_name": None,
        "geom_type": None,
        "srid": None,
        "bbox_minx": None,
        "bbox_miny": None,
        "bbox_maxx": None,
        "bbox_maxy": None,
        "local_path": None,
        "created_at": datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC),
    }
    layer = database.PostgresLayerRepository._from_row(row)  # type: ignore
    assert layer.bbox is None
    assert layer.srid is None


def test_get_layer_repository_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test factory function returns PostgresLayerRepository."""

    class FakeRepo(database.PostgresLayerRepository):
        def __init__(self, settings: config.Settings):
            self.settings = settings

    def fake_get_repo(
        settings: config.Settings,
    ) -> database.LayerRepositoryProtocol:
        return FakeRepo(settings)

    monkeypatch.setattr(database, "PostgresLayerRepository", FakeRepo)
    settings = config.Settings()
    repo = database.get_layer_repository(settings)
    assert isinstance(repo, database.PostgresLayerRepository)
