from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://watchpoint:watchpoint@localhost:5432/watchpoint"
    cors_origins: str = "http://localhost:3000"
    storage_path: str = "./storage"
    api_version: str = "0.1.0"
    jwt_secret_key: str = "watchpoint-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    anthropic_api_key: str = ""  # optional — LLM summary disabled if empty
    # POST /seed/demo writes fixed-ID demo data. Off by default so an
    # unconfigured production deploy cannot be seeded by an anonymous caller.
    # docker-compose sets this true for local dev; render.yaml sets it false.
    enable_demo_seed: bool = False

    model_config = {"env_file": ".env", "extra": "ignore"}

    @field_validator("database_url")
    @classmethod
    def normalize_postgres_url(cls, v: str) -> str:
        """Auto-rewrite plain postgres:// URLs to postgresql+asyncpg:// for SQLAlchemy.

        Supabase, Render, and Heroku all expose URLs as postgres:// or postgresql://
        but SQLAlchemy with asyncpg driver requires postgresql+asyncpg://.
        Also strips ?sslmode=require since asyncpg uses ssl=true via different mechanism.
        """
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://") and "+asyncpg" not in v:
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        # asyncpg doesn't accept sslmode in URL params; remove it (asyncpg uses TLS by default for hosted DBs)
        if "?" in v:
            base, params = v.split("?", 1)
            kept = [p for p in params.split("&") if not p.startswith("sslmode=")]
            v = base + ("?" + "&".join(kept) if kept else "")
        return v


settings = Settings()
