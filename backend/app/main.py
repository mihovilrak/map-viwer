"""FastAPI entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ingest, layers, tiles
from app.core.config import get_settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    app = FastAPI(title="Map Viewer", version="0.1.0")

    app.include_router(ingest.router)
    app.include_router(layers.router)
    app.include_router(tiles.router)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allow_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:  # type: ignore[misc]
        """Health probe endpoint."""
        return {"status": "ok"}

    return app


app = create_app()

