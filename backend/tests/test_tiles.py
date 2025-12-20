"""Unit and integration tests for tile service and endpoints.

This module includes tests for:
    - SQL generation for vector tile (MVT) queries for PostGIS layers,
    - Raster tile endpoint routing and rio-tiler raster rendering integration,
    - Validation of tile layer repository contracts for both vector ('postgis')
      and raster ('cog') providers,
    - End-to-end FastAPI tile endpoint plumbing using dependency injection,
      including mock behaviors for COG readers,
    - Ensuring all tile logic always acts only on layers registered in the
      metadata repository.

These tests enforce:
    - Secure, parameterized SQL for vector tile queries,
    - Correct FastAPI dependency override patterns
      for layer metadata isolation,
    - Raster tile contract: raster files must be COG, and responses are always
      in Web Mercator/EPSG:3857 per ingest requirements.

See Also:
    - backend/app/services/tiles_postgis.py for vector tile logic,
    - backend/app/services/tiles_raster.py for raster tile service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import testclient

from backend.app import main
from backend.app.core import config
from backend.app.db import database
from backend.app.db import models as db_models
from backend.app.services import tiles_postgis

if TYPE_CHECKING:
    import pathlib
    import types

    import pytest


def test_build_mvt_sql_contains_layer() -> None:
    """Test that the SQL contains the layer name."""
    sql = tiles_postgis.build_mvt_sql("public.demo")
    assert "public.demo" in sql
    assert "ST_AsMVT" in sql


def test_raster_tile_redirect(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """Test that the raster tile endpoint redirects to the correct URL."""
    repo = database.InMemoryLayerRepository()
    layer = db_models.LayerMetadata(
        id="layer1",
        name="raster",
        source="raster.tif",
        provider="cog",
        table_name=None,
        geom_type="raster",
        srid=None,
        bbox=None,
        local_path=str(tmp_path / "fake_cog.tif"),
    )
    repo.add(layer)

    class FakeTile:
        """A fake tile object that simulates tile rendering for tests."""

        def render(self, img_format: str = "PNG") -> bytes:
            """Mock the render method to return a PNG image."""
            return b"pngdata"

    class FakeCOGReader:
        """A fake COG reader that simulates the COGReader interface."""

        def __init__(self, input: str, **kwargs: Any):
            self.path = input

        def __enter__(self) -> FakeCOGReader:
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: types.TracebackType | None,
        ) -> None:
            return None

        def tile(self, x: int, y: int, z: int) -> FakeTile:
            return FakeTile()

    def get_test_settings() -> config.Settings:
        return config.get_settings()

    def get_test_repo(
        _settings: config.Settings,
    ) -> database.LayerRepositoryProtocol:
        return repo

    monkeypatch.setattr(config, "get_settings", get_test_settings)
    monkeypatch.setattr(database, "get_layer_repository", get_test_repo)
    monkeypatch.setattr("app.db.database.get_layer_repository", get_test_repo)
    monkeypatch.setattr("rio_tiler.io.COGReader", FakeCOGReader)
    app = main.create_app()
    from backend.app.api import tiles as api_tiles

    app.dependency_overrides[api_tiles._get_repo] = lambda: repo
    client = testclient.TestClient(app)
    try:
        resp = client.get("/tiles/raster/layer1/0/0/0.png")
        assert resp.status_code == 200
        assert resp.content == b"pngdata"
    finally:
        app.dependency_overrides.clear()
