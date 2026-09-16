"""Runtime settings and data-directory layout."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import platformdirs
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def default_data_dir() -> Path:
    return Path(platformdirs.user_data_dir("KotobaStudio", appauthor=False))


class Settings(BaseSettings):
    """Process-level settings. Override with KOTOBA_* environment variables."""

    model_config = SettingsConfigDict(env_prefix="KOTOBA_", extra="ignore")

    data_dir: Path = Field(default_factory=default_data_dir)
    host: str = "127.0.0.1"
    port: int = 8720
    web_dist: Path | None = None
    ai_key: str | None = None
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


@dataclass(frozen=True)
class Paths:
    data_dir: Path

    @property
    def db_path(self) -> Path:
        return self.data_dir / "kotoba.db"

    @property
    def media_dir(self) -> Path:
        return self.data_dir / "media"

    @property
    def screens_dir(self) -> Path:
        return self.media_dir / "screens"

    @property
    def audio_dir(self) -> Path:
        return self.media_dir / "audio"

    @property
    def dicts_dir(self) -> Path:
        return self.data_dir / "dicts"

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def exports_dir(self) -> Path:
        return self.data_dir / "exports"

    def ensure(self) -> Paths:
        for d in (
            self.data_dir,
            self.media_dir,
            self.screens_dir,
            self.audio_dir,
            self.dicts_dir,
            self.backups_dir,
            self.exports_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)
        return self


def paths(settings: Settings | None = None) -> Paths:
    return Paths((settings or get_settings()).data_dir)
