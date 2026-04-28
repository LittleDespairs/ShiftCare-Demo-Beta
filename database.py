import shutil
import sqlite3
import sys
import os
from datetime import datetime
from pathlib import Path

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


# Database file path / Путь к файлу базы данных
DATABASE_PATH = get_database_path()
DEFAULT_ORGANIZATION_PUBLIC_ID = "local-default"


def _table_columns(cursor: sqlite3.Cursor, table_name: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row["name"] for row in cursor.fetchall()}


def _add_column_if_missing(cursor: sqlite3.Cursor, table_name: str, column_name: str, definition: str) -> None:
    if column_name not in _table_columns(cursor, table_name):
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def get_backup_dir() -> Path:
    backup_dir = DATABASE_PATH.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


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
    source = DATABASE_PATH
    if not source.exists():
        raise FileNotFoundError(f"Database file does not exist: {source}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{source.stem}_{timestamp}_{_sanitize_backup_label(label)}.db"
    backup_path = get_backup_dir() / backup_name
    shutil.copy2(source, backup_path)
    return backup_path


def list_database_backups(limit: int = 20) -> list[dict]:
    backups = sorted(get_backup_dir().glob("*.db"), key=lambda path: path.stat().st_mtime, reverse=True)
    results = []
    for backup_path in backups[:limit]:
        stat = backup_path.stat()
        results.append(
            {
                "name": backup_path.name,
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            }
        )
    return results


def restore_database_backup(backup_name: str) -> dict:
    backup_path = (get_backup_dir() / backup_name).resolve()
    backup_dir = get_backup_dir().resolve()
    if backup_dir not in backup_path.parents:
        raise ValueError("Backup path is outside the backup directory")
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file does not exist: {backup_name}")

    validate_sqlite_file(backup_path)
    pre_restore_backup = create_database_backup("pre_restore")
    shutil.copy2(backup_path, DATABASE_PATH)
    return {
        "restored_backup": backup_path.name,
        "pre_restore_backup": pre_restore_backup.name,
    }


def get_connection():
    # Create SQLite connection / Создаём подключение к SQLite
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA foreign_keys = ON")

    # Return rows as dictionary-like objects / Возвращаем строки как объекты с доступом по имени колонки
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    # Initialize database tables / Инициализируем таблицы базы данных
    connection = get_connection()
    cursor = connection.cursor()

    # Turn on foreign keys in SQLite / Включаем внешние ключи в SQLite
    cursor.execute("PRAGMA foreign_keys = ON")

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
            role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'scheduler', 'employee', 'manager', 'read_only')),
            token_hash TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'expired', 'revoked')),
            expires_at TEXT NOT NULL,
            accepted_at TEXT,
            created_by_user_id INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
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

    # =========================
    # Employees / Сотрудники
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    if "day_off" not in day_status_table_sql:
        cursor.execute("ALTER TABLE employee_day_statuses RENAME TO employee_day_statuses_old")
        cursor.execute("""
            CREATE TABLE employee_day_statuses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                status_type TEXT NOT NULL CHECK (status_type IN ('sick', 'day_off')),
                UNIQUE(employee_id, date),
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            INSERT INTO employee_day_statuses (id, employee_id, date, status_type)
            SELECT id, employee_id, date, status_type
            FROM employee_day_statuses_old
            WHERE status_type IN ('sick', 'day_off')
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
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO app_settings (key, value)
        VALUES
            ('min_rest_minutes_between_morning_and_evening', '0'),
            ('min_rest_minutes_after_night_before_evening', '480'),
            ('schedule_coverage_display_mode', 'interval'),
            ('schedule_morning_color', '#ecfeff'),
            ('schedule_evening_color', '#fff7ed'),
            ('schedule_night_color', '#eef2ff'),
            ('schedule_status_color', '#f5f3ff'),
            ('max_work_days_per_week', '6'),
            ('max_consecutive_nights', '2'),
            ('emergency_max_consecutive_nights', '3'),
            ('max_consecutive_split_days', '2'),
            ('emergency_max_consecutive_split_days', '3'),
            ('allow_multiple_positions_per_day', '0'),
            ('after_night_evening_penalty', '1200'),
            ('consecutive_night_penalty', '500'),
            ('consecutive_split_penalty', '450'),
            ('coverage_shortage_gain_weight', '100'),
            ('coverage_overage_penalty_weight', '25'),
            ('target_gender_bonus_weight', '250'),
            ('wrong_gender_penalty_weight', '120'),
            ('balance_missing_min_weight', '300'),
            ('balance_target_distance_weight', '70'),
            ('balance_over_target_weight', '80'),
            ('balance_over_max_weight', '10000'),
            ('balance_worked_day_weight', '15'),
            ('balance_night_weight', '60'),
            ('balance_split_weight', '55'),
            ('balance_consecutive_night_weight', '120'),
            ('balance_consecutive_split_weight', '100'),
            ('balance_excess_night_weight', '2000'),
            ('balance_excess_split_weight', '1800')
    """)

    organization_owned_tables = (
        "employees",
        "positions",
        "shift_templates",
        "schedule_entries",
        "shift_requirements",
        "employee_preferences",
        "employee_week_preferences",
        "employee_day_statuses",
        "coverage_requirements",
    )
    for table_name in organization_owned_tables:
        _add_column_if_missing(cursor, table_name, "organization_id", "INTEGER NOT NULL DEFAULT 1")
        _add_column_if_missing(cursor, table_name, "created_at", "TEXT")
        _add_column_if_missing(cursor, table_name, "updated_at", "TEXT")
        _add_column_if_missing(cursor, table_name, "updated_by", "INTEGER")

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_employees_org
        ON employees (organization_id, id)
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
        CREATE INDEX IF NOT EXISTS idx_coverage_requirements_org_position
        ON coverage_requirements (organization_id, position_id)
    """)

    connection.commit()
    connection.close()
