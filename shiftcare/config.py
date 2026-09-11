"""Config for ShiftCare."""
from __future__ import annotations

from release_config import APP_VERSION
import os
import threading

TRUTHY_ENV_VALUES = {"1", "true", "yes", "on", "enabled"}


APP_DEMO_MODE = any(
    os.environ.get(name, "").strip().lower() in TRUTHY_ENV_VALUES
    for name in ("SHIFTCARE_DEMO", "SCHEDULE_APP_DEMO_MODE")
)


APP_NAME = "ShiftCare Demo" if APP_DEMO_MODE else "ShiftCare"


APP_TITLE = f"{APP_NAME} - Thoughtful Scheduling for Care Teams {APP_VERSION}"


DEFAULT_CLOUD_API_BASE_URL = "https://schedule-app-beta.web.app"


DEFAULT_PUBLIC_APP_BASE_URL = "https://portal.shiftcare.co.il"


DEMO_EMPLOYEE_LIMIT = 24


DEMO_SCHEDULE_ENTRY_LIMIT = 20


DEMO_ACCESS_TOKEN = "shiftcare-demo-session"


RETRYABLE_CLOUD_STATUS_CODES = {429, 502, 503, 504}


AUTH_LOGIN_RATE_LIMIT_ATTEMPTS = int(os.environ.get("AUTH_LOGIN_RATE_LIMIT_ATTEMPTS", "5"))


AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300"))


AUTH_LOGIN_RATE_LIMIT_LOCK_SECONDS = int(os.environ.get("AUTH_LOGIN_RATE_LIMIT_LOCK_SECONDS", "900"))


AUTH_LOGIN_ATTEMPTS: dict[str, dict] = {}


AUTH_LOGIN_ATTEMPTS_LOCK = threading.Lock()


FEEDBACK_RATE_LIMIT_ATTEMPTS = int(os.environ.get("FEEDBACK_RATE_LIMIT_ATTEMPTS", "5"))


FEEDBACK_RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("FEEDBACK_RATE_LIMIT_WINDOW_SECONDS", "600"))


FEEDBACK_ATTEMPTS: dict[str, list[float]] = {}


FEEDBACK_ATTEMPTS_LOCK = threading.Lock()


WEEKLY_PREFERENCE_TYPES = (
    "no_preference",
    "off_day",
    "vacation",
    "only_morning",
    "only_evening",
    "only_night",
    "not_morning",
    "not_evening",
    "not_night",
    "no_morning_evening_combo",
)


PERSISTED_RECURRING_PREFERENCE_TYPES = tuple(value for value in WEEKLY_PREFERENCE_TYPES if value != "no_preference")


EMPLOYEE_DIRECT_WEEKLY_PREFERENCE_DAY_LIMIT = 2


SOFT_PREFERENCE_PENALTY = 350


SOFT_DAY_OFF_PENALTY = 1200


SOFT_COMBO_PENALTY = 500


STRICT_REQUEST_MATCH_BONUS = 950


STRICT_REQUEST_MISMATCH_PENALTY = 450


GENERATION_MODE_BALANCED = "balanced"


GENERATION_MODE_COVERAGE = "coverage"


GENERATION_MODE_REQUESTS = "requests"


GENERATION_MODES = {
    GENERATION_MODE_BALANCED,
    GENERATION_MODE_COVERAGE,
    GENERATION_MODE_REQUESTS,
}


tags_metadata = [
    {"name": "Auth", "description": "Authorization and organization access / Авторизация и доступ к организации"},
    {"name": "Pages", "description": "Frontend pages / HTML страницы"},
    {"name": "Employees", "description": "Employee management / Сотрудники"},
    {"name": "Positions", "description": "Position management / Должности"},
    {"name": "Assignments", "description": "Employee-position assignments / Привязки"},
    {"name": "Shift Templates", "description": "Shift templates / Шаблоны смен"},
    {"name": "Preferences", "description": "Employee preferences / Пожелания"},
    {"name": "Weekly Preferences", "description": "Weekly preferences / Недельные пожелания"},
    {"name": "Permanent Preferences", "description": "Permanent employee preferences / Постоянные пожелания"},
    {"name": "Requirements", "description": "Shift and coverage requirements / Требования"},
    {"name": "Schedule", "description": "Schedule management / Расписание"},
    {"name": "Licensing", "description": "License and support entitlement / Лицензия и поддержка"},
    {"name": "Feedback", "description": "User bug reports and feature requests / Обращения пользователей"},
]


OPENAPI_BEARER_AUTH_SCHEME = "BearerAuth"


DESKTOP_CLOUD_SYNC_ROLES = {"owner", "admin", "scheduler", "manager"}


ORGANIZATION_MEMBER_ROLES = {"owner", "admin", "scheduler", "manager", "read_only", "employee"}


OWNER_MANAGED_ROLES = {"owner", "admin"}


DEPARTMENT_ACCESS_LIMITED_ROLES = {"admin", "scheduler", "manager", "read_only"}


DESKTOP_CLOUD_LOGIN_BASE_URL = "https://schedule-app-beta.web.app"


ORGANIZATION_EXPORT_TABLES = (
    "departments",
    "employees",
    "positions",
    "shift_templates",
    "shift_requirements",
    "coverage_requirements",
    "employee_preferences",
    "employee_week_preferences",
    "employee_week_preference_requests",
    "employee_recurring_preferences",
    "employee_day_statuses",
    "schedule_entries",
    "shift_swap_requests",
    "licenses",
    "app_settings",
)


ORGANIZATION_IMPORT_DELETE_ORDER = (
    "licenses",
    "shift_swap_requests",
    "schedule_entries",
    "employee_day_statuses",
    "employee_recurring_preferences",
    "employee_week_preference_requests",
    "employee_week_preferences",
    "employee_preferences",
    "coverage_requirements",
    "shift_requirements",
    "employee_positions",
    "shift_templates",
    "positions",
    "departments",
    "employees",
    "app_settings",
)


LOCAL_ONLY_APP_SETTING_KEYS = {
    "cloud_api_base_url",
    "cloud_organization_id",
    "cloud_organization_public_id",
    "cloud_linked_at",
    "desktop_cloud_sync_baseline",
    "desktop_cloud_access_token",
    "desktop_cloud_last_pull_at",
    "desktop_cloud_last_pull_app_version",
    "desktop_cloud_last_push_at",
    "desktop_cloud_last_push_error",
    "desktop_sync_suspended",
    "desktop_pending_update_changelog_body",
    "desktop_pending_update_changelog_name",
    "desktop_pending_update_changelog_summary",
    "desktop_pending_update_changelog_version",
    "desktop_update_changelog_seen_version",
}


PENDING_UPDATE_CHANGELOG_VERSION_KEY = "desktop_pending_update_changelog_version"


PENDING_UPDATE_CHANGELOG_NAME_KEY = "desktop_pending_update_changelog_name"


PENDING_UPDATE_CHANGELOG_BODY_KEY = "desktop_pending_update_changelog_body"


PENDING_UPDATE_CHANGELOG_SUMMARY_KEY = "desktop_pending_update_changelog_summary"


UPDATE_CHANGELOG_SEEN_VERSION_KEY = "desktop_update_changelog_seen_version"
