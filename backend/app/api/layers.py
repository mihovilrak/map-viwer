"""Layer metadata query and retrieval API endpoints.

This module provides REST API endpoints for querying layer metadata
including listing all registered layers and retrieving bounding boxes
for specific layers. All bounding boxes are returned in EPSG:3857
(Web Mercator) coordinates.

Example:
    List all registered layers:
        >>> response = client.get("/api/layers")
        >>> layers = response.json()
        >>> # Returns: [{"id": "1", "name": "cities",
        >>> #           "provider": "postgis", ...}, ...]

    Get bounding box for a specific layer:
        >>> response = client.get("/api/layers/layer_123/bbox")
        >>> bbox = response.json()["bbox"]
        >>> # Returns: {"bbox": [-20037508.34, -20037508.34,
        >>> #                    20037508.34, 20037508.34]}
        >>> # Format: [minx, miny, maxx, maxy] in Web Mercator coordinates
"""

import dataclasses
from typing import Any

import fastapi

from app.api import ingest
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
) -> list[dict[str, Any]]:
    """List all registered layers.

    Returns all layers registered in the system, ordered by creation date
    (newest first). Each layer includes complete metadata including id, name,
    provider, geometry type, SRID, bounding box, and creation timestamp.

    Args:
        repo: Layer repository (injected via FastAPI Depends).

    Returns:
        List of layer metadata dictionaries, ordered by creation date
        (newest first). Each dictionary contains all LayerMetadata fields.

    Example:
        Get all layers:
            >>> response = client.get("/api/layers")
            >>> layers = response.json()
            >>> # Returns: [
            >>> #     {
            >>> #         "id": "abc-123",
            >>> #         "name": "cities",
            >>> #         "provider": "postgis",
            >>> #         "geom_type": "Point",
            >>> #         "srid": 3857,
            >>> #         "bbox": [-20037508.34, -20037508.34,
            >>> #                  20037508.34, 20037508.34],
            >>> #         ...
            >>> #     },
            >>> #     ...
            >>> # ]
    """
    return [ingest._convert_to_string(dataclasses.asdict(layer))
            for layer in repo.all()]


@router.get("/{layer_id}/bbox")
async def get_layer_bbox(
    layer_id: str,
    repo: database.LayerRepositoryProtocol = fastapi.Depends(_get_repo),  # noqa: B008
) -> dict[str, BBox | None]:
    """Get the bounding box for a registered layer.

    Returns the bounding box of a layer in EPSG:3857 (Web Mercator)
    coordinates. The bbox can be used to zoom the map viewport to
    the layer's extent.

    Args:
        layer_id: Unique identifier for the layer.
        repo: Layer repository (injected via FastAPI Depends).

    Returns:
        Dictionary containing the bounding box as [minx, miny, maxx, maxy]
        in Web Mercator (EPSG:3857) coordinates. Returns None if the
        layer has no bounding box.

    Raises:
        HTTPException: If the layer is not found (404 status code).

    Example:
        Get bounding box for a layer:
            >>> response = client.get("/api/layers/abc-123/bbox")
            >>> result = response.json()
            >>> # Returns: {"bbox": [-20037508.34, -20037508.34,
            >>> #                  20037508.34, 20037508.34]}

        Use bbox to set map viewport (MapLibre GL JS):
            >>> const bbox = response.bbox;  // [minx, miny, maxx, maxy]
            >>> map.fitBounds([[bbox[0], bbox[1]], [bbox[2], bbox[3]]]);
    """
    layer: db_models.LayerMetadata | None = repo.get(layer_id)
    if not layer:
        raise fastapi.HTTPException(
            status_code=404,
            detail="Layer not found",
        )

    return {"bbox": layer.bbox}
