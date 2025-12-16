"""Helpers to build PostGIS MVT SQL for Tegola or direct queries."""


def build_mvt_sql(layer_name: str) -> str:
    """Return an ST_AsMVT query for a given layer name.

    Note: callers must validate ``layer_name`` (only alphanumerics/underscores)
    before invoking to avoid SQL injection.
    """
    return f"""
WITH
  bounds AS (
    SELECT ST_TileEnvelope($1, $2, $3) AS geom
  ),
  mvtgeom AS (
    SELECT ST_AsMVTGeom(ST_Transform(t.geom, 3857), bounds.geom, 4096, 0, true) AS geom, t.*
    FROM {layer_name} t, bounds
    WHERE ST_Intersects(ST_Transform(t.geom, 3857), bounds.geom)
  )
SELECT ST_AsMVT(mvtgeom.*, '{layer_name}', 4096, 'geom') FROM mvtgeom;
""".strip()

