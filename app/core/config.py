import json
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors_origins_value(v: Any) -> list[str]:
    if isinstance(v, list):
        return [str(item).strip() for item in v if str(item).strip()]
    if isinstance(v, str):
        v = v.strip()
        if not v or v == "*":
            return ["*"]
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1].strip()
        if not v or v == "*":
            return ["*"]
        if v.startswith("[") and v.endswith("]"):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except Exception:
                pass
            cleaned = v[1:-1]
            return [
                item.strip().strip("'\"")
                for item in cleaned.split(",")
                if item.strip().strip("'\"")
            ]
        return [
            item.strip().strip("'\"")
            for item in v.split(",")
            if item.strip().strip("'\"")
        ]
    return ["*"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Perretes Tiernos API"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    CORS_ORIGINS: Any = ["*"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        return parse_cors_origins_value(v)

    # Base de datos PostgreSQL en Supabase
    DATABASE_URL: str = "sqlite+aiosqlite:///:memory:"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Redis & Workers ARQ (Railway)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Supabase Auth & Storage
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_JWT_SECRET: str = "dev-only-jwt-secret-change-in-production-32bytes"
    SUPABASE_JWT_AUDIENCE: str = "authenticated"
    SUPABASE_JWKS_URL: str = ""
    SUPABASE_STORAGE_BUCKET_PUBLIC: str = "public-media"
    SUPABASE_STORAGE_BUCKET_PRIVATE: str = "private-verifications"

    # Observabilidad y servicios externos
    SENTRY_DSN: str = ""
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "no-reply@perretestiernos.es"
    MAPS_API_KEY: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Rate Limiting
    RATE_LIMIT_DEFAULT_PER_MINUTE: int = 60
    RATE_LIMIT_SENSITIVE_PER_MINUTE: int = 15

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ("production", "prod")


settings = Settings()

