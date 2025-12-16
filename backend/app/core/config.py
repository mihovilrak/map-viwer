"""Application settings and configuration helpers."""

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration pulled from environment variables or defaults."""

    database_url: str = "postgresql://gis:gis@localhost:5432/gis"
    storage_dir: Path = Path("/tmp/map_viewer/uploads")
    raster_cache_dir: Path = Path("/tmp/map_viewer/cog")
    tegola_base_url: AnyHttpUrl | str = "http://localhost:8080"
    allow_origins: list[str] = ["*"]
    max_upload_size_bytes: int = 512 * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )

    def ensure_directories(self) -> None:
        """Create local directories for uploads and raster cache."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.raster_cache_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    settings = Settings()
    settings.ensure_directories()
    return settings

