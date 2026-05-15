import shutil
import sqlite3
import sys
import os
import json
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from app_config import get_app_config
from db_adapter import apply_postgres_schema, connect_postgres, is_postgres_engine

# Base directory / Базовая папка проекта
BASE_DIR = Path(__file__).resolve().parent


def get_windows_app_data_dir() -> Path:
    app_data_root = os.environ.get("LOCALAPPDATA")
    if app_data_root:
        app_data_dir = Path(app_data_root) / "Schedule App"
    else:
        app_data_dir = Path.home() / "AppData" / "Local" / "Schedule App"

    app_data_dir.mkdir(parents=True, exist_ok=True)
    return app_data_dir


def get_database_path() -> Path:
    configured_path = os.environ.get("SCHEDULE_APP_DATABASE_PATH", "").strip()
    if configured_path:
        runtime_path = Path(configured_path).expanduser()
        runtime_path.parent.mkdir(parents=True, exist_ok=True)
        return runtime_path

    if getattr(sys, "frozen", False):
        runtime_dir = get_windows_app_data_dir()
        runtime_path = runtime_dir / "schedule_app.db"

        if not runtime_path.exists():
            bundled_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
            bundled_path = bundled_dir / "schedule_app.db"
            if bundled_path.exists():
                shutil.copy2(bundled_path, runtime_path)

        return runtime_path

    if os.environ.get("ANDROID_ROOT") and os.environ.get("ANDROID_DATA") and os.environ.get("HOME"):
        runtime_dir = Path(os.environ["HOME"]).resolve()
        runtime_dir.mkdir(parents=True, exist_ok=True)
        runtime_path = runtime_dir / "schedule_app.db"

        if not runtime_path.exists():
            bundled_path = BASE_DIR / "schedule_app.db"
            if bundled_path.exists():
                shutil.copy2(bundled_path, runtime_path)

        return runtime_path

    return BASE_DIR / "schedule_app.db"


def get_bundled_database_path() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    bundled_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    bundled_path = bundled_dir / "schedule_app.db"
    return bundled_path if bundled_path.exists() else None


# Database file path / Путь к файлу базы данных
DATABASE_PATH = get_database_path()
DEFAULT_ORGANIZATION_PUBLIC_ID = "local-default"
CURRENT_SCHEMA_VERSION = 18
POSTGRES_SCHEMA_PATH = BASE_DIR / "docs" / "postgresql" / "001_initial_schema.sql"
PUBLIC_ID_TABLE_PREFIXES = {
    "employees": "emp",
    "positions": "pos",
    "shift_templates": "tpl",
    "schedule_entries": "sch",
    "shift_requirements": "shr",
    "employee_preferences": "prf",
    "employee_week_preferences": "wpr",
    "employee_recurring_preferences": "rpr",
    "employee_day_statuses": "dst",
    "coverage_requirements": "cov",
}
DESKTOP_SYNC_TABLES = tuple(PUBLIC_ID_TABLE_PREFIXES.keys())


class ClosingSQLiteConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def _table_columns(cursor: sqlite3.Cursor, table_name: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row["name"] for row in cursor.fetchall()}


