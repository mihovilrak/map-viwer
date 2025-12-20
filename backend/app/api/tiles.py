"""Tile-serving endpoints."""

import fastapi
from fastapi import responses
from rio_tiler import io as rio_tiler_io

from app.core import config
from app.db import database
from app.db import models as db_models

router = fastapi.APIRouter(prefix="/tiles", tags=["tiles"])


def _build_tegola_url(base: str, layer: str, z: int, x: int, y: int) -> str:
    """Construct a Tegola vector tile URL.

    Args:
        base: Base URL for the Tegola service.
        layer: Layer/table name in PostGIS.
        z: Zoom level.
        x: Tile X coordinate.
        y: Tile Y coordinate.

    Returns:
        Complete URL for the vector tile in MVT format.
    """
    return f"{base}/maps/{layer}/tiles/{z}/{x}/{y}.pbf"


def _get_repo(
    settings: config.Settings = fastapi.Depends(config.get_settings),  # noqa: B008
) -> database.LayerRepositoryProtocol:
    """Resolve the layer repository dependency.

    Args:
        settings: Application settings (injected via FastAPI Depends).

    Returns:
        LayerRepositoryProtocol implementation
            (PostgresLayerRepository in production).
    """
    return database.get_layer_repository(settings)


@router.get("/vector/{layer}/{z}/{x}/{y}.pbf")
async def proxy_vector_tile(
    layer: str,
    z: int,
    x: int,
    y: int,
    settings: config.Settings = fastapi.Depends(config.get_settings),  # noqa: B008
) -> responses.RedirectResponse:
    """Proxy vector tile requests to Tegola service.

    FastAPI redirects the request to Tegola, which generates MVT tiles
    from PostGIS. All geometries are expected to be in EPSG:3857.

    Args:
        layer: Layer/table name in PostGIS.
        z: Zoom level (0-20+).
        x: Tile X coordinate.
        y: Tile Y coordinate.
        settings: Application settings (injected via FastAPI Depends).

    Returns:
        HTTP redirect response to Tegola tile endpoint.
    """
    url = _build_tegola_url(str(settings.tegola_base_url), layer, z, x, y)
    return responses.RedirectResponse(url)


@router.get("/raster/{layer_id}/{z}/{x}/{y}.png")
async def raster_tile(
    layer_id: str,
    z: int,
    x: int,
    y: int,
    repo: database.LayerRepositoryProtocol = fastapi.Depends(_get_repo),  # noqa: B008
) -> responses.Response:
    """Generate an XYZ raster tile from a Cloud Optimized GeoTIFF.

    Uses rio-tiler to read the requested tile window from the COG
    and render it as a PNG image. The COG is expected to be in EPSG:3857.

    Args:
        layer_id: Unique identifier for the raster layer.
        z: Zoom level (0-20+).
        x: Tile X coordinate.
        y: Tile Y coordinate.
        repo: Layer repository (injected via FastAPI Depends).

    Returns:
        PNG image response with the raster tile.

    Raises:
        HTTPException: If the layer is not found or is not a raster layer.
    """
    layer: db_models.LayerMetadata | None = repo.get(layer_id)
    if not layer or layer.provider != "cog" or not layer.local_path:
        raise fastapi.HTTPException(
            status_code=404,
            detail="Raster layer not found",
        )

    with rio_tiler_io.COGReader(
        input=layer.local_path,
        options={"nodata": 0},
    ) as cog:
        tile = cog.tile(x, y, z)

    return responses.Response(
        content=tile.render(img_format="PNG"),  # type: ignore[attr-defined]
        media_type="image/png",
    )
