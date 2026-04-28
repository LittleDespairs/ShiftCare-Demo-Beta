from __future__ import annotations

from app_config import AppConfig, get_app_config


def _postgres_host(config: AppConfig) -> str:
    if config.database_host:
        return config.database_host
    if config.cloud_sql_connection_name:
        return f"/cloudsql/{config.cloud_sql_connection_name}"
    return ""


def check_postgres_connection(config: AppConfig | None = None) -> dict:
    config = config or get_app_config()
    try:
        import psycopg
    except ImportError as exc:
        return {
            "status": "error",
            "error": "psycopg is not installed",
            "details": str(exc),
        }

    host = _postgres_host(config)
    try:
        with psycopg.connect(
            dbname=config.database_name,
            user=config.database_user,
            password=config.database_password,
            host=host,
            port=config.database_port,
            sslmode=config.database_ssl_mode if config.database_host else "disable",
            connect_timeout=5,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "host": host or None,
        }

    return {
        "status": "ok",
        "host": host or None,
        "database": config.database_name,
        "user": config.database_user,
    }
