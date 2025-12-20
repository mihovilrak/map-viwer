"""Database-adjacent data structures."""

from __future__ import annotations

import dataclasses
import datetime
from typing import Literal

BBox = tuple[float, float, float, float]
Provider = Literal["postgis", "geopackage", "cog", "mbtiles"]


@dataclasses.dataclass
class LayerMetadata:
    """Represents a vector or raster layer the app knows about."""

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
