"""Data models for layer metadata.

This module defines the core data structures used throughout the application
to represent geospatial layers. The LayerMetadata dataclass encapsulates all
information about a layer including its source, provider type, geometry
characteristics, spatial reference system, and bounding box.

Example:
    Creating a LayerMetadata instance for a vector layer:
        >>> from app.db.models import LayerMetadata
        >>> layer = LayerMetadata(
        ...     id="layer_123",
        ...     name="cities",
        ...     source="/path/to/cities.shp",
        ...     provider="postgis",
        ...     table_name="cities",
        ...     geom_type="Point",
        ...     srid=3857,
        ...     bbox=(-20037508.34, -20037508.34,
        ...           20037508.34, 20037508.34),
        ... )

    Creating metadata for a raster layer:
        >>> raster = LayerMetadata(
        ...     id="raster_456",
        ...     name="elevation",
        ...     source="/path/to/elevation.tif",
        ...     provider="cog",
        ...     table_name=None,
        ...     geom_type="raster",
        ...     srid=None,
        ...     bbox=(-20037508.34, -20037508.34,
        ...           20037508.34, 20037508.34),
        ...     local_path="/cache/elevation_cog.tif",
        ... )
"""

from __future__ import annotations

import dataclasses
import datetime
from typing import Literal

BBox = tuple[float, float, float, float]
Provider = Literal["postgis", "geopackage", "cog", "mbtiles"]


@dataclasses.dataclass
class LayerMetadata:
    """Represents a vector or raster layer the app knows about.

    This dataclass encapsulates all metadata about a geospatial layer including
    its source, storage provider, geometry characteristics, spatial reference
    system, and bounding box. All bounding boxes are stored in EPSG:3857
    (Web Mercator) coordinates.

    Attributes:
        id: Unique identifier for the layer (UUID string).
        name: Human-readable layer name.
        source: Original source file path or identifier.
        provider: Storage provider type
            ("postgis", "cog", "geopackage", "mbtiles").
        table_name: PostGIS table name for vector layers, None for rasters.
        geom_type: Geometry type
            ("Point", "LineString", "Polygon", "raster", etc.).
        srid: Spatial reference system ID (should be 3857 after ingestion).
        bbox: Bounding box as (minx, miny, maxx, maxy) in Web Mercator.
        local_path: Local file path for COG rasters, None for PostGIS vectors.
        created_at: Timestamp when the layer was registered.

    Example:
        Create metadata for a vector layer:
            >>> layer = LayerMetadata(
            ...     id="abc-123",
            ...     name="cities",
            ...     source="/uploads/cities.geojson",
            ...     provider="postgis",
            ...     table_name="cities",
            ...     geom_type="Point",
            ...     srid=3857,
            ...     bbox=(-20037508.34, -20037508.34,
            ...           20037508.34, 20037508.34),
            ...     local_path=None
            ... )

        Create metadata for a raster layer:
            >>> raster = LayerMetadata(
            ...     id="def-456",
            ...     name="elevation",
            ...     source="/uploads/elevation.tif",
            ...     provider="cog",
            ...     table_name=None,
            ...     geom_type="raster",
            ...     srid=None,
            ...     bbox=(-20037508.34, -20037508.34,
            ...           20037508.34, 20037508.34),
            ...     local_path="/cache/elevation_cog.tif"
            ... )
    """

    id: str
    name: str
    source: str
    provider: Provider
    table_name: str | None
    geom_type: str | None
    srid: int | None
    bbox: BBox | None
    local_path: str | None
    created_at: datetime.datetime = datetime.datetime.now(tz=datetime.UTC)
