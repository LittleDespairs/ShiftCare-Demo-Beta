import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class AppConfig:
    app_env: str
    database_engine: str
    database_path: str
    database_name: str
    database_user: str
    database_password: str
    database_host: str
    database_port: int
    database_ssl_mode: str
    cloud_sql_connection_name: str
    google_cloud_project: str
    google_cloud_region: str
    auth_token_secret: str
    cloud_run_service: str
    public_app_base_url: str

    @property
    def is_cloud_run(self) -> bool:
        return bool(self.cloud_run_service)

    @property
    def is_deployed_env(self) -> bool:
        return self.app_env in {"staging", "production"} or self.is_cloud_run


def get_app_config() -> AppConfig:
    return AppConfig(
        app_env=os.environ.get("APP_ENV", "development").strip().lower() or "development",
        database_engine=os.environ.get("DATABASE_ENGINE", "sqlite").strip().lower() or "sqlite",
        database_path=os.environ.get("SCHEDULE_APP_DATABASE_PATH", "").strip(),
        database_name=os.environ.get("DATABASE_NAME", "").strip(),
        database_user=os.environ.get("DATABASE_USER", "").strip(),
        database_password=os.environ.get("DATABASE_PASSWORD", "").strip(),
        database_host=os.environ.get("DATABASE_HOST", "").strip(),
        database_port=int(os.environ.get("DATABASE_PORT", "5432").strip() or "5432"),
        database_ssl_mode=os.environ.get("DATABASE_SSL_MODE", "require").strip().lower() or "require",
        cloud_sql_connection_name=os.environ.get("CLOUD_SQL_CONNECTION_NAME", "").strip(),
        google_cloud_project=os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip(),
        google_cloud_region=os.environ.get("GOOGLE_CLOUD_REGION", "").strip(),
        auth_token_secret=os.environ.get("AUTH_TOKEN_SECRET", "").strip(),
        cloud_run_service=os.environ.get("K_SERVICE", "").strip(),
        public_app_base_url=os.environ.get("PUBLIC_APP_BASE_URL", "").strip().rstrip("/"),
    )


def validate_runtime_config(config: AppConfig | None = None) -> dict:
    config = config or get_app_config()
    issues: list[str] = []
    warnings: list[str] = []

    if config.database_engine not in {"sqlite", "postgres", "postgresql"}:
        issues.append(f"DATABASE_ENGINE={config.database_engine} is not supported.")

    if config.database_engine in {"postgres", "postgresql"}:
        missing = []
        if not config.database_name:
            missing.append("DATABASE_NAME")
        if not config.database_user:
            missing.append("DATABASE_USER")
        if not config.database_password:
            missing.append("DATABASE_PASSWORD")
        if not config.database_host and not config.cloud_sql_connection_name:
            missing.append("DATABASE_HOST or CLOUD_SQL_CONNECTION_NAME")
        if missing:
            issues.append("PostgreSQL configuration is incomplete: " + ", ".join(missing))

        issues.append(
            "PostgreSQL/Cloud SQL connectivity can be checked, but the application data layer is not yet switched "
            "from SQLite SQL to PostgreSQL SQL. Keep production traffic blocked until the adapter migration is complete."
        )

    if config.is_deployed_env and not config.auth_token_secret:
        warnings.append(
            "AUTH_TOKEN_SECRET is not set. The current beta token implementation is database-backed, "
            "but deployed environments should still define a server secret before adding signed tokens or external integrations."
        )

    if config.is_cloud_run and config.database_engine == "sqlite":
        warnings.append(
            "Cloud Run is using SQLite. This is acceptable only for smoke tests because the container filesystem is ephemeral."
        )

    if config.database_path:
        database_path = Path(config.database_path)
        if not database_path.parent.exists():
            issues.append(f"SCHEDULE_APP_DATABASE_PATH parent directory does not exist: {database_path.parent}")

    return {
        "status": "ok" if not issues else "blocked",
        "environment": config.app_env,
        "database_engine": config.database_engine,
        "is_cloud_run": config.is_cloud_run,
        "cloud_run_service": config.cloud_run_service or None,
        "cloud_sql_connection_name_configured": bool(config.cloud_sql_connection_name),
        "google_cloud_project_configured": bool(config.google_cloud_project),
        "google_cloud_region_configured": bool(config.google_cloud_region),
        "issues": issues,
        "warnings": warnings,
    }
