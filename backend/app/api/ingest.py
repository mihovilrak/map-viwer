"""Upload and ingestion endpoints."""

import shutil
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.core.config import Settings, get_settings
from app.db.database import LayerRepositoryProtocol, get_layer_repository
from app.db.models import LayerMetadata
from app.services.ingest_raster import ingest_raster
from app.services.ingest_vector import ingest_vector_to_postgis


router = APIRouter(prefix="/api/layers", tags=["layers"])

_upload_cache: dict[str, Path] = {}


def _get_repo(settings: Settings = Depends(get_settings)) -> LayerRepositoryProtocol:
    """Resolve the layer repository."""
    return get_layer_repository(settings)


def _validate_layer_name(name: str) -> str:
    """Allow only safe layer names to avoid SQL injection."""
    if not name.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid layer name")
    return name


def _save_upload(file: UploadFile, storage_dir: Path, max_size: int) -> Path:
    """Persist an uploaded file to disk with size checks."""
    storage_dir.mkdir(parents=True, exist_ok=True)
    target_path = storage_dir / file.filename
    with tempfile.NamedTemporaryFile(delete=False, dir=storage_dir) as tmp:
        size = 0
        for chunk in iter(lambda: file.file.read(1024 * 1024), b""):
            size += len(chunk)
            if size > max_size:
                raise HTTPException(status_code=413, detail="Upload too large")
            tmp.write(chunk)
        tmp.flush()
    shutil.move(tmp.name, target_path)
    return target_path


@router.post("/upload")
async def upload_layer(
    file: UploadFile, settings: Settings = Depends(get_settings)
) -> dict:
    """Accept a multipart upload and store it on disk."""
    saved_path = _save_upload(file, settings.storage_dir, settings.max_upload_size_bytes)
    upload_id = str(uuid4())
    _upload_cache[upload_id] = saved_path
    return {"upload_id": upload_id, "filename": file.filename, "path": str(saved_path)}


@router.post("/ingest/{upload_id}")
async def ingest_layer(
    upload_id: str,
    kind: Literal["vector", "raster"],
    layer_name: str | None = None,
    settings: Settings = Depends(get_settings),
    repo: LayerRepositoryProtocol = Depends(_get_repo),
) -> dict:
    """Ingest a previously uploaded file into the configured backend."""
    source_path = _upload_cache.get(upload_id)
    if not source_path:
        raise HTTPException(status_code=404, detail="Upload not found")

    if kind == "vector":
        if not layer_name:
            raise HTTPException(status_code=400, detail="layer_name required for vector")
        metadata = ingest_vector_to_postgis(
            source_path, _validate_layer_name(layer_name), settings
        )
    else:
        metadata = ingest_raster(source_path, settings)

    repo.add(metadata)
    return asdict(metadata)

