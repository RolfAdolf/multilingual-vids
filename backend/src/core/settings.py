import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


BASE_DIR = Path(os.getcwd())
DEBUG = int(os.environ.get("DEBUG", 0))


class AppSettings(BaseSettings):
    app_host: str = Field("0.0.0.0", alias="APP_HOST")
    app_port: int = Field(8888, alias="APP_PORT")
    storage_dir: Path = Field(BASE_DIR / "storage", alias="STORAGE_DIR")
    cors_origins: str = Field("http://localhost:5173,http://localhost:3000", alias="CORS_ORIGINS")

    @property
    def parsed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


class DatabaseSettings(BaseSettings):
    db: str = Field(..., alias="DATABASE_DB")
    password: str = Field(..., alias="DATABASE_PASSWORD")
    user: str = Field(..., alias="DATABASE_USER")
    host: str = Field(..., alias="DATABASE_HOST")
    port: str = Field(..., alias="DATABASE_PORT")

    @property
    def dsn(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class TranslatorSettings(BaseSettings):
    provider: str = Field("seamless_m4t", alias="TRANSLATOR_PROVIDER")
    seamless_model: str = Field("facebook/hf-seamless-m4t-medium", alias="SEAMLESS_MODEL")
    device: str = Field("auto", alias="TRANSLATOR_DEVICE")


app_settings = AppSettings()
db_settings = DatabaseSettings()
translator_settings = TranslatorSettings()