def _add_column_if_missing(cursor: sqlite3.Cursor, table_name: str, column_name: str, definition: str) -> None:
    if column_name not in _table_columns(cursor, table_name):
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def _ensure_postgres_runtime_schema(connection) -> None:
    cursor = connection.cursor(track_lastrowid=False)
    try:
        cursor.execute("""
            ALTER TABLE employee_week_preferences
            ADD COLUMN IF NOT EXISTS request_type TEXT NOT NULL DEFAULT 'request_shift'
        """)
        cursor.execute("""
            ALTER TABLE employee_week_preferences
            ADD COLUMN IF NOT EXISTS target_category TEXT
        """)
        cursor.execute("""
            UPDATE employee_week_preferences
            SET request_type = CASE
                    WHEN preference_type = 'off_day' THEN 'day_off'
                    WHEN preference_type = 'vacation' THEN 'vacation'
                    WHEN preference_type LIKE 'not_%' THEN 'exclude_shift'
                    ELSE request_type
                END,
                target_category = CASE
                    WHEN preference_type LIKE '%morning' THEN 'morning'
                    WHEN preference_type LIKE '%evening' THEN 'evening'
                    WHEN preference_type LIKE '%night' THEN 'night'
                    ELSE target_category
                END
        """)
        cursor.execute("""
            ALTER TABLE employee_week_preferences
            DROP CONSTRAINT IF EXISTS employee_week_preferences_employee_id_preference_date_key
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_employee_week_preferences_request
            ON employee_week_preferences (employee_id, preference_date, request_type, target_category)
        """)
        cursor.execute("""
            ALTER TABLE employee_day_statuses
            DROP CONSTRAINT IF EXISTS employee_day_statuses_status_type_check
        """)
        cursor.execute("""
            ALTER TABLE employee_day_statuses
            ADD CONSTRAINT employee_day_statuses_status_type_check
            CHECK (status_type IN ('sick', 'day_off', 'vacation'))
        """)
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def _rebuild_employee_week_preferences_for_multiple_requests(cursor: sqlite3.Cursor) -> None:
    cursor.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'employee_week_preferences'")
    row = cursor.fetchone()
    table_sql = row["sql"] if row else ""
    compact_sql = table_sql.replace(" ", "")
    if "UNIQUE(employee_id,preference_date)" not in compact_sql:
        return

    cursor.execute("ALTER TABLE employee_week_preferences RENAME TO employee_week_preferences_old")
    cursor.execute("""
        CREATE TABLE employee_week_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            week_start_date TEXT NOT NULL,
            preference_date TEXT NOT NULL,
            preference_type TEXT NOT NULL,
            request_type TEXT NOT NULL DEFAULT 'request_shift',
            target_category TEXT,
            organization_id INTEGER NOT NULL DEFAULT 1,
            public_id TEXT,
            created_at TEXT,
            updated_at TEXT,
            updated_by INTEGER,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
        )
    """)
    old_columns = _table_columns(cursor, "employee_week_preferences_old")
    cursor.execute(
        f"""
        INSERT INTO employee_week_preferences (
            id, employee_id, week_start_date, preference_date, preference_type,
            request_type, target_category, organization_id, public_id, created_at, updated_at, updated_by
        )
        SELECT
            id,
            employee_id,
            week_start_date,
            preference_date,
            preference_type,
            CASE
                WHEN preference_type = 'off_day' THEN 'day_off'
                WHEN preference_type = 'vacation' THEN 'vacation'
                WHEN preference_type LIKE 'not_%' THEN 'exclude_shift'
                ELSE 'request_shift'
            END,
            CASE
                WHEN preference_type LIKE '%morning' THEN 'morning'
                WHEN preference_type LIKE '%evening' THEN 'evening'
                WHEN preference_type LIKE '%night' THEN 'night'
                ELSE NULL
            END,
            {"organization_id" if "organization_id" in old_columns else "1"},
            {"public_id" if "public_id" in old_columns else "NULL"},
            {"created_at" if "created_at" in old_columns else "NULL"},
            {"updated_at" if "updated_at" in old_columns else "NULL"},
            {"updated_by" if "updated_by" in old_columns else "NULL"}
        FROM employee_week_preferences_old
        WHERE preference_type <> 'no_preference'
        """
    )
    cursor.execute("DROP TABLE employee_week_preferences_old")


def _ensure_schema_migration_tables(cursor: sqlite3.Cursor) -> None:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_version INTEGER NOT NULL,
            to_version INTEGER NOT NULL,
            description TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)


def _get_schema_version(cursor: sqlite3.Cursor) -> int:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'schema_metadata'"
    )
    if not cursor.fetchone():
        return 0
    cursor.execute("SELECT value FROM schema_metadata WHERE key = 'schema_version'")
    row = cursor.fetchone()
    if not row:
        return 0
    try:
        return int(row["value"])
    except (TypeError, ValueError):
        return 0


def _set_schema_version(cursor: sqlite3.Cursor, version: int) -> None:
    cursor.execute(
        """
        INSERT INTO schema_metadata (key, value, updated_at)
        VALUES ('schema_version', ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key)
        DO UPDATE SET value = excluded.value,
                      updated_at = excluded.updated_at
        """,
        (str(version),),
    )


def _record_schema_migration(
    cursor: sqlite3.Cursor,
    from_version: int,
    to_version: int,
    description: str,
) -> None:
    cursor.execute(
        """
        INSERT INTO schema_migrations (from_version, to_version, description)
        VALUES (?, ?, ?)
        """,
        (from_version, to_version, description),
    )


def _ensure_public_ids(cursor: sqlite3.Cursor, table_name: str, prefix: str) -> None:
    _add_column_if_missing(cursor, table_name, "public_id", "TEXT")
    cursor.execute(
        f"""
        UPDATE {table_name}
        SET public_id = ? || '_' || lower(hex(randomblob(16)))
        WHERE public_id IS NULL OR public_id = ''
        """,
        (prefix,),
    )
    cursor.execute(
        f"""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_{table_name}_public_id
        ON {table_name} (public_id)
        """
    )
    cursor.execute(
        f"""
        CREATE TRIGGER IF NOT EXISTS trg_{table_name}_public_id
        AFTER INSERT ON {table_name}
        FOR EACH ROW
        WHEN NEW.public_id IS NULL OR NEW.public_id = ''
        BEGIN
            UPDATE {table_name}
            SET public_id = '{prefix}_' || lower(hex(randomblob(16)))
            WHERE id = NEW.id;
        END
        """
    )


