"""Tile-related unit tests."""

from fastapi.testclient import TestClient

from app import main
from app.core import config
from app.db import database
from app.db.database import InMemoryLayerRepository
from app.db.models import LayerMetadata
from app.services.tiles_postgis import build_mvt_sql


def test_build_mvt_sql_contains_layer():
    sql = build_mvt_sql("public.demo")
    assert "public.demo" in sql
    assert "ST_AsMVT" in sql


def test_raster_tile_redirect(monkeypatch, tmp_path):
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
        def render(self, img_format="PNG"):
            return b"pngdata"

    class FakeCOGReader:
        def __init__(self, path):
            self.path = path

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def tile(self, x, y, z):
            return FakeTile()

    monkeypatch.setattr(config, "get_settings", lambda: config.get_settings())
    monkeypatch.setattr(database, "get_layer_repository", lambda settings: repo)
    monkeypatch.setattr("app.api.tiles.COGReader", FakeCOGReader)
    app = main.create_app()
    client = TestClient(app)

    resp = client.get("/tiles/raster/layer1/0/0/0.png")
    assert resp.status_code == 200
    assert resp.content == b"pngdata"

