"""Tile-serving endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse, Response
from rio_tiler.io import COGReader

from app.core.config import Settings, get_settings
from app.db.database import LayerRepositoryProtocol, get_layer_repository
from app.db.models import LayerMetadata


router = APIRouter(prefix="/tiles", tags=["tiles"])


def _build_tegola_url(base: str, layer: str, z: int, x: int, y: int) -> str:
    """Construct a Tegola vector tile URL."""
    return f"{base}/maps/{layer}/tiles/{z}/{x}/{y}.pbf"


def _get_repo(settings: Settings = Depends(get_settings)) -> LayerRepositoryProtocol:
    """Resolve the layer repository."""
    return get_layer_repository(settings)


@router.get("/vector/{layer}/{z}/{x}/{y}.pbf")
async def proxy_vector_tile(
    layer: str, z: int, x: int, y: int, settings: Settings = Depends(get_settings)
) -> RedirectResponse:
    """Redirect vector tile requests to Tegola."""
    url = _build_tegola_url(str(settings.tegola_base_url), layer, z, x, y)
    return RedirectResponse(url)


@router.get("/raster/{layer_id}/{z}/{x}/{y}.png")
async def raster_tile(
    layer_id: str,
    z: int,
    x: int,
    y: int,
    repo: LayerRepositoryProtocol = Depends(_get_repo),
) -> Response:
    """Return an XYZ raster tile from a COG."""
    layer: LayerMetadata | None = repo.get(layer_id)
    if not layer or layer.provider != "cog" or not layer.local_path:
        raise HTTPException(status_code=404, detail="Raster layer not found")

    with COGReader(layer.local_path) as cog:
        tile = cog.tile(x, y, z)
    return Response(content=tile.render(img_format="PNG"), media_type="image/png")

