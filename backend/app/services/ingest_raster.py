"""Raster ingestion utilities for creating Cloud Optimized GeoTIFFs."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import rio_tiler.io as rio_tiler_io
from app.db import models as db_models
from app.utils import gdal_helpers

if TYPE_CHECKING:
    import pathlib

    from app.core import config

    BBox = tuple[float, float, float, float]


def convert_to_cog(
    source_path: pathlib.Path,
    output_dir: pathlib.Path,
) -> pathlib.Path:
    """Convert a raster into a Cloud Optimized GeoTIFF (COG).

    Transforms the raster to EPSG:3857 (Web Mercator) before COG creation
    to ensure consistent coordinate system for web mapping.

    Args:
        source_path: Path to the source raster file.
        output_dir: Directory where the COG will be written.

    Returns:
        Path to the created COG file.

    Raises:
        CommandError: If gdalwarp or gdal_translate commands fail.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    warped_path = output_dir / f"{source_path.stem}_3857.tif"
    warp_command = (
        "gdalwarp",
        "-t_srs",
        "EPSG:3857",
        "-r",
        "bilinear",
        str(source_path),
        str(warped_path),
    )
    gdal_helpers.run_command(warp_command)

    cog_path = output_dir / f"{source_path.stem}_cog.tif"
    command = (
        "gdal_translate",
        "-of",
        "COG",
        "-co",
        "COMPRESS=LZW",
        str(warped_path),
        str(cog_path),
    )
    gdal_helpers.run_command(command)
    return cog_path


def _compute_bbox(cog_path: pathlib.Path) -> BBox | None:
    """Extract bounding box from a COG using rio-tiler.

    Args:
        cog_path: Path to the COG file.

    Returns:
        Tuple of (minx, miny, maxx, maxy) in Web Mercator (EPSG:3857),
        or None if bounds cannot be determined.
    """
    with rio_tiler_io.COGReader(input=str(cog_path), options={}) as cog:
        bounds = cog.bounds
    if bounds:
        return (
            bounds.left,  # type: ignore[attr-defined]
            bounds.bottom,  # type: ignore[attr-defined]
            bounds.right,  # type: ignore[attr-defined]
            bounds.top,  # type: ignore[attr-defined]
        )

    return None


def ingest_raster(
    source_path: pathlib.Path,
    settings: config.Settings,
) -> db_models.LayerMetadata:
    """Ingest a raster file by converting to COG and extracting metadata.

    Transforms the raster to EPSG:3857 (Web Mercator) during conversion.
    Extracts bounding box and creates layer metadata for registration.

    Args:
        source_path: Path to the source raster file.
        settings: Application settings including raster cache directory.

    Returns:
        LayerMetadata describing the ingested raster layer.

    Raises:
        CommandError: If COG conversion fails.
    """
    cog_path = convert_to_cog(source_path, settings.raster_cache_dir)
    bbox = _compute_bbox(cog_path)
    return db_models.LayerMetadata(
        id=str(uuid.uuid4()),
        name=source_path.stem,
        source=str(source_path),
        provider="cog",
        table_name=None,
        geom_type="raster",
        srid=None,
        bbox=bbox if bbox else None,
        local_path=str(cog_path),
    )
