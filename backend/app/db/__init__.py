"""Database interface and repository abstractions.

This module consolidates database interfaces/protocols and repository patterns
for layer metadata management. It provides a stable import location for
repository dependency injection throughout the application, supporting
production and testing backends.

Re-exports LayerRepositoryProtocol and repository constructors
from app.db.database for convenience and to centralize database access logic.

Example:
    Use in a service or FastAPI dependency:
        >>> from app.db import LayerRepositoryProtocol, get_layer_repository
        >>> repo = get_layer_repository(settings)
"""

