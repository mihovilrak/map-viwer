"""Unit tests for backend.app.services.tiles_postgis tile SQL generation.

This module tests the build_mvt_sql function, validating:
    - Correct inclusion of the requested PostGIS layer (table) name.
    - Proper usage of PostGIS MVT (Mapbox Vector Tile) SQL functions.
    - Reliance on parameterized query placeholders to prevent SQL injection.
    - Contract that SQL differs for different input layer names.

These tests ensure the tile SQL builder fulfills project requirements for
secure, deterministic, API-compliant generation of MVT SQL for tile endpoints.

See Also:
    - backend/app/services/tiles_postgis.py for implementation.
"""

from __future__ import annotations

from backend.app.services import tiles_postgis


def test_build_mvt_sql_contains_layer_name() -> None:
    """Test that generated SQL contains the layer name."""
    sql = tiles_postgis.build_mvt_sql("cities")
    assert "cities" in sql
    assert "FROM cities" in sql or "FROM %s" in sql


def test_build_mvt_sql_contains_mvt_functions() -> None:
    """Test that generated SQL uses PostGIS MVT functions."""
    sql = tiles_postgis.build_mvt_sql("test_layer")
    assert "ST_AsMVT" in sql
    assert "ST_AsMVTGeom" in sql
    assert "ST_TileEnvelope" in sql


def test_build_mvt_sql_uses_parameters() -> None:
    """Test that generated SQL uses parameterized queries."""
    sql = tiles_postgis.build_mvt_sql("layer")
    # Should use $1, $2, $3 for z, x, y parameters
    assert "$1" in sql or "$2" in sql or "$3" in sql


def test_build_mvt_sql_different_layers() -> None:
    """Test that different layer names produce different SQL."""
    sql1 = tiles_postgis.build_mvt_sql("cities")
    sql2 = tiles_postgis.build_mvt_sql("rivers")
    assert sql1 != sql2
    assert "cities" in sql1
    assert "rivers" in sql2
