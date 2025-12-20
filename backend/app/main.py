"""FastAPI entrypoint."""

import fastapi
from fastapi.middleware import cors

from app.api import ingest, layers, tiles
from app.core import config


def create_app() -> fastapi.FastAPI:
    """Create and configure the FastAPI application.

    Sets up CORS middleware, includes API routers,
    and adds a health check endpoint.

    Returns:
        Configured FastAPI application instance.
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
