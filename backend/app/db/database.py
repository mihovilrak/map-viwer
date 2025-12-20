"""Database helpers and repositories for layer metadata."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Protocol, cast

import psycopg2
import psycopg2.extensions

from app.db import models as db_models

if TYPE_CHECKING:
    from collections.abc import Iterable

    from app.core import config


def _cast[T](value: object, dtype: type[T]) -> T | None:  # type: ignore[misc]
    """Cast a value to a specific type, returning None if value is None."""
    if value is None:
        return None

    return cast(T, value)


class LayerRepositoryProtocol(Protocol):
    """Protocol interface for storing and retrieving layer metadata.

    Implementations provide persistence for LayerMetadata objects,
    supporting both in-memory (testing) and PostgreSQL (production) backends.
    """

    def add(
        self,
        layer: db_models.LayerMetadata,
    ) -> db_models.LayerMetadata: ...

    def get(self, layer_id: str) -> db_models.LayerMetadata | None: ...

    def all(self) -> Iterable[db_models.LayerMetadata]: ...


class InMemoryLayerRepository(LayerRepositoryProtocol):
    """Simple in-memory store for tests and local development.

    Stores layer metadata in a dictionary. Data is lost when the process exits.
    Suitable for testing and development scenarios.
    """

    def __init__(self) -> None:
        """Initialize an empty in-memory repository."""
        self._store: dict[str, db_models.LayerMetadata] = {}

    def add(self, layer: db_models.LayerMetadata) -> db_models.LayerMetadata:
        """Add or update a layer in the repository.

        Args:
            layer: Layer metadata to store.

        Returns:
            The stored layer metadata.
        """
        self._store[layer.id] = layer
        return layer

    def get(self, layer_id: str) -> db_models.LayerMetadata | None:
        """Retrieve a layer by ID.

        Args:
            layer_id: Unique identifier for the layer.

        Returns:
            LayerMetadata if found, None otherwise.
        """
        return self._store.get(layer_id)

    def all(self) -> Iterable[db_models.LayerMetadata]:
        """Get all stored layers.

        Returns:
            Iterable of all LayerMetadata objects in the repository.
        """
        return self._store.values()


class PostgresLayerRepository(LayerRepositoryProtocol):
    """PostgreSQL/PostGIS-backed repository for layer metadata.

    Persists layer metadata to a PostgreSQL database with PostGIS extension.
    Automatically creates the layers table and enables PostGIS
    on initialization.
    """

    CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS layers (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      source TEXT NOT NULL,
      provider TEXT NOT NULL,
      table_name TEXT,
      geom_type TEXT,
      srid INTEGER,
      bbox_minx DOUBLE PRECISION,
      bbox_miny DOUBLE PRECISION,
      bbox_maxx DOUBLE PRECISION,
      bbox_maxy DOUBLE PRECISION,
      local_path TEXT,
      created_at TIMESTAMPTZ DEFAULT now()
    );
    """

    def __init__(self, settings: config.Settings) -> None:
        """Initialize repository with database settings.

        Args:
            settings: Application settings containing database connection URL.
        """
        self.settings = settings
        self._ensure_schema()

    def _connection(self) -> psycopg2.extensions.connection:
        """Create a new database connection.

        Returns:
            psycopg2 connection object.
        """
        return psycopg2.connect(self.settings.database_url)

    def _ensure_schema(self) -> None:
        """Ensure PostGIS extension and layers table exist.

        Creates the PostGIS extension if not present and creates the layers
        table if it doesn't exist. Called automatically on initialization.
        """
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
            cur.execute(self.CREATE_TABLE_SQL)
            conn.commit()

    def add(self, layer: db_models.LayerMetadata) -> db_models.LayerMetadata:
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO layers (
                    id, name, source, provider, table_name, geom_type, srid,
                    bbox_minx, bbox_miny, bbox_maxx, bbox_maxy, local_path,
                    created_at
                ) VALUES (%(id)s, %(name)s, %(source)s, %(provider)s,
                    %(table_name)s, %(geom_type)s, %(srid)s, %(bbox_minx)s,
                    %(bbox_miny)s, %(bbox_maxx)s, %(bbox_maxy)s,
                    %(local_path)s, %(created_at)s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    source = EXCLUDED.source,
                    provider = EXCLUDED.provider,
                    table_name = EXCLUDED.table_name,
                    geom_type = EXCLUDED.geom_type,
                    srid = EXCLUDED.srid,
                    bbox_minx = EXCLUDED.bbox_minx,
                    bbox_miny = EXCLUDED.bbox_miny,
                    bbox_maxx = EXCLUDED.bbox_maxx,
                    bbox_maxy = EXCLUDED.bbox_maxy,
                    local_path = EXCLUDED.local_path;
                """,
                self._to_row(layer),
            )
            conn.commit()
        return layer

    def get(self, layer_id: str) -> db_models.LayerMetadata | None:
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM layers WHERE id = %s", (layer_id,))
            row = cur.fetchone()
            if row is None:
                return None
            else:
                return self._from_row(cast(dict[str, object], row))

    def all(self) -> Iterable[db_models.LayerMetadata]:
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM layers ORDER BY created_at DESC")
            for row in cur.fetchall():
                yield self._from_row(cast(dict[str, object], row))

    @staticmethod
    def _to_row(layer: db_models.LayerMetadata) -> dict[str, object]:
        """Convert LayerMetadata to database row dictionary.

        Args:
            layer: Layer metadata to convert.

        Returns:
            Dictionary suitable for parameterized SQL insertion.
        """
        bbox = layer.bbox or (None, None, None, None)
        return {
            "id": layer.id,
            "name": layer.name,
            "source": layer.source,
            "provider": layer.provider,
            "table_name": layer.table_name,
            "geom_type": layer.geom_type,
            "srid": layer.srid,
            "bbox_minx": bbox[0],
            "bbox_miny": bbox[1],
            "bbox_maxx": bbox[2],
            "bbox_maxy": bbox[3],
            "local_path": layer.local_path,
            "created_at": layer.created_at,
        }

    @staticmethod
    def _from_row(row: dict[str, object]) -> db_models.LayerMetadata:
        """Convert database row dictionary to LayerMetadata.

        Args:
            row: Dictionary from database query result.

        Returns:
            LayerMetadata object with all fields populated.
        """
        bbox = (
            row.get("bbox_minx"),
            row.get("bbox_miny"),
            row.get("bbox_maxx"),
            row.get("bbox_maxy"),
        )
        if any(v is None for v in bbox):
            bbox_tuple = None
        else:
            bbox_tuple = tuple(bbox)  # type: ignore[arg-type]
        srid_value = row.get("srid")
        srid = int(cast(int, srid_value)) if srid_value is not None else None
        table_name_value = row.get("table_name")
        table_name = _cast(table_name_value, str)
        geom_type_value = row.get("geom_type")
        geom_type = _cast(geom_type_value, str)
        local_path_value = row.get("local_path")
        local_path = _cast(local_path_value, str)
        created_at_value = row.get("created_at")
        created_at = _cast(
            created_at_value, datetime.datetime
        ) or datetime.datetime.now(datetime.UTC)

        return db_models.LayerMetadata(
            id=str(row["id"]),
            name=str(row["name"]),
            source=str(row["source"]),
            provider=cast(db_models.Provider, str(row["provider"])),
            table_name=table_name,
            geom_type=geom_type,
            srid=srid,
            bbox=bbox_tuple,  # type: ignore[arg-type]
            local_path=local_path,
            created_at=created_at,
        )


def get_layer_repository(settings: config.Settings) -> LayerRepositoryProtocol:
    """Factory function to create a layer repository.

    Args:
        settings: Application settings for database connection.

    Returns:
        PostgresLayerRepository instance for production use.
    """
    return PostgresLayerRepository(settings)


def get_connection(
    settings: config.Settings,
) -> psycopg2.extensions.connection:
    """Create a synchronous psycopg2 extensions connection.

    Args:
        settings: Application settings containing database connection URL.

    Returns:
        psycopg2 extensions connection object for direct database access.
    """
    return psycopg2.connect(settings.database_url)
