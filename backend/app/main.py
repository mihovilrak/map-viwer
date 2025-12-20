"""FastAPI application entrypoint and configuration.

This module provides the main FastAPI application factory that sets up
CORS middleware, includes API routers for ingestion, layers, and tiles,
and exposes a health check endpoint for monitoring.

Example:
    The application can be run with uvicorn:
        $ uvicorn app.main:app --reload

    Or imported and used programmatically:
        >>> from app.main import app
        >>> # Use app in ASGI server
"""

import fastapi
from fastapi.middleware import cors

from app.api import ingest, layers, tiles
from app.core import config


def create_app() -> fastapi.FastAPI:
    """Create and configure the FastAPI application.

    Sets up CORS middleware, includes API routers for ingestion, layers,
    and tiles, and adds a health check endpoint. CORS origins are configured
    from settings, allowing cross-origin requests from specified domains.

    Returns:
        Configured FastAPI application instance ready for ASGI server.

    Example:
        The app can be used with uvicorn or other ASGI servers:
            >>> app = create_app()
            >>> # Or use the module-level app instance:
            >>> from app.main import app
    """
    settings = config.get_settings()
    app = fastapi.FastAPI(title="Map Viewer", version="0.1.0")

    app.include_router(ingest.router)
    app.include_router(layers.router)
    app.include_router(tiles.router)

    app.add_middleware(
        cors.CORSMiddleware,  # type: ignore[arg-type]
        allow_origins=settings.allow_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:  # type: ignore[misc]
        """Health check endpoint for monitoring and load balancers.

        Returns:
            Dictionary with status "ok" if the service is running.
        """
        return {"status": "ok"}

    return app


app = create_app()
