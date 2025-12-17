"""Vector ingestion using ogr2ogr into PostGIS."""

from pathlib import Path
from typing import cast
from uuid import uuid4

from psycopg import sql

from app.core.config import Settings
from app.db.database import get_connection
from app.db.models import LayerMetadata
from app.utils.gdal_helpers import run_command


def _fetch_metadata(
    table_name: str, settings: Settings
) -> tuple[str | None, int | None, tuple[float, float, float, float] | None]:
    """Compute geom type, SRID, and bbox from PostGIS."""
    with get_connection(settings) as conn, conn.cursor() as cur:
        cur.execute(
            sql.SQL(
                "SELECT GeometryType(geom), ST_SRID(geom) FROM {} LIMIT 1;"
            ).format(sql.Identifier(table_name))
        )
        row = cur.fetchone()
        geom_type: str | None = cast(str, row[0]) if row and row[0] is not None else None
        srid: int | None = cast(int, row[1]) if row and row[1] is not None else None

        cur.execute(
            sql.SQL(
                """
                SELECT ST_XMin(ext), ST_YMin(ext), ST_XMax(ext), ST_YMax(ext)
                FROM (SELECT ST_Extent(geom) AS ext FROM {}) AS b;
                """
            ).format(sql.Identifier(table_name))
        )
        bbox_row = cur.fetchone()
        bbox: tuple[float, float, float, float] | None = None
        if bbox_row and all(v is not None for v in bbox_row) and len(bbox_row) == 4:
            bbox = cast(
                tuple[float, float, float, float],
                (
                    float(bbox_row[0]),  # type: ignore[arg-type]
                    float(bbox_row[1]),  # type: ignore[arg-type]
                    float(bbox_row[2]),  # type: ignore[arg-type]
                    float(bbox_row[3]),  # type: ignore[arg-type]
                ),
            )
        return geom_type, srid, bbox


def ingest_vector_to_postgis(
    source_path: Path, layer_name: str, settings: Settings
) -> LayerMetadata:
    """Import a vector dataset into PostGIS using ogr2ogr.

    Args:
        source_path: Path to the uploaded vector file.
        layer_name: Destination layer/table name.
        settings: Application settings.

    Returns:
        LayerMetadata describing the ingested layer.
    """
    command = (
        "ogr2ogr",
        "-f",
        "PostgreSQL",
        settings.database_url,
        str(source_path),
        "-nln",
        layer_name,
        "-lco",
        "GEOMETRY_NAME=geom",
        "-overwrite",
    )
    run_command(command)
    geom_type, srid, bbox = _fetch_metadata(layer_name, settings)

    return LayerMetadata(
        id=str(uuid4()),
        name=layer_name,
        source=str(source_path),
        provider="postgis",
        table_name=layer_name,
        geom_type=geom_type,
        srid=srid,
        bbox=bbox,
        local_path=None,
    )

