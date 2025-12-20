"""API router subpackage for map viewer backend.

This package organizes REST endpoints for core map viewer functionality,
including layer management, vector/raster tile serving, and related utilities.
Each module exposes its own APIRouter for composition in the application's
main FastAPI instance.

Submodules:
    - layers: Endpoints for registering, listing, and describing map layers.
    - tiles: Endpoints for serving vector (via Tegola) and raster (rio-tiler)
      map tiles.
    - (future) auth, healthcheck, and additional APIs.

Routers are grouped by major feature domain to promote clarity and
independent testing.
"""

