"""Database helpers and repositories for layer metadata."""

from collections.abc import Iterable
from typing import Dict, Optional, Protocol

import psycopg
from psycopg.rows import dict_row

from app.core.config import Settings
from app.db.models import LayerMetadata


class LayerRepositoryProtocol(Protocol):
    """Interface for storing and retrieving layer metadata."""

    def add(self, layer: LayerMetadata) -> LayerMetadata: ...

    def get(self, layer_id: str) -> Optional[LayerMetadata]: ...

    def all(self) -> Iterable[LayerMetadata]: ...


class InMemoryLayerRepository(LayerRepositoryProtocol):
    """Simple in-memory store for tests and local development."""

    def __init__(self) -> None:
        self._store: Dict[str, LayerMetadata] = {}

    def add(self, layer: LayerMetadata) -> LayerMetadata:
        self._store[layer.id] = layer
        return layer

    def get(self, layer_id: str) -> Optional[LayerMetadata]:
        return self._store.get(layer_id)

    def all(self) -> Iterable[LayerMetadata]:
        return self._store.values()


class PostgresLayerRepository(LayerRepositoryProtocol):
    """PostgreSQL/PostGIS-backed repository for layer metadata."""

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

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._ensure_schema()

    def _connection(self) -> psycopg.Connection:
        return psycopg.connect(self.settings.database_url)

    def _ensure_schema(self) -> None:
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
            cur.execute(self.CREATE_TABLE_SQL)
            conn.commit()

    def add(self, layer: LayerMetadata) -> LayerMetadata:
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO layers (
                    id, name, source, provider, table_name, geom_type, srid,
                    bbox_minx, bbox_miny, bbox_maxx, bbox_maxy, local_path, created_at
                ) VALUES (%(id)s, %(name)s, %(source)s, %(provider)s, %(table_name)s,
                    %(geom_type)s, %(srid)s, %(bbox_minx)s, %(bbox_miny)s,
                    %(bbox_maxx)s, %(bbox_maxy)s, %(local_path)s, %(created_at)s)
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

    def get(self, layer_id: str) -> Optional[LayerMetadata]:
        with self._connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM layers WHERE id = %s", (layer_id,))
            row = cur.fetchone()
            if not row:
                return None
            return self._from_row(row)

    def all(self) -> Iterable[LayerMetadata]:
        with self._connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM layers ORDER BY created_at DESC")
            for row in cur.fetchall():
                yield self._from_row(row)

    @staticmethod
    def _to_row(layer: LayerMetadata) -> Dict[str, object]:
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
    def _from_row(row: Dict[str, object]) -> LayerMetadata:
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
        return LayerMetadata(
            id=str(row["id"]),
            name=str(row["name"]),
            source=str(row["source"]),
            provider=str(row["provider"]),
            table_name=row.get("table_name"),
            geom_type=row.get("geom_type"),
            srid=row.get("srid"),
            bbox=bbox_tuple,  # type: ignore[arg-type]
            local_path=row.get("local_path"),
            created_at=row.get("created_at"),
        )


def get_layer_repository(settings: Settings) -> LayerRepositoryProtocol:
    """Return a Postgres-backed layer repository."""
    return PostgresLayerRepository(settings)


def get_connection(settings: Settings) -> psycopg.Connection:
    """Create a synchronous psycopg connection using provided settings."""
    return psycopg.connect(settings.database_url)

