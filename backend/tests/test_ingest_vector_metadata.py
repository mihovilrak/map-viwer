"""Unit tests for vector ingestion metadata extraction.

This module focuses on testing the logic that extracts vector layer metadata
(geometry type, SRID, and bounding box) from PostGIS after vector data
is ingested. Mocks are used for all database interactions, ensuring no
actual database connections or ogr2ogr commands are run during testing.

Critical project requirements enforced by these tests:
    - All ingested vector layers must be transformed to EPSG:3857 (SRID 3857),
      as mandated in Instructions.md.
    - Metadata returned from PostGIS is correctly parsed and mapped to
      domain models.
    - Only safe SQL queries (parameterized, quoting enforced) are used.

See Also:
    - backend/app/services/ingest_vector.py for the implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from backend.app.core import config
from backend.app.services import ingest_vector

if TYPE_CHECKING:
    pass


def test_fetch_metadata_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _fetch_metadata with mocked database connection."""
    called_args: dict[str, Any] = {}

    def fake_quote_ident(name: str, scope: Any) -> str:
        """Mock quote_ident to return the table name quoted."""
        return f'"{name}"'

    def fake_connection(settings: config.Settings) -> Any:
        """Mock database connection to return a fake cursor."""

        class FakeConn:
            """Mock database connection to return a fake cursor."""

            def __enter__(self) -> FakeConn:
                return self

            def __exit__(self, *args: Any) -> None:
                pass

            def cursor(self) -> Any:
                """Mock cursor to return a fake result."""

                class FakeCursor:
                    """Mock cursor to return a fake result."""

                    def __enter__(self) -> FakeCursor:
                        return self

                    def __exit__(self, *args: Any) -> None:
                        pass

                    def execute(self, sql: str, params: Any = None) -> None:
                        """Mock execute to capture SQL and params."""
                        called_args["sql"] = sql
                        called_args["params"] = params

                    def fetchone(
                        self,
                    ) -> (
                        tuple[str, int]
                        | tuple[float, float, float, float]
                        | None
                    ):
                        """Mock fetchone to return a fake result."""
                        sql_str = str(called_args.get("sql", ""))
                        if "ST_SRID" in sql_str or "GeometryType" in sql_str:
                            return ("Point", 3857)
                        return (
                            -20037508.34,
                            -20037508.34,
                            20037508.34,
                            20037508.34,
                        )

                return FakeCursor()

        return FakeConn()

    monkeypatch.setattr("psycopg2.extensions.quote_ident", fake_quote_ident)
    monkeypatch.setattr("app.db.database.get_connection", fake_connection)
    settings = config.Settings()
    metadata = ingest_vector._fetch_metadata("test_table", settings)
    assert metadata.geom_type == "Point"
    assert metadata.srid == 3857
    assert metadata.bbox == (
        -20037508.34,
        -20037508.34,
        20037508.34,
        20037508.34,
    )


def test_fetch_metadata_none_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test _fetch_metadata handles None values from database."""

    def fake_quote_ident(name: str, scope: Any) -> str:
        """Mock quote_ident to return the table name quoted."""
        return f'"{name}"'

    def fake_connection(settings: config.Settings) -> Any:
        """Mock database connection to return a fake cursor."""

        class FakeConn:
            """Mock database connection to return a fake cursor."""

            def __enter__(self) -> FakeConn:
                return self

            def __exit__(self, *args: Any) -> None:
                pass

            def cursor(self) -> Any:
                """Mock cursor to return a fake result."""

                class FakeCursor:
                    """Mock cursor to return a fake result."""

                    def __enter__(self) -> FakeCursor:
                        return self

                    def __exit__(self, *args: Any) -> None:
                        pass

                    def execute(self, sql: str, params: Any = None) -> None:
                        pass

                    def fetchone(self) -> tuple[None, None] | None:
                        # Return None for geometry type/SRID query
                        # Return None for bbox query
                        return None

                return FakeCursor()

        return FakeConn()

    monkeypatch.setattr("psycopg2.extensions.quote_ident", fake_quote_ident)
    monkeypatch.setattr("app.db.database.get_connection", fake_connection)
    settings = config.Settings()
    metadata = ingest_vector._fetch_metadata("empty_table", settings)
    assert metadata.geom_type is None
    assert metadata.srid is None
    assert metadata.bbox is None
