"""Raster ingestion utilities for creating Cloud Optimized GeoTIFFs."""

from pathlib import Path
from uuid import uuid4

from rio_tiler.io import COGReader

from app.core.config import Settings
from app.db.models import LayerMetadata
from app.utils.gdal_helpers import run_command


def convert_to_cog(source_path: Path, output_dir: Path) -> Path:
    """Convert a raster into a COG using gdal_translate."""
    output_dir.mkdir(parents=True, exist_ok=True)
    cog_path = output_dir / f"{source_path.stem}_cog.tif"
    command = (
        "gdal_translate",
        "-of",
        "COG",
        "-co",
        "COMPRESS=LZW",
        str(source_path),
        str(cog_path),
    )
    run_command(command)
    return cog_path


def _compute_bbox(cog_path: Path) -> tuple[float, float, float, float] | None:
    """Extract bounds from a COG using rio-tiler."""
    with COGReader(cog_path) as cog:
        bounds = cog.bounds
    if bounds:
        return (bounds.left, bounds.bottom, bounds.right, bounds.top)
    return None


def ingest_raster(source_path: Path, settings: Settings) -> LayerMetadata:
    """Create a COG and register minimal metadata."""
    cog_path = convert_to_cog(source_path, settings.raster_cache_dir)
    bbox = _compute_bbox(cog_path)
    return LayerMetadata(
        id=str(uuid4()),
        name=source_path.stem,
        source=str(source_path),
        provider="cog",
        table_name=None,
        geom_type="raster",
        srid=None,
        bbox=bbox,
        local_path=str(cog_path),
    )