def _ensure_desktop_sync_triggers(cursor: sqlite3.Cursor) -> None:
    for table_name in DESKTOP_SYNC_TABLES:
        cursor.execute(
            f"""
            CREATE TRIGGER IF NOT EXISTS trg_{table_name}_desktop_sync_insert
            AFTER INSERT ON {table_name}
            FOR EACH ROW
            BEGIN
                INSERT INTO desktop_sync_outbox (
                    organization_id, entity_type, entity_public_id, operation, payload_json
                )
                SELECT NEW.organization_id, '{table_name}', NEW.public_id, 'upsert', '{{}}'
                WHERE COALESCE((SELECT value FROM app_settings WHERE key = 'desktop_sync_suspended'), '0') != '1';
            END
            """
        )
        cursor.execute(
            f"""
            CREATE TRIGGER IF NOT EXISTS trg_{table_name}_desktop_sync_update
            AFTER UPDATE ON {table_name}
            FOR EACH ROW
            BEGIN
                INSERT INTO desktop_sync_outbox (
                    organization_id, entity_type, entity_public_id, operation, payload_json
                )
                SELECT NEW.organization_id, '{table_name}', NEW.public_id, 'upsert', '{{}}'
                WHERE COALESCE((SELECT value FROM app_settings WHERE key = 'desktop_sync_suspended'), '0') != '1';
            END
            """
        )
        cursor.execute(
            f"""
            CREATE TRIGGER IF NOT EXISTS trg_{table_name}_desktop_sync_delete
            AFTER DELETE ON {table_name}
            FOR EACH ROW
            BEGIN
                INSERT INTO desktop_sync_outbox (
                    organization_id, entity_type, entity_public_id, operation, payload_json
                )
                SELECT OLD.organization_id, '{table_name}', OLD.public_id, 'delete', '{{}}'
                WHERE COALESCE((SELECT value FROM app_settings WHERE key = 'desktop_sync_suspended'), '0') != '1';
            END
            """
        )


def _seed_licenses_from_bundled_database(cursor: sqlite3.Cursor) -> None:
    bundled_path = get_bundled_database_path()
    if not bundled_path or bundled_path.resolve() == DATABASE_PATH.resolve():
        return

    cursor.execute("SELECT COUNT(*) AS count FROM licenses WHERE organization_id = 1 AND revoked_at IS NULL")
    if int(cursor.fetchone()["count"] or 0) > 0:
        return

    cursor.execute("SELECT public_id FROM organizations WHERE id = 1")
    organization_row = cursor.fetchone()
    if not organization_row:
        return
    organization_public_id = organization_row["public_id"]

    bundled_connection = sqlite3.connect(bundled_path)
    bundled_connection.row_factory = sqlite3.Row
    try:
        bundled_cursor = bundled_connection.cursor()
        bundled_cursor.execute(
            """
            SELECT license_id, status, plan_code, employee_limit, support_cloud_expires_at,
                   grace_ends_at, certificate_json, signature, key_id, source,
                   imported_at, last_verified_at, revoked_at
            FROM licenses
            WHERE organization_id = 1
              AND revoked_at IS NULL
            ORDER BY imported_at DESC, id DESC
            """
        )
        for row in bundled_cursor.fetchall():
            try:
                certificate = json.loads(row["certificate_json"])
            except (TypeError, json.JSONDecodeError):
                continue
            if certificate.get("organization_public_id") != organization_public_id:
                continue
            cursor.execute(
                """
                INSERT INTO licenses (
                    organization_id, license_id, status, plan_code, employee_limit,
                    support_cloud_expires_at, grace_ends_at, certificate_json, signature,
                    key_id, source, imported_at, last_verified_at, revoked_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(license_id)
                DO UPDATE SET status = excluded.status,
                              plan_code = excluded.plan_code,
                              employee_limit = excluded.employee_limit,
                              support_cloud_expires_at = excluded.support_cloud_expires_at,
                              grace_ends_at = excluded.grace_ends_at,
                              certificate_json = excluded.certificate_json,
                              signature = excluded.signature,
                              key_id = excluded.key_id,
                              source = excluded.source,
                              imported_at = excluded.imported_at,
                              last_verified_at = excluded.last_verified_at,
                              revoked_at = excluded.revoked_at
                """,
                (
                    1,
                    row["license_id"],
                    row["status"],
                    row["plan_code"],
                    int(row["employee_limit"] or 0),
                    row["support_cloud_expires_at"],
                    row["grace_ends_at"],
                    row["certificate_json"],
                    row["signature"],
                    row["key_id"],
                    row["source"],
                    row["imported_at"],
                    row["last_verified_at"],
                    row["revoked_at"],
                ),
            )
            break
    finally:
        bundled_connection.close()


def get_backup_dir() -> Path:
    backup_dir = DATABASE_PATH.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def is_sqlite_runtime() -> bool:
    return not is_postgres_engine(get_app_config().database_engine)


def _sanitize_backup_label(label: str) -> str:
    filtered = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in (label or "backup"))
    filtered = filtered.strip("_")
    return filtered or "backup"


