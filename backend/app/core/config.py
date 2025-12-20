"""Application settings and configuration helpers."""

import functools
import pathlib

import pydantic
import pydantic_settings


class Settings(pydantic_settings.BaseSettings):
    """Runtime configuration pulled from environment variables or defaults.

    All settings can be overridden via environment variables or .env file.
    Directory paths are automatically created on initialization.
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

    Returns:
        Settings instance with all configuration values populated.
    """
    settings = Settings()
    settings.ensure_directories()
    return settings
