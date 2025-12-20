"""XYZ tile serving endpoints for vector and raster layers.

This module provides REST API endpoints for serving map tiles in standard
XYZ format. Vector tiles are proxied to the Tegola service which generates
MVT (Mapbox Vector Tiles) from PostGIS. Raster tiles are generated on-demand
from Cloud Optimized GeoTIFFs using rio-tiler.

All tiles are served in EPSG:3857 (Web Mercator) coordinate system.
Vector tiles are served as Protocol Buffer (.pbf) format, while raster
tiles are served as PNG images.

Example:
    Request a vector tile:
        >>> response = client.get("/tiles/vector/cities/10/512/512.pbf")
        >>> # Returns MVT tile data (binary Protocol Buffer format)
        >>> # Proxies to: http://tegola:8080/maps/cities/tiles/10/512/512.pbf

    Request a raster tile:
        >>> response = client.get("/tiles/raster/layer_123/10/512/512.png")
        >>> # Returns PNG image tile generated from COG
        >>> # Tile coordinates: z=10, x=512, y=512
"""

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
    The layer parameter should match the PostGIS table name.

    Args:
        layer: Layer/table name in PostGIS (must match ingested table name).
        z: Zoom level (0-20+, standard XYZ tile zoom).
        x: Tile X coordinate (standard XYZ tile X).
        y: Tile Y coordinate (standard XYZ tile Y).
        settings: Application settings (injected via FastAPI Depends).

    Returns:
        HTTP redirect response (302/307) to Tegola tile endpoint.

    Example:
        Request a vector tile:
            >>> response = client.get(
            ...     "/tiles/vector/cities/10/512/512.pbf",
            ...     allow_redirects=False
            ... )
            >>> # Returns 302 redirect to:
            >>> # http://tegola:8080/maps/cities/tiles/10/512/512.pbf

        Use in MapLibre GL JS:
            >>> map.addSource('cities', {
            ...     type: 'vector',
            ...     tiles: ['http://api/tiles/vector/cities/{z}/{x}/{y}.pbf']
            ... });
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
    Tiles are generated on-demand, leveraging COG's internal tiling
    structure for efficient access.

    Args:
        layer_id: Unique identifier for the raster layer (from layer metadata).
        z: Zoom level (0-20+, standard XYZ tile zoom).
        x: Tile X coordinate (standard XYZ tile X).
        y: Tile Y coordinate (standard XYZ tile Y).
        repo: Layer repository (injected via FastAPI Depends).

    Returns:
        PNG image response with the raster tile. Content-Type is image/png.

    Raises:
        HTTPException: If the layer is not found (404) or is not a raster
            layer (provider != "cog" or local_path is None).

    Example:
        Request a raster tile:
            >>> response = client.get("/tiles/raster/abc-123/10/512/512.png")
            >>> # Returns PNG image bytes with Content-Type: image/png

        Use in MapLibre GL JS:
            >>> map.addSource('elevation', {
            ...     type: 'raster',
            ...     tiles: ['http://api/tiles/raster/abc-123/{z}/{x}/{y}.png'],
            ...     tileSize: 256
            ... });
    """
    layer: db_models.LayerMetadata | None = repo.get(layer_id)
    if not layer or layer.provider != "cog" or not layer.local_path:
        raise fastapi.HTTPException(
            status_code=404,
            detail="Raster layer not found",
        )

    with rio_tiler_io.COGReader(
        input=layer.local_path,
        options={"nodata": 0},  # type: ignore[arg-type]
    ) as cog:
        tile = cog.tile(x, y, z)

    return responses.Response(
        content=tile.render(img_format="PNG"),  # type: ignore[attr-defined]
        media_type="image/png",
    )
