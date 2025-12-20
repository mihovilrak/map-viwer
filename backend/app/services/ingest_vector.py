"""Vector ingestion using ogr2ogr into PostGIS."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, NamedTuple, cast

import psycopg2.extensions
from app.db import database
from app.db import models as db_models
from app.utils import gdal_helpers

if TYPE_CHECKING:
    import pathlib

    from app.core import config


BBox = tuple[float, float, float, float]


class VectorMetadata(NamedTuple):
    geom_type: str | None
    srid: int | None
    bbox: BBox | None


def _fetch_metadata(
    table_name: str, settings: config.Settings
) -> VectorMetadata:
    """Compute geometry type, SRID, and bounding box from PostGIS.

    Args:
        table_name: Name of the PostGIS table to query.
        settings: Application settings for database connection.

    Returns:
        Tuple of (geometry_type, srid, bbox) where:
        - geometry_type: String like 'POINT', 'LINESTRING', 'POLYGON', or None
        - srid: Integer SRID code (should be 3857 after ingestion), or None
        - bbox: Tuple of (minx, miny, maxx, maxy) in Web Mercator, or None
    """
    with database.get_connection(settings) as conn, conn.cursor() as cur:
        quoted_table = psycopg2.extensions.quote_ident(  # type: ignore[arg-type]
            table_name,
            conn,
        )
        cur.execute(
            """SELECT GeometryType(geom),
                    ST_SRID(geom)
                FROM %(table_name)s
                LIMIT 1;""",
            {"table_name": quoted_table},
        )
        row = cur.fetchone()
        geom_type: str | None = (
            cast(str, row[0]) if row and row[0] is not None else None
        )
        srid: int | None = (
            cast(int, row[1]) if row and row[1] is not None else None
        )

        quoted_table = psycopg2.extensions.quote_ident(table_name, conn)  # type: ignore[arg-type]
        cur.execute(
            """
            SELECT ST_XMin(ext), ST_YMin(ext), ST_XMax(ext), ST_YMax(ext)
            FROM (SELECT ST_Extent(geom) AS ext FROM %(table_name)s) AS b;
            """,
            {"table_name": quoted_table},
        )
        bbox_row = cur.fetchone()
        bbox: BBox | None = None
        if (
            bbox_row
            and all(v is not None for v in bbox_row)
            and len(bbox_row) == 4
        ):
            bbox = cast(BBox, tuple(map(float, bbox_row)))
        return VectorMetadata(geom_type, srid, bbox)


def ingest_vector_to_postgis(
    source_path: pathlib.Path,
    table_name: str,
    settings: config.Settings,
) -> db_models.LayerMetadata:
    """Import a vector dataset into PostGIS using ogr2ogr.

    Transforms all geometries to EPSG:3857 (Web Mercator) at ingestion time
    to ensure consistent coordinate system for web mapping.

    Args:
        source_path: Path to the uploaded vector file.
        table_name: Destination layer/table name.
        settings: Application settings.

    Returns:
        LayerMetadata describing the ingested layer.

    Raises:
        CommandError: If ogr2ogr command fails.
    """
    command = (
        "ogr2ogr",
        "-f",
        "PostgreSQL",
        settings.database_url,
        str(source_path),
        "-t_srs",
        "EPSG:3857",
        "-nln",
        table_name,
        "-lco",
        "GEOMETRY_NAME=geom",
        "-overwrite",
    )
    gdal_helpers.run_command(command)
    vector_metadata = _fetch_metadata(table_name, settings)

    return db_models.LayerMetadata(
        id=str(uuid.uuid4()),
        name=table_name,
        source=str(source_path),
        provider="postgis",
        table_name=table_name,
        geom_type=vector_metadata.geom_type,
        srid=vector_metadata.srid,
        bbox=vector_metadata.bbox,
        local_path=None,
    )
