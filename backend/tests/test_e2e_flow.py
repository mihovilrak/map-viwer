"""End-to-end style test covering upload -> ingest -> tiles."""

from pathlib import Path
from types import TracebackType
from typing import Optional, Type

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from backend.app import main
from backend.app.core import config
from backend.app.db import database
from backend.app.db.database import InMemoryLayerRepository
from backend.app.db.models import LayerMetadata


def test_full_flow(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    repo = InMemoryLayerRepository()

    def _get_layer_repository(_settings: config.Settings) -> InMemoryLayerRepository:
        return repo

    monkeypatch.setattr(database, "get_layer_repository", _get_layer_repository)
    # Patch the imported get_layer_repository in each API module
    monkeypatch.setattr("app.api.ingest.get_layer_repository", _get_layer_repository)
    monkeypatch.setattr("app.api.layers.get_layer_repository", _get_layer_repository)
    monkeypatch.setattr("app.api.tiles.get_layer_repository", _get_layer_repository)

    def fake_vector_ingest(source_path: Path, layer_name: str, _settings: config.Settings) -> LayerMetadata:
        return LayerMetadata(
            id="vec1",
            name=layer_name,
            source=str(source_path),
            provider="postgis",
            table_name=layer_name,
            geom_type="Polygon",
            srid=4326,
            bbox=(0.0, 0.0, 1.0, 1.0),
            local_path=None,
        )

    def fake_raster_ingest(source_path: Path, settings: config.Settings) -> LayerMetadata:
        cog_path = tmp_path / "raster_cog.tif"
        cog_path.write_bytes(b"cog")
        return LayerMetadata(
            id="rast1",
            name="rast",
            source=str(source_path),
            provider="cog",
            table_name=None,
            geom_type="raster",
            srid=None,
            bbox=(1.0, 2.0, 3.0, 4.0),
            local_path=str(cog_path),
        )

    class FakeTile:
        def render(self, img_format: str = "PNG") -> bytes:
            return b"pngbytes"

    class FakeCOGReader:
        def __init__(self, path: Path) -> None:
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

        def tile(self, x: int, y: int, z: int) -> "FakeTile":
            return FakeTile()

    def _get_settings() -> config.Settings:
        return config.Settings(storage_dir=tmp_path, raster_cache_dir=tmp_path)

    monkeypatch.setattr("app.api.ingest.ingest_vector_to_postgis", fake_vector_ingest)
    monkeypatch.setattr("app.api.ingest.ingest_raster", fake_raster_ingest)
    monkeypatch.setattr("app.api.tiles.COGReader", FakeCOGReader)
    monkeypatch.setattr(config, "get_settings", _get_settings)

    app = main.create_app()
    client = TestClient(app)

    up_vec = client.post("/api/layers/upload", files={"file": ("vec.geojson", b"{}")})
    assert up_vec.status_code == 200
    vec_upload_id = up_vec.json()["upload_id"]

    ingest_vec = client.post(f"/api/layers/ingest/{vec_upload_id}?kind=vector&layer_name=demo")
    assert ingest_vec.status_code == 200

    up_rast = client.post("/api/layers/upload", files={"file": ("rast.tif", b"tif")})
    assert up_rast.status_code == 200
    rast_upload_id = up_rast.json()["upload_id"]

    ingest_rast = client.post(f"/api/layers/ingest/{rast_upload_id}?kind=raster")
    assert ingest_rast.status_code == 200

    layers = client.get("/api/layers")
    assert layers.status_code == 200
    assert len(layers.json()) == 2

    bbox = client.get("/api/layers/rast1/bbox")
    assert bbox.json()["bbox"] == [1.0, 2.0, 3.0, 4.0]

    raster_tile = client.get("/tiles/raster/rast1/0/0/0.png")
    assert raster_tile.status_code == 200
    assert raster_tile.content == b"pngbytes"

    vector_tile = client.get("/tiles/vector/demo/0/0/0.pbf", allow_redirects=False)
    assert vector_tile.status_code in (302, 307)

