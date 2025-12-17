"""Layer metadata endpoints."""

from dataclasses import asdict
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.db.database import LayerRepositoryProtocol, get_layer_repository
from app.db.models import LayerMetadata


router = APIRouter(prefix="/api/layers", tags=["layers"])


def _get_repo(settings: Settings = Depends(get_settings)) -> LayerRepositoryProtocol:
    """Resolve the layer repository."""
    return get_layer_repository(settings)


@router.get("")
async def list_layers(
    repo: LayerRepositoryProtocol = Depends(_get_repo),
) -> list[dict]:
    """Return all registered layers."""
    return [asdict(layer) for layer in repo.all()]


@router.get("/{layer_id}/bbox")
async def get_layer_bbox(
    layer_id: str, repo: LayerRepositoryProtocol = Depends(_get_repo)
) -> dict:
    """Return a bounding box for a stored layer."""
    layer = repo.get(layer_id)
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")
    return {"bbox": layer.bbox}

