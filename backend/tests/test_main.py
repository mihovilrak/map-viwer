"""Tests for the FastAPI main application factory and health checks.

This module validates that:
    - The FastAPI app is correctly instantiated via main.create_app,
    - OpenAPI metadata (title, version) matches the project contract,
    - Core routers such as health and API endpoints are registered,
    - The /health endpoint returns the expected response.

These tests verify the compositional integrity of the FastAPI app
and are independent of repository or service implementation details.

See Also:
    - backend/app/main.py for the application factory.
"""

from __future__ import annotations

from typing import cast

from fastapi import testclient

from backend.app import main


def test_create_app() -> None:
    """Test that create_app returns a configured FastAPI instance."""
    app = main.create_app()
    assert app is not None
    assert app.title == "Map Viewer"
    assert app.version == "0.1.0"


def test_health_endpoint() -> None:
    """Test the health check endpoint returns ok status."""
    app = main.create_app()
    client = testclient.TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_app_includes_routers() -> None:
    """Test that all API routers are included in the app."""
    app = main.create_app()
    routes: list[str] = [
        cast(str, getattr(route, "path", ""))
        for route in app.routes  # type: ignore[attr-defined]
        if hasattr(route, "path")
    ]
    assert "/health" in routes
    api_routes: list[str] = [
        route_path
        for route_path in routes
        if route_path.startswith("/api") or route_path.startswith("/tiles")
    ]
    assert len(api_routes) > 0
