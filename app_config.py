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
    email_enabled: bool
    email_from: str
    email_reply_to: str
    support_reports_email: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_use_tls: bool
    smtp_use_ssl: bool

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
        email_enabled=os.environ.get("EMAIL_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on", "enabled"},
        email_from=os.environ.get("EMAIL_FROM", "").strip(),
        email_reply_to=os.environ.get("EMAIL_REPLY_TO", "").strip(),
        support_reports_email=os.environ.get("SUPPORT_REPORTS_EMAIL", "reports@shiftcare.co.il").strip(),
        smtp_host=os.environ.get("SMTP_HOST", "").strip(),
        smtp_port=int(os.environ.get("SMTP_PORT", "587").strip() or "587"),
        smtp_username=os.environ.get("SMTP_USERNAME", "").strip(),
        smtp_password=os.environ.get("SMTP_PASSWORD", "").strip(),
        smtp_use_tls=os.environ.get("SMTP_USE_TLS", "1").strip().lower() in {"1", "true", "yes", "on", "enabled"},
        smtp_use_ssl=os.environ.get("SMTP_USE_SSL", "0").strip().lower() in {"1", "true", "yes", "on", "enabled"},
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

    if config.is_deployed_env and not config.auth_token_secret:
        warnings.append(
            "AUTH_TOKEN_SECRET is not set. The current beta token implementation is database-backed, "
            "but deployed environments should still define a server secret before adding signed tokens or external integrations."
        )

    if config.email_enabled:
        missing_email = []
        if not config.email_from:
            missing_email.append("EMAIL_FROM")
        if not config.smtp_host:
            missing_email.append("SMTP_HOST")
        if not config.smtp_port:
            missing_email.append("SMTP_PORT")
        if missing_email:
            issues.append("Email delivery is enabled but incomplete: " + ", ".join(missing_email))

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