def validate_sqlite_file(path: Path) -> None:
    with path.open("rb") as file_handle:
        header = file_handle.read(16)
    if header != b"SQLite format 3\x00":
        raise ValueError("Uploaded file is not a valid SQLite database")

    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA quick_check")
    finally:
        connection.close()


def create_database_backup(label: str = "manual") -> Path:
    if not is_sqlite_runtime():
        raise NotImplementedError("File database backups are available only for the SQLite desktop runtime")
    source = DATABASE_PATH
    if not source.exists():
        raise FileNotFoundError(f"Database file does not exist: {source}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{source.stem}_{timestamp}_{_sanitize_backup_label(label)}.db"
    backup_path = get_backup_dir() / backup_name
    shutil.copy2(source, backup_path)
    return backup_path


def create_schedule_backup(
    label: str = "manual",
    app_version: str = "",
    schema_version: int = CURRENT_SCHEMA_VERSION,
    organization_id: int = 1,
    created_by: int | None = None,
) -> Path:
    if not is_sqlite_runtime():
        raise NotImplementedError("Schedule backup files are available only for the SQLite desktop runtime")
    source = DATABASE_PATH
    if not source.exists():
        raise FileNotFoundError(f"Database file does not exist: {source}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{source.stem}_{timestamp}_{_sanitize_backup_label(label)}.schedulebackup"
    backup_path = get_backup_dir() / backup_name
    metadata = {
        "format": "schedulebackup",
        "format_version": 1,
        "app_version": app_version,
        "schema_version": schema_version,
        "organization_id": organization_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "created_by": created_by,
        "contains_password_hashes": True,
        "contains_access_tokens": False,
        "contains_server_secrets": False,
    }
    with ZipFile(backup_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.write(source, "schedule_app.db")
        archive.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2))
    return backup_path


def list_database_backups(limit: int = 20) -> list[dict]:
    if not is_sqlite_runtime():
        return []
    backups = sorted(
        [*get_backup_dir().glob("*.db"), *get_backup_dir().glob("*.schedulebackup")],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    results = []
    for backup_path in backups[:limit]:
        stat = backup_path.stat()
        results.append(
            {
                "name": backup_path.name,
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                "format": "schedulebackup" if backup_path.suffix == ".schedulebackup" else "sqlite",
            }
        )
    return results


def _extract_schedule_backup(backup_path: Path) -> Path:
    temp_path = backup_path.with_suffix(".restore.db")
    with ZipFile(backup_path, "r") as archive:
        names = set(archive.namelist())
        if "schedule_app.db" not in names or "metadata.json" not in names:
            raise ValueError("Schedule backup is missing required files")
        with archive.open("schedule_app.db") as source_handle, temp_path.open("wb") as target_handle:
            shutil.copyfileobj(source_handle, target_handle)
    try:
        validate_sqlite_file(temp_path)
        return temp_path
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise


def restore_database_backup(backup_name: str) -> dict:
    if not is_sqlite_runtime():
        raise NotImplementedError("File restore is available only for the SQLite desktop runtime")
    backup_path = (get_backup_dir() / backup_name).resolve()
    backup_dir = get_backup_dir().resolve()
    if backup_dir not in backup_path.parents:
        raise ValueError("Backup path is outside the backup directory")
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file does not exist: {backup_name}")

    restore_source = backup_path
    extracted_path = None
    if backup_path.suffix == ".schedulebackup":
        extracted_path = _extract_schedule_backup(backup_path)
        restore_source = extracted_path
    else:
        validate_sqlite_file(backup_path)
    pre_restore_backup = create_database_backup("pre_restore")
    try:
        shutil.copy2(restore_source, DATABASE_PATH)
        return {
            "restored_backup": backup_path.name,
            "pre_restore_backup": pre_restore_backup.name,
        }
    finally:
        if extracted_path and extracted_path.exists():
            extracted_path.unlink()


def get_connection():
    config = get_app_config()
    if is_postgres_engine(config.database_engine):
        return connect_postgres(config)

    # Create SQLite connection / Создаём подключение к SQLite
    connection = sqlite3.connect(DATABASE_PATH, factory=ClosingSQLiteConnection)
    connection.execute("PRAGMA foreign_keys = ON")

    # Return rows as dictionary-like objects / Возвращаем строки как объекты с доступом по имени колонки
    connection.row_factory = sqlite3.Row
    return connection


def _postgres_schema_is_current(connection) -> bool:
    cursor = connection.cursor(track_lastrowid=False)
    try:
        cursor.execute("SELECT value FROM schema_metadata WHERE key = ?", ("schema_version",))
        row = cursor.fetchone()
    except Exception:
        connection.rollback()
        return False
    return bool(row and str(row["value"]) == str(CURRENT_SCHEMA_VERSION))


def init_db():
    if is_postgres_engine(get_app_config().database_engine):
        connection = get_connection()
        try:
            if not _postgres_schema_is_current(connection):
                apply_postgres_schema(connection, POSTGRES_SCHEMA_PATH)
            _ensure_postgres_runtime_schema(connection)
        finally:
            connection.close()
        return

    # Initialize database tables / Инициализируем таблицы базы данных
    connection = get_connection()
    cursor = connection.cursor()

    # Turn on foreign keys in SQLite / Включаем внешние ключи в SQLite
    cursor.execute("PRAGMA foreign_keys = ON")
    previous_schema_version = _get_schema_version(cursor)
    _ensure_schema_migration_tables(cursor)

    # ==========================================
    # Organizations and authorization / Организации и авторизация
    # ==========================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            public_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'deleted')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute(
        """
        INSERT OR IGNORE INTO organizations (id, public_id, name, status)
        VALUES (1, ?, 'Local Organization', 'active')
        """,
        (DEFAULT_ORGANIZATION_PUBLIC_ID,),
    )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            password_hash TEXT,
            status TEXT NOT NULL DEFAULT 'invited' CHECK (status IN ('invited', 'active', 'disabled')),
            email_verified INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_login_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS organization_memberships (
            organization_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'scheduler', 'employee', 'manager', 'read_only')),
            status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('invited', 'active', 'disabled')),
            employee_id INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (organization_id, user_id),
            FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE SET NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS organization_invitations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            employee_id INTEGER,
            role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'scheduler', 'employee', 'manager', 'read_only')),
            token_hash TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'expired', 'revoked')),
            expires_at TEXT NOT NULL,
            accepted_at TEXT,
            created_by_user_id INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE SET NULL,
            FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auth_audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER,
            user_id INTEGER,
            event_type TEXT NOT NULL,
            actor_ip TEXT,
            user_agent TEXT,
            metadata_json TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE SET NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auth_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT NOT NULL,
            revoked_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auth_password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            used_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auth_email_verification_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            used_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS desktop_sync_outbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL DEFAULT 1,
            entity_type TEXT NOT NULL,
            entity_public_id TEXT,
            operation TEXT NOT NULL CHECK (operation IN ('upsert', 'delete', 'replace')),
            payload_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'syncing', 'synced', 'failed')),
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            next_attempt_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            synced_at TEXT,
            FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)")
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_memberships_user
        ON organization_memberships (user_id, organization_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_invitations_org_email_status
        ON organization_invitations (organization_id, email, status)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_auth_audit_events_org_created
        ON auth_audit_events (organization_id, created_at)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_active
        ON auth_sessions (user_id, expires_at, revoked_at)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_auth_password_reset_tokens_user
        ON auth_password_reset_tokens (user_id, expires_at, used_at)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_auth_email_verification_tokens_user
        ON auth_email_verification_tokens (user_id, expires_at, used_at)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_desktop_sync_outbox_pending
        ON desktop_sync_outbox (status, next_attempt_at, created_at)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL DEFAULT 1,
            license_id TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('trial', 'active', 'payment_due', 'grace', 'expired', 'revoked')),
            plan_code TEXT NOT NULL,
            employee_limit INTEGER NOT NULL,
            support_cloud_expires_at TEXT,
            grace_ends_at TEXT,
            certificate_json TEXT NOT NULL,
            signature TEXT NOT NULL,
            key_id TEXT,
            source TEXT NOT NULL DEFAULT 'imported' CHECK (source IN ('imported', 'activation_code', 'refresh', 'support')),
            imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_verified_at TEXT,
            revoked_at TEXT,
            FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS license_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL DEFAULT 1,
            license_id TEXT,
            event_type TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS license_activation_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL DEFAULT 1,
            activation_code_hash TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('success', 'failed')),
            error TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_licenses_org_status
        ON licenses (organization_id, status, imported_at)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_license_events_org_created
        ON license_events (organization_id, created_at)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_license_activation_attempts_org_created
        ON license_activation_attempts (organization_id, created_at)
    """)

    # =========================
    # Employees / Сотрудники
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_card TEXT,
        full_name TEXT NOT NULL,
        sex TEXT NOT NULL CHECK (sex IN ('male', 'female')),
        min_shifts_per_week INTEGER NOT NULL,
        target_shifts_per_week INTEGER NOT NULL DEFAULT 0,
        max_shifts_per_week INTEGER NOT NULL,
        can_work_night INTEGER NOT NULL,
        can_work_weekends INTEGER NOT NULL,
        can_work_evenings_after_night INTEGER NOT NULL,
        can_work_mornings_and_evenings INTEGER NOT NULL
    )
""")

    # =========================
    # Positions / Должности
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        color TEXT NOT NULL DEFAULT '#eff6ff',
        requires_continuous_coverage INTEGER NOT NULL DEFAULT 0,
        minimum_staff_presence INTEGER NOT NULL DEFAULT 0,
        allow_same_day_other_positions INTEGER NOT NULL DEFAULT 0,
        max_consecutive_nights INTEGER,
        emergency_max_consecutive_nights INTEGER,
        max_consecutive_split_days INTEGER,
        emergency_max_consecutive_split_days INTEGER
    )
