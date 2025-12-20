"""Upload and ingestion endpoints."""

from __future__ import annotations

import dataclasses
import shutil
import tempfile
import uuid
from typing import TYPE_CHECKING, Literal, TypedDict

import fastapi

from app.core import config
from app.db import database
from app.services import ingest_raster, ingest_vector

if TYPE_CHECKING:
    import pathlib

router = fastapi.APIRouter(prefix="/api/layers", tags=["layers"])

_upload_cache: dict[str, pathlib.Path] = {}


class UploadResponse(TypedDict):
    upload_id: str
    filename: str | None
    path: str | None


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


def _validate_layer_name(name: str) -> str:
    """Validate layer name to prevent SQL injection.

    Only allows alphanumeric characters and underscores.

    Args:
        name: Layer name to validate.

    Returns:
        Validated layer name.

    Raises:
        HTTPException: If the layer name contains invalid characters.
    """
    if not name.replace("_", "").isalnum():
        raise fastapi.HTTPException(
            status_code=400,
            detail="Invalid layer name",
        )

    return name


def _save_upload(
    file: fastapi.UploadFile,
    storage_dir: pathlib.Path,
    max_size: int,
) -> pathlib.Path:
    """Persist an uploaded file to disk with size validation.

    Args:
        file: FastAPI UploadFile object containing the file data.
        storage_dir: Directory where the file should be saved.
        max_size: Maximum allowed file size in bytes.

    Returns:
        Path to the saved file.

    Raises:
        HTTPException: If the file exceeds the maximum size limit.
    """
    storage_dir.mkdir(parents=True, exist_ok=True)
    target_path = storage_dir / (file.filename or "")
    with tempfile.NamedTemporaryFile(delete=False, dir=storage_dir) as tmp:
        size = 0
        for chunk in iter(lambda: file.file.read(1024 * 1024), b""):
            size += len(chunk)
            if size > max_size:
                raise fastapi.HTTPException(
                    status_code=413,
                    detail="Upload too large",
                )

            tmp.write(chunk)

        tmp.flush()

    shutil.move(tmp.name, target_path)

    return target_path


@router.post("/upload")
async def upload_layer(
    file: fastapi.UploadFile,
    settings: config.Settings = fastapi.Depends(config.get_settings),  # noqa: B008
) -> UploadResponse:
    """Accept a multipart file upload and store it temporarily.

    The uploaded file is saved to disk and assigned an upload_id for later
    ingestion. Files are stored in the configured storage directory.

    Args:
        file: Uploaded file from multipart form data.
        settings: Application settings (injected via FastAPI Depends).

    Returns:
        Dictionary containing upload_id, filename, and storage path.

    Raises:
        HTTPException: If the file exceeds the maximum upload size.
    """
    saved_path = _save_upload(
        file,
        settings.storage_dir,
        settings.max_upload_size_bytes,
    )

    upload_id = str(uuid.uuid4())

    _upload_cache[upload_id] = saved_path

    return UploadResponse(
        upload_id=upload_id,
        filename=file.filename,
        path=str(saved_path),
    )


@router.post("/ingest/{upload_id}")
async def ingest_layer(
    upload_id: str,
    kind: Literal["vector", "raster"],
    layer_name: str | None = None,
    settings: config.Settings = fastapi.Depends(config.get_settings),  # noqa: B008
    repo: database.LayerRepositoryProtocol = fastapi.Depends(_get_repo),  # noqa: B008
) -> dict[str, str | None]:
    """Ingest a previously uploaded file into the configured backend.

    For vector files: imports to PostGIS with EPSG:3857 transformation.
    For raster files: converts to COG with EPSG:3857 transformation.

    Args:
        upload_id: ID returned from the upload endpoint.
        kind: Type of layer to ingest ("vector" or "raster").
        layer_name: Required for vector layers, ignored for raster.
        settings: Application settings (injected via FastAPI Depends).
        repo: Layer repository for storing metadata
            (injected via FastAPI Depends).

    Returns:
        Dictionary containing the layer metadata.

    Raises:
        HTTPException: If upload_id not found, layer_name missing for vector,
            or ingestion fails.
    """
    source_path = _upload_cache.get(upload_id)
    if not source_path:
        raise fastapi.HTTPException(
            status_code=404,
            detail="Upload not found",
        )

    if kind == "vector":
        if not layer_name:
            raise fastapi.HTTPException(
                status_code=400,
                detail="layer_name required for vector",
            )
        metadata = ingest_vector.ingest_vector_to_postgis(
            source_path,
            _validate_layer_name(layer_name),
            settings,
        )
    else:
        metadata = ingest_raster.ingest_raster(source_path, settings)

    repo.add(metadata)
    return dataclasses.asdict(metadata)
