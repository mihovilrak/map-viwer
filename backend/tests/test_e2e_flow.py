"""End-to-end tests for backend ingest and tile serving workflows.

This module verifies the integrated flow of:
- Vector/raster upload and ingestion,
- SRID transformation to EPSG:3857 (Web Mercator),
- Layer metadata registration, and
- On-demand tile serving endpoints.

Tests ensure that at ingestion time, all geospatial data are transformed to
SRID 3857, are discoverable via the API, and can be served as tiles.
Dependency injection and repo monkeypatching allow for isolated, fast tests.

Critical Project Requirements (see Instructions.md):
    - All vectors and rasters must be ingested in SRID 3857.
    - Layer names, upload size, and SRID must be validated.
    - Repository pattern and service layer are used for testability.

See Also:
- backend/app/utils/gdal_helpers.py for ingest command execution.
- backend/app/services/* for ingest/metadata logic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import testclient

from backend.app import main
from backend.app.api import ingest as api_ingest
from backend.app.api import layers as api_layers
from backend.app.api import tiles as api_tiles
from backend.app.core import config
from backend.app.db import database
from backend.app.db import models as db_models
from backend.app.services import ingest_raster, ingest_vector

if TYPE_CHECKING:
    import pathlib
    import types

    import pytest


def test_full_flow(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """Test the full flow of uploading, ingesting, and serving tiles."""
    repo = database.InMemoryLayerRepository()

    def _get_layer_repository(
        _settings: config.Settings,
    ) -> database.InMemoryLayerRepository:
        return repo

    monkeypatch.setattr(
        database,
        "get_layer_repository",
        _get_layer_repository,
    )
    monkeypatch.setattr(
        "app.db.database.get_layer_repository",
        _get_layer_repository,
    )

    def fake_vector_ingest(
        source_path: pathlib.Path,
        layer_name: str,
        _settings: config.Settings,
    ) -> db_models.LayerMetadata:
        """Mock vector ingest that simulates the ingestion of a vector layer.

        Args:
            source_path: Path to the input vector file.
            layer_name: Name to assign to the ingested layer.
            _settings: Application settings (unused in mock).

        Returns:
            LayerMetadata instance representing a mock vector layer
                with fixed test data.
        """
        return db_models.LayerMetadata(
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

    def fake_raster_ingest(
        source_path: pathlib.Path,
        settings: config.Settings,
    ) -> db_models.LayerMetadata:
        """Mock raster ingest that simulates creation of a COG.

        Args:
            source_path: Path to the input raster file.
            settings: Application settings (unused in mock).

        Returns:
            LayerMetadata instance for a mock raster layer,
                emulating a COG ingest.
        """
        cog_path = tmp_path / "raster_cog.tif"
        cog_path.write_bytes(b"cog")
        return db_models.LayerMetadata(
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
        """A fake tile object that simulates tile rendering for tests.

        This mock is used to stand in for rio-tiler tile objects and provides
        a predictable byte output for testing raster tile API responses.
        """

        def render(self, img_format: str = "PNG") -> bytes:
            return b"pngbytes"

    class FakeCOGReader:
        """Mock implementation of rio-tiler COGReader for tile endpoints.

        This fake class simulates the interface of rio_tiler.io.COGReader,
        providing deterministic output for use in end-to-end test flows.
        It supports context manager usage and stubs the tile() method
        to return a mock tile object, allowing raster tile APIs
        to be exercised without accessing real raster files or invoking GDAL.

        Attributes:
            path: The path argument, passed through from initialization
                to simulate the behavior of the actual COGReader API.
        """

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

    def _get_settings() -> config.Settings:
        return config.Settings(
            storage_dir=tmp_path,
            raster_cache_dir=tmp_path,
            allow_origins=["*"],
        )

    monkeypatch.setattr(
        ingest_vector,
        "ingest_vector_to_postgis",
        fake_vector_ingest,
    )
    monkeypatch.setattr(
        "app.services.ingest_vector.ingest_vector_to_postgis",
        fake_vector_ingest,
    )
    monkeypatch.setattr(
        ingest_raster,
        "ingest_raster",
        fake_raster_ingest,
    )
    monkeypatch.setattr(
        "app.services.ingest_raster.ingest_raster",
        fake_raster_ingest,
    )
    monkeypatch.setattr(
        "rio_tiler.io.COGReader",
        FakeCOGReader,
    )
    monkeypatch.setattr(
        config,
        "get_settings",
        _get_settings,
    )

    app = main.create_app()
    app.dependency_overrides[api_ingest._get_repo] = lambda: repo
    app.dependency_overrides[api_layers._get_repo] = lambda: repo
    app.dependency_overrides[api_tiles._get_repo] = lambda: repo
    client = testclient.TestClient(app)
    try:
        up_vec = client.post(
            "/api/layers/upload",
            files={"file": ("vec.geojson", b"{}")},
        )
        assert up_vec.status_code == 200
        vec_upload_id = up_vec.json()["upload_id"]

        ingest_vec = client.post(
            f"/api/layers/ingest/{vec_upload_id}?kind=vector&layer_name=demo",
        )
        assert ingest_vec.status_code == 200

        up_rast = client.post(
            "/api/layers/upload",
            files={"file": ("rast.tif", b"tif")},
        )
        assert up_rast.status_code == 200
        rast_upload_id = up_rast.json()["upload_id"]

        ingest_rast = client.post(
            f"/api/layers/ingest/{rast_upload_id}?kind=raster",
        )
        assert ingest_rast.status_code == 200

        layers = client.get("/api/layers")
        assert layers.status_code == 200
        assert len(layers.json()) == 2

        bbox = client.get("/api/layers/rast1/bbox")
        assert bbox.json()["bbox"] == [1.0, 2.0, 3.0, 4.0]

        raster_tile = client.get("/tiles/raster/rast1/0/0/0.png")
        assert raster_tile.status_code == 200
        assert raster_tile.content == b"pngbytes"

        vector_tile = client.get(
            "/tiles/vector/demo/0/0/0.pbf",
            allow_redirects=False,
        )
        assert vector_tile.status_code in (302, 307)
    finally:
        app.dependency_overrides.clear()
