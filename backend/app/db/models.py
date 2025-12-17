"""Database-adjacent data structures."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Optional, Tuple


BBox = Tuple[float, float, float, float]
Provider = Literal["postgis", "geopackage", "cog", "mbtiles"]


@dataclass
class LayerMetadata:
    """Represents a vector or raster layer the app knows about."""

    id: str
    name: str
    source: str
    provider: Provider
    table_name: Optional[str]
    geom_type: Optional[str]
    srid: Optional[int]
    bbox: Optional[BBox]
    local_path: Optional[str]
    created_at: datetime = datetime.now(tz=timezone.utc)
