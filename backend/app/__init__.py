"""App package initializer for backend FastAPI geospatial service.

This package contains the core backend for geospatial vector
and raster data ingestion,tile serving, and metadata management.
The system ensures all ingested data istransformed to EPSG:3857
(Web Mercator) at import time and provides APIs forlayer registration,
Cloud Optimized GeoTIFF workflows, and PostGIS-backed vector tiles.

- Handles secure ingestion of OGR/GDAL datasets into PostGIS and COGs
- Stores and manages layer metadata for fast lookup and API discovery
- Vector tiles served via PostGIS queries (EPSG:3857) through proxy endpoints
- Raster tiles generated on-demand via rio-tiler
- Designed for robust FastAPI dependency injection, testability, and compliance
  with modern geospatial backend standards

See README and module sub-docstrings for details on architecture and usage.
"""
