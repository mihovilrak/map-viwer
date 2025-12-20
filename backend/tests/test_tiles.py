"""Tile-related unit tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
    sql = tiles_postgis.build_mvt_sql("public.demo")
    assert "public.demo" in sql
    assert "ST_AsMVT" in sql


def test_raster_tile_redirect(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
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
        def render(self, img_format: str = "PNG") -> bytes:
            return b"pngdata"

    class FakeCOGReader:
        def __init__(self, path: str) -> None:
            self.path = path

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
    monkeypatch.setattr(
        "app.api.tiles.get_layer_repository",
        get_test_repo,
    )
    monkeypatch.setattr("app.api.tiles.COGReader", FakeCOGReader)
    app = main.create_app()
    client = testclient.TestClient(app)

    resp = client.get("/tiles/raster/layer1/0/0/0.png")
    assert resp.status_code == 200
    assert resp.content == b"pngdata"
