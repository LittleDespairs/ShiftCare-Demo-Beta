import shutil
import sqlite3
import sys
from pathlib import Path

# Base directory / Базовая папка проекта
BASE_DIR = Path(__file__).resolve().parent


def get_database_path() -> Path:
    if getattr(sys, "frozen", False):
        runtime_dir = Path(sys.executable).resolve().parent
        runtime_path = runtime_dir / "schedule_app.db"

        if not runtime_path.exists():
            bundled_dir = Path(getattr(sys, "_MEIPASS", runtime_dir))
            bundled_path = bundled_dir / "schedule_app.db"
            if bundled_path.exists():
                shutil.copy2(bundled_path, runtime_path)

        return runtime_path

    return BASE_DIR / "schedule_app.db"


# Database file path / Путь к файлу базы данных
DATABASE_PATH = get_database_path()


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
        requires_continuous_coverage INTEGER NOT NULL DEFAULT 0,
        minimum_staff_presence INTEGER NOT NULL DEFAULT 0
    )
""")

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
        name TEXT NOT NULL UNIQUE,
        category TEXT NOT NULL CHECK (category IN ('morning', 'evening', 'night')),
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        is_overnight INTEGER NOT NULL DEFAULT 0,
        is_active INTEGER NOT NULL DEFAULT 1,
        is_split_only INTEGER NOT NULL DEFAULT 0
    )
    """)

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

    # Optional helpful index / Полезный индекс
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_schedule_entries_employee_date
        ON schedule_entries (employee_id, date)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_schedule_entries_position_date
        ON schedule_entries (position_id, date)
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
            ('max_work_days_per_week', '6'),
            ('max_consecutive_nights', '2'),
            ('emergency_max_consecutive_nights', '3'),
            ('max_consecutive_split_days', '2'),
            ('emergency_max_consecutive_split_days', '3'),
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

    connection.commit()
    connection.close()
