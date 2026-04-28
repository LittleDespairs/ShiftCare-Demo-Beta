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
    cloud_sql_connection_name: str
    google_cloud_project: str
    google_cloud_region: str
    auth_token_secret: str
    cloud_run_service: str

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
        cloud_sql_connection_name=os.environ.get("CLOUD_SQL_CONNECTION_NAME", "").strip(),
        google_cloud_project=os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip(),
        google_cloud_region=os.environ.get("GOOGLE_CLOUD_REGION", "").strip(),
        auth_token_secret=os.environ.get("AUTH_TOKEN_SECRET", "").strip(),
        cloud_run_service=os.environ.get("K_SERVICE", "").strip(),
    )


def validate_runtime_config(config: AppConfig | None = None) -> dict:
    config = config or get_app_config()
    issues: list[str] = []
    warnings: list[str] = []

    if config.database_engine not in {"sqlite"}:
        issues.append(
            "DATABASE_ENGINE=%s is configured, but the current 0.14.x beta backend still uses the SQLite data layer. "
            "PostgreSQL/Cloud SQL support needs a dedicated migration before production data can run on Google Cloud."
            % config.database_engine
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
