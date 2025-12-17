"""Tile-related unit tests."""

from pathlib import Path
from types import TracebackType
from typing import Optional, Type

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from backend.app import main
from backend.app.core import config
from backend.app.db import database
from backend.app.db.database import InMemoryLayerRepository, LayerRepositoryProtocol
from backend.app.db.models import LayerMetadata
from backend.app.services.tiles_postgis import build_mvt_sql


def test_build_mvt_sql_contains_layer() -> None:
    sql = build_mvt_sql("public.demo")
    assert "public.demo" in sql
    assert "ST_AsMVT" in sql


def test_raster_tile_redirect(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Raster tile endpoint should serve rendered content when COGReader is mocked."""
    repo = InMemoryLayerRepository()
    layer = LayerMetadata(
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
        def render(self, img_format: str = "PNG") -> bytes:
            return b"pngdata"

    class FakeCOGReader:
        def __init__(self, path: str) -> None:
            self.path = path

        def __enter__(self) -> "FakeCOGReader":
            return self

        def __exit__(
            self,
            exc_type: Optional[Type[BaseException]],
            exc: Optional[BaseException],
            tb: Optional[TracebackType],
        ) -> None:
            return None

        def tile(self, x: int, y: int, z: int) -> FakeTile:
            return FakeTile()

    def get_test_settings() -> config.Settings:
        return config.get_settings()
    
    def get_test_repo(settings: config.Settings) -> LayerRepositoryProtocol:
        return repo
    
    monkeypatch.setattr(config, "get_settings", get_test_settings)
    monkeypatch.setattr(database, "get_layer_repository", get_test_repo)
    monkeypatch.setattr("app.api.tiles.COGReader", FakeCOGReader)
    app = main.create_app()
    client = TestClient(app)

    resp = client.get("/tiles/raster/layer1/0/0/0.png")
    assert resp.status_code == 200
    assert resp.content == b"pngdata"

