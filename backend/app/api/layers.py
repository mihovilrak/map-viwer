"""Layer metadata endpoints."""

import dataclasses

import fastapi

from app.core import config
from app.db import database
from app.db import models as db_models

BBox = tuple[float, float, float, float]

router = fastapi.APIRouter(prefix="/api/layers", tags=["layers"])


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


@router.get("")
async def list_layers(
    repo: database.LayerRepositoryProtocol = fastapi.Depends(_get_repo),  # noqa: B008
) -> list[dict[str, str | None]]:
    """List all registered layers.

    Args:
        repo: Layer repository (injected via FastAPI Depends).

    Returns:
        List of layer metadata dictionaries,
            ordered by creation date (newest first).
    """
    return [dataclasses.asdict(layer) for layer in repo.all()]


@router.get("/{layer_id}/bbox")
async def get_layer_bbox(
    layer_id: str,
    repo: database.LayerRepositoryProtocol = fastapi.Depends(_get_repo),  # noqa: B008
) -> dict[str, BBox | None]:
    """Get the bounding box for a registered layer.

    Args:
        layer_id: Unique identifier for the layer.
        repo: Layer repository (injected via FastAPI Depends).

    Returns:
        Dictionary containing the bounding box as [minx, miny, maxx, maxy]
        in Web Mercator (EPSG:3857) coordinates.

    Raises:
        HTTPException: If the layer is not found.
    """
    layer: db_models.LayerMetadata | None = repo.get(layer_id)
    if not layer:
        raise fastapi.HTTPException(
            status_code=404,
            detail="Layer not found",
        )

    return {"bbox": layer.bbox}
