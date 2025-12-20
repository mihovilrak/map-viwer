"""Vector data ingestion service using ogr2ogr.

This module provides functionality to import vector datasets into PostGIS
using the ogr2ogr command-line tool. All geometries are automatically
transformed to EPSG:3857 (Web Mercator) at ingestion time using the
`-t_srs EPSG:3857` flag, ensuring consistent coordinate systems for
web mapping applications.

After import, the service extracts metadata including geometry type,
spatial reference system (SRID), and bounding box from the PostGIS table.

Example:
    Ingest a GeoJSON file into PostGIS:
        >>> from app.core.config import get_settings
        >>> from app.services.ingest_vector import ingest_vector_to_postgis
        >>> from pathlib import Path

        >>> settings = get_settings()
        >>> source_file = Path("data.geojson")
        >>> table_name = "my_layer"

        >>> metadata = ingest_vector_to_postgis(
        ...     source_path=source_file,
        ...     table_name=table_name,
        ...     settings=settings
        ... )
        >>> # Returns LayerMetadata with:
        >>> # - geom_type: "Point", "LineString", "Polygon", etc.
        >>> # - srid: 3857 (always Web Mercator after ingestion)
        >>> # - bbox: (minx, miny, maxx, maxy) in Web Mercator coordinates
"""

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
        geom_type, srid = row if row is not None else (None, None)

        quoted_table = psycopg2.extensions.quote_ident(  # type: ignore[arg-type]
            table_name,
            conn,
        )
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
    r"""Import a vector dataset into PostGIS using ogr2ogr.

    Transforms all geometries to EPSG:3857 (Web Mercator) at ingestion time
    to ensure consistent coordinate system for web mapping. The transformation
    is performed using the `-t_srs EPSG:3857` flag in ogr2ogr, which reprojects
    all geometries regardless of their source coordinate system.

    After import, metadata is extracted from PostGIS including geometry type,
    SRID (should be 3857), and bounding box in Web Mercator coordinates.

    Args:
        source_path: Path to the uploaded vector file
            (any OGR-supported format).
        table_name: Destination layer/table name in PostGIS (must be valid
            identifier: alphanumeric + underscores only).
        settings: Application settings containing database connection URL.

    Returns:
        LayerMetadata describing the ingested layer with:
        - provider: "postgis"
        - table_name: The PostGIS table name
        - geom_type: Geometry type from PostGIS
        - srid: 3857 (always Web Mercator after transformation)
        - bbox: Bounding box in Web Mercator coordinates

    Raises:
        CommandError: If ogr2ogr command fails
            (invalid file, database error, etc.).

    Example:
        Ingest a GeoJSON file:
            >>> from pathlib import Path
            >>> from app.core.config import get_settings
            >>> from app.services.ingest_vector import ingest_vector_to_postgis

            >>> settings = get_settings()
            >>> metadata = ingest_vector_to_postgis(
            ...     source_path=Path("cities.geojson"),
            ...     table_name="cities",
            ...     settings=settings
            ... )
            >>> # Returns LayerMetadata with srid=3857, bbox in Web Mercator

        The ogr2ogr command executed:
            $ ogr2ogr -f PostgreSQL "postgresql://..." cities.geojson \\
            $    -t_srs EPSG:3857 -nln cities -lco GEOMETRY_NAME=geom -overwrite
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
