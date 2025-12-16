"""End-to-end style test covering upload -> ingest -> tiles."""

from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import main
from backend.app.api import tiles as tiles_api
from backend.app.core import config
from backend.app.db import database
from backend.app.db.database import InMemoryLayerRepository
from backend.app.db.models import LayerMetadata


def test_full_flow(monkeypatch, tmp_path):
    repo = InMemoryLayerRepository()
    monkeypatch.setattr(database, "get_layer_repository", lambda settings: repo)

    def fake_vector_ingest(source_path: Path, layer_name: str, settings):
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

    def fake_raster_ingest(source_path: Path, settings):
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
        def render(self, img_format="PNG"):
            return b"pngbytes"

    class FakeCOGReader:
        def __init__(self, path):
            self.path = path

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def tile(self, x, y, z):
            return FakeTile()

    monkeypatch.setattr("app.services.ingest_vector.ingest_vector_to_postgis", fake_vector_ingest)
    monkeypatch.setattr("app.services.ingest_raster.ingest_raster", fake_raster_ingest)
    monkeypatch.setattr(tiles_api, "COGReader", FakeCOGReader)
    monkeypatch.setattr(config, "get_settings", lambda: config.Settings(storage_dir=tmp_path, raster_cache_dir=tmp_path))

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

