import os
from dataclasses import dataclass, field
from pathlib import Path


def csv_env(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    service_name: str = os.getenv("SERVICE_NAME", "demo-order-service")
    environment: str = os.getenv("ENVIRONMENT", "local")
    version: str = os.getenv("APP_VERSION", "0.1.0")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./demo_order_service.db")
    log_file_path: str = os.getenv(
        "LOG_FILE_PATH", str(Path("logs") / "demo-order-service.log")
    )
    reconciliation_job_enabled: bool = (
        os.getenv("RECONCILIATION_JOB_ENABLED", "true").lower() == "true"
    )
    reconciliation_interval_seconds: float = float(
        os.getenv("RECONCILIATION_INTERVAL_SECONDS", "30")
    )
    cors_allowed_origins: list[str] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "cors_allowed_origins",
            csv_env(
                "CORS_ALLOWED_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ),
        )


settings = Settings()
