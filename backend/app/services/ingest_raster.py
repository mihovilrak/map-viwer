"""Raster data ingestion service for Cloud Optimized GeoTIFF creation.

This module provides functionality to convert raster files into Cloud
Optimized GeoTIFF (COG) format. The service first transforms the raster
to EPSG:3857 (Web Mercator) using gdalwarp, then converts it to COG format
using gdal_translate. This ensures all rasters are in a consistent
coordinate system optimized for web tile serving.

The service extracts bounding box information from the COG using rio-tiler
and creates layer metadata for registration in the system.

Example:
    Ingest a GeoTIFF file and convert to COG:
        >>> from app.core.config import get_settings
        >>> from app.services.ingest_raster import ingest_raster
        >>> from pathlib import Path

        >>> settings = get_settings()
        >>> source_file = Path("elevation.tif")

        >>> metadata = ingest_raster(
        ...     source_path=source_file,
        ...     settings=settings
        ... )
        >>> # Returns LayerMetadata with:
        >>> # - provider: "cog"
        >>> # - geom_type: "raster"
        >>> # - local_path: Path to the created COG file
        >>> # - bbox: (minx, miny, maxx, maxy) in Web Mercator coordinates

    The COG file is stored in settings.raster_cache_dir and can be
    used for on-demand tile generation via rio-tiler.
"""

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
    using gdalwarp with bilinear resampling. The transformed raster is then
    converted to COG format using gdal_translate with LZW compression.
    This two-step process ensures all rasters are in Web Mercator and
    optimized for tile serving.

    Args:
        source_path: Path to the source raster file
            (any GDAL-supported format).
        output_dir: Directory where the COG will be written
            (created if needed).

    Returns:
        Path to the created COG file (named {source_stem}_cog.tif).

    Raises:
        CommandError: If gdalwarp or gdal_translate commands fail.

    Example:
        Convert a GeoTIFF to COG:
            >>> from pathlib import Path
            >>> from app.services.ingest_raster import convert_to_cog

            >>> cog_path = convert_to_cog(
            ...     source_path=Path("elevation.tif"),
            ...     output_dir=Path("/cache/cog")
            ... )
            >>> # Returns: Path("/cache/cog/elevation_cog.tif")

        The process:
            1. gdalwarp transforms to EPSG:3857: elevation_3857.tif
            2. gdal_translate creates COG: elevation_cog.tif
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
    Extracts bounding box using rio-tiler and creates layer metadata for
    registration in the system. The COG file is stored in the configured
    raster cache directory.

    Args:
        source_path: Path to the source raster file
            (any GDAL-supported format).
        settings: Application settings including raster_cache_dir
            for COG storage.

    Returns:
        LayerMetadata describing the ingested raster layer with:
        - provider: "cog"
        - geom_type: "raster"
        - local_path: Path to the created COG file
        - bbox: Bounding box in Web Mercator coordinates (from COG)

    Raises:
        CommandError: If COG conversion fails (gdalwarp/gdal_translate error).

    Example:
        Ingest a GeoTIFF file:
            >>> from pathlib import Path
            >>> from app.core.config import get_settings
            >>> from app.services.ingest_raster import ingest_raster

            >>> settings = get_settings()
            >>> metadata = ingest_raster(
            ...     source_path=Path("elevation.tif"),
            ...     settings=settings
            ... )
            >>> # Returns LayerMetadata with:
            >>> # - provider="cog"
            >>> # - local_path="/cache/elevation_cog.tif"
            >>> # - bbox in Web Mercator coordinates
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
