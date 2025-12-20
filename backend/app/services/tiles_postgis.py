"""PostGIS MVT (Mapbox Vector Tiles) SQL query builder.

This module provides utilities for generating PostGIS SQL queries that
produce Mapbox Vector Tiles (MVT) format. The generated SQL uses PostGIS
functions like ST_AsMVT, ST_AsMVTGeom, and ST_TileEnvelope to create
optimized vector tiles from geometry data.

The SQL queries are designed to work with geometries already stored in
EPSG:3857 (Web Mercator) coordinate system. Callers must validate layer
names to prevent SQL injection before using the generated SQL.

Example:
    Generate MVT SQL for a layer:
        >>> from app.services.tiles_postgis import build_mvt_sql

        >>> # Validate layer name first (alphanumeric + underscore only)
        >>> layer_name = "cities"
        >>> sql = build_mvt_sql(layer_name)

        >>> # Execute with tile parameters: z, x, y
        >>> # The SQL expects $1=z, $2=x, $3=y as parameters
        >>> cursor.execute(sql, (10, 512, 512))

    The generated SQL:
     - Uses ST_TileEnvelope to create tile bounds
     - Transforms geometries to 3857 (if needed)
     - Clips geometries to tile extent
     - Returns MVT binary data via ST_AsMVT
"""


def build_mvt_sql(layer_name: str) -> str:
    """Return an ST_AsMVT query for a given layer name.

    Generates a PostGIS SQL query that produces Mapbox Vector Tiles (MVT)
    format. The query uses ST_TileEnvelope to create tile bounds, clips
    geometries to the tile extent, and returns MVT binary data via ST_AsMVT.

    The generated SQL expects three parameters: $1=z (zoom), $2=x (tile X),
    $3=y (tile Y). Geometries are expected to be in EPSG:3857.

    Note: callers must validate ``layer_name`` (only alphanumerics/underscores)
    before invoking to avoid SQL injection. The layer_name is inserted into
    the SQL string, so validation is critical.

    Args:
        layer_name: PostGIS table name (must be validated for safety).

    Returns:
        SQL query string ready for execution with tile parameters.

    Example:
        Generate and execute MVT SQL:
            >>> from app.services.tiles_postgis import build_mvt_sql

            >>> # Validate layer_name first!
            >>> layer_name = "cities"  # Already validated
            >>> sql = build_mvt_sql(layer_name)

            >>> # Execute with tile coordinates
            >>> cursor.execute(sql, (10, 512, 512))
            >>> mvt_data = cursor.fetchone()[0]  # Binary MVT data

        The generated SQL includes:
        - ST_TileEnvelope for tile bounds
        - ST_AsMVTGeom for geometry clipping
        - ST_AsMVT for MVT binary output
    """
    return (
        """
WITH
  bounds AS (
    SELECT ST_TileEnvelope($1, $2, $3) AS geom
  ),
  mvtgeom AS (
    SELECT ST_AsMVTGeom(
        ST_Transform(t.geom, 3857),
        bounds.geom,
        4096,
        0,
        true,
    ) AS geom, t.*
    FROM %s t, bounds
    WHERE ST_Intersects(ST_Transform(t.geom, 3857), bounds.geom)
  )
SELECT ST_AsMVT(mvtgeom.*, %s, 4096, 'geom') FROM mvtgeom;
"""  # noqa: UP031
        % (layer_name, layer_name)
    ).strip()