""")

    cursor.execute("PRAGMA table_info(positions)")
    position_columns = {row["name"] for row in cursor.fetchall()}
    if "color" not in position_columns:
        cursor.execute("ALTER TABLE positions ADD COLUMN color TEXT NOT NULL DEFAULT '#eff6ff'")
    if "allow_same_day_other_positions" not in position_columns:
        cursor.execute("ALTER TABLE positions ADD COLUMN allow_same_day_other_positions INTEGER NOT NULL DEFAULT 0")
    for column_name in (
        "max_consecutive_nights",
        "emergency_max_consecutive_nights",
        "max_consecutive_split_days",
        "emergency_max_consecutive_split_days",
    ):
        if column_name not in position_columns:
            cursor.execute(f"ALTER TABLE positions ADD COLUMN {column_name} INTEGER")

    # ==========================================
    # Employee-position assignments / Связи
    # ==========================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employee_positions (
            employee_id INTEGER NOT NULL,
            position_id INTEGER NOT NULL,
            is_primary INTEGER NOT NULL DEFAULT 0,
            priority_score INTEGER NOT NULL DEFAULT 50,
            is_fallback_only INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (employee_id, position_id),
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
            FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE
        )
    """)

    # ==========================================
    # Shift templates / Шаблоны смен
    # ==========================================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shift_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        position_id INTEGER,
        category TEXT NOT NULL CHECK (category IN ('morning', 'evening', 'night')),
        name TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        is_overnight INTEGER NOT NULL DEFAULT 0,
        is_active INTEGER NOT NULL DEFAULT 1,
        is_split_only INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE,
        UNIQUE(position_id, name)
    )
    """)

    cursor.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'shift_templates'")
    shift_templates_sql = cursor.fetchone()["sql"]
    if "position_id" not in shift_templates_sql or "UNIQUE(position_id, name)" not in shift_templates_sql:
        cursor.execute("ALTER TABLE shift_templates RENAME TO shift_templates_old")
        cursor.execute("""
        CREATE TABLE shift_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position_id INTEGER,
            category TEXT NOT NULL CHECK (category IN ('morning', 'evening', 'night')),
            name TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            is_overnight INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            is_split_only INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE,
            UNIQUE(position_id, name)
        )
        """)
        cursor.execute("""
        INSERT INTO shift_templates (id, position_id, category, name, start_time, end_time, is_overnight, is_active, is_split_only)
        SELECT id, NULL, category, name, start_time, end_time, is_overnight, is_active, is_split_only
        FROM shift_templates_old
        """)
        cursor.execute("DROP TABLE shift_templates_old")

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_shift_templates_position_active
        ON shift_templates (position_id, is_active, category, start_time, end_time)
        """
    )

    # ==========================================
    # Schedule entries / Записи расписания
    # ==========================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schedule_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            position_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            shift_template_id INTEGER NOT NULL,
            no_show INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
            FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE,
            FOREIGN KEY (shift_template_id) REFERENCES shift_templates(id) ON DELETE RESTRICT
        )
    """)

    cursor.execute("PRAGMA table_info(schedule_entries)")
    schedule_entry_columns = {row["name"] for row in cursor.fetchall()}
    if "no_show" not in schedule_entry_columns:
        cursor.execute("ALTER TABLE schedule_entries ADD COLUMN no_show INTEGER NOT NULL DEFAULT 0")

    schedule_entry_fk_targets = {row["table"] for row in cursor.execute("PRAGMA foreign_key_list(schedule_entries)")}
    if "shift_templates_old" in schedule_entry_fk_targets:
        cursor.execute("ALTER TABLE schedule_entries RENAME TO schedule_entries_old")
        cursor.execute("""
            CREATE TABLE schedule_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                position_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                shift_template_id INTEGER NOT NULL,
                no_show INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE,
                FOREIGN KEY (shift_template_id) REFERENCES shift_templates(id) ON DELETE RESTRICT
            )
        """)
        cursor.execute("""
            INSERT INTO schedule_entries (id, employee_id, position_id, date, shift_template_id, no_show)
            SELECT id, employee_id, position_id, date, shift_template_id, no_show
            FROM schedule_entries_old
        """)
        cursor.execute("DROP TABLE schedule_entries_old")

    # Optional helpful index / Полезный индекс
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_schedule_entries_employee_date
        ON schedule_entries (employee_id, date)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_schedule_entries_position_date
        ON schedule_entries (position_id, date)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_employee_positions_position_employee
        ON employee_positions (position_id, employee_id)
    """)

    # ==========================================
    # Shift requirements / Требования к сменам
    # ==========================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shift_requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position_id INTEGER NOT NULL,
            shift_category TEXT NOT NULL CHECK (shift_category IN ('morning', 'evening', 'night')),
            required_total INTEGER NOT NULL,
            required_female_min INTEGER NOT NULL,
            required_male_min INTEGER NOT NULL DEFAULT 0,
            UNIQUE(position_id, shift_category),
            FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("PRAGMA table_info(shift_requirements)")
    shift_requirement_columns = {row["name"] for row in cursor.fetchall()}
    if "required_male_min" not in shift_requirement_columns:
        cursor.execute("ALTER TABLE shift_requirements ADD COLUMN required_male_min INTEGER NOT NULL DEFAULT 0")

    # ==========================================
    # General employee preferences / Общие пожелания
    # ==========================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employee_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL UNIQUE,
            allow_morning INTEGER NOT NULL,
            allow_evening INTEGER NOT NULL,
            allow_night INTEGER NOT NULL,
            allow_morning_evening_combo INTEGER NOT NULL,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
        )
    """)

    # ==========================================
    # Weekly employee preferences / Недельные пожелания
    # ==========================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employee_week_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            week_start_date TEXT NOT NULL,
            preference_date TEXT NOT NULL,
            preference_type TEXT NOT NULL,
            UNIQUE(employee_id, preference_date),
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employee_day_statuses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status_type TEXT NOT NULL CHECK (status_type IN ('sick', 'day_off')),
            UNIQUE(employee_id, date),
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_employee_day_statuses_employee_date
        ON employee_day_statuses (employee_id, date)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_employee_week_preferences_employee_week
        ON employee_week_preferences (employee_id, week_start_date, preference_date)
    """)
    _rebuild_employee_week_preferences_for_multiple_requests(cursor)
    _add_column_if_missing(cursor, "employee_week_preferences", "request_type", "TEXT NOT NULL DEFAULT 'request_shift'")
    _add_column_if_missing(cursor, "employee_week_preferences", "target_category", "TEXT")
    cursor.execute("""
        UPDATE employee_week_preferences
        SET request_type = CASE
                WHEN preference_type = 'off_day' THEN 'day_off'
                WHEN preference_type = 'vacation' THEN 'vacation'
                WHEN preference_type LIKE 'not_%' THEN 'exclude_shift'
                ELSE request_type
            END,
            target_category = CASE
                WHEN preference_type LIKE '%morning' THEN 'morning'
                WHEN preference_type LIKE '%evening' THEN 'evening'
                WHEN preference_type LIKE '%night' THEN 'night'
                ELSE target_category
            END
    """)

    # ==============================================================
    # Permanent employee preferences / Постоянные пожелания
    # ==============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employee_recurring_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            preference_kind TEXT NOT NULL CHECK (preference_kind IN ('strict', 'soft')),
            day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
            preference_type TEXT NOT NULL CHECK (
                preference_type IN (
                    'off_day',
                    'vacation',
                    'only_morning',
                    'only_evening',
                    'only_night',
                    'not_morning',
                    'not_evening',
                    'not_night',
                    'no_morning_evening_combo'
                )
            ),
            UNIQUE(employee_id, preference_kind, day_of_week),
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_employee_recurring_preferences_employee
        ON employee_recurring_preferences (employee_id, preference_kind, day_of_week)
    """)

    cursor.execute("""
        UPDATE schedule_entries
        SET no_show = 1
        WHERE EXISTS (
            SELECT 1
            FROM employee_day_statuses eds
            WHERE eds.employee_id = schedule_entries.employee_id
              AND eds.date = schedule_entries.date
              AND eds.status_type = 'no_show'
        )
    """)
    cursor.execute("DELETE FROM employee_day_statuses WHERE status_type = 'no_show'")

    cursor.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'employee_day_statuses'")
    day_status_table_sql = cursor.fetchone()["sql"]
    if "vacation" not in day_status_table_sql:
        cursor.execute("ALTER TABLE employee_day_statuses RENAME TO employee_day_statuses_old")
        cursor.execute("""
            CREATE TABLE employee_day_statuses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                status_type TEXT NOT NULL CHECK (status_type IN ('sick', 'day_off', 'vacation')),
                UNIQUE(employee_id, date),
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            INSERT INTO employee_day_statuses (id, employee_id, date, status_type)
            SELECT id, employee_id, date, status_type
            FROM employee_day_statuses_old
            WHERE status_type IN ('sick', 'day_off', 'vacation')
        """)
        cursor.execute("DROP TABLE employee_day_statuses_old")

    # ==========================================
    # Time-based coverage requirements / Интервальные требования покрытия
    # ==========================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS coverage_requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position_id INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            required_total INTEGER NOT NULL,
            required_female_min INTEGER NOT NULL DEFAULT 0,
            required_male_min INTEGER NOT NULL DEFAULT 0,
            is_overnight INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("PRAGMA table_info(coverage_requirements)")
    coverage_requirement_columns = {row["name"] for row in cursor.fetchall()}
    if "required_male_min" not in coverage_requirement_columns:
        cursor.execute("ALTER TABLE coverage_requirements ADD COLUMN required_male_min INTEGER NOT NULL DEFAULT 0")

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_coverage_requirements_position
        ON coverage_requirements (position_id, start_time, end_time)
    """)

    # ==========================================
    # Application settings / Настройки приложения
    # ==========================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            organization_id INTEGER NOT NULL DEFAULT 1,
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
        )
    """)

    _add_column_if_missing(cursor, "app_settings", "organization_id", "INTEGER NOT NULL DEFAULT 1")

    cursor.execute("""
        INSERT OR IGNORE INTO app_settings (organization_id, key, value)
        VALUES
            (1, 'min_rest_minutes_between_morning_and_evening', '0'),
            (1, 'min_rest_minutes_after_night_before_evening', '480'),
            (1, 'max_daily_work_minutes', '720'),
            (1, 'schedule_coverage_display_mode', 'interval'),
            (1, 'schedule_morning_color', '#ecfeff'),
            (1, 'schedule_evening_color', '#fff7ed'),
            (1, 'schedule_night_color', '#eef2ff'),
            (1, 'schedule_status_color', '#f5f3ff'),
            (1, 'max_work_days_per_week', '6'),
            (1, 'max_consecutive_nights', '2'),
            (1, 'emergency_max_consecutive_nights', '3'),
            (1, 'max_consecutive_split_days', '2'),
            (1, 'emergency_max_consecutive_split_days', '3'),
            (1, 'allow_multiple_positions_per_day', '0'),
            (1, 'after_night_evening_penalty', '1200'),
            (1, 'consecutive_night_penalty', '500'),
            (1, 'consecutive_split_penalty', '450'),
            (1, 'coverage_shortage_gain_weight', '100'),
            (1, 'coverage_overage_penalty_weight', '25'),
            (1, 'target_gender_bonus_weight', '250'),
            (1, 'wrong_gender_penalty_weight', '120'),
            (1, 'balance_missing_min_weight', '300'),
            (1, 'balance_target_distance_weight', '70'),
            (1, 'balance_over_target_weight', '80'),
            (1, 'balance_over_max_weight', '10000'),
            (1, 'balance_worked_day_weight', '15'),
            (1, 'balance_night_weight', '60'),
            (1, 'balance_split_weight', '55'),
            (1, 'balance_consecutive_night_weight', '120'),
            (1, 'balance_consecutive_split_weight', '100'),
            (1, 'balance_excess_night_weight', '2000'),
            (1, 'balance_excess_split_weight', '1800')
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_app_settings_organization
        ON app_settings (organization_id, key)
    """)

    organization_owned_tables = (
        "employees",
        "positions",
        "shift_templates",
        "schedule_entries",
        "shift_requirements",
        "employee_preferences",
        "employee_week_preferences",
        "employee_recurring_preferences",
        "employee_day_statuses",
        "coverage_requirements",
    )
    for table_name in organization_owned_tables:
        _add_column_if_missing(cursor, table_name, "organization_id", "INTEGER NOT NULL DEFAULT 1")
        _ensure_public_ids(cursor, table_name, PUBLIC_ID_TABLE_PREFIXES[table_name])
        _add_column_if_missing(cursor, table_name, "created_at", "TEXT")
        _add_column_if_missing(cursor, table_name, "updated_at", "TEXT")
        _add_column_if_missing(cursor, table_name, "updated_by", "INTEGER")

    _add_column_if_missing(cursor, "employees", "id_card", "TEXT")
    _add_column_if_missing(cursor, "organization_invitations", "employee_id", "INTEGER")

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_employees_org
        ON employees (organization_id, id)
    """)
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_employees_org_id_card
        ON employees (organization_id, id_card)
        WHERE id_card IS NOT NULL AND id_card <> ''
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_positions_org
        ON positions (organization_id, id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_shift_templates_org
        ON shift_templates (organization_id, position_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_schedule_entries_org_date
        ON schedule_entries (organization_id, date)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_employee_week_preferences_org_week
        ON employee_week_preferences (organization_id, week_start_date, preference_date)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_employee_recurring_preferences_org_employee
        ON employee_recurring_preferences (organization_id, employee_id, preference_kind, day_of_week)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_coverage_requirements_org_position
        ON coverage_requirements (organization_id, position_id)
    """)
    _ensure_desktop_sync_triggers(cursor)

    if previous_schema_version < CURRENT_SCHEMA_VERSION:
        _record_schema_migration(
            cursor,
            previous_schema_version,
            CURRENT_SCHEMA_VERSION,
            "Add permanent employee recurring preferences",
        )
        _set_schema_version(cursor, CURRENT_SCHEMA_VERSION)

    _seed_licenses_from_bundled_database(cursor)

    connection.commit()
    connection.close()
