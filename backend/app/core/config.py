from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings"""

    # Application basic settings
    APP_NAME: str = "Bidding Flash Sale System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # PostgreSQL database settings
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "bidding-flash-sale-system"

    # PgBouncer settings (set USE_PGBOUNCER=true to enable)
    USE_PGBOUNCER: bool = False
    PGBOUNCER_HOST: str = "127.0.0.1"
    PGBOUNCER_PORT: int = 6432

    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None
    REDIS_CACHE_EXPIRE: int = 3600
    AUTH_CACHE_TTL_SECONDS: int = 5
    AUTH_CACHE_MAX_ENTRIES: int = 5000

    # RabbitMQ settings
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"

    # JWT settings
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS settings
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    @property
    def DATABASE_URL(self) -> str:
        """Generate PostgreSQL connection string (via PgBouncer if enabled)"""
        if self.USE_PGBOUNCER:
            return (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.PGBOUNCER_HOST}:{self.PGBOUNCER_PORT}/{self.POSTGRES_DB}"
            )
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Generate synchronous PostgreSQL connection string (for Alembic)"""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def REDIS_URL(self) -> str:
        """Generate Redis connection string"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def RABBITMQ_URL(self) -> str:
        """Generate RabbitMQ connection string"""
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"


settings = Settings()
