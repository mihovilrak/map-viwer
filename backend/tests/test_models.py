"""Unit tests for backend.app.db.models domain models.

This module validates the LayerMetadata structure and typing contract,
ensuring correct initialization, field defaults, and invariants for both
vector (PostGIS) and raster (COG) layers.

Key coverage:
    - Creation and initialization of LayerMetadata for vector and raster
      sources, matching project contract and SRID requirements.
    - Ensures bbox, srid, and provider fields are set and mapped as expected.
    - Tests default behaviors, such as created_at timestamps.

See Also:
    - backend/app/db/models.py for the LayerMetadata implementation.
"""

from __future__ import annotations

import datetime

from backend.app.db import models as db_models


def test_layer_metadata_creation() -> None:
    """Test creating a LayerMetadata instance."""
    layer = db_models.LayerMetadata(
        id="test-123",
        name="test_layer",
        source="/path/to/file.shp",
        provider="postgis",
        table_name="test_layer",
        geom_type="Point",
        srid=3857,
        bbox=(-20037508.34, -20037508.34, 20037508.34, 20037508.34),
        local_path=None,
    )
    assert layer.id == "test-123"
    assert layer.name == "test_layer"
    assert layer.provider == "postgis"
    assert layer.srid == 3857


def test_layer_metadata_raster() -> None:
    """Test creating a raster LayerMetadata instance."""
    raster = db_models.LayerMetadata(
        id="raster-456",
        name="elevation",
        source="/path/to/elevation.tif",
        provider="cog",
        table_name=None,
        geom_type="raster",
        srid=None,
        bbox=(-20037508.34, -20037508.34, 20037508.34, 20037508.34),
        local_path="/cache/elevation_cog.tif",
    )
    assert raster.provider == "cog"
    assert raster.table_name is None
    assert raster.local_path == "/cache/elevation_cog.tif"


def test_layer_metadata_default_created_at() -> None:
    """Test that created_at has a default value."""
    layer = db_models.LayerMetadata(
        id="test",
        name="test",
        source="/path",
        provider="postgis",
        table_name="test",
        geom_type="Point",
        srid=3857,
        bbox=None,
        local_path=None,
    )
    assert isinstance(layer.created_at, datetime.datetime)


def test_layer_metadata_custom_created_at() -> None:
    """Test setting custom created_at timestamp."""
    custom_time = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)
    layer = db_models.LayerMetadata(
        id="test",
        name="test",
        source="/path",
        provider="postgis",
        table_name="test",
        geom_type="Point",
        srid=3857,
        bbox=None,
        local_path=None,
        created_at=custom_time,
    )
    assert layer.created_at == custom_time


def test_layer_metadata_none_bbox() -> None:
    """Test LayerMetadata with None bbox."""
    layer = db_models.LayerMetadata(
        id="test",
        name="test",
        source="/path",
        provider="postgis",
        table_name="test",
        geom_type="Point",
        srid=3857,
        bbox=None,
        local_path=None,
    )
    assert layer.bbox is None
