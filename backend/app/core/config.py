"""Application settings and configuration management.

This module provides Pydantic-based settings management that loads
configuration from environment variables or a .env file. Settings include
database connection URLs, storage directories, Tegola service URLs, CORS
origins, and file upload size limits.

Example:
    Settings can be accessed via the cached get_settings() function:
        >>> from app.core.config import get_settings
        >>> settings = get_settings()
        >>> print(settings.database_url)

    Environment variables can override defaults:
        >>> DATABASE_URL=postgresql://user:pass@localhost:5432/db
        >>> STORAGE_DIR=/custom/path/uploads
        >>> MAX_UPLOAD_SIZE_BYTES=1073741824
"""

import functools
import pathlib

import pydantic
import pydantic_settings


class Settings(pydantic_settings.BaseSettings):
    """Runtime configuration pulled from environment variables or defaults.

    All settings can be overridden via environment variables or .env file.
    Directory paths are automatically created on initialization via
    ensure_directories().

    Attributes:
        database_url: PostgreSQL connection string with PostGIS support.
        storage_dir: Directory for temporary file uploads.
        raster_cache_dir: Directory for Cloud Optimized GeoTIFF storage.
        tegola_base_url: Base URL for Tegola vector tile service.
        allow_origins: List of allowed CORS origins (["*"] allows all).
        max_upload_size_bytes: Maximum file upload size (default 512MB).

    Example:
        Create settings with custom values:
            >>> settings = Settings(
            ...     database_url="postgresql://user:pass@localhost:5432/gis",
            ...     storage_dir=Path("/custom/uploads"),
            ...     max_upload_size_bytes=1024 * 1024 * 1024  # 1GB
            ... )
            >>> settings.ensure_directories()

        Or use environment variables:
            >>> export DATABASE_URL=postgresql://user:pass@localhost:5432/gis
            >>> export MAX_UPLOAD_SIZE_BYTES=1073741824
            >>> settings = Settings()  # Loads from environment
    """

    database_url: str = "postgresql://gis:gis@localhost:5432/gis"
    storage_dir: pathlib.Path = pathlib.Path("/tmp/map_viewer/uploads")
    raster_cache_dir: pathlib.Path = pathlib.Path("/tmp/map_viewer/cog")
    tegola_base_url: pydantic.AnyHttpUrl | str = "http://localhost:8080"
    allow_origins: list[str] = ["*"]
    max_upload_size_bytes: int = 512 * 1024 * 1024

    model_config = pydantic_settings.SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    def ensure_directories(self) -> None:
        """Create local directories for uploads and raster cache.

        Creates storage_dir for uploaded files and raster_cache_dir for
        Cloud Optimized GeoTIFFs if they don't already exist.
        """
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.raster_cache_dir.mkdir(parents=True, exist_ok=True)


@functools.lru_cache
def get_settings() -> Settings:
    """Get cached settings instance with directories initialized.

    Settings are loaded from environment variables or .env file and cached
    for the lifetime of the application. Directories are created on first call.
    Subsequent calls return the same cached instance.

    Returns:
        Settings instance with all configuration values populated and
        directories ensured to exist.

    Example:
        Get settings anywhere in the application:
            >>> from app.core.config import get_settings
            >>> settings = get_settings()
            >>> print(settings.database_url)

        The settings are cached, so multiple calls return the same instance:
            >>> settings1 = get_settings()
            >>> settings2 = get_settings()
            >>> assert settings1 is settings2  # Same instance
    """
    settings = Settings()
    settings.ensure_directories()
    return settings
