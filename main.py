import database as database_module
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, date as Date, datetime, time, timedelta
from io import BytesIO
from pathlib import Path
from time import monotonic, sleep
from urllib.parse import quote, urlparse
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr, Field, model_validator

import auth_repository
import license_runtime
from app_config import get_app_config, validate_runtime_config
from cloud_sql import check_postgres_connection
from database import get_connection, init_db
from excel_export import build_all_schedule_export_workbook, build_schedule_export_workbook
from word_export import build_all_schedule_export_document, build_schedule_export_document

APP_VERSION = "0.15.13_beta"
APP_TITLE = f"ShiftCare - Thoughtful Scheduling for Care Teams {APP_VERSION}"
DEFAULT_CLOUD_API_BASE_URL = "https://schedule-app-beta.web.app"
DEFAULT_PUBLIC_APP_BASE_URL = "https://portal.shiftcare.co.il"
TRUTHY_ENV_VALUES = {"1", "true", "yes", "on", "enabled"}
GITHUB_REPO_OWNER = "LittleDespairs"
GITHUB_REPO_NAME = "Schedule_app_releases"
GITHUB_RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases"
GITHUB_RELEASE_ASSET_PATTERN = re.compile(r"^(?:ScheduleApp|ShiftCare)_Setup_(?P<version>\d+\.\d+\.\d+(?:[-_][A-Za-z0-9.]+)?)\.exe$")
AUTH_LOGIN_RATE_LIMIT_ATTEMPTS = int(os.environ.get("AUTH_LOGIN_RATE_LIMIT_ATTEMPTS", "5"))
AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300"))
AUTH_LOGIN_RATE_LIMIT_LOCK_SECONDS = int(os.environ.get("AUTH_LOGIN_RATE_LIMIT_LOCK_SECONDS", "900"))
AUTH_LOGIN_ATTEMPTS: dict[str, dict] = {}
AUTH_LOGIN_ATTEMPTS_LOCK = threading.Lock()
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
SOFT_PREFERENCE_PENALTY = 350
SOFT_DAY_OFF_PENALTY = 1200
SOFT_COMBO_PENALTY = 500

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
]

app = FastAPI(
    title=APP_TITLE,
    description="Web application for nursing staff scheduling",
    version=APP_VERSION,
    openapi_tags=tags_metadata,
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


def get_base_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


BASE_PATH = get_base_path()
init_db()

app.mount("/static", StaticFiles(directory=str(BASE_PATH / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_PATH / "templates"))
templates.env.globals["app_version"] = APP_VERSION


def is_developer_mode_enabled() -> bool:
    if os.environ.get("SCHEDULE_APP_DEVELOPER_MODE", "").strip().lower() in TRUTHY_ENV_VALUES:
        return True
    app_data_root = os.environ.get("LOCALAPPDATA", "").strip()
    if not app_data_root:
        return False
    return (Path(app_data_root) / "Schedule App" / "developer_mode.flag").exists()


templates.env.globals["developer_mode_enabled"] = is_developer_mode_enabled


def is_license_bypass_enabled() -> bool:
    config = get_app_config()
    if config.is_deployed_env:
        return False
    if not is_developer_mode_enabled():
        return False
    return os.environ.get("SCHEDULE_APP_LICENSE_BYPASS", "").strip().lower() in TRUTHY_ENV_VALUES


def is_cloud_employee_portal_mode() -> bool:
    return get_app_config().is_deployed_env


templates.env.globals["cloud_employee_portal_mode"] = is_cloud_employee_portal_mode


def is_trusted_desktop_cloud_request(request: Request) -> bool:
    return request.headers.get("X-ShiftCare-Desktop-Client", "").strip().lower() in TRUTHY_ENV_VALUES


def normalize_public_app_base_url(value: str) -> str:
    trimmed = (value or "").strip().rstrip("/")
    if not trimmed:
        return ""
    parsed = urlparse(trimmed)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def get_public_app_base_url() -> str:
    config = get_app_config()
    configured_url = normalize_public_app_base_url(config.public_app_base_url)
    if configured_url:
        return configured_url
    if config.is_deployed_env:
        return DEFAULT_CLOUD_API_BASE_URL
    return DEFAULT_PUBLIC_APP_BASE_URL


def build_public_app_url(path: str) -> str:
    base_url = get_public_app_base_url()
    if not base_url:
        return ""
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{base_url}{normalized_path}"


def build_invitation_url(invitation_token: str) -> str:
    return build_public_app_url(f"/accept-invitation?token={quote(invitation_token)}")


def build_invitation_url_for_request(request: Request | None, invitation_token: str) -> str:
    configured_url = build_invitation_url(invitation_token)
    if configured_url:
        return configured_url
    if request:
        parsed = urlparse(str(request.base_url))
        if parsed.hostname and parsed.hostname not in {"127.0.0.1", "localhost", "::1", "testserver"}:
            return f"{parsed.scheme}://{parsed.netloc}/accept-invitation?token={quote(invitation_token)}"
    return f"/accept-invitation?token={quote(invitation_token)}"


def read_organization_cloud_link_settings(cursor: sqlite3.Cursor, organization_id: int) -> dict:
    cursor.execute(
        """
        SELECT key, value
        FROM app_settings
        WHERE organization_id = ?
          AND key IN (
              'cloud_api_base_url',
              'cloud_organization_id',
              'cloud_organization_public_id',
              'cloud_linked_at'
          )
        """,
        (organization_id,),
    )
    return {row["key"]: row["value"] for row in cursor.fetchall()}


def organization_has_cloud_link(settings: dict) -> bool:
    return bool(settings.get("cloud_api_base_url") and settings.get("cloud_organization_id"))


def build_linked_organization_invitation_url(
    cursor: sqlite3.Cursor,
    organization_id: int,
    invitation_token: str,
) -> str:
    return build_invitation_url(invitation_token)


def get_desktop_cloud_login_base_url() -> str:
    configured_url = normalize_public_app_base_url(os.environ.get("SCHEDULE_APP_CLOUD_LOGIN_BASE_URL", ""))
    return configured_url or DESKTOP_CLOUD_LOGIN_BASE_URL


def is_desktop_sqlite_runtime() -> bool:
    config = get_app_config()
    return not config.is_deployed_env and config.database_engine.strip().lower() == "sqlite"


def read_desktop_cloud_sync_settings(cursor: sqlite3.Cursor, organization_id: int) -> dict[str, str]:
    cursor.execute(
        """
        SELECT key, value
        FROM app_settings
        WHERE organization_id = ?
          AND key IN (
              'cloud_api_base_url',
              'cloud_organization_id',
              'cloud_organization_public_id',
              'desktop_cloud_access_token'
          )
        """,
        (organization_id,),
    )
    return {row["key"]: row["value"] for row in cursor.fetchall()}


def desktop_cloud_sync_is_ready(settings: dict[str, str]) -> bool:
    return bool(
        settings.get("cloud_api_base_url")
        and settings.get("cloud_organization_id")
        and settings.get("desktop_cloud_access_token")
    )


def is_desktop_invitation_request(request: Request) -> bool:
    hostname = request.url.hostname or ""
    return getattr(sys, "frozen", False) or hostname in {"127.0.0.1", "localhost", "::1"}


def request_cloud_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict | None = None,
    token: str = "",
    extra_headers: dict[str, str] | None = None,
) -> dict:
    normalized_base = normalize_public_app_base_url(base_url)
    if not normalized_base:
        raise HTTPException(status_code=500, detail="Cloud login base URL is not configured")
    url = f"{normalized_base}{path if path.startswith('/') else f'/{path}'}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    headers.update(extra_headers or {})
    raw = ""
    last_network_error: Exception | None = None
    for attempt in range(2):
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
            break
        except urllib.error.HTTPError as exc:
            try:
                error_payload = json.loads(exc.read().decode("utf-8") or "{}")
            except (json.JSONDecodeError, UnicodeDecodeError):
                error_payload = {}
            detail = error_payload.get("detail") or f"Cloud request failed with {exc.code}"
            raise HTTPException(status_code=exc.code, detail=detail) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_network_error = exc
            if attempt == 0:
                sleep(1)
                continue
            raise HTTPException(status_code=503, detail=f"Cloud is not reachable: {exc}") from exc
    if last_network_error and not raw:
        raise HTTPException(status_code=503, detail=f"Cloud is not reachable: {last_network_error}")
    try:
        return json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Cloud returned an invalid JSON response") from exc


def select_desktop_cloud_membership(cloud_user: dict) -> dict:
    memberships = [
        membership
        for membership in cloud_user.get("memberships") or []
        if membership.get("status") == "active" and membership.get("role") in DESKTOP_CLOUD_SYNC_ROLES
    ]
    if not memberships:
        raise HTTPException(
            status_code=403,
            detail="This cloud account does not have desktop scheduling access",
        )
    return memberships[0]


def upsert_desktop_cloud_user(cursor: sqlite3.Cursor, cloud_user: dict, cloud_membership: dict, organization_id: int) -> int:
    now = current_utc_timestamp()
    email = str(cloud_user.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=502, detail="Cloud user response is missing email")
    cursor.execute("SELECT id FROM users WHERE lower(email) = ?", (email,))
    row = cursor.fetchone()
    if row:
        user_id = int(row["id"])
        cursor.execute(
            """
            UPDATE users
            SET full_name = ?, status = 'active', email_verified = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                cloud_user.get("full_name") or email,
                int(bool(cloud_user.get("email_verified"))),
                now,
                user_id,
            ),
        )
    else:
        cursor.execute(
            """
            INSERT INTO users (email, full_name, password_hash, status, email_verified, created_at, updated_at)
            VALUES (?, ?, NULL, 'active', ?, ?, ?)
            """,
            (
                email,
                cloud_user.get("full_name") or email,
                int(bool(cloud_user.get("email_verified"))),
                now,
                now,
            ),
        )
        user_id = int(cursor.lastrowid)
    cursor.execute(
        """
        INSERT INTO organization_memberships (organization_id, user_id, role, status, employee_id, created_at, updated_at)
        VALUES (?, ?, ?, 'active', NULL, ?, ?)
        ON CONFLICT(organization_id, user_id)
        DO UPDATE SET role = excluded.role,
                      status = excluded.status,
                      employee_id = NULL,
                      updated_at = excluded.updated_at
        """,
        (organization_id, user_id, cloud_membership.get("role") or "scheduler", now, now),
    )
    return user_id


MAX_WORK_DAYS_PER_WEEK = 6
MAX_CONSECUTIVE_NIGHTS = 2
EMERGENCY_MAX_CONSECUTIVE_NIGHTS = 3
MAX_CONSECUTIVE_SPLIT_DAYS = 2
EMERGENCY_MAX_CONSECUTIVE_SPLIT_DAYS = 3
MIN_REST_MINUTES_AFTER_NIGHT_BEFORE_EVENING = 8 * 60
MIN_REST_MINUTES_BETWEEN_MORNING_AND_EVENING = 0
AFTER_NIGHT_EVENING_PENALTY = 1200
DEFAULT_POSITION_COLOR = "#eff6ff"
DEFAULT_SCHEDULE_COLORS = {
    "schedule_morning_color": "#ecfeff",
    "schedule_evening_color": "#fff7ed",
    "schedule_night_color": "#eef2ff",
    "schedule_status_color": "#f5f3ff",
}
DESKTOP_CLOUD_SYNC_ROLES = {"owner", "admin", "scheduler", "manager"}
DESKTOP_CLOUD_LOGIN_BASE_URL = "https://schedule-app-beta.web.app"


@app.get("/service-worker.js", include_in_schema=False)
async def service_worker():
    return FileResponse(
        BASE_PATH / "static" / "service-worker.js",
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/api/health/live", tags=["Health"])
def health_live():
    return {
        "status": "ok",
        "app_version": APP_VERSION,
        "environment": get_app_config().app_env,
    }


@app.get("/api/health/ready", tags=["Health"])
def health_ready():
    config = get_app_config()
    runtime = validate_runtime_config()
    database_status = "ok"
    database_error = None
    if config.database_engine in {"postgres", "postgresql"}:
        postgres_check = check_postgres_connection(config)
        database_status = postgres_check["status"]
        database_error = postgres_check.get("error")
        if postgres_check["status"] != "ok":
            runtime["issues"].append("PostgreSQL connection check failed")
            runtime["status"] = "blocked"
    else:
        try:
            connection = get_connection()
            try:
                connection.execute("SELECT 1")
            finally:
                connection.close()
        except Exception as exc:
            database_status = "error"
            database_error = str(exc)
            runtime["issues"].append("Database connection check failed")
            runtime["status"] = "blocked"

    payload = {
        "status": "ok" if runtime["status"] == "ok" and database_status == "ok" else "blocked",
        "app_version": APP_VERSION,
        "runtime": runtime,
        "database": {
            "status": database_status,
            "error": database_error,
        },
    }
    if payload["status"] != "ok":
        raise HTTPException(status_code=503, detail=payload)
    return payload


@app.get("/api/client-config", tags=["Health"])
def client_config():
    public_app_base_url = get_public_app_base_url()
    return {
        "app_version": APP_VERSION,
        "default_api_base_url": os.environ.get("SCHEDULE_APP_DEFAULT_API_BASE_URL", DEFAULT_CLOUD_API_BASE_URL).strip(),
        "local_api_base_url": "",
        "public_app_base_url": public_app_base_url,
        "employee_portal_url": f"{public_app_base_url}/login" if public_app_base_url else "",
        "employee_invitation_url_base": f"{public_app_base_url}/accept-invitation" if public_app_base_url else "",
        "environment": get_app_config().app_env,
        "developer_mode": is_developer_mode_enabled(),
        "cloud_employee_portal_mode": is_cloud_employee_portal_mode(),
    }


# =========================
# Models
# =========================


class AuthBootstrapRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=120)
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class AuthLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class DesktopCloudLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class AuthOrganizationCreateRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=120)
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class AuthProfileUpdateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)


class AuthPasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class AuthPasswordResetRequest(BaseModel):
    email: EmailStr


class AuthPasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=32, max_length=512)
    new_password: str = Field(min_length=8, max_length=128)


class AuthEmailVerificationRequest(BaseModel):
    token: str = Field(min_length=32, max_length=512)


class AuthInvitationAcceptRequest(BaseModel):
    token: str = Field(min_length=32, max_length=512)
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str | None = Field(default=None, min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_password_confirmation(self):
        if self.confirm_password is not None and self.password != self.confirm_password:
            raise ValueError("password confirmation does not match")
        return self


class OrganizationInvitationCreate(BaseModel):
    email: EmailStr
    employee_id: int | None = Field(default=None, ge=1)
    employee_public_id: str | None = Field(default=None, min_length=2, max_length=120)
    role: Literal["admin", "scheduler", "employee", "manager", "read_only"] = "employee"
    expires_in_days: int = Field(default=7, ge=1, le=30)


class OrganizationMemberEmployeeLinkUpdate(BaseModel):
    employee_id: int | None = Field(default=None, ge=1)
    employee_public_id: str | None = Field(default=None, min_length=2, max_length=120)


class CloudOrganizationImportRequest(BaseModel):
    bundle: dict[str, Any]
    replace_existing: bool = True


class CloudOrganizationLinkRequest(BaseModel):
    cloud_api_base_url: str = Field(min_length=8, max_length=255)
    cloud_organization_id: int = Field(ge=1)
    cloud_organization_public_id: str = Field(min_length=2, max_length=120)
    linked_at: str | None = Field(default=None, max_length=40)


class EmployeeCreate(BaseModel):
    id_card: str | None = Field(default=None, max_length=32)
    full_name: str = Field(min_length=2, max_length=100)
    sex: Literal["male", "female"]
    min_shifts_per_week: int = Field(ge=0, le=14)
    target_shifts_per_week: int = Field(ge=0, le=14)
    max_shifts_per_week: int = Field(ge=0, le=14)
    can_work_night: bool
    can_work_weekends: bool
    can_work_evenings_after_night: bool
    can_work_mornings_and_evenings: bool

    @model_validator(mode="after")
    def validate_shift_range(self):
        if self.id_card is not None:
            normalized_id_card = normalize_id_card(self.id_card)
            self.id_card = normalized_id_card or None
        if self.min_shifts_per_week > self.max_shifts_per_week:
            raise ValueError("min_shifts_per_week cannot be greater than max_shifts_per_week")
        if self.target_shifts_per_week < self.min_shifts_per_week:
            raise ValueError("target_shifts_per_week cannot be less than min_shifts_per_week")
        if self.target_shifts_per_week > self.max_shifts_per_week:
            raise ValueError("target_shifts_per_week cannot be greater than max_shifts_per_week")
        return self


class PositionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    color: str = Field(default="#eff6ff", pattern=r"^#[0-9A-Fa-f]{6}$")
    requires_continuous_coverage: bool = False
    minimum_staff_presence: int = Field(ge=0, le=50, default=0)
    max_consecutive_nights: int | None = Field(default=None, ge=1, le=7)
    emergency_max_consecutive_nights: int | None = Field(default=None, ge=1, le=7)
    max_consecutive_split_days: int | None = Field(default=None, ge=1, le=7)
    emergency_max_consecutive_split_days: int | None = Field(default=None, ge=1, le=7)

    @model_validator(mode="after")
    def validate_presence(self):
        if not self.requires_continuous_coverage and self.minimum_staff_presence != 0:
            raise ValueError("minimum_staff_presence must be 0 if continuous coverage is disabled")
        return self


class EmployeePositionCreate(BaseModel):
    employee_id: int
    position_id: int
    is_primary: bool = False
    priority_score: int = Field(ge=0, le=100, default=50)
    is_fallback_only: bool = False

    @model_validator(mode="after")
    def validate_assignment_flags(self):
        if self.is_primary and self.is_fallback_only:
            raise ValueError("assignment cannot be both primary and fallback-only")
        return self


class ShiftTemplateCreate(BaseModel):
    position_id: int
    name: str = Field(min_length=2, max_length=100)
    category: Literal["morning", "evening", "night"]
    start_time: str
    end_time: str
    is_overnight: bool = False
    is_active: bool = True
    is_split_only: bool = False

    @model_validator(mode="after")
    def validate_time_window(self):
        start = parse_time_string(self.start_time)
        end = parse_time_string(self.end_time)
        if start == end:
            raise ValueError("shift start_time and end_time cannot be the same")
        if not self.is_overnight and end <= start:
            raise ValueError("non-overnight shift must end after start_time")
        return self


class ShiftRequirementCreate(BaseModel):
    position_id: int
    shift_category: Literal["morning", "evening", "night"]
    required_total: int = Field(ge=1, le=50)
    required_female_min: int = Field(ge=0, le=50)
    required_male_min: int = Field(ge=0, le=50, default=0)

    @model_validator(mode="after")
    def validate_gender_minimums(self):
        if self.required_female_min > self.required_total:
            raise ValueError("required_female_min cannot be greater than required_total")
        if self.required_male_min > self.required_total:
            raise ValueError("required_male_min cannot be greater than required_total")
        if self.required_female_min + self.required_male_min > self.required_total:
            raise ValueError("gender minimums cannot be greater than required_total")
        return self


class CoverageRequirementCreate(BaseModel):
    position_id: int
    start_time: str
    end_time: str
    required_total: int = Field(ge=0, le=50)
    required_female_min: int = Field(ge=0, le=50, default=0)
    required_male_min: int = Field(ge=0, le=50, default=0)
    is_overnight: bool = False

    @model_validator(mode="after")
    def validate_requirement(self):
        start = parse_time_string(self.start_time)
        end = parse_time_string(self.end_time)
        if self.required_female_min > self.required_total:
            raise ValueError("required_female_min cannot be greater than required_total")
        if self.required_male_min > self.required_total:
            raise ValueError("required_male_min cannot be greater than required_total")
        if self.required_female_min + self.required_male_min > self.required_total:
            raise ValueError("gender minimums cannot be greater than required_total")
        if not self.is_overnight and end <= start:
            raise ValueError("non-overnight coverage interval must end after start_time")
        if start == end:
            raise ValueError("coverage interval start_time and end_time cannot be the same")
        return self


class EmployeePreferenceCreate(BaseModel):
    employee_id: int
    allow_morning: bool
    allow_evening: bool
    allow_night: bool
    allow_morning_evening_combo: bool


class EmployeeWeekPreferenceCreate(BaseModel):
    employee_id: int
    week_start_date: str
    preference_date: str
    preference_type: Literal[
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
    ]

    @model_validator(mode="after")
    def validate_preference_date_belongs_to_week(self):
        week_dates = build_week_dates(self.week_start_date)
        if self.preference_date not in week_dates:
            raise ValueError("preference_date must belong to the selected week")
        return self


class EmployeeRecurringPreferenceRule(BaseModel):
    preference_kind: Literal["strict", "soft"]
    day_of_week: int = Field(ge=0, le=6)
    preference_type: Literal[
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
    ]


class EmployeeRecurringPreferencesUpdate(BaseModel):
    employee_id: int
    rules: list[EmployeeRecurringPreferenceRule] = Field(default_factory=list, max_length=14)

    @model_validator(mode="after")
    def validate_unique_rules(self):
        seen = set()
        for rule in self.rules:
            key = (rule.preference_kind, rule.day_of_week)
            if key in seen:
                raise ValueError("Each permanent preference kind/day pair can appear only once")
            seen.add(key)
        return self


class EmployeeDayStatusCreate(BaseModel):
    employee_id: int
    date: str
    status_type: Literal["sick", "day_off"]


class ScheduleEntryCreate(BaseModel):
    employee_id: int
    position_id: int
    date: str
    shift_template_id: int


class ScheduleEntryStatusUpdate(BaseModel):
    no_show: bool


class AutoGenerateScheduleRequest(BaseModel):
    position_id: int
    week_start_date: str

    @model_validator(mode="after")
    def validate_week_start_date(self):
        parse_date_string(self.week_start_date)
        return self


class AutoGenerateAllScheduleRequest(BaseModel):
    week_start_date: str

    @model_validator(mode="after")
    def validate_week_start_date(self):
        parse_date_string(self.week_start_date)
        return self


class ClearWeekScheduleRequest(BaseModel):
    position_id: int
    week_start_date: str

    @model_validator(mode="after")
    def validate_week_start_date(self):
        parse_date_string(self.week_start_date)
        return self


class ClearAllWeekScheduleRequest(BaseModel):
    week_start_date: str

    @model_validator(mode="after")
    def validate_week_start_date(self):
        parse_date_string(self.week_start_date)
        return self


class DatabaseBackupCreateRequest(BaseModel):
    label: str = Field(default="manual", min_length=1, max_length=50)


class DatabaseRestoreRequest(BaseModel):
    backup_name: str = Field(min_length=1, max_length=255)


class UpdateInstallRequest(BaseModel):
    download_url: str = Field(min_length=1, max_length=2048)
    asset_name: str = Field(min_length=1, max_length=255)


class LicenseImportRequest(BaseModel):
    certificate: dict[str, Any]


class LicenseActivationCodeRequest(BaseModel):
    activation_code: str = Field(min_length=8, max_length=512)


class AppSettingsUpdate(BaseModel):
    min_rest_minutes_between_morning_and_evening: int | None = Field(
        default=None,
        ge=0,
        le=24 * 60,
    )
    min_rest_minutes_after_night_before_evening: int | None = Field(
        default=None,
        ge=0,
        le=24 * 60,
    )
    schedule_coverage_display_mode: Literal["category", "interval"] | None = None
    schedule_morning_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    schedule_evening_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    schedule_night_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    schedule_status_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    allow_multiple_positions_per_day: bool | None = None
    max_work_days_per_week: int | None = Field(default=None, ge=1, le=7)
    max_consecutive_nights: int | None = Field(default=None, ge=1, le=7)
    emergency_max_consecutive_nights: int | None = Field(default=None, ge=1, le=7)
    max_consecutive_split_days: int | None = Field(default=None, ge=1, le=7)
    emergency_max_consecutive_split_days: int | None = Field(default=None, ge=1, le=7)
    after_night_evening_penalty: int | None = Field(default=None, ge=0, le=10000)
    consecutive_night_penalty: int | None = Field(default=None, ge=0, le=10000)
    consecutive_split_penalty: int | None = Field(default=None, ge=0, le=10000)
    coverage_shortage_gain_weight: int | None = Field(default=None, ge=1, le=1000)
    coverage_overage_penalty_weight: int | None = Field(default=None, ge=0, le=1000)
    target_gender_bonus_weight: int | None = Field(default=None, ge=0, le=2000)
    wrong_gender_penalty_weight: int | None = Field(default=None, ge=0, le=2000)
    balance_missing_min_weight: int | None = Field(default=None, ge=0, le=10000)
    balance_target_distance_weight: int | None = Field(default=None, ge=0, le=10000)
    balance_over_target_weight: int | None = Field(default=None, ge=0, le=10000)
    balance_over_max_weight: int | None = Field(default=None, ge=0, le=50000)
    balance_worked_day_weight: int | None = Field(default=None, ge=0, le=10000)
    balance_night_weight: int | None = Field(default=None, ge=0, le=10000)
    balance_split_weight: int | None = Field(default=None, ge=0, le=10000)
    balance_consecutive_night_weight: int | None = Field(default=None, ge=0, le=10000)
    balance_consecutive_split_weight: int | None = Field(default=None, ge=0, le=10000)
    balance_excess_night_weight: int | None = Field(default=None, ge=0, le=50000)
    balance_excess_split_weight: int | None = Field(default=None, ge=0, le=50000)


@dataclass(frozen=True)
class Interval:
    start: int
    end: int

    def contains(self, start: int, end: int) -> bool:
        return self.start <= start and end <= self.end

    def overlaps(self, other: "Interval") -> bool:
        return self.start < other.end and other.start < self.end


# =========================
# Helpers
# =========================


def parse_time_string(value: str) -> time:
    return datetime.strptime(value, "%H:%M").time()


def parse_date_string(value: str) -> Date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def time_to_minutes(value: str) -> int:
    parsed = parse_time_string(value)
    return parsed.hour * 60 + parsed.minute


def build_interval(start_time: str, end_time: str, is_overnight: bool = False) -> Interval:
    start = time_to_minutes(start_time)
    end = time_to_minutes(end_time)
    if is_overnight or end <= start:
        end += 24 * 60
    return Interval(start=start, end=end)


def build_week_dates(week_start_date: str) -> list[str]:
    start = parse_date_string(week_start_date)
    return [(start + timedelta(days=offset)).isoformat() for offset in range(7)]


def get_week_start_for_date(date_string: str) -> str:
    current = parse_date_string(date_string)
    days_since_sunday = (current.weekday() + 1) % 7
    return (current - timedelta(days=days_since_sunday)).isoformat()


def recurring_day_of_week(date_string: str) -> int:
    # App weeks start on Sunday: Sunday=0, Monday=1, ..., Saturday=6.
    return (parse_date_string(date_string).weekday() + 1) % 7


def get_week_end_date(week_start_date: str) -> str:
    return build_week_dates(week_start_date)[-1]


def get_app_settings(connection, organization_id: int = 1) -> dict:
    cursor = connection.cursor()
    cursor.execute("SELECT key, value FROM app_settings WHERE organization_id = ?", (organization_id,))
    raw_settings = {row["key"]: row["value"] for row in cursor.fetchall()}

    def read_int(key: str, default: int) -> int:
        try:
            return int(raw_settings.get(key, default))
        except (TypeError, ValueError):
            return default

    def read_bool(key: str, default: bool) -> bool:
        raw_value = raw_settings.get(key)
        if raw_value is None:
            return default
        if isinstance(raw_value, bool):
            return raw_value
        return str(raw_value).strip().lower() in {"1", "true", "yes", "on"}

    def read_color(key: str, default: str) -> str:
        raw_value = str(raw_settings.get(key, default)).strip()
        if len(raw_value) == 7 and raw_value.startswith("#"):
            hex_part = raw_value[1:]
            if all(character in "0123456789abcdefABCDEF" for character in hex_part):
                return raw_value
        return default

    return {
        "min_rest_minutes_between_morning_and_evening": read_int(
            "min_rest_minutes_between_morning_and_evening",
            MIN_REST_MINUTES_BETWEEN_MORNING_AND_EVENING,
        ),
        "min_rest_minutes_after_night_before_evening": read_int(
            "min_rest_minutes_after_night_before_evening",
            MIN_REST_MINUTES_AFTER_NIGHT_BEFORE_EVENING,
        ),
        "schedule_coverage_display_mode": (
            raw_settings.get("schedule_coverage_display_mode")
            if raw_settings.get("schedule_coverage_display_mode") in {"category", "interval"}
            else "interval"
        ),
        "schedule_morning_color": read_color("schedule_morning_color", DEFAULT_SCHEDULE_COLORS["schedule_morning_color"]),
        "schedule_evening_color": read_color("schedule_evening_color", DEFAULT_SCHEDULE_COLORS["schedule_evening_color"]),
        "schedule_night_color": read_color("schedule_night_color", DEFAULT_SCHEDULE_COLORS["schedule_night_color"]),
        "schedule_status_color": read_color("schedule_status_color", DEFAULT_SCHEDULE_COLORS["schedule_status_color"]),
        "allow_multiple_positions_per_day": read_bool("allow_multiple_positions_per_day", False),
        "max_work_days_per_week": read_int("max_work_days_per_week", MAX_WORK_DAYS_PER_WEEK),
        "max_consecutive_nights": read_int("max_consecutive_nights", MAX_CONSECUTIVE_NIGHTS),
        "emergency_max_consecutive_nights": read_int("emergency_max_consecutive_nights", EMERGENCY_MAX_CONSECUTIVE_NIGHTS),
        "max_consecutive_split_days": read_int("max_consecutive_split_days", MAX_CONSECUTIVE_SPLIT_DAYS),
        "emergency_max_consecutive_split_days": read_int("emergency_max_consecutive_split_days", EMERGENCY_MAX_CONSECUTIVE_SPLIT_DAYS),
        "after_night_evening_penalty": read_int("after_night_evening_penalty", AFTER_NIGHT_EVENING_PENALTY),
        "consecutive_night_penalty": read_int("consecutive_night_penalty", 500),
        "consecutive_split_penalty": read_int("consecutive_split_penalty", 450),
        "coverage_shortage_gain_weight": read_int("coverage_shortage_gain_weight", 100),
        "coverage_overage_penalty_weight": read_int("coverage_overage_penalty_weight", 25),
        "target_gender_bonus_weight": read_int("target_gender_bonus_weight", 250),
        "wrong_gender_penalty_weight": read_int("wrong_gender_penalty_weight", 120),
        "balance_missing_min_weight": read_int("balance_missing_min_weight", 300),
        "balance_target_distance_weight": read_int("balance_target_distance_weight", 70),
        "balance_over_target_weight": read_int("balance_over_target_weight", 80),
        "balance_over_max_weight": read_int("balance_over_max_weight", 10000),
        "balance_worked_day_weight": read_int("balance_worked_day_weight", 15),
        "balance_night_weight": read_int("balance_night_weight", 60),
        "balance_split_weight": read_int("balance_split_weight", 55),
        "balance_consecutive_night_weight": read_int("balance_consecutive_night_weight", 120),
        "balance_consecutive_split_weight": read_int("balance_consecutive_split_weight", 100),
        "balance_excess_night_weight": read_int("balance_excess_night_weight", 2000),
        "balance_excess_split_weight": read_int("balance_excess_split_weight", 1800),
    }


POSITION_GENERATION_LIMIT_FIELDS = (
    "max_consecutive_nights",
    "emergency_max_consecutive_nights",
    "max_consecutive_split_days",
    "emergency_max_consecutive_split_days",
)


def apply_position_generation_limits(settings: dict, position: dict | sqlite3.Row | None) -> dict:
    effective_settings = dict(settings)
    if position is None:
        return effective_settings

    for field in POSITION_GENERATION_LIMIT_FIELDS:
        value = position[field] if isinstance(position, sqlite3.Row) else position.get(field)
        if value is not None:
            effective_settings[field] = int(value)
    return effective_settings


def get_position_app_settings(
    connection,
    position_id: int,
    base_settings: dict | None = None,
    organization_id: int = 1,
) -> dict:
    settings = base_settings or get_app_settings(connection, organization_id=organization_id)
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT max_consecutive_nights, emergency_max_consecutive_nights,
               max_consecutive_split_days, emergency_max_consecutive_split_days
        FROM positions
        WHERE id = ?
        """,
        (position_id,),
    )
    return apply_position_generation_limits(settings, cursor.fetchone())


def save_app_settings(connection, settings: AppSettingsUpdate, organization_id: int = 1) -> None:
    cursor = connection.cursor()
    for key, value in settings.model_dump(exclude_none=True).items():
        cursor.execute(
            """
            INSERT INTO app_settings (organization_id, key, value)
            VALUES (?, ?, ?)
            ON CONFLICT(key)
            DO UPDATE SET organization_id = excluded.organization_id,
                          value = excluded.value
            """,
            (organization_id, key, str(value)),
        )


def reset_visual_color_settings(connection, organization_id: int = 1) -> int:
    cursor = connection.cursor()
    for key, value in DEFAULT_SCHEDULE_COLORS.items():
        cursor.execute(
            """
            INSERT INTO app_settings (organization_id, key, value)
            VALUES (?, ?, ?)
            ON CONFLICT(key)
            DO UPDATE SET organization_id = excluded.organization_id,
                          value = excluded.value
            """,
            (organization_id, key, value),
        )
    cursor.execute("UPDATE positions SET color = ?", (DEFAULT_POSITION_COLOR,))
    return cursor.rowcount


def is_weekend(date_string: str) -> bool:
    # Python: Monday=0. The app week starts on Sunday, but this still catches Friday/Saturday.
    weekday = parse_date_string(date_string).weekday()
    return weekday in (4, 5)


def row_to_employee_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "public_id": row["public_id"] if "public_id" in row.keys() else None,
        "id_card": row["id_card"] if "id_card" in row.keys() else None,
        "full_name": row["full_name"],
        "sex": row["sex"],
        "min_shifts_per_week": row["min_shifts_per_week"],
        "target_shifts_per_week": row["target_shifts_per_week"],
        "max_shifts_per_week": row["max_shifts_per_week"],
        "can_work_night": bool(row["can_work_night"]),
        "can_work_weekends": bool(row["can_work_weekends"]),
        "can_work_evenings_after_night": bool(row["can_work_evenings_after_night"]),
        "can_work_mornings_and_evenings": bool(row["can_work_mornings_and_evenings"]),
    }


def row_to_position_dict(row: sqlite3.Row) -> dict:
    item = {
        "id": row["id"],
        "name": row["name"],
        "color": row["color"] if "color" in row.keys() and row["color"] else "#eff6ff",
        "requires_continuous_coverage": bool(row["requires_continuous_coverage"]),
        "minimum_staff_presence": row["minimum_staff_presence"],
        "max_consecutive_nights": row["max_consecutive_nights"] if "max_consecutive_nights" in row.keys() else None,
        "emergency_max_consecutive_nights": row["emergency_max_consecutive_nights"] if "emergency_max_consecutive_nights" in row.keys() else None,
        "max_consecutive_split_days": row["max_consecutive_split_days"] if "max_consecutive_split_days" in row.keys() else None,
        "emergency_max_consecutive_split_days": row["emergency_max_consecutive_split_days"] if "emergency_max_consecutive_split_days" in row.keys() else None,
    }
    if "is_primary" in row.keys():
        item["is_primary"] = bool(row["is_primary"])
    if "priority_score" in row.keys():
        item["priority_score"] = row["priority_score"]
    if "is_fallback_only" in row.keys():
        item["is_fallback_only"] = bool(row["is_fallback_only"])
    return item


def row_to_shift_template_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "position_id": row["position_id"] if "position_id" in row.keys() else None,
        "position_name": row["position_name"] if "position_name" in row.keys() else None,
        "name": row["name"],
        "category": row["category"],
        "start_time": row["start_time"],
        "end_time": row["end_time"],
        "is_overnight": bool(row["is_overnight"]),
        "is_active": bool(row["is_active"]),
        "is_split_only": bool(row["is_split_only"]),
    }


def row_to_coverage_requirement_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "position_id": row["position_id"],
        "position_name": row["position_name"] if "position_name" in row.keys() else None,
        "start_time": row["start_time"],
        "end_time": row["end_time"],
        "required_total": row["required_total"],
        "required_female_min": row["required_female_min"],
        "required_male_min": row["required_male_min"],
        "is_overnight": bool(row["is_overnight"]),
    }


def fetch_one_or_404(cursor, query: str, params: tuple, message: str):
    cursor.execute(query, params)
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=message)
    return row


def fetch_count(cursor, query: str, params: tuple = ()) -> int:
    cursor.execute(query, params)
    return int(cursor.fetchone()[0])


def current_utc_timestamp() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="seconds")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 210_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        algorithm, iterations_value, salt_hex, digest_hex = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_value)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_request_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    if forwarded_for:
        return forwarded_for
    return request.client.host if request.client else "unknown"


def normalize_login_identifier(value: str) -> str:
    return str(value or "").strip().lower()


def normalize_id_card(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def login_rate_limit_key(identifier: str, request: Request) -> str:
    return f"{normalize_login_identifier(identifier)}|{get_request_ip(request)}"


def is_login_rate_limited(identifier: str, request: Request) -> bool:
    now = monotonic()
    key = login_rate_limit_key(identifier, request)
    with AUTH_LOGIN_ATTEMPTS_LOCK:
        entry = AUTH_LOGIN_ATTEMPTS.get(key)
        if not entry:
            return False
        locked_until = float(entry.get("locked_until") or 0)
        if locked_until > now:
            return True
        failures = [
            timestamp
            for timestamp in entry.get("failures", [])
            if now - timestamp <= AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS
        ]
        if failures:
            entry["failures"] = failures
            entry["locked_until"] = 0
        else:
            AUTH_LOGIN_ATTEMPTS.pop(key, None)
        return False


def record_login_failure(identifier: str, request: Request) -> bool:
    now = monotonic()
    key = login_rate_limit_key(identifier, request)
    with AUTH_LOGIN_ATTEMPTS_LOCK:
        entry = AUTH_LOGIN_ATTEMPTS.setdefault(key, {"failures": [], "locked_until": 0})
        entry["failures"] = [
            timestamp
            for timestamp in entry["failures"]
            if now - timestamp <= AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS
        ]
        entry["failures"].append(now)
        if len(entry["failures"]) >= AUTH_LOGIN_RATE_LIMIT_ATTEMPTS:
            entry["locked_until"] = now + AUTH_LOGIN_RATE_LIMIT_LOCK_SECONDS
            return True
    return False


def clear_login_failures(identifier: str, request: Request) -> None:
    key = login_rate_limit_key(identifier, request)
    with AUTH_LOGIN_ATTEMPTS_LOCK:
        AUTH_LOGIN_ATTEMPTS.pop(key, None)


def find_user_for_login(cursor, identifier: str):
    normalized_identifier = normalize_login_identifier(identifier)
    cursor.execute(
        """
        SELECT id, password_hash, status
        FROM users
        WHERE lower(email) = ?
        """,
        (normalized_identifier,),
    )
    user_row = cursor.fetchone()
    if user_row:
        return user_row

    id_card = normalize_id_card(identifier)
    if not id_card:
        return None
    cursor.execute(
        """
        SELECT u.id, u.password_hash, u.status
        FROM users u
        JOIN organization_memberships om ON om.user_id = u.id AND om.status = 'active'
        JOIN employees e ON e.id = om.employee_id
        WHERE replace(replace(replace(e.id_card, '-', ''), ' ', ''), '.', '') = ?
        ORDER BY u.id
        LIMIT 1
        """,
        (id_card,),
    )
    user_row = cursor.fetchone()
    if user_row:
        return user_row

    cursor.execute(
        """
        SELECT u.id, u.password_hash, u.status
        FROM employees e
        JOIN organization_invitations oi
            ON oi.organization_id = e.organization_id
           AND oi.employee_id = e.id
           AND oi.role = 'employee'
           AND oi.status = 'accepted'
        JOIN users u ON lower(u.email) = lower(oi.email)
        JOIN organization_memberships om
            ON om.organization_id = e.organization_id
           AND om.user_id = u.id
           AND om.role = 'employee'
           AND om.status = 'active'
           AND om.employee_id IS NULL
        WHERE replace(replace(replace(e.id_card, '-', ''), ' ', ''), '.', '') = ?
          AND NOT EXISTS (
              SELECT 1
              FROM organization_memberships linked
              WHERE linked.organization_id = e.organization_id
                AND linked.employee_id = e.id
                AND linked.status = 'active'
          )
        ORDER BY oi.accepted_at DESC, oi.id DESC
        LIMIT 1
        """,
        (id_card,),
    )
    user_row = cursor.fetchone()
    if user_row:
        return user_row

    cursor.execute(
        """
        SELECT u.id, u.password_hash, u.status
        FROM employees e
        JOIN organization_memberships om
            ON om.organization_id = e.organization_id
           AND om.role = 'employee'
           AND om.status = 'active'
           AND om.employee_id IS NULL
        JOIN users u ON u.id = om.user_id
        WHERE replace(replace(replace(e.id_card, '-', ''), ' ', ''), '.', '') = ?
          AND lower(trim(u.full_name)) = lower(trim(e.full_name))
          AND NOT EXISTS (
              SELECT 1
              FROM organization_memberships linked
              WHERE linked.organization_id = e.organization_id
                AND linked.employee_id = e.id
                AND linked.status = 'active'
          )
        ORDER BY u.id
        """,
        (id_card,),
    )
    rows = cursor.fetchall()
    if len(rows) == 1:
        return rows[0]
    return None


def token_expiration(days: int = 1) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).replace(tzinfo=None).isoformat(timespec="seconds")


def build_auth_response(connection, user_id: int) -> dict:
    token = secrets.token_urlsafe(32)
    expires_at = (
        datetime.now(UTC) + timedelta(days=int(os.environ.get("AUTH_REFRESH_TOKEN_DAYS", "30")))
    ).replace(tzinfo=None).isoformat(timespec="seconds")
    cursor = connection.cursor()
    auth_repository.create_auth_session(cursor, user_id, hash_session_token(token), expires_at)
    user = get_user_context(cursor, user_id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at,
        "user": user,
    }


def get_user_context(cursor, user_id: int) -> dict:
    user = auth_repository.get_user_context(cursor, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")
    return user


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    connection = get_connection()
    try:
        cursor = connection.cursor()
        user_id = auth_repository.get_session_user_id(
            cursor,
            hash_session_token(token),
            current_utc_timestamp(),
        )
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        return get_user_context(cursor, user_id)
    finally:
        connection.close()


def find_membership(current_user: dict, organization_id: int) -> dict | None:
    for membership in current_user["memberships"]:
        if membership["organization_id"] == organization_id and membership["status"] == "active":
            return membership
    return None


def require_organization_role(current_user: dict, organization_id: int, allowed_roles: set[str]) -> dict:
    membership = find_membership(current_user, organization_id)
    if not membership:
        raise HTTPException(status_code=403, detail="User is not an active member of this organization")
    if membership["role"] not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient organization permissions")
    return membership


def find_any_membership_with_role(current_user: dict, allowed_roles: set[str]) -> dict | None:
    for membership in current_user["memberships"]:
        if membership["status"] == "active" and membership["role"] in allowed_roles:
            return membership
    return None


def find_repair_employee_id_for_member(
    cursor,
    organization_id: int,
    user_id: int,
    user_email: str,
    full_name: str,
) -> int | None:
    normalized_email = str(user_email or "").strip().lower()
    if normalized_email:
        cursor.execute(
            """
            SELECT oi.employee_id
            FROM organization_invitations oi
            JOIN employees e ON e.id = oi.employee_id AND e.organization_id = oi.organization_id
            WHERE oi.organization_id = ?
              AND lower(oi.email) = ?
              AND oi.role = 'employee'
              AND oi.status = 'accepted'
              AND oi.employee_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM organization_memberships linked
                  WHERE linked.organization_id = oi.organization_id
                    AND linked.employee_id = oi.employee_id
                    AND linked.user_id != ?
                    AND linked.status = 'active'
              )
            ORDER BY oi.accepted_at DESC, oi.id DESC
            LIMIT 1
            """,
            (organization_id, normalized_email, user_id),
        )
        invitation = cursor.fetchone()
        if invitation:
            return int(invitation["employee_id"])

    normalized_name = str(full_name or "").strip().lower()
    if not normalized_name:
        return None
    cursor.execute(
        """
        SELECT e.id
        FROM employees e
        WHERE e.organization_id = ?
          AND lower(trim(e.full_name)) = ?
          AND NOT EXISTS (
              SELECT 1
              FROM organization_memberships linked
              WHERE linked.organization_id = e.organization_id
                AND linked.employee_id = e.id
                AND linked.user_id != ?
                AND linked.status = 'active'
          )
        ORDER BY e.id
        """,
        (organization_id, normalized_name, user_id),
    )
    matches = cursor.fetchall()
    if len(matches) == 1:
        return int(matches[0]["id"])
    return None


def repair_employee_membership_links(cursor, current_user: dict) -> bool:
    repaired = False
    user_email = str(current_user.get("email") or "").strip().lower()
    user_id = int(current_user["id"])
    full_name = str(current_user.get("full_name") or "")
    if not user_email and not full_name:
        return False

    for membership in current_user.get("memberships") or []:
        if membership.get("status") != "active" or membership.get("role") != "employee":
            continue
        if membership.get("employee_id"):
            continue

        organization_id = int(membership["organization_id"])
        employee_id = find_repair_employee_id_for_member(cursor, organization_id, user_id, user_email, full_name)
        if employee_id is None:
            continue
        cursor.execute(
            """
            UPDATE organization_memberships
            SET employee_id = ?, updated_at = ?
            WHERE organization_id = ?
              AND user_id = ?
              AND role = 'employee'
              AND status = 'active'
              AND employee_id IS NULL
            """,
            (employee_id, current_utc_timestamp(), organization_id, current_user["id"]),
        )
        if cursor.rowcount:
            membership["employee_id"] = employee_id
            repaired = True

    return repaired


def repair_organization_employee_membership_links(cursor, organization_id: int) -> int:
    cursor.execute(
        """
        SELECT om.user_id, u.email, u.full_name
        FROM organization_memberships om
        JOIN users u ON u.id = om.user_id
        WHERE om.organization_id = ?
          AND om.role = 'employee'
          AND om.status = 'active'
          AND om.employee_id IS NULL
        ORDER BY om.user_id
        """,
        (organization_id,),
    )
    members = cursor.fetchall()
    repaired_count = 0
    for member in members:
        employee_id = find_repair_employee_id_for_member(
            cursor,
            organization_id,
            int(member["user_id"]),
            str(member["email"] or ""),
            str(member["full_name"] or ""),
        )
        if employee_id is None:
            continue
        cursor.execute(
            """
            UPDATE organization_memberships
            SET employee_id = ?, updated_at = ?
            WHERE organization_id = ?
              AND user_id = ?
              AND role = 'employee'
              AND status = 'active'
              AND employee_id IS NULL
            """,
            (employee_id, current_utc_timestamp(), organization_id, int(member["user_id"])),
        )
        if cursor.rowcount:
            repaired_count += 1
    return repaired_count


def active_user_count(cursor) -> int:
    return auth_repository.active_user_count(cursor)


def require_database_admin_if_auth_initialized(authorization: str | None = Header(default=None)) -> dict | None:
    connection = get_connection()
    try:
        cursor = connection.cursor()
        has_active_users = active_user_count(cursor) > 0
    finally:
        connection.close()

    if not has_active_users:
        return None

    current_user = get_current_user(authorization)
    membership = find_any_membership_with_role(current_user, {"owner", "admin"})
    if not membership:
        raise HTTPException(status_code=403, detail="Owner or admin permissions are required")
    return {"user": current_user, "membership": membership}


def require_developer_support_access(current_user: dict = Depends(get_current_user)) -> dict:
    if not is_developer_mode_enabled():
        raise HTTPException(status_code=404, detail="Developer support mode is disabled")
    membership = find_any_membership_with_role(current_user, {"owner", "admin"})
    if not membership:
        raise HTTPException(status_code=403, detail="Owner or admin permissions are required")
    return {"user": current_user, "membership": membership}


def require_preference_access_if_auth_initialized(authorization: str | None = Header(default=None)) -> dict | None:
    connection = get_connection()
    try:
        cursor = connection.cursor()
        has_active_users = active_user_count(cursor) > 0
    finally:
        connection.close()

    if not has_active_users:
        return None

    current_user = get_current_user(authorization)
    admin_membership = find_any_membership_with_role(current_user, {"owner", "admin", "scheduler", "manager"})
    if admin_membership:
        return {"user": current_user, "membership": admin_membership, "scope": "all"}

    employee_membership = find_any_membership_with_role(current_user, {"employee"})
    if employee_membership and not employee_membership.get("employee_id"):
        connection = get_connection()
        try:
            cursor = connection.cursor()
            repaired = repair_employee_membership_links(cursor, current_user)
            if repaired:
                write_auth_audit_event(
                    cursor,
                    "employee_membership_link_repaired",
                    user_id=current_user["id"],
                    organization_id=employee_membership["organization_id"],
                    metadata={"employee_id": employee_membership.get("employee_id")},
                )
                connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    if employee_membership and employee_membership.get("employee_id"):
        return {"user": current_user, "membership": employee_membership, "scope": "own"}

    if employee_membership:
        raise HTTPException(status_code=403, detail="Employee account is not linked to an employee record")

    raise HTTPException(status_code=403, detail="Preference permissions are required")


def auth_is_initialized() -> bool:
    connection = get_connection()
    try:
        cursor = connection.cursor()
        return active_user_count(cursor) > 0
    finally:
        connection.close()


def require_roles_if_auth_initialized(
    allowed_roles: set[str],
    authorization: str | None = Header(default=None),
) -> dict | None:
    if not auth_is_initialized():
        return None

    current_user = get_current_user(authorization)
    membership = find_any_membership_with_role(current_user, allowed_roles)
    if not membership:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return {"user": current_user, "membership": membership}


def require_schedule_view_if_auth_initialized(authorization: str | None = Header(default=None)) -> dict | None:
    return require_roles_if_auth_initialized({"owner", "admin", "scheduler", "manager", "read_only", "employee"}, authorization)


def require_schedule_edit_if_auth_initialized(authorization: str | None = Header(default=None)) -> dict | None:
    return require_roles_if_auth_initialized({"owner", "admin", "scheduler"}, authorization)


def require_setup_edit_if_auth_initialized(authorization: str | None = Header(default=None)) -> dict | None:
    return require_roles_if_auth_initialized({"owner", "admin", "scheduler"}, authorization)


def require_permanent_preference_admin_if_auth_initialized(authorization: str | None = Header(default=None)) -> dict | None:
    return require_roles_if_auth_initialized({"owner", "admin"}, authorization)


def employee_scope_from_access(access_context: dict | None) -> int | None:
    if not access_context:
        return None
    membership = access_context.get("membership") or {}
    if membership.get("role") != "employee":
        return None
    employee_id = membership.get("employee_id")
    if not employee_id:
        raise HTTPException(status_code=403, detail="Employee account is not linked to an employee record")
    return int(employee_id)


def require_employee_position_scope(cursor, employee_id: int, position_id: int | None) -> int | None:
    if position_id is None:
        return None
    cursor.execute(
        """
        SELECT 1
        FROM employee_positions
        WHERE employee_id = ? AND position_id = ?
        """,
        (employee_id, position_id),
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=403, detail="Employees can view only schedules for their assigned positions")
    return position_id


def require_employee_preference_scope(preference_context: dict | None, employee_id: int) -> None:
    if not preference_context or preference_context["scope"] == "all":
        return
    if preference_context["membership"].get("employee_id") != employee_id:
        raise HTTPException(status_code=403, detail="Employees can manage only their own preferences")


def get_optional_current_user(authorization: str | None = Header(default=None)) -> dict | None:
    if not authorization:
        return None
    try:
        return get_current_user(authorization)
    except HTTPException:
        return None


def write_auth_audit_event(
    cursor,
    event_type: str,
    user_id: int | None = None,
    organization_id: int | None = None,
    metadata: dict | None = None,
) -> None:
    auth_repository.write_auth_audit_event(
        cursor,
        event_type,
        user_id=user_id,
        organization_id=organization_id,
        metadata=metadata,
    )


def write_auth_audit_event_record(
    event_type: str,
    user_id: int | None = None,
    organization_id: int | None = None,
    metadata: dict | None = None,
) -> None:
    connection = get_connection()
    try:
        cursor = connection.cursor()
        write_auth_audit_event(
            cursor,
            event_type,
            user_id=user_id,
            organization_id=organization_id,
            metadata=metadata,
        )
        connection.commit()
    finally:
        connection.close()


def write_license_event(
    cursor,
    event_type: str,
    organization_id: int = 1,
    license_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    cursor.execute(
        """
        INSERT INTO license_events (organization_id, license_id, event_type, metadata_json)
        VALUES (?, ?, ?, ?)
        """,
        (organization_id, license_id, event_type, json.dumps(metadata or {}, ensure_ascii=False)),
    )


def count_organization_employees(cursor, organization_id: int = 1) -> int:
    cursor.execute("SELECT COUNT(*) FROM employees WHERE organization_id = ?", (organization_id,))
    return int(cursor.fetchone()[0])


def get_default_organization_row(cursor, organization_id: int = 1):
    cursor.execute(
        """
        SELECT id, public_id, name, created_at
        FROM organizations
        WHERE id = ?
        """,
        (organization_id,),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Organization not found")
    return row


def get_latest_license_certificate(cursor, organization_id: int = 1) -> dict | None:
    cursor.execute(
        """
        SELECT certificate_json, last_verified_at, imported_at, source
        FROM licenses
        WHERE organization_id = ?
          AND revoked_at IS NULL
        ORDER BY imported_at DESC, id DESC
        LIMIT 1
        """,
        (organization_id,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    try:
        certificate = json.loads(row["certificate_json"])
        certificate["_last_verified_at"] = row["last_verified_at"]
        certificate["_imported_at"] = row["imported_at"]
        certificate["_source"] = row["source"]
        return certificate
    except (TypeError, json.JSONDecodeError):
        return None


def build_license_status_payload(cursor, organization_id: int = 1) -> dict:
    organization = get_default_organization_row(cursor, organization_id)
    employee_count = count_organization_employees(cursor, organization_id)
    if is_license_bypass_enabled():
        payload = license_runtime.build_developer_bypass_status()
        payload.update(
            {
                "employee_count": employee_count,
                "organization_id": organization_id,
                "organization_public_id": organization["public_id"],
                "organization_name": organization["name"],
                "key_id": "developer",
                "last_verified_at": None,
                "imported_at": None,
            }
        )
        payload["enforcement"] = license_runtime.build_enforcement(
            payload["status"],
            int(payload["employee_limit"]),
            employee_count,
        )
        return payload

    certificate = get_latest_license_certificate(cursor, organization_id)
    if certificate:
        status = license_runtime.calculate_certificate_status(certificate)
        employee_limit = int(certificate.get("employee_limit") or license_runtime.TRIAL_EMPLOYEE_LIMIT)
        payload = {
            "status": status,
            "source": "license",
            "license_id": certificate.get("license_id"),
            "plan_code": certificate.get("plan_code"),
            "employee_limit": employee_limit,
            "employee_count": employee_count,
            "organization_id": organization_id,
            "organization_public_id": organization["public_id"],
            "organization_name": organization["name"],
            "trial_started_at": certificate.get("trial_started_at"),
            "trial_expires_at": certificate.get("trial_expires_at"),
            "support_cloud_expires_at": certificate.get("support_cloud_expires_at"),
            "grace_ends_at": certificate.get("grace_ends_at"),
            "features": certificate.get("features") or [],
            "key_id": certificate.get("key_id"),
            "last_verified_at": certificate.get("_last_verified_at"),
            "imported_at": certificate.get("_imported_at"),
        }
    else:
        payload = license_runtime.calculate_trial_status(organization["created_at"])
        payload.update(
            {
                "employee_count": employee_count,
                "organization_id": organization_id,
                "organization_public_id": organization["public_id"],
                "organization_name": organization["name"],
                "key_id": None,
                "last_verified_at": None,
                "imported_at": None,
            }
        )
        employee_limit = int(payload["employee_limit"])
        status = str(payload["status"])
    payload["enforcement"] = license_runtime.build_enforcement(status, employee_limit, employee_count)
    return payload


def require_license_capability(cursor, capability: str, organization_id: int = 1) -> dict:
    payload = build_license_status_payload(cursor, organization_id)
    enforcement = payload.get("enforcement") or {}
    if enforcement.get(capability):
        return payload
    status = payload.get("status") or "unknown"
    detail = {
        "message": "License does not allow this action",
        "capability": capability,
        "license_status": status,
        "plan_code": payload.get("plan_code"),
        "employee_limit": payload.get("employee_limit"),
        "employee_count": payload.get("employee_count"),
        "blocking_reason": enforcement.get("blocking_reason"),
        "employee_limit_reached": enforcement.get("employee_limit_reached"),
    }
    raise HTTPException(status_code=402, detail=detail)


def import_license_certificate(cursor, certificate_data: dict[str, Any], organization_id: int = 1, source: str = "imported") -> dict:
    organization = get_default_organization_row(cursor, organization_id)
    certificate = license_runtime.normalize_certificate(certificate_data)
    if certificate["organization_public_id"] != organization["public_id"]:
        raise HTTPException(status_code=400, detail="License certificate belongs to a different organization")
    try:
        license_runtime.verify_certificate_signature(certificate, developer_mode=is_developer_mode_enabled())
    except license_runtime.LicenseValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    status = license_runtime.calculate_certificate_status(certificate)
    now = current_utc_timestamp()
    certificate_json = json.dumps(certificate, ensure_ascii=False, sort_keys=True)
    cursor.execute(
        """
        INSERT INTO licenses (
            organization_id,
            license_id,
            status,
            plan_code,
            employee_limit,
            support_cloud_expires_at,
            grace_ends_at,
            certificate_json,
            signature,
            key_id,
            source,
            imported_at,
            last_verified_at,
            revoked_at
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
            organization_id,
            certificate["license_id"],
            status,
            certificate["plan_code"],
            certificate["employee_limit"],
            certificate.get("support_cloud_expires_at"),
            certificate.get("grace_ends_at"),
            certificate_json,
            certificate.get("signature"),
            certificate.get("key_id"),
            source,
            now,
            now,
            certificate.get("revoked_at"),
        ),
    )
    write_license_event(
        cursor,
        "license_imported",
        organization_id=organization_id,
        license_id=certificate["license_id"],
        metadata={"source": source, "status": status, "plan_code": certificate["plan_code"]},
    )
    return build_license_status_payload(cursor, organization_id)


def audit_context_from_admin(admin_context: dict | None) -> tuple[int | None, int | None]:
    if not admin_context:
        return None, None
    return admin_context["user"]["id"], admin_context["membership"]["organization_id"]


def audit_context_from_user(current_user: dict | None) -> tuple[int | None, int | None]:
    if not current_user:
        return None, None
    membership = current_user["memberships"][0] if current_user["memberships"] else None
    return current_user["id"], membership["organization_id"] if membership else None


def create_recovery_backup(label: str) -> str:
    if not database_module.is_sqlite_runtime():
        return "cloud_sql_managed_backup"
    try:
        return database_module.create_database_backup(label).name
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create safety backup: {exc}") from exc


ORGANIZATION_EXPORT_TABLES = (
    "employees",
    "positions",
    "shift_templates",
    "shift_requirements",
    "coverage_requirements",
    "employee_preferences",
    "employee_week_preferences",
    "employee_recurring_preferences",
    "employee_day_statuses",
    "schedule_entries",
    "licenses",
    "app_settings",
)

ORGANIZATION_IMPORT_DELETE_ORDER = (
    "licenses",
    "schedule_entries",
    "employee_day_statuses",
    "employee_recurring_preferences",
    "employee_week_preferences",
    "employee_preferences",
    "coverage_requirements",
    "shift_requirements",
    "employee_positions",
    "shift_templates",
    "positions",
    "employees",
    "app_settings",
)
LOCAL_ONLY_APP_SETTING_KEYS = {
    "desktop_cloud_access_token",
    "desktop_cloud_last_pull_at",
    "desktop_cloud_last_pull_app_version",
    "desktop_cloud_last_push_at",
    "desktop_cloud_last_push_error",
    "desktop_sync_suspended",
}


def fetch_table_rows(cursor: sqlite3.Cursor, table_name: str, organization_id: int) -> list[dict]:
    order_column = "key" if table_name == "app_settings" else "id"
    if table_name == "app_settings":
        placeholders = ",".join(["?"] * len(LOCAL_ONLY_APP_SETTING_KEYS))
        cursor.execute(
            f"""
            SELECT *
            FROM app_settings
            WHERE organization_id = ?
              AND key NOT IN ({placeholders})
            ORDER BY {order_column}
            """,
            (organization_id, *sorted(LOCAL_ONLY_APP_SETTING_KEYS)),
        )
    else:
        cursor.execute(f"SELECT * FROM {table_name} WHERE organization_id = ? ORDER BY {order_column}", (organization_id,))
    return [dict(row) for row in cursor.fetchall()]


def build_organization_export_bundle(connection, organization_id: int, exported_by_user_id: int | None = None) -> dict:
    cursor = connection.cursor()
    organization = fetch_one_or_404(
        cursor,
        "SELECT id, public_id, name, status FROM organizations WHERE id = ?",
        (organization_id,),
        "Organization not found",
    )
    records = {table_name: fetch_table_rows(cursor, table_name, organization_id) for table_name in ORGANIZATION_EXPORT_TABLES}
    cursor.execute(
        """
        SELECT ep.employee_id, e.public_id AS employee_public_id,
               ep.position_id, p.public_id AS position_public_id,
               ep.is_primary, ep.priority_score, ep.is_fallback_only
        FROM employee_positions ep
        JOIN employees e ON e.id = ep.employee_id
        JOIN positions p ON p.id = ep.position_id
        WHERE e.organization_id = ? AND p.organization_id = ?
        ORDER BY ep.employee_id, ep.position_id
        """,
        (organization_id, organization_id),
    )
    records["employee_positions"] = [dict(row) for row in cursor.fetchall()]
    return {
        "format": "shiftcare.organization.v1",
        "app_version": APP_VERSION,
        "exported_at": current_utc_timestamp(),
        "exported_by_user_id": exported_by_user_id,
        "organization": dict(organization),
        "records": records,
    }


def _source_rows_by_public_id(rows: list[dict]) -> dict[str, dict]:
    return {str(row.get("public_id")): row for row in rows if row.get("public_id")}


def _insert_employee_bundle_rows(cursor: sqlite3.Cursor, rows: list[dict], organization_id: int, now: str) -> dict[int, int]:
    id_map = {}
    for row in rows:
        cursor.execute(
            """
            INSERT INTO employees (
                organization_id, public_id, id_card, full_name, sex, min_shifts_per_week, target_shifts_per_week,
                max_shifts_per_week, can_work_night, can_work_weekends,
                can_work_evenings_after_night, can_work_mornings_and_evenings, created_at, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                row.get("public_id"),
                normalize_id_card(row.get("id_card")) or None,
                row.get("full_name"),
                row.get("sex"),
                row.get("min_shifts_per_week"),
                row.get("target_shifts_per_week"),
                row.get("max_shifts_per_week"),
                int(row.get("can_work_night") or 0),
                int(row.get("can_work_weekends") or 0),
                int(row.get("can_work_evenings_after_night") or 0),
                int(row.get("can_work_mornings_and_evenings") or 0),
                row.get("created_at") or now,
                row.get("updated_at") or now,
                row.get("updated_by"),
            ),
        )
        id_map[int(row["id"])] = int(cursor.lastrowid)
    return id_map


def _insert_position_bundle_rows(cursor: sqlite3.Cursor, rows: list[dict], organization_id: int, now: str) -> dict[int, int]:
    id_map = {}
    for row in rows:
        cursor.execute(
            """
            INSERT INTO positions (
                organization_id, public_id, name, color, requires_continuous_coverage, minimum_staff_presence,
                max_consecutive_nights, emergency_max_consecutive_nights,
                max_consecutive_split_days, emergency_max_consecutive_split_days, created_at, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                row.get("public_id"),
                row.get("name"),
                row.get("color") or DEFAULT_POSITION_COLOR,
                int(row.get("requires_continuous_coverage") or 0),
                int(row.get("minimum_staff_presence") or 0),
                row.get("max_consecutive_nights"),
                row.get("emergency_max_consecutive_nights"),
                row.get("max_consecutive_split_days"),
                row.get("emergency_max_consecutive_split_days"),
                row.get("created_at") or now,
                row.get("updated_at") or now,
                row.get("updated_by"),
            ),
        )
        id_map[int(row["id"])] = int(cursor.lastrowid)
    return id_map


def _insert_license_bundle_rows(cursor: sqlite3.Cursor, rows: list[dict], organization_id: int, now: str) -> int:
    imported_count = 0
    for row in rows:
        certificate_json = row.get("certificate_json")
        if not certificate_json:
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
            DO UPDATE SET organization_id = excluded.organization_id,
                          status = excluded.status,
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
                organization_id,
                row.get("license_id"),
                row.get("status") or "active",
                row.get("plan_code"),
                int(row.get("employee_limit") or license_runtime.TRIAL_EMPLOYEE_LIMIT),
                row.get("support_cloud_expires_at"),
                row.get("grace_ends_at"),
                certificate_json,
                row.get("signature") or "",
                row.get("key_id"),
                row.get("source") or "imported",
                row.get("imported_at") or now,
                row.get("last_verified_at") or now,
                row.get("revoked_at"),
            ),
        )
        imported_count += 1
    return imported_count


def import_organization_bundle(connection, organization_id: int, bundle: dict, replace_existing: bool, imported_by_user_id: int) -> dict:
    if bundle.get("format") != "shiftcare.organization.v1":
        raise HTTPException(status_code=400, detail="Unsupported organization bundle format")
    records = bundle.get("records") or {}
    organization = bundle.get("organization") or {}
    now = current_utc_timestamp()
    cursor = connection.cursor()

    target_organization = fetch_one_or_404(
        cursor,
        "SELECT id, public_id FROM organizations WHERE id = ?",
        (organization_id,),
        "Organization not found",
    )
    existing_counts = {
        table_name: fetch_count(cursor, f"SELECT COUNT(*) FROM {table_name} WHERE organization_id = ?", (organization_id,))
        for table_name in ("employees", "positions", "shift_templates", "schedule_entries")
    }
    if any(existing_counts.values()) and not replace_existing:
        raise HTTPException(status_code=409, detail="Target organization already has scheduling data")

    if replace_existing:
        for table_name in ORGANIZATION_IMPORT_DELETE_ORDER:
            if table_name == "employee_positions":
                cursor.execute(
                    """
                    DELETE FROM employee_positions
                    WHERE employee_id IN (SELECT id FROM employees WHERE organization_id = ?)
                       OR position_id IN (SELECT id FROM positions WHERE organization_id = ?)
                    """,
                    (organization_id, organization_id),
                )
            else:
                cursor.execute(f"DELETE FROM {table_name} WHERE organization_id = ?", (organization_id,))

    cursor.execute(
        "UPDATE organizations SET name = ?, status = 'active', updated_at = ? WHERE id = ?",
        (organization.get("name") or "Imported Organization", now, organization_id),
    )

    employee_id_map = _insert_employee_bundle_rows(cursor, records.get("employees") or [], organization_id, now)
    position_id_map = _insert_position_bundle_rows(cursor, records.get("positions") or [], organization_id, now)
    license_count = _insert_license_bundle_rows(cursor, records.get("licenses") or [], organization_id, now)
    employees_by_public_id = _source_rows_by_public_id(records.get("employees") or [])
    positions_by_public_id = _source_rows_by_public_id(records.get("positions") or [])

    shift_template_id_map = {}
    for row in records.get("shift_templates") or []:
        new_position_id = position_id_map.get(int(row["position_id"])) if row.get("position_id") is not None else None
        cursor.execute(
            """
            INSERT INTO shift_templates (
                organization_id, public_id, position_id, category, name, start_time, end_time,
                is_overnight, is_active, is_split_only, created_at, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                row.get("public_id"),
                new_position_id,
                row.get("category"),
                row.get("name"),
                row.get("start_time"),
                row.get("end_time"),
                int(row.get("is_overnight") or 0),
                int(row.get("is_active") if row.get("is_active") is not None else 1),
                int(row.get("is_split_only") or 0),
                row.get("created_at") or now,
                row.get("updated_at") or now,
                row.get("updated_by"),
            ),
        )
        shift_template_id_map[int(row["id"])] = int(cursor.lastrowid)

    for row in records.get("employee_positions") or []:
        source_employee = employees_by_public_id.get(str(row.get("employee_public_id")))
        source_position = positions_by_public_id.get(str(row.get("position_public_id")))
        if not source_employee or not source_position:
            continue
        new_employee_id = employee_id_map.get(int(source_employee["id"]))
        new_position_id = position_id_map.get(int(source_position["id"]))
        if not new_employee_id or not new_position_id:
            continue
        cursor.execute(
            """
            INSERT INTO employee_positions (
                employee_id, position_id, is_primary, priority_score, is_fallback_only
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(employee_id, position_id)
            DO UPDATE SET is_primary = excluded.is_primary,
                          priority_score = excluded.priority_score,
                          is_fallback_only = excluded.is_fallback_only
            """,
            (
                new_employee_id,
                new_position_id,
                int(row.get("is_primary") or 0),
                int(row.get("priority_score") or 50),
                int(row.get("is_fallback_only") or 0),
            ),
        )

    for row in records.get("shift_requirements") or []:
        new_position_id = position_id_map.get(int(row["position_id"]))
        if not new_position_id:
            continue
        cursor.execute(
            """
            INSERT INTO shift_requirements (
                organization_id, public_id, position_id, shift_category, required_total,
                required_female_min, required_male_min, created_at, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                row.get("public_id"),
                new_position_id,
                row.get("shift_category"),
                int(row.get("required_total") or 0),
                int(row.get("required_female_min") or 0),
                int(row.get("required_male_min") or 0),
                row.get("created_at") or now,
                row.get("updated_at") or now,
                row.get("updated_by"),
            ),
        )

    for row in records.get("coverage_requirements") or []:
        new_position_id = position_id_map.get(int(row["position_id"]))
        if not new_position_id:
            continue
        cursor.execute(
            """
            INSERT INTO coverage_requirements (
                organization_id, public_id, position_id, start_time, end_time, required_total,
                required_female_min, required_male_min, is_overnight, created_at, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                row.get("public_id"),
                new_position_id,
                row.get("start_time"),
                row.get("end_time"),
                int(row.get("required_total") or 0),
                int(row.get("required_female_min") or 0),
                int(row.get("required_male_min") or 0),
                int(row.get("is_overnight") or 0),
                row.get("created_at") or now,
                row.get("updated_at") or now,
                row.get("updated_by"),
            ),
        )

    for row in records.get("employee_preferences") or []:
        new_employee_id = employee_id_map.get(int(row["employee_id"]))
        if not new_employee_id:
            continue
        cursor.execute(
            """
            INSERT INTO employee_preferences (
                organization_id, public_id, employee_id, allow_morning, allow_evening, allow_night,
                allow_morning_evening_combo, created_at, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                row.get("public_id"),
                new_employee_id,
                int(row.get("allow_morning") or 0),
                int(row.get("allow_evening") or 0),
                int(row.get("allow_night") or 0),
                int(row.get("allow_morning_evening_combo") or 0),
                row.get("created_at") or now,
                row.get("updated_at") or now,
                row.get("updated_by"),
            ),
        )

    for row in records.get("employee_week_preferences") or []:
        new_employee_id = employee_id_map.get(int(row["employee_id"]))
        if not new_employee_id:
            continue
        cursor.execute(
            """
            INSERT INTO employee_week_preferences (
                organization_id, public_id, employee_id, week_start_date, preference_date,
                preference_type, created_at, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                row.get("public_id"),
                new_employee_id,
                row.get("week_start_date"),
                row.get("preference_date"),
                row.get("preference_type"),
                row.get("created_at") or now,
                row.get("updated_at") or now,
                row.get("updated_by"),
            ),
        )

    for row in records.get("employee_recurring_preferences") or []:
        new_employee_id = employee_id_map.get(int(row["employee_id"]))
        if not new_employee_id:
            continue
        cursor.execute(
            """
            INSERT INTO employee_recurring_preferences (
                organization_id, public_id, employee_id, preference_kind, day_of_week,
                preference_type, created_at, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                row.get("public_id"),
                new_employee_id,
                row.get("preference_kind"),
                int(row.get("day_of_week") or 0),
                row.get("preference_type"),
                row.get("created_at") or now,
                row.get("updated_at") or now,
                row.get("updated_by"),
            ),
        )

    for row in records.get("employee_day_statuses") or []:
        new_employee_id = employee_id_map.get(int(row["employee_id"]))
        if not new_employee_id:
            continue
        cursor.execute(
            """
            INSERT INTO employee_day_statuses (
                organization_id, public_id, employee_id, date, status_type, created_at, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                row.get("public_id"),
                new_employee_id,
                row.get("date"),
                row.get("status_type"),
                row.get("created_at") or now,
                row.get("updated_at") or now,
                row.get("updated_by"),
            ),
        )

    for row in records.get("schedule_entries") or []:
        new_employee_id = employee_id_map.get(int(row["employee_id"]))
        new_position_id = position_id_map.get(int(row["position_id"]))
        new_template_id = shift_template_id_map.get(int(row["shift_template_id"]))
        if not new_employee_id or not new_position_id or not new_template_id:
            continue
        cursor.execute(
            """
            INSERT INTO schedule_entries (
                organization_id, public_id, employee_id, position_id, date, shift_template_id,
                no_show, created_at, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                row.get("public_id"),
                new_employee_id,
                new_position_id,
                row.get("date"),
                new_template_id,
                int(row.get("no_show") or 0),
                row.get("created_at") or now,
                row.get("updated_at") or now,
                row.get("updated_by"),
            ),
        )

    for row in records.get("app_settings") or []:
        cursor.execute(
            """
            INSERT INTO app_settings (organization_id, key, value)
            VALUES (?, ?, ?)
            ON CONFLICT(key)
            DO UPDATE SET organization_id = excluded.organization_id,
                          value = excluded.value
            """,
            (organization_id, row.get("key"), row.get("value")),
        )

    write_auth_audit_event(
        cursor,
        "organization_cloud_imported",
        user_id=imported_by_user_id,
        organization_id=organization_id,
        metadata={"source_organization_public_id": organization.get("public_id"), "source_app_version": bundle.get("app_version")},
    )
    return {
        "organization_id": organization_id,
        "organization_public_id": target_organization["public_id"],
        "source_organization_public_id": organization.get("public_id"),
        "imported": {
            "employees": len(employee_id_map),
            "positions": len(position_id_map),
            "shift_templates": len(shift_template_id_map),
            "schedule_entries": len(records.get("schedule_entries") or []),
            "licenses": license_count,
        },
    }


def normalize_version(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized.startswith("v"):
        normalized = normalized[1:]
    return normalized.replace("_", "-")


def version_sort_key(value: str) -> tuple[int, int, int, int]:
    normalized = normalize_version(value)
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", normalized)
    if not match:
        return 0, 0, 0, 0

    major, minor, patch = (int(part) for part in match.groups())
    stability = 0 if any(label in normalized for label in ("alpha", "beta", "rc")) else 1
    return major, minor, patch, stability


def is_newer_version(candidate: str, current: str | None = None) -> bool:
    return version_sort_key(candidate) > version_sort_key(current or APP_VERSION)


def request_github_releases() -> list[dict]:
    request = urllib.request.Request(
        GITHUB_RELEASES_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"ShiftCare/{APP_VERSION}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Could not contact GitHub Releases: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="GitHub Releases returned invalid JSON") from exc


def release_asset_version(asset_name: str) -> str | None:
    match = GITHUB_RELEASE_ASSET_PATTERN.match(asset_name or "")
    if not match:
        return None
    return normalize_version(match.group("version"))


def find_latest_installable_release(releases: list[dict]) -> dict | None:
    candidates: list[dict] = []
    for release in releases:
        if release.get("draft"):
            continue

        release_version = normalize_version(release.get("tag_name") or release.get("name") or "")
        for asset in release.get("assets") or []:
            asset_version = release_asset_version(asset.get("name", ""))
            if not asset_version:
                continue

            candidates.append(
                {
                    "version": asset_version or release_version,
                    "release_name": release.get("name") or release.get("tag_name") or asset_version,
                    "tag_name": release.get("tag_name") or "",
                    "body": release.get("body") or "",
                    "published_at": release.get("published_at") or "",
                    "asset_name": asset.get("name") or "",
                    "download_url": asset.get("browser_download_url") or "",
                    "size_bytes": asset.get("size") or 0,
                    "html_url": release.get("html_url") or "",
                    "prerelease": bool(release.get("prerelease")),
                }
            )

    if not candidates:
        return None

    return max(candidates, key=lambda candidate: version_sort_key(candidate["version"]))


def get_update_status() -> dict:
    latest_release = find_latest_installable_release(request_github_releases())
    if latest_release is None:
        return {
            "current_version": APP_VERSION,
            "update_available": False,
            "message": "No installable Windows release asset was found.",
        }

    return {
        "current_version": APP_VERSION,
        "update_available": is_newer_version(latest_release["version"]),
        "latest": latest_release,
    }


def validate_release_download_url(download_url: str) -> None:
    parsed = urlparse(download_url)
    if parsed.scheme != "https":
        raise HTTPException(status_code=400, detail="Update download URL must use HTTPS")

    if parsed.netloc.lower() not in {"github.com", "objects.githubusercontent.com"}:
        raise HTTPException(status_code=400, detail="Update download URL is not a GitHub release asset")


def download_update_installer(download_url: str, asset_name: str) -> Path:
    validate_release_download_url(download_url)
    safe_asset_name = Path(asset_name).name
    if not release_asset_version(safe_asset_name):
        raise HTTPException(status_code=400, detail="Release asset is not a ShiftCare installer")

    target_dir = Path(tempfile.gettempdir()) / "ShiftCare" / "updates"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / safe_asset_name

    request = urllib.request.Request(
        download_url,
        headers={"User-Agent": f"ShiftCare/{APP_VERSION}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response, target_path.open("wb") as output_file:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output_file.write(chunk)
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Could not download update: {exc}") from exc

    return target_path


def schedule_desktop_shutdown(delay_seconds: float = 2.0) -> None:
    if not getattr(sys, "frozen", False):
        return

    def delayed_exit() -> None:
        import time as time_module

        time_module.sleep(delay_seconds)
        os._exit(0)

    threading.Thread(target=delayed_exit, daemon=True).start()


def get_employee_week_shift_count(connection, employee_id: int, week_start_date: str) -> int:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM schedule_entries
        WHERE employee_id = ? AND date >= ? AND date <= ? AND no_show = 0
        """,
        (employee_id, week_start_date, get_week_end_date(week_start_date)),
    )
    return cursor.fetchone()["cnt"]


def get_employee_week_worked_dates(connection, employee_id: int, week_start_date: str) -> set[str]:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT DISTINCT date
        FROM schedule_entries
        WHERE employee_id = ? AND date >= ? AND date <= ? AND no_show = 0
        """,
        (employee_id, week_start_date, get_week_end_date(week_start_date)),
    )
    return {row["date"] for row in cursor.fetchall()}


def entry_category(entry: dict) -> str:
    return entry.get("category") or entry.get("shift_category")


def get_employee_entries_for_date(connection, employee_id: int, date_string: str) -> list[dict]:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT se.*, st.category, st.start_time, st.end_time, st.is_overnight, st.is_split_only
        FROM schedule_entries se
        JOIN shift_templates st ON st.id = se.shift_template_id
        WHERE se.employee_id = ? AND se.date = ? AND se.no_show = 0
        ORDER BY st.start_time
        """,
        (employee_id, date_string),
    )
    return [dict(row) for row in cursor.fetchall()]


def employee_has_night_on_date(connection, employee_id: int, date_string: str) -> bool:
    return any(entry["category"] == "night" for entry in get_employee_entries_for_date(connection, employee_id, date_string))


def get_previous_night_entries(
    connection,
    employee_id: int,
    date_string: str,
    staged_entries: list[dict] | None = None,
) -> list[dict]:
    previous_date = (parse_date_string(date_string) - timedelta(days=1)).isoformat()
    staged_entries = staged_entries or []
    return [
        entry
        for entry in [
            *get_employee_entries_for_date(connection, employee_id, previous_date),
            *[
                staged_entry
                for staged_entry in staged_entries
                if staged_entry["employee_id"] == employee_id and staged_entry["date"] == previous_date
            ],
        ]
        if entry_category(entry) == "night"
    ]


def had_previous_night(
    connection,
    employee_id: int,
    date_string: str,
    staged_entries: list[dict] | None = None,
) -> bool:
    return bool(get_previous_night_entries(connection, employee_id, date_string, staged_entries))


def get_next_morning_entries(
    connection,
    employee_id: int,
    date_string: str,
    staged_entries: list[dict] | None = None,
) -> list[dict]:
    next_date = (parse_date_string(date_string) + timedelta(days=1)).isoformat()
    staged_entries = staged_entries or []
    return [
        entry
        for entry in [
            *get_employee_entries_for_date(connection, employee_id, next_date),
            *[
                staged_entry
                for staged_entry in staged_entries
                if staged_entry["employee_id"] == employee_id and staged_entry["date"] == next_date
            ],
        ]
        if entry_category(entry) == "morning"
    ]


def has_next_morning(
    connection,
    employee_id: int,
    date_string: str,
    staged_entries: list[dict] | None = None,
) -> bool:
    return bool(get_next_morning_entries(connection, employee_id, date_string, staged_entries))


def get_break_minutes_after_previous_night(
    connection,
    employee_id: int,
    date_string: str,
    template: dict,
    staged_entries: list[dict] | None = None,
) -> int | None:
    previous_nights = get_previous_night_entries(connection, employee_id, date_string, staged_entries)
    if not previous_nights:
        return None

    current_start = 24 * 60 + time_to_minutes(template["start_time"])
    shortest_break = None
    for entry in previous_nights:
        night_interval = build_interval(entry["start_time"], entry["end_time"], bool(entry["is_overnight"]))
        break_minutes = current_start - night_interval.end
        if shortest_break is None or break_minutes < shortest_break:
            shortest_break = break_minutes

    return shortest_break


def get_break_minutes_between_same_day_categories(
    connection,
    employee_id: int,
    date_string: str,
    template: dict,
    first_category: str,
    second_category: str,
    entries: list[dict] | None = None,
) -> int | None:
    template_interval = build_interval(template["start_time"], template["end_time"], template["is_overnight"])
    breaks = []

    for entry in entries if entries is not None else get_employee_entries_for_date(connection, employee_id, date_string):
        if entry_category(entry) == first_category and template["category"] == second_category:
            first_interval = build_interval(entry["start_time"], entry["end_time"], bool(entry["is_overnight"]))
            breaks.append(template_interval.start - first_interval.end)

        if entry_category(entry) == second_category and template["category"] == first_category:
            second_interval = build_interval(entry["start_time"], entry["end_time"], bool(entry["is_overnight"]))
            breaks.append(second_interval.start - template_interval.end)

    if not breaks:
        return None

    return min(breaks)


def employee_has_split_day(connection, employee_id: int, date_string: str) -> bool:
    entries = get_employee_entries_for_date(connection, employee_id, date_string)
    categories = {entry["category"] for entry in entries}
    return "morning" in categories and "evening" in categories


def would_have_night_day(connection, employee_id: int, date_string: str, template: dict) -> bool:
    return template["category"] == "night" or employee_has_night_on_date(connection, employee_id, date_string)


def would_have_split_day(connection, employee_id: int, date_string: str, template: dict) -> bool:
    entries = get_employee_entries_for_date(connection, employee_id, date_string)
    categories = {entry["category"] for entry in entries}
    categories.add(template["category"])
    return "morning" in categories and "evening" in categories


def explain_same_day_pairing_rejection(
    connection,
    employee: dict,
    date_string: str,
    template: dict,
    existing_entries: list[dict],
    app_settings: dict,
) -> str | None:
    if not existing_entries:
        return None

    if len(existing_entries) >= 2:
        return "employee already has two shifts that day"

    existing_categories = {entry_category(entry) for entry in existing_entries}
    projected_categories = set(existing_categories)
    projected_categories.add(template["category"])

    if projected_categories == {"morning", "evening"}:
        if not employee["can_work_mornings_and_evenings"]:
            return "employee cannot work morning and evening on the same day"
        if get_week_preference(connection, employee["id"], date_string) == "no_morning_evening_combo":
            return "weekly preference blocks morning-evening combo"
        if get_recurring_preference(connection, employee["id"], date_string, "strict") == "no_morning_evening_combo":
            return "permanent strict preference blocks morning-evening combo"

        morning_evening_break = get_break_minutes_between_same_day_categories(
            connection,
            employee["id"],
            date_string,
            template,
            "morning",
            "evening",
            entries=existing_entries,
        )
        if (
            morning_evening_break is not None
            and morning_evening_break < app_settings["min_rest_minutes_between_morning_and_evening"]
        ):
            return "morning-evening rest gap is too short"

        return None

    if projected_categories == {"morning", "night"}:
        return None

    return "employee already has another shift type that cannot be paired"


def count_consecutive_days_before(connection, employee_id: int, date_string: str, predicate) -> int:
    current_date = parse_date_string(date_string) - timedelta(days=1)
    count = 0

    while count < 7:
        if not predicate(connection, employee_id, current_date.isoformat()):
            break
        count += 1
        current_date -= timedelta(days=1)

    return count


def count_consecutive_days_after(connection, employee_id: int, date_string: str, predicate) -> int:
    current_date = parse_date_string(date_string) + timedelta(days=1)
    count = 0

    while count < 7:
        if not predicate(connection, employee_id, current_date.isoformat()):
            break
        count += 1
        current_date += timedelta(days=1)

    return count


def get_fatigue_penalty(connection, employee_id: int, date_string: str, template: dict) -> int:
    app_settings = get_app_settings(connection)
    penalty = 0

    if had_previous_night(connection, employee_id, date_string):
        if template["category"] == "evening":
            penalty += app_settings["after_night_evening_penalty"]
        elif template["category"] == "night":
            penalty += app_settings["after_night_evening_penalty"] // 2

    if would_have_night_day(connection, employee_id, date_string, template):
        previous_nights = count_consecutive_days_before(connection, employee_id, date_string, employee_has_night_on_date)
        next_nights = count_consecutive_days_after(connection, employee_id, date_string, employee_has_night_on_date)
        penalty += (previous_nights + next_nights) * app_settings["consecutive_night_penalty"]

    if would_have_split_day(connection, employee_id, date_string, template):
        previous_splits = count_consecutive_days_before(connection, employee_id, date_string, employee_has_split_day)
        next_splits = count_consecutive_days_after(connection, employee_id, date_string, employee_has_split_day)
        penalty += (previous_splits + next_splits) * app_settings["consecutive_split_penalty"]

    return penalty


def get_week_preference(connection, employee_id: int, date_string: str) -> str:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT preference_type
        FROM employee_week_preferences
        WHERE employee_id = ? AND preference_date = ?
        """,
        (employee_id, date_string),
    )
    row = cursor.fetchone()
    return row["preference_type"] if row else "no_preference"


def get_recurring_preference(connection, employee_id: int, date_string: str, preference_kind: str) -> str:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT preference_type
        FROM employee_recurring_preferences
        WHERE employee_id = ? AND preference_kind = ? AND day_of_week = ?
        """,
        (employee_id, preference_kind, recurring_day_of_week(date_string)),
    )
    row = cursor.fetchone()
    return row["preference_type"] if row else "no_preference"


def preference_allows_category(preference_type: str, category: str) -> bool:
    if preference_type in ("no_preference", "no_morning_evening_combo"):
        return True
    if preference_type in ("off_day", "vacation"):
        return False
    if preference_type.startswith("only_"):
        return preference_type == f"only_{category}"
    if preference_type == f"not_{category}":
        return False
    return True


def soft_recurring_preference_penalty(
    connection,
    employee_id: int,
    date_string: str,
    assignment_templates: list[dict],
    projected_entries: list[dict] | None = None,
) -> int:
    preference_type = get_recurring_preference(connection, employee_id, date_string, "soft")
    if preference_type == "no_preference" or not assignment_templates:
        return 0
    if preference_type in ("off_day", "vacation"):
        return SOFT_DAY_OFF_PENALTY

    penalty = 0
    assignment_categories = [template["category"] for template in assignment_templates]
    for category in assignment_categories:
        if not preference_allows_category(preference_type, category):
            penalty += SOFT_PREFERENCE_PENALTY

    if preference_type == "no_morning_evening_combo":
        projected_categories = set(assignment_categories)
        projected_categories.update(entry_category(entry) for entry in (projected_entries or []))
        if "morning" in projected_categories and "evening" in projected_categories:
            penalty += SOFT_COMBO_PENALTY

    return penalty


def get_employee_day_status(connection, employee_id: int, date_string: str):
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT status_type
        FROM employee_day_statuses
        WHERE employee_id = ? AND date = ?
        """,
        (employee_id, date_string),
    )
    return cursor.fetchone()


def get_general_preference(connection, employee_id: int) -> dict:
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM employee_preferences WHERE employee_id = ?", (employee_id,))
    row = cursor.fetchone()
    if not row:
        return {
            "allow_morning": True,
            "allow_evening": True,
            "allow_night": True,
            "allow_morning_evening_combo": True,
        }
    return {
        "allow_morning": bool(row["allow_morning"]),
        "allow_evening": bool(row["allow_evening"]),
        "allow_night": bool(row["allow_night"]),
        "allow_morning_evening_combo": bool(row["allow_morning_evening_combo"]),
    }


def category_allowed_by_preferences(connection, employee: dict, date_string: str, category: str) -> bool:
    if category == "night" and not employee["can_work_night"]:
        return False
    if is_weekend(date_string) and not employee["can_work_weekends"]:
        return False

    general = get_general_preference(connection, employee["id"])
    if category == "morning" and not general["allow_morning"]:
        return False
    if category == "evening" and not general["allow_evening"]:
        return False
    if category == "night" and not general["allow_night"]:
        return False

    weekly = get_week_preference(connection, employee["id"], date_string)
    if not preference_allows_category(weekly, category):
        return False

    strict_recurring = get_recurring_preference(connection, employee["id"], date_string, "strict")
    if not preference_allows_category(strict_recurring, category):
        return False
    return True


def can_employee_take_template(
    connection,
    employee: dict,
    position_id: int,
    date_string: str,
    template: dict,
    week_start_date: str,
    fatigue_relaxation: int = 0,
    staged_entries: list[dict] | None = None,
) -> bool:
    app_settings = get_position_app_settings(connection, position_id)
    staged_entries = staged_entries or []
    week_end_date = get_week_end_date(week_start_date)
    staged_week_entries = [
        entry
        for entry in staged_entries
        if entry["employee_id"] == employee["id"] and week_start_date <= entry["date"] <= week_end_date
    ]

    if get_employee_day_status(connection, employee["id"], date_string):
        return False
    if not category_allowed_by_preferences(connection, employee, date_string, template["category"]):
        return False
    if get_employee_week_shift_count(connection, employee["id"], week_start_date) + len(staged_week_entries) >= employee["max_shifts_per_week"]:
        return False

    worked_dates = get_employee_week_worked_dates(connection, employee["id"], week_start_date)
    worked_dates.update(entry["date"] for entry in staged_week_entries)
    projected_worked_dates = set(worked_dates)
    projected_worked_dates.add(date_string)
    if len(projected_worked_dates) > app_settings["max_work_days_per_week"]:
        return False

    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT 1
        FROM employee_positions
        WHERE employee_id = ? AND position_id = ?
        """,
        (employee["id"], position_id),
    )
    if not cursor.fetchone():
        return False

    new_interval = build_interval(template["start_time"], template["end_time"], template["is_overnight"])
    existing_entries = [
        *get_employee_entries_for_date(connection, employee["id"], date_string),
        *[
            entry
            for entry in staged_entries
            if entry["employee_id"] == employee["id"] and entry["date"] == date_string
        ],
    ]

    if not app_settings["allow_multiple_positions_per_day"] and any(
        entry["position_id"] != position_id
        for entry in existing_entries
    ):
        return False

    for entry in existing_entries:
        existing_interval = build_interval(entry["start_time"], entry["end_time"], bool(entry["is_overnight"]))
        if new_interval.overlaps(existing_interval):
            return False

    if explain_same_day_pairing_rejection(connection, employee, date_string, template, existing_entries, app_settings):
        return False

    if had_previous_night(connection, employee["id"], date_string, staged_entries=staged_entries):
        if template["category"] == "morning":
            return False

        if template["category"] == "evening":
            break_minutes = get_break_minutes_after_previous_night(
                connection,
                employee["id"],
                date_string,
                template,
                staged_entries=staged_entries,
            )
            if (
                break_minutes is None
                or break_minutes < app_settings["min_rest_minutes_after_night_before_evening"]
            ):
                return False

    if template["category"] == "night" and has_next_morning(
        connection,
        employee["id"],
        date_string,
        staged_entries=staged_entries,
    ):
        return False

    if would_have_night_day(connection, employee["id"], date_string, template):
        previous_nights = count_consecutive_days_before(connection, employee["id"], date_string, employee_has_night_on_date)
        next_nights = count_consecutive_days_after(connection, employee["id"], date_string, employee_has_night_on_date)
        projected_nights = previous_nights + 1 + next_nights
        allowed_nights = (
            app_settings["max_consecutive_nights"]
            if fatigue_relaxation == 0
            else app_settings["emergency_max_consecutive_nights"]
        )
        if projected_nights > allowed_nights:
            return False

    existing_categories = {entry_category(entry) for entry in existing_entries}
    projected_categories = set(existing_categories)
    projected_categories.add(template["category"])
    if "morning" in projected_categories and "evening" in projected_categories:
        previous_splits = count_consecutive_days_before(connection, employee["id"], date_string, employee_has_split_day)
        next_splits = count_consecutive_days_after(connection, employee["id"], date_string, employee_has_split_day)
        projected_splits = previous_splits + 1 + next_splits
        allowed_splits = (
            app_settings["max_consecutive_split_days"]
            if fatigue_relaxation == 0
            else app_settings["emergency_max_consecutive_split_days"]
        )
        if projected_splits > allowed_splits:
            return False

    return True


def explain_employee_template_rejection(
    connection,
    employee: dict,
    position_id: int,
    date_string: str,
    template: dict,
    week_start_date: str,
    fatigue_relaxation: int = 0,
    staged_entries: list[dict] | None = None,
) -> str | None:
    app_settings = get_position_app_settings(connection, position_id)
    staged_entries = staged_entries or []
    week_end_date = get_week_end_date(week_start_date)
    staged_week_entries = [
        entry
        for entry in staged_entries
        if entry["employee_id"] == employee["id"] and week_start_date <= entry["date"] <= week_end_date
    ]

    if get_employee_day_status(connection, employee["id"], date_string):
        return "day status blocks employee"
    if not category_allowed_by_preferences(connection, employee, date_string, template["category"]):
        return "employee preferences or permissions block this shift"
    if get_employee_week_shift_count(connection, employee["id"], week_start_date) + len(staged_week_entries) >= employee["max_shifts_per_week"]:
        return "employee reached weekly maximum shifts"

    worked_dates = get_employee_week_worked_dates(connection, employee["id"], week_start_date)
    worked_dates.update(entry["date"] for entry in staged_week_entries)
    projected_worked_dates = set(worked_dates)
    projected_worked_dates.add(date_string)
    if len(projected_worked_dates) > app_settings["max_work_days_per_week"]:
        return "mandatory weekly day off would be violated"

    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT 1
        FROM employee_positions
        WHERE employee_id = ? AND position_id = ?
        """,
        (employee["id"], position_id),
    )
    if not cursor.fetchone():
        return "employee is not assigned to this position"

    new_interval = build_interval(template["start_time"], template["end_time"], template["is_overnight"])
    existing_entries = [
        *get_employee_entries_for_date(connection, employee["id"], date_string),
        *[
            entry
            for entry in staged_entries
            if entry["employee_id"] == employee["id"] and entry["date"] == date_string
        ],
    ]
    if not app_settings["allow_multiple_positions_per_day"] and any(
        entry["position_id"] != position_id
        for entry in existing_entries
    ):
        return "employee already has a shift on another position this day"
    for entry in existing_entries:
        existing_interval = build_interval(entry["start_time"], entry["end_time"], bool(entry["is_overnight"]))
        if new_interval.overlaps(existing_interval):
            return "employee already has an overlapping shift"

    pairing_rejection = explain_same_day_pairing_rejection(
        connection,
        employee,
        date_string,
        template,
        existing_entries,
        app_settings,
    )
    if pairing_rejection:
        return pairing_rejection

    if had_previous_night(connection, employee["id"], date_string, staged_entries=staged_entries):
        if template["category"] == "morning":
            return "morning after previous night is forbidden"

        if template["category"] == "evening":
            break_minutes = get_break_minutes_after_previous_night(
                connection,
                employee["id"],
                date_string,
                template,
                staged_entries=staged_entries,
            )
            if (
                break_minutes is None
                or break_minutes < app_settings["min_rest_minutes_after_night_before_evening"]
            ):
                return "night-evening rest gap is too short"

    if template["category"] == "night" and has_next_morning(
        connection,
        employee["id"],
        date_string,
        staged_entries=staged_entries,
    ):
        return "night before next morning is forbidden"

    if would_have_night_day(connection, employee["id"], date_string, template):
        previous_nights = count_consecutive_days_before(connection, employee["id"], date_string, employee_has_night_on_date)
        next_nights = count_consecutive_days_after(connection, employee["id"], date_string, employee_has_night_on_date)
        projected_nights = previous_nights + 1 + next_nights
        allowed_nights = (
            app_settings["max_consecutive_nights"]
            if fatigue_relaxation == 0
            else app_settings["emergency_max_consecutive_nights"]
        )
        if projected_nights > allowed_nights:
            return "too many consecutive night shifts"

    existing_categories = {entry_category(entry) for entry in existing_entries}
    projected_categories = set(existing_categories)
    projected_categories.add(template["category"])
    if "morning" in projected_categories and "evening" in projected_categories:
        previous_splits = count_consecutive_days_before(connection, employee["id"], date_string, employee_has_split_day)
        next_splits = count_consecutive_days_after(connection, employee["id"], date_string, employee_has_split_day)
        projected_splits = previous_splits + 1 + next_splits
        allowed_splits = (
            app_settings["max_consecutive_split_days"]
            if fatigue_relaxation == 0
            else app_settings["emergency_max_consecutive_split_days"]
        )
        if projected_splits > allowed_splits:
            return "too many consecutive split shifts"

    return None


def validate_schedule_entry_basic(connection, entry: ScheduleEntryCreate):
    parse_date_string(entry.date)
    cursor = connection.cursor()
    employee_row = fetch_one_or_404(cursor, "SELECT * FROM employees WHERE id = ?", (entry.employee_id,), "Employee not found")
    fetch_one_or_404(cursor, "SELECT * FROM positions WHERE id = ?", (entry.position_id,), "Position not found")
    template_row = fetch_one_or_404(
        cursor,
        "SELECT * FROM shift_templates WHERE id = ? AND position_id = ?",
        (entry.shift_template_id, entry.position_id),
        "Shift template not found for this position",
    )
    employee = row_to_employee_dict(employee_row)
    template = row_to_shift_template_dict(template_row)
    week_start = get_week_start_for_date(entry.date)
    if not can_employee_take_template(connection, employee, entry.position_id, entry.date, template, week_start):
        raise HTTPException(status_code=400, detail="Employee cannot be assigned to this shift")
    return employee, template


def validate_manual_schedule_entry_basics(connection, entry: ScheduleEntryCreate):
    parse_date_string(entry.date)
    cursor = connection.cursor()
    fetch_one_or_404(cursor, "SELECT id FROM employees WHERE id = ?", (entry.employee_id,), "Employee not found")
    fetch_one_or_404(cursor, "SELECT id FROM positions WHERE id = ?", (entry.position_id,), "Position not found")
    template_row = fetch_one_or_404(
        cursor,
        "SELECT * FROM shift_templates WHERE id = ? AND position_id = ?",
        (entry.shift_template_id, entry.position_id),
        "Shift template not found for this position",
    )
    app_settings = get_app_settings(connection)
    if not app_settings["allow_multiple_positions_per_day"]:
        cursor.execute(
            """
            SELECT 1
            FROM schedule_entries
            WHERE employee_id = ? AND date = ? AND position_id != ? AND no_show = 0
            LIMIT 1
            """,
            (entry.employee_id, entry.date, entry.position_id),
        )
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Employee already has a shift on another position this day")
    return row_to_shift_template_dict(template_row)


# =========================
# Pages
# =========================


@app.post("/api/auth/bootstrap", tags=["Auth"])
def bootstrap_first_owner(request_data: AuthBootstrapRequest, request: Request):
    if is_cloud_employee_portal_mode() and not is_trusted_desktop_cloud_request(request):
        raise HTTPException(status_code=404, detail="Organization setup is available only in the desktop app")
    connection = get_connection()
    try:
        cursor = connection.cursor()
        active_user_count = fetch_count(cursor, "SELECT COUNT(*) FROM users WHERE status = 'active'")
        if active_user_count:
            raise HTTPException(status_code=409, detail="Application already has an active user")

        email = str(request_data.email).strip().lower()
        now = current_utc_timestamp()
        cursor.execute(
            """
            UPDATE organizations
            SET name = ?, updated_at = ?
            WHERE id = 1
            """,
            (request_data.organization_name.strip(), now),
        )
        cursor.execute(
            """
            INSERT INTO users (email, full_name, password_hash, status, email_verified, created_at, updated_at)
            VALUES (?, ?, ?, 'active', 1, ?, ?)
            """,
            (email, request_data.full_name.strip(), hash_password(request_data.password), now, now),
        )
        user_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO organization_memberships (organization_id, user_id, role, status, created_at, updated_at)
            VALUES (1, ?, 'owner', 'active', ?, ?)
            """,
            (user_id, now, now),
        )
        write_auth_audit_event(cursor, "bootstrap_owner_created", user_id=user_id, organization_id=1)
        auth_response = build_auth_response(connection, user_id)
        connection.commit()
        return auth_response
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise HTTPException(status_code=409, detail="User already exists") from exc
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.post("/api/auth/login", tags=["Auth"])
def login(request_data: AuthLoginRequest, request: Request):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        identifier = normalize_login_identifier(request_data.email)
        if is_login_rate_limited(identifier, request):
            write_auth_audit_event(
                cursor,
                "login_rate_limited",
                metadata={"identifier": identifier, "ip": get_request_ip(request)},
            )
            connection.commit()
            raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")

        user_row = find_user_for_login(cursor, identifier)
        if not user_row or user_row["status"] != "active" or not verify_password(request_data.password, user_row["password_hash"]):
            user_id = user_row["id"] if user_row else None
            write_auth_audit_event(
                cursor,
                "login_failed",
                user_id=user_id,
                metadata={"identifier": identifier, "ip": get_request_ip(request)},
            )
            connection.commit()
            if record_login_failure(identifier, request):
                write_auth_audit_event_record(
                    "login_rate_limited",
                    user_id=user_id,
                    metadata={"identifier": identifier, "ip": get_request_ip(request)},
                )
                raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")
            raise HTTPException(status_code=401, detail="Invalid login or password")

        now = current_utc_timestamp()
        cursor.execute("UPDATE users SET last_login_at = ?, updated_at = ? WHERE id = ?", (now, now, user_row["id"]))
        write_auth_audit_event(cursor, "login_success", user_id=user_row["id"])
        auth_response = build_auth_response(connection, user_row["id"])
        if repair_employee_membership_links(cursor, auth_response["user"]):
            write_auth_audit_event(cursor, "employee_membership_link_repaired", user_id=user_row["id"])
            auth_response["user"] = get_user_context(cursor, user_row["id"])
        connection.commit()
        clear_login_failures(identifier, request)
        return auth_response
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.post("/api/auth/create-organization", tags=["Auth"])
def create_owner_organization(request_data: AuthOrganizationCreateRequest, request: Request):
    if is_cloud_employee_portal_mode() and not is_trusted_desktop_cloud_request(request):
        raise HTTPException(status_code=404, detail="Organization setup is available only in the desktop app")
    connection = get_connection()
    try:
        cursor = connection.cursor()
        email = str(request_data.email).strip().lower()
        now = current_utc_timestamp()
        cursor.execute("SELECT id, password_hash, status FROM users WHERE lower(email) = ?", (email,))
        user_row = cursor.fetchone()
        if user_row:
            if user_row["status"] != "active" or not verify_password(request_data.password, user_row["password_hash"]):
                raise HTTPException(status_code=401, detail="Existing account password is incorrect")
            user_id = int(user_row["id"])
            cursor.execute(
                "UPDATE users SET full_name = ?, updated_at = ? WHERE id = ?",
                (request_data.full_name.strip(), now, user_id),
            )
        else:
            cursor.execute(
                """
                INSERT INTO users (email, full_name, password_hash, status, email_verified, created_at, updated_at)
                VALUES (?, ?, ?, 'active', 1, ?, ?)
                """,
                (email, request_data.full_name.strip(), hash_password(request_data.password), now, now),
            )
            user_id = int(cursor.lastrowid)

        public_id = f"org_{secrets.token_hex(16)}"
        cursor.execute(
            """
            INSERT INTO organizations (public_id, name, status, created_at, updated_at)
            VALUES (?, ?, 'active', ?, ?)
            """,
            (public_id, request_data.organization_name.strip(), now, now),
        )
        organization_id = int(cursor.lastrowid)
        cursor.execute(
            """
            INSERT INTO organization_memberships (organization_id, user_id, role, status, created_at, updated_at)
            VALUES (?, ?, 'owner', 'active', ?, ?)
            """,
            (organization_id, user_id, now, now),
        )
        write_auth_audit_event(cursor, "organization_created", user_id=user_id, organization_id=organization_id)
        auth_response = build_auth_response(connection, user_id)
        connection.commit()
        return auth_response
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise HTTPException(status_code=409, detail="Organization or owner already exists") from exc
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


def import_cloud_session_to_desktop(cloud_base_url: str, cloud_session: dict) -> dict:
    cloud_token = cloud_session.get("access_token")
    cloud_user = cloud_session.get("user") or {}
    if not cloud_token or not cloud_user:
        raise HTTPException(status_code=502, detail="Cloud login response is incomplete")
    cloud_membership = select_desktop_cloud_membership(cloud_user)
    cloud_organization_id = int(cloud_membership["organization_id"])
    cloud_bundle = request_cloud_json(
        cloud_base_url,
        f"/api/organizations/{cloud_organization_id}/cloud-export",
        token=cloud_token,
    )

    connection = get_connection()
    try:
        cursor = connection.cursor()
        user_id = upsert_desktop_cloud_user(cursor, cloud_user, cloud_membership, 1)
        import_result = import_organization_bundle(
            connection,
            1,
            cloud_bundle,
            replace_existing=True,
            imported_by_user_id=user_id,
        )
        now = current_utc_timestamp()
        for key, value in {
            "cloud_api_base_url": cloud_base_url,
            "cloud_organization_id": str(cloud_organization_id),
            "cloud_organization_public_id": str(cloud_membership.get("organization_public_id") or cloud_bundle.get("organization", {}).get("public_id") or ""),
            "cloud_linked_at": now,
            "desktop_cloud_access_token": str(cloud_token),
            "desktop_cloud_last_pull_at": now,
            "desktop_cloud_last_pull_app_version": str(cloud_bundle.get("app_version") or ""),
        }.items():
            cursor.execute(
                """
                INSERT INTO app_settings (organization_id, key, value)
                VALUES (1, ?, ?)
                ON CONFLICT(key)
                DO UPDATE SET organization_id = excluded.organization_id,
                              value = excluded.value
                """,
                (key, value),
            )
        cursor.execute("DELETE FROM desktop_sync_outbox WHERE organization_id = 1")
        auth_response = build_auth_response(connection, user_id)
        connection.commit()
        return {
            **auth_response,
            "desktop_sync": {
                "cloud_api_base_url": cloud_base_url,
                "cloud_organization_id": cloud_organization_id,
                "cloud_organization_public_id": cloud_membership.get("organization_public_id") or cloud_bundle.get("organization", {}).get("public_id") or "",
                "last_pull_at": now,
                "imported": import_result.get("imported", {}),
            },
        }
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise HTTPException(status_code=409, detail=f"Desktop import conflict: {exc}") from exc
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.post("/api/desktop/cloud-login", tags=["Auth"])
def desktop_cloud_login(request_data: DesktopCloudLoginRequest):
    if not is_desktop_sqlite_runtime():
        raise HTTPException(status_code=404, detail="Desktop cloud login is available only in the installed SQLite app")

    cloud_base_url = get_desktop_cloud_login_base_url()
    cloud_session = request_cloud_json(
        cloud_base_url,
        "/api/auth/login",
        method="POST",
        payload={"email": str(request_data.email), "password": request_data.password},
    )
    return import_cloud_session_to_desktop(cloud_base_url, cloud_session)


@app.post("/api/desktop/cloud-create-organization", tags=["Auth"])
def desktop_cloud_create_organization(request_data: AuthOrganizationCreateRequest):
    if not is_desktop_sqlite_runtime():
        raise HTTPException(status_code=404, detail="Desktop organization setup is available only in the installed SQLite app")
    cloud_base_url = get_desktop_cloud_login_base_url()
    cloud_session = request_cloud_json(
        cloud_base_url,
        "/api/auth/create-organization",
        method="POST",
        payload=request_data.model_dump(mode="json"),
        extra_headers={"X-ShiftCare-Desktop-Client": "1"},
    )
    return import_cloud_session_to_desktop(cloud_base_url, cloud_session)


@app.get("/api/auth/me", tags=["Auth"])
def get_authenticated_user(current_user: dict = Depends(get_current_user)):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        if repair_employee_membership_links(cursor, current_user):
            write_auth_audit_event(cursor, "employee_membership_link_repaired", user_id=current_user["id"])
            connection.commit()
            return {"user": get_user_context(cursor, current_user["id"])}
        return {"user": current_user}
    finally:
        connection.close()


@app.get("/api/desktop/sync/status", tags=["Auth"])
def desktop_sync_status(current_user: dict = Depends(get_current_user)):
    if not is_desktop_sqlite_runtime():
        raise HTTPException(status_code=404, detail="Desktop sync status is available only in the installed SQLite app")
    connection = get_connection()
    try:
        cursor = connection.cursor()
        membership = find_any_membership_with_role(current_user, DESKTOP_CLOUD_SYNC_ROLES)
        if not membership:
            raise HTTPException(status_code=403, detail="Desktop scheduling permissions are required")
        organization_id = int(membership["organization_id"])
        settings = read_organization_cloud_link_settings(cursor, organization_id)
        cursor.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM desktop_sync_outbox
            WHERE organization_id = ?
            GROUP BY status
            """,
            (organization_id,),
        )
        queue_counts = {row["status"]: row["count"] for row in cursor.fetchall()}
        cursor.execute(
            """
            SELECT value
            FROM app_settings
            WHERE organization_id = ? AND key = 'desktop_cloud_last_pull_at'
            """,
            (organization_id,),
        )
        last_pull_row = cursor.fetchone()
        return {
            "linked": organization_has_cloud_link(settings),
            "cloud_api_base_url": settings.get("cloud_api_base_url") or "",
            "cloud_organization_id": int(settings["cloud_organization_id"]) if settings.get("cloud_organization_id") else None,
            "cloud_organization_public_id": settings.get("cloud_organization_public_id") or "",
            "last_pull_at": last_pull_row["value"] if last_pull_row else "",
            "queue": {
                "pending": int(queue_counts.get("pending", 0)),
                "syncing": int(queue_counts.get("syncing", 0)),
                "failed": int(queue_counts.get("failed", 0)),
                "synced": int(queue_counts.get("synced", 0)),
            },
        }
    finally:
        connection.close()


def should_start_desktop_sync_worker() -> bool:
    if os.environ.get("SCHEDULE_APP_DISABLE_BACKGROUND_SYNC", "").strip().lower() in TRUTHY_ENV_VALUES:
        return False
    return is_desktop_sqlite_runtime() and (
        getattr(sys, "frozen", False)
        or os.environ.get("SCHEDULE_APP_ENABLE_BACKGROUND_SYNC", "").strip().lower() in TRUTHY_ENV_VALUES
    )


def run_desktop_sync_once() -> bool:
    if not is_desktop_sqlite_runtime():
        return False

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) AS count
            FROM desktop_sync_outbox
            WHERE status IN ('pending', 'failed')
              AND (next_attempt_at IS NULL OR next_attempt_at <= ?)
            """,
            (current_utc_timestamp(),),
        )
        pending_count = int(cursor.fetchone()["count"])
        if pending_count <= 0:
            return False

        cursor.execute(
            """
            SELECT key, value
            FROM app_settings
            WHERE organization_id = 1
              AND key IN ('cloud_api_base_url', 'cloud_organization_id', 'desktop_cloud_access_token')
            """
        )
        settings = {row["key"]: row["value"] for row in cursor.fetchall()}
        cloud_base_url = settings.get("cloud_api_base_url") or get_desktop_cloud_login_base_url()
        cloud_organization_id = settings.get("cloud_organization_id")
        cloud_token = settings.get("desktop_cloud_access_token")
        if not cloud_organization_id or not cloud_token:
            return False

        sync_cloud_preferences_to_desktop(connection, settings)

        cursor.execute(
            """
            UPDATE desktop_sync_outbox
            SET status = 'syncing', attempts = attempts + 1, updated_at = ?
            WHERE organization_id = 1 AND status IN ('pending', 'failed')
            """,
            (current_utc_timestamp(),),
        )
        connection.commit()

        bundle = build_organization_export_bundle(connection, 1)
        request_cloud_json(
            cloud_base_url,
            f"/api/organizations/{int(cloud_organization_id)}/cloud-import",
            method="POST",
            payload={"bundle": bundle, "replace_existing": True},
            token=cloud_token,
        )

        now = current_utc_timestamp()
        cursor.execute(
            """
            UPDATE desktop_sync_outbox
            SET status = 'synced', updated_at = ?, synced_at = ?, last_error = NULL
            WHERE organization_id = 1 AND status = 'syncing'
            """,
            (now, now),
        )
        cursor.execute(
            """
            INSERT INTO app_settings (organization_id, key, value)
            VALUES (1, 'desktop_cloud_last_push_at', ?)
            ON CONFLICT(key)
            DO UPDATE SET organization_id = excluded.organization_id,
                          value = excluded.value
            """,
            (now,),
        )
        connection.commit()
        return True
    except Exception as exc:
        connection.rollback()
        try:
            cursor = connection.cursor()
            now = current_utc_timestamp()
            next_attempt = (datetime.now(UTC) + timedelta(minutes=2)).replace(tzinfo=None).isoformat(timespec="seconds")
            cursor.execute(
                """
                UPDATE desktop_sync_outbox
                SET status = 'failed', updated_at = ?, last_error = ?, next_attempt_at = ?
                WHERE organization_id = 1 AND status = 'syncing'
                """,
                (now, str(exc)[:500], next_attempt),
            )
            cursor.execute(
                """
                INSERT INTO app_settings (organization_id, key, value)
                VALUES (1, 'desktop_cloud_last_push_error', ?)
                ON CONFLICT(key)
                DO UPDATE SET organization_id = excluded.organization_id,
                              value = excluded.value
                """,
                (str(exc)[:500],),
            )
            connection.commit()
        except Exception:
            connection.rollback()
        return False
    finally:
        connection.close()


def desktop_sync_worker_loop() -> None:
    while True:
        sleep(20)
        run_desktop_sync_once()


_DESKTOP_SYNC_WORKER_STARTED = False


@app.on_event("startup")
def start_desktop_sync_worker():
    global _DESKTOP_SYNC_WORKER_STARTED
    if _DESKTOP_SYNC_WORKER_STARTED or not should_start_desktop_sync_worker():
        return
    _DESKTOP_SYNC_WORKER_STARTED = True
    threading.Thread(target=desktop_sync_worker_loop, name="shiftcare-desktop-sync", daemon=True).start()


@app.get("/api/auth/status", tags=["Auth"])
def auth_status():
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) AS user_count FROM users WHERE status = 'active'")
        user_count = cursor.fetchone()["user_count"]
        cursor.execute("SELECT COUNT(*) AS organization_count FROM organizations WHERE status = 'active'")
        organization_count = cursor.fetchone()["organization_count"]
        return {
            "app_version": APP_VERSION,
            "bootstrap_available": user_count == 0,
            "active_user_count": user_count,
            "active_organization_count": organization_count,
            "environment": get_app_config().app_env,
        }
    finally:
        connection.close()


@app.put("/api/auth/profile", tags=["Auth"])
def update_authenticated_profile(
    request_data: AuthProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        now = current_utc_timestamp()
        full_name = request_data.full_name.strip()
        cursor.execute(
            """
            UPDATE users
            SET full_name = ?, updated_at = ?
            WHERE id = ? AND status = 'active'
            """,
            (full_name, now, current_user["id"]),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")
        write_auth_audit_event(cursor, "profile_updated", user_id=current_user["id"])
        updated_user = get_user_context(cursor, current_user["id"])
        connection.commit()
        return {"user": updated_user}
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


def sync_cloud_preferences_to_desktop(connection, settings: dict[str, str]) -> bool:
    cloud_base_url = settings.get("cloud_api_base_url") or get_desktop_cloud_login_base_url()
    cloud_organization_id = settings.get("cloud_organization_id")
    cloud_token = settings.get("desktop_cloud_access_token")
    if not cloud_organization_id or not cloud_token:
        return False

    cloud_bundle = request_cloud_json(
        cloud_base_url,
        f"/api/organizations/{int(cloud_organization_id)}/cloud-export",
        token=cloud_token,
    )
    records = cloud_bundle.get("records") or {}
    cloud_employees = records.get("employees") or []
    cloud_employee_public_ids = {
        int(row["id"]): str(row.get("public_id") or "")
        for row in cloud_employees
        if row.get("id") is not None and row.get("public_id")
    }
    cursor = connection.cursor()
    cursor.execute("SELECT id, public_id FROM employees WHERE organization_id = 1")
    local_employee_ids = {str(row["public_id"]): int(row["id"]) for row in cursor.fetchall() if row["public_id"]}
    now = current_utc_timestamp()

    cursor.execute("DELETE FROM employee_preferences WHERE organization_id = 1")
    for row in records.get("employee_preferences") or []:
        public_id = cloud_employee_public_ids.get(int(row["employee_id"])) if row.get("employee_id") is not None else None
        local_employee_id = local_employee_ids.get(str(public_id))
        if not local_employee_id:
            continue
        cursor.execute(
            """
            INSERT INTO employee_preferences (
                organization_id, public_id, employee_id, allow_morning, allow_evening, allow_night,
                allow_morning_evening_combo, created_at, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                row.get("public_id"),
                local_employee_id,
                int(row.get("allow_morning") or 0),
                int(row.get("allow_evening") or 0),
                int(row.get("allow_night") or 0),
                int(row.get("allow_morning_evening_combo") or 0),
                row.get("created_at") or now,
                row.get("updated_at") or now,
                None,
            ),
        )

    cursor.execute("DELETE FROM employee_week_preferences WHERE organization_id = 1")
    for row in records.get("employee_week_preferences") or []:
        public_id = cloud_employee_public_ids.get(int(row["employee_id"])) if row.get("employee_id") is not None else None
        local_employee_id = local_employee_ids.get(str(public_id))
        if not local_employee_id:
            continue
        cursor.execute(
            """
            INSERT INTO employee_week_preferences (
                organization_id, public_id, employee_id, week_start_date, preference_date,
                preference_type, created_at, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                row.get("public_id"),
                local_employee_id,
                row.get("week_start_date"),
                row.get("preference_date"),
                row.get("preference_type"),
                row.get("created_at") or now,
                row.get("updated_at") or now,
                None,
            ),
        )

    cursor.execute("DELETE FROM employee_recurring_preferences WHERE organization_id = 1")
    for row in records.get("employee_recurring_preferences") or []:
        public_id = cloud_employee_public_ids.get(int(row["employee_id"])) if row.get("employee_id") is not None else None
        local_employee_id = local_employee_ids.get(str(public_id))
        if not local_employee_id:
            continue
        cursor.execute(
            """
            INSERT INTO employee_recurring_preferences (
                organization_id, public_id, employee_id, preference_kind, day_of_week,
                preference_type, created_at, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                row.get("public_id"),
                local_employee_id,
                row.get("preference_kind"),
                int(row.get("day_of_week") or 0),
                row.get("preference_type"),
                row.get("created_at") or now,
                row.get("updated_at") or now,
                None,
            ),
        )
    cursor.execute(
        """
        INSERT INTO app_settings (organization_id, key, value)
        VALUES (1, 'desktop_cloud_last_pull_at', ?)
        ON CONFLICT(key)
        DO UPDATE SET organization_id = excluded.organization_id,
                      value = excluded.value
        """,
        (now,),
    )
    return True


def pull_cloud_preferences_for_desktop_generation(connection) -> None:
    if not is_desktop_sqlite_runtime():
        return
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM desktop_sync_outbox
        WHERE organization_id = 1
          AND entity_type IN (
              'employee_preferences',
              'employee_week_preferences',
              'employee_recurring_preferences',
              'employee_day_statuses'
          )
          AND status IN ('pending', 'failed', 'syncing')
        """
    )
    if int(cursor.fetchone()["count"] or 0) > 0:
        return
    cursor.execute(
        """
        SELECT key, value
        FROM app_settings
        WHERE organization_id = 1
          AND key IN ('cloud_api_base_url', 'cloud_organization_id', 'desktop_cloud_access_token')
        """
    )
    settings = {row["key"]: row["value"] for row in cursor.fetchall()}
    if desktop_cloud_sync_is_ready(settings):
        sync_cloud_preferences_to_desktop(connection, settings)


@app.post("/api/auth/change-password", tags=["Auth"])
def change_authenticated_password(
    request_data: AuthPasswordChangeRequest,
    authorization: str | None = Header(default=None),
    current_user: dict = Depends(get_current_user),
):
    token = authorization.split(" ", 1)[1].strip() if authorization else ""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE id = ?", (current_user["id"],))
        user_row = cursor.fetchone()
        if not user_row or not verify_password(request_data.current_password, user_row["password_hash"]):
            raise HTTPException(status_code=401, detail="Current password is incorrect")

        now = current_utc_timestamp()
        cursor.execute(
            """
            UPDATE users
            SET password_hash = ?, updated_at = ?
            WHERE id = ?
            """,
            (hash_password(request_data.new_password), now, current_user["id"]),
        )
        cursor.execute(
            """
            UPDATE auth_sessions
            SET revoked_at = ?
            WHERE user_id = ?
              AND token_hash != ?
              AND revoked_at IS NULL
            """,
            (now, current_user["id"], hash_session_token(token)),
        )
        write_auth_audit_event(cursor, "password_changed", user_id=current_user["id"])
        connection.commit()
        return {"message": "Password changed successfully"}
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.post("/api/auth/request-password-reset", tags=["Auth"])
def request_password_reset(request_data: AuthPasswordResetRequest, request: Request):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        email = str(request_data.email).strip().lower()
        cursor.execute("SELECT id, status FROM users WHERE lower(email) = ?", (email,))
        user_row = cursor.fetchone()
        reset_token = None
        if user_row and user_row["status"] == "active":
            reset_token = secrets.token_urlsafe(32)
            cursor.execute(
                """
                INSERT INTO auth_password_reset_tokens (user_id, token_hash, expires_at)
                VALUES (?, ?, ?)
                """,
                (user_row["id"], hash_session_token(reset_token), token_expiration(days=1)),
            )
            write_auth_audit_event(
                cursor,
                "password_reset_requested",
                user_id=user_row["id"],
                metadata={"email": email, "ip": get_request_ip(request)},
            )
        connection.commit()
        return {
            "message": "If the account exists, password reset instructions were created.",
            "reset_token": reset_token,
        }
    finally:
        connection.close()


@app.post("/api/auth/reset-password", tags=["Auth"])
def reset_password(request_data: AuthPasswordResetConfirmRequest):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        now = current_utc_timestamp()
        cursor.execute(
            """
            SELECT id, user_id
            FROM auth_password_reset_tokens
            WHERE token_hash = ?
              AND used_at IS NULL
              AND expires_at > ?
            """,
            (hash_session_token(request_data.token), now),
        )
        token_row = cursor.fetchone()
        if not token_row:
            raise HTTPException(status_code=404, detail="Password reset token not found or expired")

        cursor.execute(
            "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
            (hash_password(request_data.new_password), now, token_row["user_id"]),
        )
        cursor.execute(
            "UPDATE auth_password_reset_tokens SET used_at = ? WHERE id = ?",
            (now, token_row["id"]),
        )
        cursor.execute(
            "UPDATE auth_sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
            (now, token_row["user_id"]),
        )
        write_auth_audit_event(cursor, "password_reset_completed", user_id=token_row["user_id"])
        connection.commit()
        return {"message": "Password reset successfully"}
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.post("/api/auth/request-email-verification", tags=["Auth"])
def request_email_verification(current_user: dict = Depends(get_current_user)):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        verification_token = secrets.token_urlsafe(32)
        cursor.execute(
            """
            INSERT INTO auth_email_verification_tokens (user_id, token_hash, expires_at)
            VALUES (?, ?, ?)
            """,
            (current_user["id"], hash_session_token(verification_token), token_expiration(days=7)),
        )
        write_auth_audit_event(cursor, "email_verification_requested", user_id=current_user["id"])
        connection.commit()
        return {
            "message": "Email verification token created.",
            "verification_token": verification_token,
        }
    finally:
        connection.close()


@app.post("/api/auth/verify-email", tags=["Auth"])
def verify_email(request_data: AuthEmailVerificationRequest):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        now = current_utc_timestamp()
        cursor.execute(
            """
            SELECT id, user_id
            FROM auth_email_verification_tokens
            WHERE token_hash = ?
              AND used_at IS NULL
              AND expires_at > ?
            """,
            (hash_session_token(request_data.token), now),
        )
        token_row = cursor.fetchone()
        if not token_row:
            raise HTTPException(status_code=404, detail="Email verification token not found or expired")
        cursor.execute(
            "UPDATE users SET email_verified = 1, updated_at = ? WHERE id = ?",
            (now, token_row["user_id"]),
        )
        cursor.execute(
            "UPDATE auth_email_verification_tokens SET used_at = ? WHERE id = ?",
            (now, token_row["id"]),
        )
        write_auth_audit_event(cursor, "email_verified", user_id=token_row["user_id"])
        connection.commit()
        return {"message": "Email verified successfully"}
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.post("/api/auth/accept-invitation", tags=["Auth"])
def accept_invitation(request_data: AuthInvitationAcceptRequest):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        now = current_utc_timestamp()
        token_hash = hash_session_token(request_data.token)
        cursor.execute(
            """
            SELECT oi.id, oi.organization_id, oi.email, oi.role, oi.employee_id,
                   e.full_name AS employee_name
            FROM organization_invitations oi
            LEFT JOIN employees e ON e.id = oi.employee_id
            WHERE token_hash = ?
              AND oi.status = 'pending'
              AND oi.expires_at > ?
            """,
            (token_hash, now),
        )
        invitation = cursor.fetchone()
        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found or expired")
        full_name = (invitation["employee_name"] or request_data.full_name or "").strip()
        if not full_name:
            raise HTTPException(status_code=400, detail="Invitation is not linked to an employee name")

        cursor.execute(
            "SELECT id, password_hash, status FROM users WHERE lower(email) = ?",
            (invitation["email"].lower(),),
        )
        existing_user = cursor.fetchone()
        if existing_user:
            if existing_user["status"] != "active":
                raise HTTPException(status_code=409, detail="Existing user account is disabled")
            if existing_user["password_hash"] and not verify_password(request_data.password, existing_user["password_hash"]):
                raise HTTPException(status_code=401, detail="Account already exists. Enter the existing account password to accept this invitation.")
            user_id = int(existing_user["id"])
            cursor.execute(
                "UPDATE users SET full_name = ?, updated_at = ? WHERE id = ?",
                (full_name, now, user_id),
            )
        else:
            cursor.execute(
                """
                INSERT INTO users (email, full_name, password_hash, status, email_verified, created_at, updated_at)
                VALUES (?, ?, ?, 'active', 0, ?, ?)
                """,
                (
                    invitation["email"].lower(),
                    full_name,
                    hash_password(request_data.password),
                    now,
                    now,
                ),
            )
            user_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO organization_memberships (organization_id, user_id, role, status, employee_id, created_at, updated_at)
            VALUES (?, ?, ?, 'active', ?, ?, ?)
            ON CONFLICT(organization_id, user_id)
            DO UPDATE SET role = excluded.role,
                          status = 'active',
                          employee_id = excluded.employee_id,
                          updated_at = excluded.updated_at
            """,
            (
                invitation["organization_id"],
                user_id,
                invitation["role"],
                invitation["employee_id"],
                now,
                now,
            ),
        )
        cursor.execute(
            """
            UPDATE organization_invitations
            SET status = 'accepted', accepted_at = ?
            WHERE id = ?
            """,
            (now, invitation["id"]),
        )
        write_auth_audit_event(
            cursor,
            "invitation_accepted",
            user_id=user_id,
            organization_id=invitation["organization_id"],
            metadata={
                "invitation_id": invitation["id"],
                "role": invitation["role"],
                "employee_id": invitation["employee_id"],
            },
        )
        auth_response = build_auth_response(connection, user_id)
        connection.commit()
        return auth_response
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.get("/api/auth/invitation-preview", tags=["Auth"])
def get_invitation_preview(token: str):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT oi.email, oi.role, oi.employee_id, oi.expires_at,
                   e.full_name AS employee_name,
                   o.name AS organization_name
            FROM organization_invitations oi
            JOIN organizations o ON o.id = oi.organization_id
            LEFT JOIN employees e ON e.id = oi.employee_id
            WHERE oi.token_hash = ?
              AND oi.status = 'pending'
              AND oi.expires_at > ?
            """,
            (hash_session_token(token), current_utc_timestamp()),
        )
        invitation = cursor.fetchone()
        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found or expired")
        return {
            "email": invitation["email"],
            "role": invitation["role"],
            "employee_id": invitation["employee_id"],
            "employee_name": invitation["employee_name"] or "",
            "organization_name": invitation["organization_name"],
            "expires_at": invitation["expires_at"],
            "requires_name": not bool(invitation["employee_name"]),
        }
    finally:
        connection.close()


@app.post("/api/auth/logout", tags=["Auth"])
def logout(authorization: str | None = Header(default=None), current_user: dict = Depends(get_current_user)):
    token = authorization.split(" ", 1)[1].strip() if authorization else ""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        now = current_utc_timestamp()
        cursor.execute(
            """
            UPDATE auth_sessions
            SET revoked_at = ?
            WHERE token_hash = ? AND revoked_at IS NULL
            """,
            (now, hash_session_token(token)),
        )
        write_auth_audit_event(cursor, "logout", user_id=current_user["id"])
        connection.commit()
        return {"message": "Logged out successfully"}
    finally:
        connection.close()


@app.get("/api/organizations", tags=["Auth"])
def get_user_organizations(current_user: dict = Depends(get_current_user)):
    return {"organizations": current_user["memberships"]}


@app.get("/api/support/accounts", tags=["Support"])
def get_support_accounts(_support: dict = Depends(require_developer_support_access)):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT o.id, o.public_id, o.name, o.status, o.created_at, o.updated_at,
                   COUNT(DISTINCT om.user_id) AS member_count,
                   COUNT(DISTINCT e.id) AS employee_count
            FROM organizations o
            LEFT JOIN organization_memberships om
                ON om.organization_id = o.id AND om.status = 'active'
            LEFT JOIN employees e
                ON 1 = 1
            GROUP BY o.id, o.public_id, o.name, o.status, o.created_at, o.updated_at
            ORDER BY o.id
            """
        )
        organizations = [dict(row) for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT u.id AS user_id, u.email, u.full_name, u.status AS user_status,
                   u.email_verified, u.created_at, u.updated_at, u.last_login_at,
                   o.id AS organization_id, o.name AS organization_name,
                   om.role, om.status AS membership_status, om.employee_id,
                   e.full_name AS employee_name
            FROM users u
            LEFT JOIN organization_memberships om ON om.user_id = u.id
            LEFT JOIN organizations o ON o.id = om.organization_id
            LEFT JOIN employees e ON e.id = om.employee_id
            ORDER BY o.id, u.full_name, u.email
            """
        )
        accounts = [
            {
                "user_id": row["user_id"],
                "email": row["email"],
                "full_name": row["full_name"],
                "user_status": row["user_status"],
                "email_verified": bool(row["email_verified"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "last_login_at": row["last_login_at"],
                "organization_id": row["organization_id"],
                "organization_name": row["organization_name"],
                "role": row["role"],
                "membership_status": row["membership_status"],
                "employee_id": row["employee_id"],
                "employee_name": row["employee_name"],
            }
            for row in cursor.fetchall()
        ]

        cursor.execute(
            """
            SELECT id, full_name, sex, min_shifts_per_week, target_shifts_per_week, max_shifts_per_week
            FROM employees
            ORDER BY full_name, id
            """
        )
        employees = [dict(row) for row in cursor.fetchall()]
        return {
            "developer_mode": True,
            "organizations": organizations,
            "accounts": accounts,
            "employees": employees,
        }
    finally:
        connection.close()


@app.get("/api/organizations/{organization_id}/members", tags=["Auth"])
def get_organization_members(organization_id: int, current_user: dict = Depends(get_current_user)):
    require_organization_role(current_user, organization_id, {"owner", "admin", "scheduler", "manager"})
    connection = get_connection()
    try:
        cursor = connection.cursor()
        if is_desktop_sqlite_runtime():
            settings = read_desktop_cloud_sync_settings(cursor, organization_id)
            if desktop_cloud_sync_is_ready(settings):
                return request_cloud_json(
                    settings["cloud_api_base_url"],
                    f"/api/organizations/{int(settings['cloud_organization_id'])}/members",
                    token=settings["desktop_cloud_access_token"],
                )
        repaired_count = repair_organization_employee_membership_links(cursor, organization_id)
        if repaired_count:
            write_auth_audit_event(
                cursor,
                "organization_employee_membership_links_repaired",
                user_id=current_user["id"],
                organization_id=organization_id,
                metadata={"repaired_count": repaired_count},
            )
            connection.commit()
        cursor.execute(
            """
            SELECT u.id, u.email, u.full_name, u.status AS user_status, u.email_verified,
                   e.full_name AS employee_name,
                   e.public_id AS employee_public_id,
                   om.role, om.status AS membership_status, om.employee_id, om.created_at, om.updated_at
            FROM organization_memberships om
            JOIN users u ON u.id = om.user_id
            LEFT JOIN employees e ON e.id = om.employee_id
            WHERE om.organization_id = ?
            ORDER BY CASE om.status WHEN 'active' THEN 0 WHEN 'invited' THEN 1 ELSE 2 END, u.full_name, u.email
            """,
            (organization_id,),
        )
        return {
            "members": [
                {
                    "user_id": row["id"],
                    "email": row["email"],
                    "full_name": row["full_name"],
                    "user_status": row["user_status"],
                    "email_verified": bool(row["email_verified"]),
                    "role": row["role"],
                    "membership_status": row["membership_status"],
                    "employee_id": row["employee_id"],
                    "employee_public_id": row["employee_public_id"],
                    "employee_name": row["employee_name"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                for row in cursor.fetchall()
            ]
        }
    finally:
        connection.close()


@app.get("/api/organizations/{organization_id}/invitations", tags=["Auth"])
def get_organization_invitations(organization_id: int, current_user: dict = Depends(get_current_user)):
    require_organization_role(current_user, organization_id, {"owner", "admin"})
    connection = get_connection()
    try:
        cursor = connection.cursor()
        if is_desktop_sqlite_runtime():
            settings = read_desktop_cloud_sync_settings(cursor, organization_id)
            if desktop_cloud_sync_is_ready(settings):
                return request_cloud_json(
                    settings["cloud_api_base_url"],
                    f"/api/organizations/{int(settings['cloud_organization_id'])}/invitations",
                    token=settings["desktop_cloud_access_token"],
                )
        cursor.execute(
            """
            SELECT oi.id, oi.email, oi.employee_id,
                   e.public_id AS employee_public_id,
                   e.full_name AS employee_name,
                   oi.role, oi.status, oi.expires_at, oi.accepted_at,
                   oi.created_by_user_id, oi.created_at
            FROM organization_invitations oi
            LEFT JOIN employees e ON e.id = oi.employee_id
            WHERE oi.organization_id = ?
            ORDER BY oi.created_at DESC
            """,
            (organization_id,),
        )
        return {"invitations": [dict(row) for row in cursor.fetchall()]}
    finally:
        connection.close()


@app.get("/api/organizations/{organization_id}/cloud-export", tags=["Auth"])
def export_organization_for_cloud(organization_id: int, current_user: dict = Depends(get_current_user)):
    require_organization_role(current_user, organization_id, DESKTOP_CLOUD_SYNC_ROLES)
    connection = get_connection()
    try:
        return build_organization_export_bundle(connection, organization_id, exported_by_user_id=current_user["id"])
    finally:
        connection.close()


@app.post("/api/organizations/{organization_id}/cloud-import", tags=["Auth"])
def import_organization_from_cloud_bundle(
    organization_id: int,
    request_data: CloudOrganizationImportRequest,
    current_user: dict = Depends(get_current_user),
):
    require_organization_role(current_user, organization_id, {"owner", "admin"})
    connection = get_connection()
    try:
        backup_name = create_recovery_backup("cloud_import")
        result = import_organization_bundle(
            connection,
            organization_id,
            request_data.bundle,
            request_data.replace_existing,
            imported_by_user_id=current_user["id"],
        )
        connection.commit()
        return {"message": "Organization imported successfully", "backup_name": backup_name, **result}
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise HTTPException(status_code=409, detail=f"Organization import conflict: {exc}") from exc
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.post("/api/organizations/{organization_id}/cloud-link", tags=["Auth"])
def save_organization_cloud_link(
    organization_id: int,
    request_data: CloudOrganizationLinkRequest,
    current_user: dict = Depends(get_current_user),
):
    require_organization_role(current_user, organization_id, {"owner", "admin"})
    cloud_base_url = normalize_public_app_base_url(request_data.cloud_api_base_url)
    if not cloud_base_url:
        raise HTTPException(status_code=400, detail="Invalid Cloud API base URL")
    linked_at = request_data.linked_at or current_utc_timestamp()
    connection = get_connection()
    try:
        cursor = connection.cursor()
        fetch_one_or_404(cursor, "SELECT id FROM organizations WHERE id = ?", (organization_id,), "Organization not found")
        for key, value in {
            "cloud_api_base_url": cloud_base_url,
            "cloud_organization_id": str(request_data.cloud_organization_id),
            "cloud_organization_public_id": request_data.cloud_organization_public_id,
            "cloud_linked_at": linked_at,
        }.items():
            cursor.execute(
                """
                INSERT OR REPLACE INTO app_settings (organization_id, key, value)
                VALUES (?, ?, ?)
                """,
                (organization_id, key, value),
            )
        write_auth_audit_event(
            cursor,
            "organization_cloud_linked",
            user_id=current_user["id"],
            organization_id=organization_id,
            metadata={
                "cloud_api_base_url": cloud_base_url,
                "cloud_organization_id": request_data.cloud_organization_id,
                "cloud_organization_public_id": request_data.cloud_organization_public_id,
            },
        )
        connection.commit()
        return {
            "message": "Cloud link saved",
            "cloud_api_base_url": cloud_base_url,
            "cloud_organization_id": request_data.cloud_organization_id,
            "cloud_organization_public_id": request_data.cloud_organization_public_id,
            "linked_at": linked_at,
        }
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.get("/api/organizations/{organization_id}/cloud-link", tags=["Auth"])
def get_organization_cloud_link(organization_id: int, current_user: dict = Depends(get_current_user)):
    require_organization_role(current_user, organization_id, {"owner", "admin", "scheduler", "manager"})
    connection = get_connection()
    try:
        cursor = connection.cursor()
        fetch_one_or_404(cursor, "SELECT id FROM organizations WHERE id = ?", (organization_id,), "Organization not found")
        settings = read_organization_cloud_link_settings(cursor, organization_id)
        cloud_organization_id = settings.get("cloud_organization_id")
        return {
            "linked": organization_has_cloud_link(settings),
            "cloud_api_base_url": settings.get("cloud_api_base_url") or "",
            "cloud_organization_id": int(cloud_organization_id) if cloud_organization_id else None,
            "cloud_organization_public_id": settings.get("cloud_organization_public_id") or "",
            "linked_at": settings.get("cloud_linked_at") or "",
        }
    finally:
        connection.close()


@app.delete("/api/organizations/{organization_id}/cloud-link", tags=["Auth"])
def delete_organization_cloud_link(organization_id: int, current_user: dict = Depends(get_current_user)):
    require_organization_role(current_user, organization_id, {"owner", "admin"})
    connection = get_connection()
    try:
        cursor = connection.cursor()
        fetch_one_or_404(cursor, "SELECT id FROM organizations WHERE id = ?", (organization_id,), "Organization not found")
        cursor.execute(
            """
            DELETE FROM app_settings
            WHERE organization_id = ?
              AND key IN (
                  'cloud_api_base_url',
                  'cloud_organization_id',
                  'cloud_organization_public_id',
                  'cloud_linked_at'
              )
            """,
            (organization_id,),
        )
        write_auth_audit_event(
            cursor,
            "organization_cloud_unlinked",
            user_id=current_user["id"],
            organization_id=organization_id,
        )
        connection.commit()
        return {"message": "Cloud link removed"}
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.post("/api/organizations/{organization_id}/invitations", tags=["Auth"])
def create_organization_invitation(
    organization_id: int,
    request_data: OrganizationInvitationCreate,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    require_organization_role(current_user, organization_id, {"owner", "admin"})
    connection = get_connection()
    try:
        cursor = connection.cursor()
        fetch_one_or_404(cursor, "SELECT id FROM organizations WHERE id = ?", (organization_id,), "Organization not found")
        email = str(request_data.email).strip().lower()
        cursor.execute(
            """
            SELECT om.status, om.role, om.employee_id
            FROM organization_memberships om
            JOIN users u ON u.id = om.user_id
            WHERE om.organization_id = ? AND lower(u.email) = ?
            """,
            (organization_id, email),
        )
        existing_membership = cursor.fetchone()
        if existing_membership and existing_membership["status"] == "active":
            raise HTTPException(status_code=409, detail="User is already a member of this organization")

        employee_id = request_data.employee_id
        employee_public_id = request_data.employee_public_id
        if employee_id is None and employee_public_id:
            cursor.execute(
                """
                SELECT id
                FROM employees
                WHERE public_id = ? AND organization_id = ?
                """,
                (employee_public_id, organization_id),
            )
            employee_row = cursor.fetchone()
            if not employee_row:
                raise HTTPException(status_code=404, detail="Employee not found in this organization")
            employee_id = int(employee_row["id"])
        if request_data.role == "employee" and employee_id is None:
            raise HTTPException(status_code=400, detail="Employee invitations must be linked to an employee")
        if employee_id is not None:
            if request_data.role != "employee":
                raise HTTPException(status_code=400, detail="Employee link is only available for employee invitations")
            cursor.execute(
                """
                SELECT id, public_id
                FROM employees
                WHERE id = ? AND organization_id = ?
                """,
                (employee_id, organization_id),
            )
            employee_row = cursor.fetchone()
            if not employee_row:
                raise HTTPException(status_code=404, detail="Employee not found in this organization")
            employee_public_id = employee_row["public_id"]
            cursor.execute(
                """
                SELECT 1
                FROM organization_memberships
                WHERE organization_id = ?
                  AND employee_id = ?
                  AND status = 'active'
                """,
                (organization_id, employee_id),
            )
            if cursor.fetchone():
                raise HTTPException(status_code=409, detail="Employee is already linked to an active user")
            cursor.execute(
                """
                SELECT 1
                FROM organization_invitations
                WHERE organization_id = ? AND employee_id = ? AND status = 'pending'
                """,
                (organization_id, employee_id),
            )
            if cursor.fetchone():
                raise HTTPException(status_code=409, detail="Employee already has a pending invitation")

        cursor.execute(
            """
            SELECT 1
            FROM organization_invitations
            WHERE organization_id = ?
              AND lower(email) = ?
              AND status = 'pending'
            """,
            (organization_id, email),
        )
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail="User already has a pending invitation")

        if is_desktop_sqlite_runtime() and is_desktop_invitation_request(request):
            settings = read_desktop_cloud_sync_settings(cursor, organization_id)
            if desktop_cloud_sync_is_ready(settings):
                cloud_payload = {
                    "email": email,
                    "employee_public_id": employee_public_id,
                    "role": request_data.role,
                    "expires_in_days": request_data.expires_in_days,
                }
                cloud_response = request_cloud_json(
                    settings["cloud_api_base_url"],
                    f"/api/organizations/{int(settings['cloud_organization_id'])}/invitations",
                    method="POST",
                    payload=cloud_payload,
                    token=settings["desktop_cloud_access_token"],
                )
                cloud_invitation = cloud_response.get("invitation") or {}
                cloud_token = cloud_response.get("invitation_token") or secrets.token_urlsafe(32)
                now = current_utc_timestamp()
                expires_at = cloud_invitation.get("expires_at") or (
                    datetime.now(UTC) + timedelta(days=request_data.expires_in_days)
                ).replace(tzinfo=None).isoformat(timespec="seconds")
                cursor.execute(
                    """
                    INSERT INTO organization_invitations (
                        organization_id, email, employee_id, role, token_hash, status, expires_at, created_by_user_id, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?)
                    """,
                    (
                        organization_id,
                        email,
                        employee_id,
                        request_data.role,
                        hash_session_token(cloud_token),
                        expires_at,
                        current_user["id"],
                        now,
                    ),
                )
                local_invitation_id = cursor.lastrowid
                write_auth_audit_event(
                    cursor,
                    "invitation_created_via_cloud",
                    user_id=current_user["id"],
                    organization_id=organization_id,
                    metadata={
                        "invitation_id": local_invitation_id,
                        "cloud_invitation_id": cloud_invitation.get("id"),
                        "email": email,
                        "employee_id": employee_id,
                    },
                )
                connection.commit()
                return {
                    "invitation": {
                        "id": local_invitation_id,
                        "organization_id": organization_id,
                        "email": email,
                        "employee_id": employee_id,
                        "role": request_data.role,
                        "status": "pending",
                        "expires_at": expires_at,
                    },
                    "invitation_token": cloud_token,
                    "invitation_url": cloud_response.get("invitation_url") or build_invitation_url_for_request(request, cloud_token),
                }
            raise HTTPException(
                status_code=409,
                detail="Cloud invitation link is not available. Sign in with a cloud organization before inviting employees.",
            )

        now = current_utc_timestamp()
        expires_at = (datetime.now(UTC) + timedelta(days=request_data.expires_in_days)).replace(tzinfo=None).isoformat(
            timespec="seconds"
        )
        invitation_token = secrets.token_urlsafe(32)
        cursor.execute(
            """
            INSERT INTO organization_invitations (
                organization_id, email, employee_id, role, token_hash, status, expires_at, created_by_user_id, created_at
            )
            VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?)
            """,
            (
                organization_id,
                email,
                employee_id,
                request_data.role,
                hash_session_token(invitation_token),
                expires_at,
                current_user["id"],
                now,
            ),
        )
        invitation_id = cursor.lastrowid
        write_auth_audit_event(
            cursor,
            "invitation_created",
            user_id=current_user["id"],
            organization_id=organization_id,
            metadata={
                "invitation_id": invitation_id,
                "email": email,
                "role": request_data.role,
                "employee_id": employee_id,
            },
        )
        connection.commit()
        return {
            "invitation": {
                "id": invitation_id,
                "organization_id": organization_id,
                "email": email,
                "employee_id": employee_id,
                "role": request_data.role,
                "status": "pending",
                "expires_at": expires_at,
            },
            "invitation_token": invitation_token,
            "invitation_url": build_invitation_url_for_request(request, invitation_token),
        }
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise HTTPException(status_code=409, detail="Invitation already exists or token collision") from exc
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.delete("/api/organizations/{organization_id}/members/{user_id}", tags=["Auth"])
def remove_organization_member(
    organization_id: int,
    user_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    actor_membership = require_organization_role(current_user, organization_id, {"owner", "admin"})

    connection = get_connection()
    try:
        cursor = connection.cursor()
        if is_desktop_sqlite_runtime() and is_desktop_invitation_request(request):
            settings = read_desktop_cloud_sync_settings(cursor, organization_id)
            if desktop_cloud_sync_is_ready(settings):
                return request_cloud_json(
                    settings["cloud_api_base_url"],
                    f"/api/organizations/{int(settings['cloud_organization_id'])}/members/{user_id}",
                    method="DELETE",
                    token=settings["desktop_cloud_access_token"],
                )

        if user_id == current_user["id"]:
            raise HTTPException(status_code=400, detail="You cannot remove your own organization access")

        cursor.execute(
            """
            SELECT om.role, om.status, u.email, u.full_name
            FROM organization_memberships om
            JOIN users u ON u.id = om.user_id
            WHERE om.organization_id = ? AND om.user_id = ?
            """,
            (organization_id, user_id),
        )
        target = cursor.fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="Organization member not found")
        if target["status"] != "active":
            raise HTTPException(status_code=409, detail="Organization member is not active")

        target_role = target["role"]
        actor_role = actor_membership["role"]
        if target_role == "owner":
            if actor_role != "owner":
                raise HTTPException(status_code=403, detail="Only owners can remove another owner")
            cursor.execute(
                """
                SELECT COUNT(*) AS owner_count
                FROM organization_memberships
                WHERE organization_id = ? AND role = 'owner' AND status = 'active'
                """,
                (organization_id,),
            )
            if cursor.fetchone()["owner_count"] <= 1:
                raise HTTPException(status_code=409, detail="Cannot remove the last active owner")
        elif target_role == "admin" and actor_role != "owner":
            raise HTTPException(status_code=403, detail="Only owners can remove administrators")

        now = current_utc_timestamp()
        cursor.execute(
            """
            UPDATE organization_memberships
            SET status = 'disabled', employee_id = NULL, updated_at = ?
            WHERE organization_id = ? AND user_id = ? AND status = 'active'
            """,
            (now, organization_id, user_id),
        )
        cursor.execute(
            """
            UPDATE auth_sessions
            SET revoked_at = ?
            WHERE user_id = ? AND revoked_at IS NULL
            """,
            (now, user_id),
        )
        write_auth_audit_event(
            cursor,
            "member_removed",
            user_id=current_user["id"],
            organization_id=organization_id,
            metadata={
                "removed_user_id": user_id,
                "removed_email": target["email"],
                "removed_role": target_role,
            },
        )
        connection.commit()
        return {"message": "Organization member access removed"}
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.put("/api/organizations/{organization_id}/members/{user_id}/employee-link", tags=["Auth"])
def update_organization_member_employee_link(
    organization_id: int,
    user_id: int,
    request_data: OrganizationMemberEmployeeLinkUpdate,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    require_organization_role(current_user, organization_id, {"owner", "admin"})
    connection = get_connection()
    try:
        cursor = connection.cursor()
        employee_id = request_data.employee_id
        employee_public_id = request_data.employee_public_id
        if employee_id is None and employee_public_id:
            cursor.execute(
                """
                SELECT id
                FROM employees
                WHERE public_id = ? AND organization_id = ?
                """,
                (employee_public_id, organization_id),
            )
            employee_row = cursor.fetchone()
            if not employee_row:
                raise HTTPException(status_code=404, detail="Employee not found in this organization")
            employee_id = int(employee_row["id"])
        elif employee_id is not None:
            cursor.execute(
                """
                SELECT public_id
                FROM employees
                WHERE id = ? AND organization_id = ?
                """,
                (employee_id, organization_id),
            )
            employee_row = cursor.fetchone()
            if not employee_row:
                raise HTTPException(status_code=404, detail="Employee not found in this organization")
            employee_public_id = employee_row["public_id"]

        if is_desktop_sqlite_runtime() and is_desktop_invitation_request(request):
            settings = read_desktop_cloud_sync_settings(cursor, organization_id)
            if desktop_cloud_sync_is_ready(settings):
                return request_cloud_json(
                    settings["cloud_api_base_url"],
                    f"/api/organizations/{int(settings['cloud_organization_id'])}/members/{user_id}/employee-link",
                    method="PUT",
                    payload={"employee_public_id": employee_public_id, "employee_id": None},
                    token=settings["desktop_cloud_access_token"],
                )

        cursor.execute(
            """
            SELECT om.role, om.status, om.employee_id, u.email
            FROM organization_memberships om
            JOIN users u ON u.id = om.user_id
            WHERE om.organization_id = ? AND om.user_id = ?
            """,
            (organization_id, user_id),
        )
        member = cursor.fetchone()
        if not member:
            raise HTTPException(status_code=404, detail="Organization member not found")
        if member["status"] != "active":
            raise HTTPException(status_code=409, detail="Organization member is not active")
        if member["role"] != "employee":
            raise HTTPException(status_code=400, detail="Only employee members can be linked to employee records")

        if employee_id is not None:
            cursor.execute(
                """
                SELECT id, full_name
                FROM employees
                WHERE id = ? AND organization_id = ?
                """,
                (employee_id, organization_id),
            )
            employee = cursor.fetchone()
            if not employee:
                raise HTTPException(status_code=404, detail="Employee not found in this organization")
            cursor.execute(
                """
                SELECT 1
                FROM organization_memberships
                WHERE organization_id = ?
                  AND employee_id = ?
                  AND user_id != ?
                  AND status = 'active'
                """,
                (organization_id, employee_id, user_id),
            )
            if cursor.fetchone():
                raise HTTPException(status_code=409, detail="Employee is already linked to another active user")

        now = current_utc_timestamp()
        cursor.execute(
            """
            UPDATE organization_memberships
            SET employee_id = ?, updated_at = ?
            WHERE organization_id = ? AND user_id = ? AND role = 'employee' AND status = 'active'
            """,
            (employee_id, now, organization_id, user_id),
        )
        if employee_id is not None:
            cursor.execute(
                """
                UPDATE organization_invitations
                SET employee_id = ?
                WHERE organization_id = ?
                  AND lower(email) = ?
                  AND role = 'employee'
                  AND status = 'accepted'
                  AND employee_id IS NULL
                """,
                (employee_id, organization_id, str(member["email"]).lower()),
            )
        write_auth_audit_event(
            cursor,
            "member_employee_link_updated",
            user_id=current_user["id"],
            organization_id=organization_id,
            metadata={
                "target_user_id": user_id,
                "target_email": member["email"],
                "employee_id": employee_id,
            },
        )
        connection.commit()
        return {"message": "Employee link updated", "user_id": user_id, "employee_id": employee_id}
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.delete("/api/organizations/{organization_id}/invitations/{invitation_id}", tags=["Auth"])
def revoke_organization_invitation(
    organization_id: int,
    invitation_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    require_organization_role(current_user, organization_id, {"owner", "admin"})
    connection = get_connection()
    try:
        cursor = connection.cursor()
        if is_desktop_sqlite_runtime() and is_desktop_invitation_request(request):
            settings = read_desktop_cloud_sync_settings(cursor, organization_id)
            if desktop_cloud_sync_is_ready(settings):
                return request_cloud_json(
                    settings["cloud_api_base_url"],
                    f"/api/organizations/{int(settings['cloud_organization_id'])}/invitations/{invitation_id}",
                    method="DELETE",
                    token=settings["desktop_cloud_access_token"],
                )

        cursor.execute(
            """
            SELECT id, email, role, status
            FROM organization_invitations
            WHERE id = ? AND organization_id = ?
            """,
            (invitation_id, organization_id),
        )
        invitation = cursor.fetchone()
        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found")
        if invitation["status"] != "pending":
            raise HTTPException(status_code=409, detail="Only pending invitations can be revoked")

        now = current_utc_timestamp()
        cursor.execute(
            """
            UPDATE organization_invitations
            SET status = 'revoked'
            WHERE id = ? AND organization_id = ? AND status = 'pending'
            """,
            (invitation_id, organization_id),
        )
        write_auth_audit_event(
            cursor,
            "invitation_revoked",
            user_id=current_user["id"],
            organization_id=organization_id,
            metadata={
                "invitation_id": invitation_id,
                "email": invitation["email"],
                "role": invitation["role"],
                "revoked_at": now,
            },
        )
        connection.commit()
        return {"message": "Invitation revoked"}
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.post("/api/organizations/{organization_id}/invitations/{invitation_id}/regenerate-token", tags=["Auth"])
def regenerate_organization_invitation_token(
    organization_id: int,
    invitation_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    require_organization_role(current_user, organization_id, {"owner", "admin"})
    connection = get_connection()
    try:
        cursor = connection.cursor()
        if is_desktop_sqlite_runtime() and is_desktop_invitation_request(request):
            settings = read_desktop_cloud_sync_settings(cursor, organization_id)
            if desktop_cloud_sync_is_ready(settings):
                return request_cloud_json(
                    settings["cloud_api_base_url"],
                    f"/api/organizations/{int(settings['cloud_organization_id'])}/invitations/{invitation_id}/regenerate-token",
                    method="POST",
                    token=settings["desktop_cloud_access_token"],
                )

        cursor.execute(
            """
            SELECT oi.id, oi.email, oi.employee_id, oi.role, oi.status,
                   e.full_name AS employee_name
            FROM organization_invitations oi
            LEFT JOIN employees e ON e.id = oi.employee_id
            WHERE oi.id = ? AND oi.organization_id = ?
            """,
            (invitation_id, organization_id),
        )
        invitation = cursor.fetchone()
        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found")
        if invitation["status"] != "pending":
            raise HTTPException(status_code=409, detail="Only pending invitations can receive a new link")

        now = current_utc_timestamp()
        expires_at = (datetime.now(UTC) + timedelta(days=7)).replace(tzinfo=None).isoformat(timespec="seconds")
        invitation_token = secrets.token_urlsafe(32)
        cursor.execute(
            """
            UPDATE organization_invitations
            SET token_hash = ?, expires_at = ?
            WHERE id = ? AND organization_id = ? AND status = 'pending'
            """,
            (hash_session_token(invitation_token), expires_at, invitation_id, organization_id),
        )
        write_auth_audit_event(
            cursor,
            "invitation_token_regenerated",
            user_id=current_user["id"],
            organization_id=organization_id,
            metadata={
                "invitation_id": invitation_id,
                "email": invitation["email"],
                "employee_id": invitation["employee_id"],
                "role": invitation["role"],
                "expires_at": expires_at,
            },
        )
        connection.commit()
        return {
            "invitation": {
                "id": invitation_id,
                "organization_id": organization_id,
                "email": invitation["email"],
                "employee_id": invitation["employee_id"],
                "role": invitation["role"],
                "status": "pending",
                "expires_at": expires_at,
            },
            "invitation_token": invitation_token,
            "invitation_url": build_invitation_url_for_request(request, invitation_token),
        }
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise HTTPException(status_code=409, detail="Invitation token collision") from exc
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.get("/api/database/backups", tags=["Settings"])
def get_database_backups(admin_context: dict | None = Depends(require_database_admin_if_auth_initialized)):
    return {"backups": database_module.list_database_backups()}


@app.post("/api/database/backups", tags=["Settings"])
def create_database_backup_endpoint(
    request_data: DatabaseBackupCreateRequest,
    admin_context: dict | None = Depends(require_database_admin_if_auth_initialized),
):
    if not database_module.is_sqlite_runtime():
        raise HTTPException(
            status_code=409,
            detail="File backups are disabled for PostgreSQL/Cloud SQL runtime. Use Cloud SQL managed backups.",
        )
    user_id, organization_id = audit_context_from_admin(admin_context)
    backup_path = database_module.create_schedule_backup(
        request_data.label,
        app_version=APP_VERSION,
        schema_version=database_module.CURRENT_SCHEMA_VERSION,
        organization_id=organization_id or 1,
        created_by=user_id,
    )
    write_auth_audit_event_record(
        "database_backup_created",
        user_id=user_id,
        organization_id=organization_id,
        metadata={"backup_name": backup_path.name, "label": request_data.label},
    )
    return {
        "message": "Database backup created successfully",
        "backup_name": backup_path.name,
    }


@app.post("/api/database/restore", tags=["Settings"])
def restore_database_backup_endpoint(
    request_data: DatabaseRestoreRequest,
    admin_context: dict | None = Depends(require_database_admin_if_auth_initialized),
):
    if not database_module.is_sqlite_runtime():
        raise HTTPException(
            status_code=409,
            detail="File restore is disabled for PostgreSQL/Cloud SQL runtime. Use Cloud SQL point-in-time recovery.",
        )
    try:
        result = database_module.restore_database_backup(request_data.backup_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Backup not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    user_id, organization_id = audit_context_from_admin(admin_context)
    write_auth_audit_event_record(
        "database_backup_restored",
        user_id=user_id,
        organization_id=organization_id,
        metadata=result,
    )
    return {"message": "Database restored successfully", **result}


@app.get("/api/updates/check", tags=["Settings"])
def check_for_updates():
    return get_update_status()


@app.post("/api/updates/install", tags=["Settings"])
def install_update(request_data: UpdateInstallRequest):
    status = get_update_status()
    latest = status.get("latest")
    if not latest or not status.get("update_available"):
        return {
            "message": "No newer update is available.",
            "current_version": APP_VERSION,
            "update_available": False,
        }

    if request_data.download_url != latest["download_url"] or request_data.asset_name != latest["asset_name"]:
        raise HTTPException(status_code=400, detail="Requested update does not match the latest release")

    installer_path = download_update_installer(latest["download_url"], latest["asset_name"])
    subprocess.Popen([str(installer_path), "/CLOSEAPPLICATIONS"], close_fds=True)
    schedule_desktop_shutdown()

    return {
        "message": "Update installer started.",
        "installer_path": str(installer_path),
        "latest": latest,
    }


@app.get("/api/license/status", tags=["Licensing"])
def get_license_status():
    connection = get_connection()
    try:
        cursor = connection.cursor()
        return build_license_status_payload(cursor)
    finally:
        connection.close()


@app.post("/api/license/import-file", tags=["Licensing"])
def import_license_file(
    request_data: LicenseImportRequest,
    admin_context: dict | None = Depends(require_database_admin_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        payload = import_license_certificate(cursor, request_data.certificate, source="imported")
        connection.commit()
        return {"message": "License imported", "license": payload}
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.post("/api/license/activate-code", tags=["Licensing"])
def activate_license_code(
    request_data: LicenseActivationCodeRequest,
    admin_context: dict | None = Depends(require_database_admin_if_auth_initialized),
):
    activation_hash = hash_session_token(request_data.activation_code)
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO license_activation_attempts (organization_id, activation_code_hash, status, error)
            VALUES (1, ?, 'success', NULL)
            """,
            (activation_hash,),
        )
        certificate = license_runtime.decode_activation_code(request_data.activation_code)
        payload = import_license_certificate(cursor, certificate, source="activation_code")
        write_license_event(
            cursor,
            "license_activation_succeeded",
            metadata={"source": "activation_code"},
            license_id=certificate["license_id"],
        )
        connection.commit()
        return {"message": "License activated", "license": payload}
    except license_runtime.LicenseValidationError as exc:
        connection.rollback()
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO license_activation_attempts (organization_id, activation_code_hash, status, error)
            VALUES (1, ?, 'failed', ?)
            """,
            (activation_hash, str(exc)),
        )
        write_license_event(
            cursor,
            "license_activation_failed",
            metadata={"reason": str(exc), "source": "activation_code"},
        )
        connection.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.post("/api/license/refresh", tags=["Licensing"])
def refresh_license(
    admin_context: dict | None = Depends(require_database_admin_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        write_license_event(
            cursor,
            "license_refresh_skipped",
            metadata={"reason": "cloud_license_backend_not_configured"},
        )
        connection.commit()
        return {
            "message": "Cloud license backend is not configured yet",
            "license": build_license_status_payload(cursor),
        }
    finally:
        connection.close()


def desktop_only_page_or_404(template_name: str, request: Request):
    if is_cloud_employee_portal_mode():
        raise HTTPException(status_code=404, detail="This page is available only in the desktop app")
    return templates.TemplateResponse(request=request, name=template_name, context={})


@app.get("/", tags=["Pages"])
def home_page(request: Request):
    if is_cloud_employee_portal_mode():
        return templates.TemplateResponse(request=request, name="schedule.html", context={})
    return templates.TemplateResponse(request=request, name="index.html", context={})


@app.get("/login", tags=["Pages"])
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={})


@app.get("/organization", tags=["Pages"])
def organization_page(request: Request):
    return templates.TemplateResponse(request=request, name="organization.html", context={})


@app.get("/organizations", tags=["Pages"], include_in_schema=False)
def organizations_page_alias(request: Request):
    return templates.TemplateResponse(request=request, name="organization.html", context={})


@app.get("/support", tags=["Pages"])
def support_page(request: Request):
    if not is_developer_mode_enabled():
        raise HTTPException(status_code=404, detail="Developer support mode is disabled")
    return templates.TemplateResponse(request=request, name="support.html", context={})


@app.get("/accept-invitation", tags=["Pages"])
def accept_invitation_page(request: Request):
    return templates.TemplateResponse(request=request, name="accept_invitation.html", context={})


@app.get("/employees", tags=["Pages"])
def employees_page(request: Request):
    return desktop_only_page_or_404("employees.html", request)


@app.get("/positions", tags=["Pages"])
def positions_page(request: Request):
    return desktop_only_page_or_404("positions.html", request)


@app.get("/employee-positions", tags=["Pages"])
def employee_positions_page(request: Request):
    return desktop_only_page_or_404("employee_positions.html", request)


@app.get("/shift-templates", tags=["Pages"])
def shift_templates_page(request: Request):
    return desktop_only_page_or_404("shift_templates.html", request)


@app.get("/coverage-requirements", tags=["Pages"])
def coverage_requirements_page(request: Request):
    return desktop_only_page_or_404("coverage_requirements.html", request)


@app.get("/weekly-preferences", tags=["Pages"])
def weekly_preferences_page(request: Request):
    return templates.TemplateResponse(request=request, name="weekly_preferences.html", context={})


@app.get("/schedule", tags=["Pages"])
def schedule_page(request: Request):
    return templates.TemplateResponse(request=request, name="schedule.html", context={})


@app.get("/settings", tags=["Pages"])
def settings_page(request: Request):
    return desktop_only_page_or_404("settings.html", request)


@app.get("/guide", tags=["Pages"])
def guide_page(request: Request):
    return templates.TemplateResponse(request=request, name="guide.html", context={})


# =========================
# CRUD APIs
# =========================


@app.get("/api/employees", tags=["Employees"])
def get_employees(
    position_id: int | None = None,
    access_context: dict | None = Depends(require_preference_access_if_auth_initialized),
):
    organization_filter = access_context["membership"]["organization_id"] if access_context else None
    employee_filter = None
    if access_context and access_context["scope"] == "own":
        employee_filter = access_context["membership"]["employee_id"]
    connection = get_connection()
    try:
        cursor = connection.cursor()
        if employee_filter and position_id is not None:
            require_employee_position_scope(cursor, int(employee_filter), position_id)
            cursor.execute(
                """
                SELECT DISTINCT e.*
                FROM employees e
                JOIN employee_positions ep ON ep.employee_id = e.id
                WHERE ep.position_id = ?
                ORDER BY e.id
                """,
                (position_id,),
            )
        elif employee_filter:
            cursor.execute("SELECT * FROM employees WHERE id = ? ORDER BY id", (employee_filter,))
        elif organization_filter and position_id is not None:
            cursor.execute(
                """
                SELECT DISTINCT e.*
                FROM employees e
                JOIN employee_positions ep ON ep.employee_id = e.id
                WHERE e.organization_id = ? AND ep.position_id = ?
                ORDER BY e.id
                """,
                (organization_filter, position_id),
            )
        elif organization_filter:
            cursor.execute("SELECT * FROM employees WHERE organization_id = ? ORDER BY id", (organization_filter,))
        elif position_id is not None:
            cursor.execute(
                """
                SELECT DISTINCT e.*
                FROM employees e
                JOIN employee_positions ep ON ep.employee_id = e.id
                WHERE ep.position_id = ?
                ORDER BY e.id
                """,
                (position_id,),
            )
        else:
            cursor.execute("SELECT * FROM employees ORDER BY id")
        return [row_to_employee_dict(row) for row in cursor.fetchall()]
    finally:
        connection.close()


@app.post("/api/employees", tags=["Employees"])
def add_employee(employee: EmployeeCreate, _access: dict | None = Depends(require_setup_edit_if_auth_initialized)):
    organization_id = _access["membership"]["organization_id"] if _access else 1
    connection = get_connection()
    try:
        cursor = connection.cursor()
        require_license_capability(cursor, "can_add_employee", organization_id)
        cursor.execute(
            """
            INSERT INTO employees (
                organization_id, id_card, full_name, sex, min_shifts_per_week, target_shifts_per_week, max_shifts_per_week,
                can_work_night, can_work_weekends, can_work_evenings_after_night, can_work_mornings_and_evenings
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                employee.id_card,
                employee.full_name,
                employee.sex,
                employee.min_shifts_per_week,
                employee.target_shifts_per_week,
                employee.max_shifts_per_week,
                int(employee.can_work_night),
                int(employee.can_work_weekends),
                int(employee.can_work_evenings_after_night),
                int(employee.can_work_mornings_and_evenings),
            ),
        )
        connection.commit()
        return {"message": "Employee added successfully", "employee": {"id": cursor.lastrowid, **employee.model_dump()}}
    finally:
        connection.close()


@app.put("/api/employees/{employee_id}", tags=["Employees"])
def update_employee(
    employee_id: int,
    employee: EmployeeCreate,
    _access: dict | None = Depends(require_setup_edit_if_auth_initialized),
):
    organization_id = _access["membership"]["organization_id"] if _access else None
    connection = get_connection()
    try:
        cursor = connection.cursor()
        if organization_id:
            fetch_one_or_404(
                cursor,
                "SELECT id FROM employees WHERE id = ? AND organization_id = ?",
                (employee_id, organization_id),
                "Employee not found",
            )
        else:
            fetch_one_or_404(cursor, "SELECT id FROM employees WHERE id = ?", (employee_id,), "Employee not found")
        cursor.execute(
            """
            UPDATE employees
            SET id_card = ?, full_name = ?, sex = ?, min_shifts_per_week = ?, target_shifts_per_week = ?,
                max_shifts_per_week = ?, can_work_night = ?, can_work_weekends = ?,
                can_work_evenings_after_night = ?, can_work_mornings_and_evenings = ?
            WHERE id = ?
            """,
            (
                employee.id_card,
                employee.full_name,
                employee.sex,
                employee.min_shifts_per_week,
                employee.target_shifts_per_week,
                employee.max_shifts_per_week,
                int(employee.can_work_night),
                int(employee.can_work_weekends),
                int(employee.can_work_evenings_after_night),
                int(employee.can_work_mornings_and_evenings),
                employee_id,
            ),
        )
        connection.commit()
        return {"message": "Employee updated successfully", "employee": {"id": employee_id, **employee.model_dump()}}
    finally:
        connection.close()


@app.delete("/api/employees/{employee_id}", tags=["Employees"])
def delete_employee(employee_id: int, _access: dict | None = Depends(require_setup_edit_if_auth_initialized)):
    organization_id = _access["membership"]["organization_id"] if _access else None
    connection = get_connection()
    try:
        cursor = connection.cursor()
        if organization_id:
            fetch_one_or_404(
                cursor,
                "SELECT id FROM employees WHERE id = ? AND organization_id = ?",
                (employee_id, organization_id),
                "Employee not found",
            )
        else:
            fetch_one_or_404(cursor, "SELECT id FROM employees WHERE id = ?", (employee_id,), "Employee not found")
        backup_name = create_recovery_backup("delete_employee")
        cursor.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
        connection.commit()
        return {"message": "Employee deleted successfully", "backup_name": backup_name}
    finally:
        connection.close()


@app.get("/api/employees/{employee_id}/delete-impact", tags=["Employees"])
def get_employee_delete_impact(employee_id: int, _access: dict | None = Depends(require_setup_edit_if_auth_initialized)):
    organization_id = _access["membership"]["organization_id"] if _access else None
    connection = get_connection()
    try:
        cursor = connection.cursor()
        if organization_id:
            employee_row = fetch_one_or_404(
                cursor,
                "SELECT id, full_name FROM employees WHERE id = ? AND organization_id = ?",
                (employee_id, organization_id),
                "Employee not found",
            )
        else:
            employee_row = fetch_one_or_404(
                cursor,
                "SELECT id, full_name FROM employees WHERE id = ?",
                (employee_id,),
                "Employee not found",
            )
        return {
            "employee_id": employee_row["id"],
            "employee_name": employee_row["full_name"],
            "assignments": fetch_count(cursor, "SELECT COUNT(*) FROM employee_positions WHERE employee_id = ?", (employee_id,)),
            "schedule_entries": fetch_count(cursor, "SELECT COUNT(*) FROM schedule_entries WHERE employee_id = ?", (employee_id,)),
            "general_preferences": fetch_count(
                cursor,
                "SELECT COUNT(*) FROM employee_preferences WHERE employee_id = ?",
                (employee_id,),
            ),
            "weekly_preferences": fetch_count(
                cursor,
                "SELECT COUNT(*) FROM employee_week_preferences WHERE employee_id = ?",
                (employee_id,),
            ),
            "recurring_preferences": fetch_count(
                cursor,
                "SELECT COUNT(*) FROM employee_recurring_preferences WHERE employee_id = ?",
                (employee_id,),
            ),
            "day_statuses": fetch_count(
                cursor,
                "SELECT COUNT(*) FROM employee_day_statuses WHERE employee_id = ?",
                (employee_id,),
            ),
        }
    finally:
        connection.close()


@app.get("/api/positions", tags=["Positions"])
def get_positions(access_context: dict | None = Depends(require_schedule_view_if_auth_initialized)):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        employee_id = employee_scope_from_access(access_context)
        if employee_id is not None:
            cursor.execute(
                """
                SELECT p.*, ep.is_primary, ep.priority_score, ep.is_fallback_only
                FROM positions p
                JOIN employee_positions ep ON ep.position_id = p.id
                WHERE ep.employee_id = ?
                ORDER BY ep.is_primary DESC, ep.is_fallback_only ASC, ep.priority_score DESC, p.id
                """,
                (employee_id,),
            )
        else:
            cursor.execute("SELECT * FROM positions ORDER BY id")
        return [row_to_position_dict(row) for row in cursor.fetchall()]
    finally:
        connection.close()


@app.post("/api/positions", tags=["Positions"])
def add_position(position: PositionCreate, _access: dict | None = Depends(require_setup_edit_if_auth_initialized)):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO positions (
                    name, color, requires_continuous_coverage, minimum_staff_presence,
                    max_consecutive_nights, emergency_max_consecutive_nights,
                    max_consecutive_split_days, emergency_max_consecutive_split_days
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    position.name,
                    position.color,
                    int(position.requires_continuous_coverage),
                    position.minimum_staff_presence,
                    position.max_consecutive_nights,
                    position.emergency_max_consecutive_nights,
                    position.max_consecutive_split_days,
                    position.emergency_max_consecutive_split_days,
                ),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Position already exists")
        connection.commit()
        return {"message": "Position added successfully", "position": {"id": cursor.lastrowid, **position.model_dump()}}
    finally:
        connection.close()


@app.put("/api/positions/{position_id}", tags=["Positions"])
def update_position(
    position_id: int,
    position: PositionCreate,
    _access: dict | None = Depends(require_setup_edit_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        fetch_one_or_404(cursor, "SELECT id FROM positions WHERE id = ?", (position_id,), "Position not found")
        try:
            cursor.execute(
                """
                UPDATE positions
                SET name = ?, color = ?, requires_continuous_coverage = ?, minimum_staff_presence = ?,
                    max_consecutive_nights = ?, emergency_max_consecutive_nights = ?,
                    max_consecutive_split_days = ?, emergency_max_consecutive_split_days = ?
                WHERE id = ?
                """,
                (
                    position.name,
                    position.color,
                    int(position.requires_continuous_coverage),
                    position.minimum_staff_presence,
                    position.max_consecutive_nights,
                    position.emergency_max_consecutive_nights,
                    position.max_consecutive_split_days,
                    position.emergency_max_consecutive_split_days,
                    position_id,
                ),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Position already exists")
        connection.commit()
        return {"message": "Position updated successfully", "position": {"id": position_id, **position.model_dump()}}
    finally:
        connection.close()


@app.delete("/api/positions/{position_id}", tags=["Positions"])
def delete_position(position_id: int, _access: dict | None = Depends(require_setup_edit_if_auth_initialized)):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        fetch_one_or_404(cursor, "SELECT id FROM positions WHERE id = ?", (position_id,), "Position not found")
        backup_name = create_recovery_backup("delete_position")
        cursor.execute("DELETE FROM positions WHERE id = ?", (position_id,))
        connection.commit()
        return {"message": "Position deleted successfully", "backup_name": backup_name}
    finally:
        connection.close()


@app.get("/api/positions/{position_id}/delete-impact", tags=["Positions"])
def get_position_delete_impact(
    position_id: int,
    _access: dict | None = Depends(require_setup_edit_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        position_row = fetch_one_or_404(
            cursor,
            "SELECT id, name FROM positions WHERE id = ?",
            (position_id,),
            "Position not found",
        )
        return {
            "position_id": position_row["id"],
            "position_name": position_row["name"],
            "assignments": fetch_count(cursor, "SELECT COUNT(*) FROM employee_positions WHERE position_id = ?", (position_id,)),
            "schedule_entries": fetch_count(cursor, "SELECT COUNT(*) FROM schedule_entries WHERE position_id = ?", (position_id,)),
            "shift_requirements": fetch_count(cursor, "SELECT COUNT(*) FROM shift_requirements WHERE position_id = ?", (position_id,)),
            "coverage_requirements": fetch_count(
                cursor,
                "SELECT COUNT(*) FROM coverage_requirements WHERE position_id = ?",
                (position_id,),
            ),
        }
    finally:
        connection.close()


@app.get("/api/employee-positions", tags=["Assignments"])
def get_employee_positions(
    position_id: int | None = None,
    access_context: dict | None = Depends(require_schedule_view_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        employee_id = employee_scope_from_access(access_context)
        params: tuple = ()
        where_sql = ""
        if employee_id is not None and position_id is not None:
            require_employee_position_scope(cursor, employee_id, position_id)
            where_sql = "WHERE ep.position_id = ?"
            params = (position_id,)
        elif employee_id is not None:
            where_sql = "WHERE ep.employee_id = ?"
            params = (employee_id,)
        elif position_id is not None:
            where_sql = "WHERE ep.position_id = ?"
            params = (position_id,)
        cursor.execute(
            f"""
            SELECT ep.*, e.full_name AS employee_name, p.name AS position_name
            FROM employee_positions ep
            JOIN employees e ON e.id = ep.employee_id
            JOIN positions p ON p.id = ep.position_id
            {where_sql}
            ORDER BY ep.employee_id, ep.is_primary DESC, ep.is_fallback_only ASC, ep.priority_score DESC, ep.position_id
            """,
            params,
        )
        items = [dict(row) for row in cursor.fetchall()]
        for item in items:
            item["is_primary"] = bool(item["is_primary"])
            item["is_fallback_only"] = bool(item["is_fallback_only"])
        return items
    finally:
        connection.close()


@app.post("/api/employee-positions", tags=["Assignments"])
def assign_employee_to_position(
    assignment: EmployeePositionCreate,
    _access: dict | None = Depends(require_setup_edit_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        fetch_one_or_404(cursor, "SELECT id FROM employees WHERE id = ?", (assignment.employee_id,), "Employee not found")
        fetch_one_or_404(cursor, "SELECT id FROM positions WHERE id = ?", (assignment.position_id,), "Position not found")
        try:
            cursor.execute(
                """
                INSERT INTO employee_positions (employee_id, position_id, is_primary, priority_score, is_fallback_only)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    assignment.employee_id,
                    assignment.position_id,
                    int(assignment.is_primary),
                    assignment.priority_score,
                    int(assignment.is_fallback_only),
                ),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Employee is already assigned to this position")
        connection.commit()
        return {"message": "Employee assigned to position successfully", "assignment": assignment.model_dump()}
    finally:
        connection.close()


@app.put("/api/employee-positions", tags=["Assignments"])
def update_employee_position(
    assignment: EmployeePositionCreate,
    _access: dict | None = Depends(require_setup_edit_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        fetch_one_or_404(cursor, "SELECT id FROM employees WHERE id = ?", (assignment.employee_id,), "Employee not found")
        fetch_one_or_404(cursor, "SELECT id FROM positions WHERE id = ?", (assignment.position_id,), "Position not found")
        cursor.execute(
            """
            UPDATE employee_positions
            SET is_primary = ?, priority_score = ?, is_fallback_only = ?
            WHERE employee_id = ? AND position_id = ?
            """,
            (
                int(assignment.is_primary),
                assignment.priority_score,
                int(assignment.is_fallback_only),
                assignment.employee_id,
                assignment.position_id,
            ),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Assignment not found")
        connection.commit()
        return {"message": "Employee assignment updated successfully", "assignment": assignment.model_dump()}
    finally:
        connection.close()


@app.delete("/api/employee-positions", tags=["Assignments"])
def delete_employee_position(
    employee_id: int,
    position_id: int,
    _access: dict | None = Depends(require_setup_edit_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        backup_name = create_recovery_backup("delete_assignment")
        cursor.execute("DELETE FROM employee_positions WHERE employee_id = ? AND position_id = ?", (employee_id, position_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Assignment not found")
        connection.commit()
        return {"message": "Employee assignment deleted successfully", "backup_name": backup_name}
    finally:
        connection.close()


@app.get("/api/employee-positions/delete-impact", tags=["Assignments"])
def get_employee_position_delete_impact(
    employee_id: int,
    position_id: int,
    _access: dict | None = Depends(require_setup_edit_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        assignment_row = fetch_one_or_404(
            cursor,
            """
            SELECT ep.employee_id, ep.position_id, e.full_name AS employee_name, p.name AS position_name
            FROM employee_positions ep
            JOIN employees e ON e.id = ep.employee_id
            JOIN positions p ON p.id = ep.position_id
            WHERE ep.employee_id = ? AND ep.position_id = ?
            """,
            (employee_id, position_id),
            "Assignment not found",
        )
        return {
            "employee_id": assignment_row["employee_id"],
            "position_id": assignment_row["position_id"],
            "employee_name": assignment_row["employee_name"],
            "position_name": assignment_row["position_name"],
            "schedule_entries": fetch_count(
                cursor,
                "SELECT COUNT(*) FROM schedule_entries WHERE employee_id = ? AND position_id = ?",
                (employee_id, position_id),
            ),
        }
    finally:
        connection.close()


@app.get("/api/shift-templates", tags=["Shift Templates"])
def get_shift_templates(
    active_only: bool = False,
    position_id: int | None = None,
    access_context: dict | None = Depends(require_schedule_view_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        employee_id = employee_scope_from_access(access_context)
        if employee_id is not None:
            if position_id is not None:
                require_employee_position_scope(cursor, employee_id, position_id)
            else:
                cursor.execute(
                    """
                    SELECT position_id
                    FROM employee_positions
                    WHERE employee_id = ?
                    ORDER BY is_primary DESC, is_fallback_only ASC, priority_score DESC, position_id
                    LIMIT 1
                    """,
                    (employee_id,),
                )
                row = cursor.fetchone()
                position_id = int(row["position_id"]) if row else -1
        base_query = """
            SELECT st.*, p.name AS position_name
            FROM shift_templates st
            LEFT JOIN positions p ON p.id = st.position_id
        """
        conditions = []
        params: list[int] = []
        if active_only:
            conditions.append("st.is_active = 1")
        if position_id is not None:
            conditions.append("st.position_id = ?")
            params.append(position_id)
        where_sql = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"{base_query}{where_sql} ORDER BY COALESCE(st.position_id, 0), st.category, st.start_time, st.end_time"
        cursor.execute(query, params)
        return [row_to_shift_template_dict(row) for row in cursor.fetchall()]
    finally:
        connection.close()


@app.post("/api/shift-templates", tags=["Shift Templates"])
def add_shift_template(
    template: ShiftTemplateCreate,
    _access: dict | None = Depends(require_setup_edit_if_auth_initialized),
):
    parse_time_string(template.start_time)
    parse_time_string(template.end_time)
    connection = get_connection()
    try:
        cursor = connection.cursor()
        fetch_one_or_404(cursor, "SELECT id FROM positions WHERE id = ?", (template.position_id,), "Position not found")
        try:
            cursor.execute(
                """
                INSERT INTO shift_templates (position_id, name, category, start_time, end_time, is_overnight, is_active, is_split_only)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    template.position_id,
                    template.name,
                    template.category,
                    template.start_time,
                    template.end_time,
                    int(template.is_overnight),
                    int(template.is_active),
                    int(template.is_split_only),
                ),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Shift template already exists for this position")
        connection.commit()
        return {"message": "Shift template added successfully", "shift_template": {"id": cursor.lastrowid, **template.model_dump()}}
    finally:
        connection.close()


@app.put("/api/shift-templates/{template_id}", tags=["Shift Templates"])
def update_shift_template(
    template_id: int,
    template: ShiftTemplateCreate,
    _access: dict | None = Depends(require_setup_edit_if_auth_initialized),
):
    parse_time_string(template.start_time)
    parse_time_string(template.end_time)
    connection = get_connection()
    try:
        cursor = connection.cursor()
        fetch_one_or_404(cursor, "SELECT id FROM shift_templates WHERE id = ?", (template_id,), "Shift template not found")
        fetch_one_or_404(cursor, "SELECT id FROM positions WHERE id = ?", (template.position_id,), "Position not found")
        try:
            cursor.execute(
                """
                UPDATE shift_templates
                SET position_id = ?, name = ?, category = ?, start_time = ?, end_time = ?, is_overnight = ?, is_active = ?, is_split_only = ?
                WHERE id = ?
                """,
                (
                    template.position_id,
                    template.name,
                    template.category,
                    template.start_time,
                    template.end_time,
                    int(template.is_overnight),
                    int(template.is_active),
                    int(template.is_split_only),
                    template_id,
                ),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Shift template with this name already exists for this position")
        connection.commit()
        return {"message": "Shift template updated successfully", "shift_template": {"id": template_id, **template.model_dump()}}
    finally:
        connection.close()


@app.delete("/api/shift-templates/{template_id}", tags=["Shift Templates"])
def delete_shift_template(
    template_id: int,
    _access: dict | None = Depends(require_setup_edit_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        backup_name = create_recovery_backup("delete_shift_template")
        cursor.execute("DELETE FROM shift_templates WHERE id = ?", (template_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Shift template not found")
        connection.commit()
        return {"message": "Shift template deleted successfully", "backup_name": backup_name}
    except sqlite3.IntegrityError:
        connection.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete shift template because it is used in schedule")
    finally:
        connection.close()


@app.get("/api/shift-templates/{template_id}/delete-impact", tags=["Shift Templates"])
def get_shift_template_delete_impact(
    template_id: int,
    _access: dict | None = Depends(require_setup_edit_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        template_row = fetch_one_or_404(
            cursor,
            """
            SELECT st.id, st.name, st.category, st.position_id, p.name AS position_name
            FROM shift_templates st
            LEFT JOIN positions p ON p.id = st.position_id
            WHERE st.id = ?
            """,
            (template_id,),
            "Shift template not found",
        )
        return {
            "template_id": template_row["id"],
            "template_name": template_row["name"],
            "category": template_row["category"],
            "position_id": template_row["position_id"],
            "position_name": template_row["position_name"],
            "schedule_entries": fetch_count(
                cursor,
                "SELECT COUNT(*) FROM schedule_entries WHERE shift_template_id = ?",
                (template_id,),
            ),
        }
    finally:
        connection.close()


@app.get("/api/shift-requirements", tags=["Requirements"])
def get_shift_requirements(
    position_id: int | None = None,
    access_context: dict | None = Depends(require_schedule_view_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        employee_id = employee_scope_from_access(access_context)
        if employee_id is not None and position_id is not None:
            require_employee_position_scope(cursor, employee_id, position_id)
        if position_id is None:
            cursor.execute(
                """
            SELECT sr.*, p.name AS position_name
            FROM shift_requirements sr
            JOIN positions p ON p.id = sr.position_id
            ORDER BY sr.position_id, sr.shift_category
                """
            )
        else:
            cursor.execute(
                """
                SELECT sr.*, p.name AS position_name
                FROM shift_requirements sr
                JOIN positions p ON p.id = sr.position_id
                WHERE sr.position_id = ?
                ORDER BY sr.shift_category
                """,
                (position_id,),
            )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        connection.close()


@app.post("/api/shift-requirements", tags=["Requirements"])
def save_shift_requirement(
    requirement: ShiftRequirementCreate,
    _access: dict | None = Depends(require_setup_edit_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        fetch_one_or_404(cursor, "SELECT id FROM positions WHERE id = ?", (requirement.position_id,), "Position not found")
        cursor.execute(
            """
            INSERT INTO shift_requirements (position_id, shift_category, required_total, required_female_min, required_male_min)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(position_id, shift_category)
            DO UPDATE SET required_total = excluded.required_total,
                          required_female_min = excluded.required_female_min,
                          required_male_min = excluded.required_male_min
            """,
            (
                requirement.position_id,
                requirement.shift_category,
                requirement.required_total,
                requirement.required_female_min,
                requirement.required_male_min,
            ),
        )
        connection.commit()
        return {"message": "Shift requirement saved successfully", "requirement": requirement.model_dump()}
    finally:
        connection.close()


@app.get("/api/coverage-requirements", tags=["Requirements"])
def get_coverage_requirements(
    position_id: int | None = None,
    access_context: dict | None = Depends(require_schedule_view_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        employee_id = employee_scope_from_access(access_context)
        if employee_id is not None and position_id is not None:
            require_employee_position_scope(cursor, employee_id, position_id)
        if position_id is None:
            cursor.execute(
                """
                SELECT cr.*, p.name AS position_name
                FROM coverage_requirements cr
                JOIN positions p ON p.id = cr.position_id
                ORDER BY cr.position_id, cr.start_time, cr.end_time
                """
            )
        else:
            cursor.execute(
                """
                SELECT cr.*, p.name AS position_name
                FROM coverage_requirements cr
                JOIN positions p ON p.id = cr.position_id
                WHERE cr.position_id = ?
                ORDER BY cr.start_time, cr.end_time
                """,
                (position_id,),
            )
        return [row_to_coverage_requirement_dict(row) for row in cursor.fetchall()]
    finally:
        connection.close()


@app.get("/api/app-settings", tags=["Requirements"])
def get_app_settings_api():
    connection = get_connection()
    try:
        return get_app_settings(connection)
    finally:
        connection.close()


@app.put("/api/app-settings", tags=["Requirements"])
def update_app_settings(
    settings: AppSettingsUpdate,
    _access: dict | None = Depends(require_setup_edit_if_auth_initialized),
):
    connection = get_connection()
    try:
        save_app_settings(connection, settings)
        connection.commit()
        return {
            "message": "Application settings updated successfully",
            "settings": get_app_settings(connection),
        }
    finally:
        connection.close()


@app.post("/api/app-settings/reset-colors", tags=["Requirements"])
def reset_app_visual_colors(_access: dict | None = Depends(require_setup_edit_if_auth_initialized)):
    connection = get_connection()
    try:
        updated_positions = reset_visual_color_settings(connection)
        connection.commit()
        return {
            "message": "Visual colors reset successfully",
            "settings": get_app_settings(connection),
            "updated_positions": updated_positions,
            "default_position_color": DEFAULT_POSITION_COLOR,
        }
    finally:
        connection.close()


@app.post("/api/coverage-requirements", tags=["Requirements"])
def add_coverage_requirement(
    requirement: CoverageRequirementCreate,
    _access: dict | None = Depends(require_setup_edit_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        fetch_one_or_404(cursor, "SELECT id FROM positions WHERE id = ?", (requirement.position_id,), "Position not found")
        cursor.execute(
            """
            INSERT INTO coverage_requirements
                (position_id, start_time, end_time, required_total, required_female_min, required_male_min, is_overnight)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                requirement.position_id,
                requirement.start_time,
                requirement.end_time,
                requirement.required_total,
                requirement.required_female_min,
                requirement.required_male_min,
                int(requirement.is_overnight),
            ),
        )
        connection.commit()
        return {"message": "Coverage requirement added successfully", "coverage_requirement": {"id": cursor.lastrowid, **requirement.model_dump()}}
    finally:
        connection.close()


@app.put("/api/coverage-requirements/{requirement_id}", tags=["Requirements"])
def update_coverage_requirement(
    requirement_id: int,
    requirement: CoverageRequirementCreate,
    _access: dict | None = Depends(require_setup_edit_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        fetch_one_or_404(cursor, "SELECT id FROM coverage_requirements WHERE id = ?", (requirement_id,), "Coverage requirement not found")
        cursor.execute(
            """
            UPDATE coverage_requirements
            SET position_id = ?, start_time = ?, end_time = ?, required_total = ?, required_female_min = ?, required_male_min = ?, is_overnight = ?
            WHERE id = ?
            """,
            (
                requirement.position_id,
                requirement.start_time,
                requirement.end_time,
                requirement.required_total,
                requirement.required_female_min,
                requirement.required_male_min,
                int(requirement.is_overnight),
                requirement_id,
            ),
        )
        connection.commit()
        return {"message": "Coverage requirement updated successfully", "coverage_requirement": {"id": requirement_id, **requirement.model_dump()}}
    finally:
        connection.close()


@app.delete("/api/coverage-requirements/{requirement_id}", tags=["Requirements"])
def delete_coverage_requirement(
    requirement_id: int,
    _access: dict | None = Depends(require_setup_edit_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM coverage_requirements WHERE id = ?", (requirement_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Coverage requirement not found")
        connection.commit()
        return {"message": "Coverage requirement deleted successfully"}
    finally:
        connection.close()


@app.get("/api/employee-preferences", tags=["Preferences"])
def get_employee_preferences(preference_context: dict | None = Depends(require_preference_access_if_auth_initialized)):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        params = ()
        scope_filter = ""
        if preference_context and preference_context["scope"] == "own":
            scope_filter = "WHERE ep.employee_id = ?"
            params = (preference_context["membership"]["employee_id"],)
        cursor.execute(
            f"""
            SELECT ep.*, e.full_name AS employee_name
            FROM employee_preferences ep
            JOIN employees e ON e.id = ep.employee_id
            {scope_filter}
            ORDER BY ep.employee_id
            """,
            params,
        )
        items = [dict(row) for row in cursor.fetchall()]
        for item in items:
            for key in ("allow_morning", "allow_evening", "allow_night", "allow_morning_evening_combo"):
                item[key] = bool(item[key])
        return items
    finally:
        connection.close()


@app.post("/api/employee-preferences", tags=["Preferences"])
def save_employee_preference(
    preference: EmployeePreferenceCreate,
    preference_context: dict | None = Depends(require_preference_access_if_auth_initialized),
):
    require_employee_preference_scope(preference_context, preference.employee_id)
    organization_id = preference_context["membership"]["organization_id"] if preference_context else 1
    user_id = preference_context["user"]["id"] if preference_context else None
    connection = get_connection()
    try:
        cursor = connection.cursor()
        fetch_one_or_404(
            cursor,
            "SELECT id FROM employees WHERE id = ? AND organization_id = ?",
            (preference.employee_id, organization_id),
            "Employee not found",
        )
        now = current_utc_timestamp()
        cursor.execute(
            """
            INSERT INTO employee_preferences
                (organization_id, employee_id, allow_morning, allow_evening, allow_night,
                 allow_morning_evening_combo, updated_at, updated_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(employee_id)
            DO UPDATE SET allow_morning = excluded.allow_morning,
                          allow_evening = excluded.allow_evening,
                          allow_night = excluded.allow_night,
                          allow_morning_evening_combo = excluded.allow_morning_evening_combo,
                          updated_at = excluded.updated_at,
                          updated_by = excluded.updated_by
            """,
            (
                organization_id,
                preference.employee_id,
                int(preference.allow_morning),
                int(preference.allow_evening),
                int(preference.allow_night),
                int(preference.allow_morning_evening_combo),
                now,
                user_id,
            ),
        )
        write_auth_audit_event(
            cursor,
            "employee_preference_saved",
            user_id=user_id,
            organization_id=organization_id,
            metadata={"employee_id": preference.employee_id},
        )
        connection.commit()
        return {"message": "Employee preference saved successfully", "preference": preference.model_dump()}
    finally:
        connection.close()


@app.get("/api/employee-week-preferences", tags=["Weekly Preferences"])
def get_employee_week_preferences(
    week_start_date: str,
    preference_context: dict | None = Depends(require_preference_access_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        filters = ["ewp.week_start_date = ?"]
        params: list = [week_start_date]
        if preference_context:
            filters.append("ewp.organization_id = ?")
            params.append(preference_context["membership"]["organization_id"])
        if preference_context and preference_context["scope"] == "own":
            filters.append("ewp.employee_id = ?")
            params.append(preference_context["membership"]["employee_id"])
        cursor.execute(
            f"""
            SELECT ewp.*, e.full_name AS employee_name
            FROM employee_week_preferences ewp
            JOIN employees e ON e.id = ewp.employee_id
            WHERE {" AND ".join(filters)}
            ORDER BY ewp.employee_id, ewp.preference_date
            """,
            tuple(params),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        connection.close()


@app.post("/api/employee-week-preferences", tags=["Weekly Preferences"])
def save_employee_week_preference(
    preference: EmployeeWeekPreferenceCreate,
    preference_context: dict | None = Depends(require_preference_access_if_auth_initialized),
):
    require_employee_preference_scope(preference_context, preference.employee_id)
    organization_id = preference_context["membership"]["organization_id"] if preference_context else 1
    user_id = preference_context["user"]["id"] if preference_context else None
    connection = get_connection()
    try:
        cursor = connection.cursor()
        fetch_one_or_404(
            cursor,
            "SELECT id FROM employees WHERE id = ? AND organization_id = ?",
            (preference.employee_id, organization_id),
            "Employee not found",
        )
        now = current_utc_timestamp()
        cursor.execute(
            """
            INSERT INTO employee_week_preferences
                (organization_id, employee_id, week_start_date, preference_date, preference_type, updated_at, updated_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(employee_id, preference_date)
            DO UPDATE SET week_start_date = excluded.week_start_date,
                          preference_type = excluded.preference_type,
                          updated_at = excluded.updated_at,
                          updated_by = excluded.updated_by
            """,
            (
                organization_id,
                preference.employee_id,
                preference.week_start_date,
                preference.preference_date,
                preference.preference_type,
                now,
                user_id,
            ),
        )
        write_auth_audit_event(
            cursor,
            "employee_week_preference_saved",
            user_id=user_id,
            organization_id=organization_id,
            metadata={
                "employee_id": preference.employee_id,
                "week_start_date": preference.week_start_date,
                "preference_date": preference.preference_date,
                "preference_type": preference.preference_type,
            },
        )
        connection.commit()
        return {"message": "Weekly preference saved successfully", "preference": preference.model_dump()}
    finally:
        connection.close()


@app.delete("/api/employee-week-preferences", tags=["Weekly Preferences"])
def delete_employee_week_preference(
    employee_id: int,
    preference_date: str,
    preference_context: dict | None = Depends(require_preference_access_if_auth_initialized),
):
    require_employee_preference_scope(preference_context, employee_id)
    organization_id = preference_context["membership"]["organization_id"] if preference_context else 1
    user_id = preference_context["user"]["id"] if preference_context else None
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            DELETE FROM employee_week_preferences
            WHERE organization_id = ? AND employee_id = ? AND preference_date = ?
            """,
            (organization_id, employee_id, preference_date),
        )
        write_auth_audit_event(
            cursor,
            "employee_week_preference_deleted",
            user_id=user_id,
            organization_id=organization_id,
            metadata={"employee_id": employee_id, "preference_date": preference_date},
        )
        connection.commit()
        return {"message": "Weekly preference deleted successfully", "deleted_count": cursor.rowcount}
    finally:
        connection.close()


@app.get("/api/employee-recurring-preferences", tags=["Permanent Preferences"])
def get_employee_recurring_preferences(
    employee_id: int | None = None,
    admin_context: dict | None = Depends(require_permanent_preference_admin_if_auth_initialized),
):
    organization_id = admin_context["membership"]["organization_id"] if admin_context else 1
    connection = get_connection()
    try:
        cursor = connection.cursor()
        filters = ["erp.organization_id = ?"]
        params: list = [organization_id]
        if employee_id is not None:
            fetch_one_or_404(
                cursor,
                "SELECT id FROM employees WHERE id = ? AND organization_id = ?",
                (employee_id, organization_id),
                "Employee not found",
            )
            filters.append("erp.employee_id = ?")
            params.append(employee_id)
        cursor.execute(
            f"""
            SELECT erp.*, e.full_name AS employee_name
            FROM employee_recurring_preferences erp
            JOIN employees e ON e.id = erp.employee_id
            WHERE {" AND ".join(filters)}
            ORDER BY erp.employee_id, erp.preference_kind, erp.day_of_week
            """,
            tuple(params),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        connection.close()


@app.post("/api/employee-recurring-preferences", tags=["Permanent Preferences"])
def save_employee_recurring_preferences(
    request_data: EmployeeRecurringPreferencesUpdate,
    admin_context: dict | None = Depends(require_permanent_preference_admin_if_auth_initialized),
):
    organization_id = admin_context["membership"]["organization_id"] if admin_context else 1
    user_id = admin_context["user"]["id"] if admin_context else None
    connection = get_connection()
    try:
        cursor = connection.cursor()
        fetch_one_or_404(
            cursor,
            "SELECT id FROM employees WHERE id = ? AND organization_id = ?",
            (request_data.employee_id, organization_id),
            "Employee not found",
        )
        now = current_utc_timestamp()
        cursor.execute(
            """
            DELETE FROM employee_recurring_preferences
            WHERE organization_id = ? AND employee_id = ?
            """,
            (organization_id, request_data.employee_id),
        )
        saved_rules = []
        for rule in request_data.rules:
            if rule.preference_type == "no_preference":
                continue
            if rule.preference_type not in PERSISTED_RECURRING_PREFERENCE_TYPES:
                raise HTTPException(status_code=400, detail="Unsupported permanent preference type")
            cursor.execute(
                """
                INSERT INTO employee_recurring_preferences (
                    organization_id, employee_id, preference_kind, day_of_week,
                    preference_type, created_at, updated_at, updated_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    organization_id,
                    request_data.employee_id,
                    rule.preference_kind,
                    rule.day_of_week,
                    rule.preference_type,
                    now,
                    now,
                    user_id,
                ),
            )
            saved_rules.append(rule.model_dump())
        write_auth_audit_event(
            cursor,
            "employee_recurring_preferences_saved",
            user_id=user_id,
            organization_id=organization_id,
            metadata={"employee_id": request_data.employee_id, "rule_count": len(saved_rules)},
        )
        connection.commit()
        return {
            "message": "Permanent preferences saved successfully",
            "employee_id": request_data.employee_id,
            "rules": saved_rules,
        }
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@app.get("/api/employee-day-statuses", tags=["Schedule"])
def get_employee_day_statuses(
    position_id: int | None = None,
    access_context: dict | None = Depends(require_schedule_view_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        employee_id = employee_scope_from_access(access_context)
        params: tuple = ()
        where_sql = ""
        if employee_id is not None and position_id is not None:
            require_employee_position_scope(cursor, employee_id, position_id)
            where_sql = """
            WHERE eds.employee_id IN (
                SELECT ep.employee_id
                FROM employee_positions ep
                WHERE ep.position_id = ?
            )
            """
            params = (position_id,)
        elif employee_id is not None:
            where_sql = "WHERE eds.employee_id = ?"
            params = (employee_id,)
        elif position_id is not None:
            where_sql = """
            WHERE eds.employee_id IN (
                SELECT ep.employee_id
                FROM employee_positions ep
                WHERE ep.position_id = ?
            )
            """
            params = (position_id,)
        cursor.execute(
            f"""
            SELECT eds.*, e.full_name AS employee_name
            FROM employee_day_statuses eds
            JOIN employees e ON e.id = eds.employee_id
            {where_sql}
            ORDER BY eds.date, eds.employee_id
            """,
            params,
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        connection.close()


@app.post("/api/employee-day-statuses", tags=["Schedule"])
def save_employee_day_status(
    status: EmployeeDayStatusCreate,
    _access: dict | None = Depends(require_schedule_edit_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        fetch_one_or_404(cursor, "SELECT id FROM employees WHERE id = ?", (status.employee_id,), "Employee not found")
        cursor.execute(
            """
            INSERT INTO employee_day_statuses (employee_id, date, status_type)
            VALUES (?, ?, ?)
            ON CONFLICT(employee_id, date)
            DO UPDATE SET status_type = excluded.status_type
            """,
            (status.employee_id, status.date, status.status_type),
        )
        connection.commit()
        return {"message": "Employee day status saved successfully", "status": status.model_dump()}
    finally:
        connection.close()


@app.delete("/api/employee-day-statuses", tags=["Schedule"])
def delete_employee_day_status(
    employee_id: int,
    date: str,
    _access: dict | None = Depends(require_schedule_edit_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM employee_day_statuses WHERE employee_id = ? AND date = ?", (employee_id, date))
        connection.commit()
        return {"message": "Employee day status deleted successfully"}
    finally:
        connection.close()


def get_employee_day_status_map(connection, employee_ids: list[int], dates: list[str]) -> dict[tuple[int, str], dict]:
    if not employee_ids or not dates:
        return {}

    cursor = connection.cursor()
    employee_placeholders = ",".join(["?"] * len(employee_ids))
    date_placeholders = ",".join(["?"] * len(dates))
    cursor.execute(
        f"""
        SELECT *
        FROM employee_day_statuses
        WHERE employee_id IN ({employee_placeholders})
          AND date IN ({date_placeholders})
        """,
        [*employee_ids, *dates],
    )
    return {(row["employee_id"], row["date"]): dict(row) for row in cursor.fetchall()}


def sync_employee_day_off_status_for_date(connection, cursor, employee_id: int, date_string: str) -> None:
    cursor.execute(
        """
        SELECT 1
        FROM schedule_entries
        WHERE employee_id = ? AND date = ?
        LIMIT 1
        """,
        (employee_id, date_string),
    )
    has_any_schedule_entry = cursor.fetchone() is not None

    if has_any_schedule_entry:
        cursor.execute(
            """
            DELETE FROM employee_day_statuses
            WHERE employee_id = ? AND date = ? AND status_type = 'day_off'
            """,
            (employee_id, date_string),
        )
        return

    cursor.execute(
        """
        SELECT status_type
        FROM employee_day_statuses
        WHERE employee_id = ? AND date = ?
        """,
        (employee_id, date_string),
    )
    existing_status = cursor.fetchone()
    if existing_status is not None:
        return

    cursor.execute(
        """
        INSERT INTO employee_day_statuses (employee_id, date, status_type)
        VALUES (?, ?, 'day_off')
        """,
        (employee_id, date_string),
    )


def sync_generated_day_off_statuses(
    connection,
    cursor,
    employees: list[dict],
    position_id: int,
    dates: list[str],
) -> int:
    employee_ids = [employee["id"] for employee in employees]
    if not employee_ids or not dates:
        return 0

    employee_placeholders = ",".join(["?"] * len(employee_ids))
    date_placeholders = ",".join(["?"] * len(dates))
    cursor.execute(
        f"""
        DELETE FROM employee_day_statuses
        WHERE status_type = 'day_off'
          AND employee_id IN ({employee_placeholders})
          AND date IN ({date_placeholders})
        """,
        [*employee_ids, *dates],
    )

    entries = get_schedule_entries(connection, dates=dates)
    employee_id_set = set(employee_ids)
    scheduled_days = {
        (entry["employee_id"], entry["date"])
        for entry in entries
        if entry["employee_id"] in employee_id_set
    }
    day_status_map = get_employee_day_status_map(connection, employee_ids, dates)

    inserted_count = 0
    for employee_id in employee_ids:
        for date_string in dates:
            if (employee_id, date_string) in scheduled_days:
                continue
            if (employee_id, date_string) in day_status_map:
                continue
            cursor.execute(
                """
                INSERT INTO employee_day_statuses (employee_id, date, status_type)
                VALUES (?, ?, 'day_off')
                """,
                (employee_id, date_string),
            )
            inserted_count += 1

    return inserted_count


# =========================
# Schedule and generator
# =========================


def get_schedule_entries(
    connection,
    position_id: int | None = None,
    dates: list[str] | None = None,
    employee_id: int | None = None,
) -> list[dict]:
    cursor = connection.cursor()
    clauses = []
    params: list = []
    if position_id is not None:
        clauses.append("se.position_id = ?")
        params.append(position_id)
    if dates:
        clauses.append(f"se.date IN ({','.join(['?'] * len(dates))})")
        params.extend(dates)
    if employee_id is not None:
        clauses.append("se.employee_id = ?")
        params.append(employee_id)
    where_sql = "WHERE " + " AND ".join(clauses) if clauses else ""
    cursor.execute(
        f"""
        SELECT
            se.id,
            se.employee_id,
            se.position_id,
            se.date,
            se.shift_template_id,
            se.no_show,
            st.name AS shift_template_name,
            st.category AS shift_category,
            st.start_time,
            st.end_time,
            st.is_overnight,
            st.is_split_only,
            p.name AS position_name,
            p.color AS position_color,
            e.full_name AS employee_name,
            e.sex AS employee_sex
        FROM schedule_entries se
        JOIN shift_templates st ON st.id = se.shift_template_id
        JOIN positions p ON p.id = se.position_id
        JOIN employees e ON e.id = se.employee_id
        {where_sql}
        ORDER BY se.date, se.employee_id, se.position_id, st.start_time
        """,
        params,
    )
    items = [dict(row) for row in cursor.fetchall()]
    for item in items:
        item["is_overnight"] = bool(item["is_overnight"])
        item["is_split_only"] = bool(item["is_split_only"])
        item["no_show"] = bool(item["no_show"])
    return items


@app.get("/api/schedule", tags=["Schedule"])
def get_schedule(
    position_id: int | None = None,
    access_context: dict | None = Depends(require_schedule_view_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        employee_id = employee_scope_from_access(access_context)
        if employee_id is not None and position_id is not None:
            require_employee_position_scope(cursor, employee_id, position_id)
            return get_schedule_entries(connection, position_id=position_id)
        return get_schedule_entries(connection, position_id=position_id, employee_id=employee_id)
    finally:
        connection.close()


@app.post("/api/schedule", tags=["Schedule"])
def add_schedule_entry(entry: ScheduleEntryCreate, _access: dict | None = Depends(require_schedule_edit_if_auth_initialized)):
    connection = get_connection()
    try:
        validate_manual_schedule_entry_basics(connection, entry)
        cursor = connection.cursor()
        organization_id = _access["membership"]["organization_id"] if _access else 1
        require_license_capability(cursor, "can_create_shift", organization_id)
        cursor.execute(
            """
            INSERT INTO schedule_entries (employee_id, position_id, date, shift_template_id)
            VALUES (?, ?, ?, ?)
            """,
            (entry.employee_id, entry.position_id, entry.date, entry.shift_template_id),
        )
        sync_employee_day_off_status_for_date(connection, cursor, entry.employee_id, entry.date)
        connection.commit()
        return {"message": "Schedule entry added successfully", "schedule_entry": {**entry.model_dump(), "id": cursor.lastrowid}}
    finally:
        connection.close()


@app.delete("/api/schedule/{schedule_entry_id}", tags=["Schedule"])
def delete_schedule_entry(
    schedule_entry_id: int,
    _access: dict | None = Depends(require_schedule_edit_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        entry_row = fetch_one_or_404(
            cursor,
            "SELECT employee_id, date FROM schedule_entries WHERE id = ?",
            (schedule_entry_id,),
            "Schedule entry not found",
        )
        cursor.execute("DELETE FROM schedule_entries WHERE id = ?", (schedule_entry_id,))
        sync_employee_day_off_status_for_date(connection, cursor, entry_row["employee_id"], entry_row["date"])
        connection.commit()
        return {"message": "Schedule entry deleted successfully", "deleted_count": cursor.rowcount}
    finally:
        connection.close()


@app.patch("/api/schedule/{schedule_entry_id}/status", tags=["Schedule"])
def update_schedule_entry_status(
    schedule_entry_id: int,
    status: ScheduleEntryStatusUpdate,
    _access: dict | None = Depends(require_schedule_edit_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE schedule_entries SET no_show = ? WHERE id = ?",
            (int(status.no_show), schedule_entry_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Schedule entry not found")
        connection.commit()
        return {"message": "Schedule entry status updated successfully", "id": schedule_entry_id, "no_show": status.no_show}
    finally:
        connection.close()


@app.post("/api/schedule/clear-week", tags=["Schedule"])
def clear_week_schedule(
    request_data: ClearWeekScheduleRequest,
    _access: dict | None = Depends(require_schedule_edit_if_auth_initialized),
):
    connection = get_connection()
    try:
        week_dates = build_week_dates(request_data.week_start_date)
        cursor = connection.cursor()
        backup_name = create_recovery_backup("clear_week")
        cursor.execute(
            f"""
            DELETE FROM schedule_entries
            WHERE position_id = ? AND date IN ({','.join(['?'] * len(week_dates))})
            """,
            [request_data.position_id, *week_dates],
        )
        deleted_count = cursor.rowcount
        employees = load_position_employees(connection, request_data.position_id)
        employee_ids = [employee["id"] for employee in employees]
        if employee_ids:
            cursor.execute(
                f"""
                DELETE FROM employee_day_statuses
                WHERE status_type = 'day_off'
                  AND employee_id IN ({','.join(['?'] * len(employee_ids))})
                  AND date IN ({','.join(['?'] * len(week_dates))})
                """,
                [*employee_ids, *week_dates],
            )
        connection.commit()
        return {
            "message": "Week schedule cleared successfully",
            "deleted_count": deleted_count,
            "backup_name": backup_name,
        }
    finally:
        connection.close()


@app.get("/api/schedule/clear-week-preview", tags=["Schedule"])
def get_clear_week_schedule_preview(
    position_id: int,
    week_start_date: str,
    _access: dict | None = Depends(require_schedule_edit_if_auth_initialized),
):
    connection = get_connection()
    try:
        week_dates = build_week_dates(week_start_date)
        cursor = connection.cursor()
        position_row = fetch_one_or_404(
            cursor,
            "SELECT id, name FROM positions WHERE id = ?",
            (position_id,),
            "Position not found",
        )
        employees = load_position_employees(connection, position_id)
        employee_ids = [employee["id"] for employee in employees]
        day_status_count = 0

        if employee_ids:
            cursor.execute(
                f"""
                SELECT COUNT(*)
                FROM employee_day_statuses
                WHERE status_type = 'day_off'
                  AND employee_id IN ({','.join(['?'] * len(employee_ids))})
                  AND date IN ({','.join(['?'] * len(week_dates))})
                """,
                [*employee_ids, *week_dates],
            )
            day_status_count = int(cursor.fetchone()[0])

        return {
            "position_id": position_row["id"],
            "position_name": position_row["name"],
            "week_start_date": week_start_date,
            "assigned_employees": len(employee_ids),
            "schedule_entries": fetch_count(
                cursor,
                f"""
                SELECT COUNT(*)
                FROM schedule_entries
                WHERE position_id = ? AND date IN ({','.join(['?'] * len(week_dates))})
                """,
                (position_id, *week_dates),
            ),
            "day_off_statuses": day_status_count,
        }
    finally:
        connection.close()


@app.post("/api/schedule/clear-week-all", tags=["Schedule"])
def clear_all_week_schedules(
    request_data: ClearAllWeekScheduleRequest,
    _access: dict | None = Depends(require_schedule_edit_if_auth_initialized),
):
    connection = get_connection()
    try:
        week_dates = build_week_dates(request_data.week_start_date)
        cursor = connection.cursor()
        backup_name = create_recovery_backup("clear_week_all")
        cursor.execute(
            f"""
            DELETE FROM schedule_entries
            WHERE date IN ({','.join(['?'] * len(week_dates))})
            """,
            week_dates,
        )
        deleted_count = cursor.rowcount
        cursor.execute(
            f"""
            DELETE FROM employee_day_statuses
            WHERE status_type = 'day_off'
              AND date IN ({','.join(['?'] * len(week_dates))})
            """,
            week_dates,
        )
        day_off_deleted_count = cursor.rowcount
        connection.commit()
        return {
            "message": "All week schedules cleared successfully",
            "deleted_count": deleted_count,
            "day_off_deleted_count": day_off_deleted_count,
            "backup_name": backup_name,
        }
    finally:
        connection.close()


@app.get("/api/schedule/clear-week-all-preview", tags=["Schedule"])
def get_clear_all_week_schedules_preview(
    week_start_date: str,
    _access: dict | None = Depends(require_schedule_edit_if_auth_initialized),
):
    connection = get_connection()
    try:
        week_dates = build_week_dates(week_start_date)
        cursor = connection.cursor()
        return {
            "week_start_date": week_start_date,
            "positions": fetch_count(cursor, "SELECT COUNT(*) FROM positions"),
            "schedule_entries": fetch_count(
                cursor,
                f"""
                SELECT COUNT(*)
                FROM schedule_entries
                WHERE date IN ({','.join(['?'] * len(week_dates))})
                """,
                tuple(week_dates),
            ),
            "day_off_statuses": fetch_count(
                cursor,
                f"""
                SELECT COUNT(*)
                FROM employee_day_statuses
                WHERE status_type = 'day_off'
                  AND date IN ({','.join(['?'] * len(week_dates))})
                """,
                tuple(week_dates),
            ),
        }
    finally:
        connection.close()


def load_position_employees(connection, position_id: int) -> list[dict]:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT e.*, ep.is_primary, ep.priority_score, ep.is_fallback_only
        FROM employees e
        JOIN employee_positions ep ON ep.employee_id = e.id
        WHERE ep.position_id = ?
        ORDER BY ep.is_fallback_only ASC, ep.is_primary DESC, ep.priority_score DESC, e.id
        """,
        (position_id,),
    )
    employees = []
    for row in cursor.fetchall():
        employee = row_to_employee_dict(row)
        employee["is_primary"] = bool(row["is_primary"])
        employee["priority_score"] = row["priority_score"]
        employee["is_fallback_only"] = bool(row["is_fallback_only"])
        employees.append(employee)
    return employees


def load_active_templates(connection, position_id: int) -> list[dict]:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT st.*, p.name AS position_name
        FROM shift_templates st
        JOIN positions p ON p.id = st.position_id
        WHERE st.position_id = ? AND st.is_active = 1
        ORDER BY st.start_time, st.end_time, st.category
        """,
        (position_id,),
    )
    return [row_to_shift_template_dict(row) for row in cursor.fetchall()]


def load_coverage_requirements_for_position(connection, position_id: int) -> list[dict]:
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM coverage_requirements WHERE position_id = ? ORDER BY start_time", (position_id,))
    return [dict(row) for row in cursor.fetchall()]


def load_legacy_shift_requirements(connection, position_id: int) -> list[dict]:
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM shift_requirements WHERE position_id = ?", (position_id,))
    return [dict(row) for row in cursor.fetchall()]


def build_atomic_slots(requirements: list[dict], templates: list[dict]) -> list[dict]:
    points = {0, 24 * 60}
    normalized_requirements = []
    for requirement in requirements:
        interval = build_interval(requirement["start_time"], requirement["end_time"], bool(requirement["is_overnight"]))
        normalized_requirements.append((interval, requirement))
        points.add(interval.start)
        points.add(interval.end)

    for template in templates:
        interval = build_interval(template["start_time"], template["end_time"], template["is_overnight"])
        points.add(interval.start)
        points.add(interval.end)

    sorted_points = sorted(points)
    slots = []
    for index in range(len(sorted_points) - 1):
        start = sorted_points[index]
        end = sorted_points[index + 1]
        if start == end:
            continue
        required_total = 0
        required_female = 0
        required_male = 0
        for interval, requirement in normalized_requirements:
            if interval.contains(start, end):
                required_total = max(required_total, requirement["required_total"])
                required_female = max(required_female, requirement["required_female_min"])
                required_male = max(required_male, requirement["required_male_min"])
        if required_total > 0 or required_female > 0 or required_male > 0:
            slots.append({
                "start": start,
                "end": end,
                "required_total": required_total,
                "required_female_min": required_female,
                "required_male_min": required_male,
            })
    return slots


def count_slot_coverage(entries: list[dict], slot: dict) -> tuple[int, int, int]:
    total = 0
    female = 0
    male = 0
    for entry in entries:
        if entry.get("no_show"):
            continue
        interval = build_interval(entry["start_time"], entry["end_time"], bool(entry["is_overnight"]))
        if interval.contains(slot["start"], slot["end"]):
            total += 1
            if entry.get("employee_sex") == "female":
                female += 1
            if entry.get("employee_sex") == "male":
                male += 1
    return total, female, male


def coverage_shortage(entries: list[dict], slots: list[dict]) -> int:
    shortage = 0
    for slot in slots:
        total, female, male = count_slot_coverage(entries, slot)
        shortage += max(0, slot["required_total"] - total) * 10
        shortage += max(0, slot["required_female_min"] - female) * 4
        shortage += max(0, slot["required_male_min"] - male) * 4
    return shortage


def coverage_overage(entries: list[dict], slots: list[dict]) -> int:
    overage = 0
    for slot in slots:
        total, _female, _male = count_slot_coverage(entries, slot)
        overage += max(0, total - slot["required_total"])
    return overage


def slot_shortage_score(entries: list[dict], slot: dict) -> int:
    total, female, male = count_slot_coverage(entries, slot)
    return (
        max(0, slot["required_total"] - total) * 10
        + max(0, slot["required_female_min"] - female) * 4
        + max(0, slot["required_male_min"] - male) * 4
    )


def template_covers_slot(template: dict, slot: dict) -> bool:
    interval = build_interval(template["start_time"], template["end_time"], template["is_overnight"])
    return interval.contains(slot["start"], slot["end"])


def get_employee_week_category_count(connection, employee_id: int, week_start_date: str, category: str) -> int:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM schedule_entries se
        JOIN shift_templates st ON st.id = se.shift_template_id
        WHERE se.employee_id = ?
          AND se.date >= ?
          AND se.date <= ?
          AND st.category = ?
          AND se.no_show = 0
        """,
        (employee_id, week_start_date, get_week_end_date(week_start_date), category),
    )
    return cursor.fetchone()["cnt"]


def get_employee_week_split_day_count(connection, employee_id: int, week_start_date: str) -> int:
    return sum(
        1
        for date_string in build_week_dates(week_start_date)
        if employee_has_split_day(connection, employee_id, date_string)
    )


def candidate_priority(connection, employee: dict, date_string: str, week_start_date: str) -> tuple:
    week_count = get_employee_week_shift_count(connection, employee["id"], week_start_date)
    worked_dates = get_employee_week_worked_dates(connection, employee["id"], week_start_date)
    night_count = get_employee_week_category_count(connection, employee["id"], week_start_date, "night")
    split_count = get_employee_week_split_day_count(connection, employee["id"], week_start_date)
    if week_count < employee["min_shifts_per_week"]:
        bucket = 0
    elif week_count < employee["target_shifts_per_week"]:
        bucket = 1
    else:
        bucket = 2
    fallback_penalty = 1 if employee.get("is_fallback_only") else 0
    primary_bonus = 0 if employee.get("is_primary") else 1
    return (
        bucket,
        len(worked_dates),
        week_count,
        night_count,
        split_count,
        fallback_penalty,
        primary_bonus,
        -int(employee.get("priority_score", 50)),
        employee["id"],
    )


def create_entry_preview(employee: dict, position_id: int, date_string: str, template: dict) -> dict:
    return {
        "id": -1,
        "employee_id": employee["id"],
        "position_id": position_id,
        "date": date_string,
        "shift_template_id": template["id"],
        "shift_template_name": template["name"],
        "shift_category": template["category"],
        "start_time": template["start_time"],
        "end_time": template["end_time"],
        "is_overnight": template["is_overnight"],
        "is_split_only": template["is_split_only"],
        "employee_name": employee["full_name"],
        "employee_sex": employee["sex"],
    }


def template_start_minutes(template: dict) -> int:
    return time_to_minutes(template["start_time"])


def build_template_assignment_options(template: dict, templates: list[dict]) -> list[list[dict]]:
    return [[template]]


def build_valid_assignment_previews(
    connection,
    employee: dict,
    assignment_templates: list[dict],
    position_id: int,
    date_string: str,
    week_start_date: str,
    fatigue_relaxation: int = 0,
) -> list[dict] | None:
    staged_entries: list[dict] = []

    for template in assignment_templates:
        if not can_employee_take_template(
            connection,
            employee,
            position_id,
            date_string,
            template,
            week_start_date,
            fatigue_relaxation=fatigue_relaxation,
            staged_entries=staged_entries,
        ):
            return None
        staged_entries.append(create_entry_preview(employee, position_id, date_string, template))

    return staged_entries


def choose_best_interval_candidate(
    connection,
    employees: list[dict],
    templates: list[dict],
    position_id: int,
    date_string: str,
    week_start_date: str,
    current_entries: list[dict],
    slots: list[dict],
    fatigue_relaxation: int = 0,
    target_slot: dict | None = None,
):
    app_settings = get_position_app_settings(connection, position_id)
    baseline_shortage = coverage_shortage(current_entries, slots)
    baseline_overage = coverage_overage(current_entries, slots)
    baseline_target_shortage = slot_shortage_score(current_entries, target_slot) if target_slot is not None else 0
    target_needs_female = False
    target_needs_male = False
    target_needs_total = False
    if target_slot is not None:
        target_total, target_female, target_male = count_slot_coverage(current_entries, target_slot)
        target_needs_total = target_total < target_slot["required_total"]
        target_needs_female = target_female < target_slot["required_female_min"]
        target_needs_male = target_male < target_slot["required_male_min"]
    candidates = []

    for employee in employees:
        if target_slot is not None and not target_needs_total:
            if target_needs_female and employee["sex"] != "female":
                continue
            if target_needs_male and employee["sex"] != "male":
                continue
        for template in templates:
            if target_slot is not None and not template_covers_slot(template, target_slot):
                continue
            for assignment_templates in build_template_assignment_options(template, templates):
                previews = build_valid_assignment_previews(
                    connection,
                    employee,
                    assignment_templates,
                    position_id,
                    date_string,
                    week_start_date,
                    fatigue_relaxation=fatigue_relaxation,
                )
                if previews is None:
                    continue

                projected_entries = [*current_entries, *previews]
                shortage_gain = baseline_shortage - coverage_shortage(projected_entries, slots)
                overage_cost = coverage_overage(projected_entries, slots) - baseline_overage
                target_shortage_gain = (
                    baseline_target_shortage - slot_shortage_score(projected_entries, target_slot)
                    if target_slot is not None
                    else 0
                )
                score = (
                    shortage_gain * app_settings["coverage_shortage_gain_weight"]
                    - overage_cost * app_settings["coverage_overage_penalty_weight"]
                )
                if target_slot is not None:
                    if target_needs_female and employee["sex"] == "female":
                        score += app_settings["target_gender_bonus_weight"]
                    if target_needs_male and employee["sex"] == "male":
                        score += app_settings["target_gender_bonus_weight"]
                    if (target_needs_female and employee["sex"] != "female") or (target_needs_male and employee["sex"] != "male"):
                        score -= app_settings["wrong_gender_penalty_weight"]
                if target_slot is not None:
                    if target_shortage_gain <= 0:
                        continue
                elif score <= 0:
                    continue

                soft_preference_penalty = soft_recurring_preference_penalty(
                    connection,
                    employee["id"],
                    date_string,
                    assignment_templates,
                    projected_entries,
                )
                fatigue_penalty = sum(
                    get_fatigue_penalty(connection, employee["id"], date_string, assignment_template)
                    for assignment_template in assignment_templates
                )
                projected_same_category_count, projected_same_category_streak = get_projected_category_metrics(
                    connection,
                    employee,
                    week_start_date,
                    previews,
                    [assignment_template["category"] for assignment_template in assignment_templates],
                )
                projected_night_count, projected_split_count = get_projected_assignment_counts(
                    connection,
                    employee,
                    week_start_date,
                    previews,
                )
                projected_balance = get_projected_assignment_score(
                    connection,
                    employee,
                    week_start_date,
                    previews,
                    app_settings,
                )
                candidates.append((
                    (
                        -target_shortage_gain if target_slot is not None else -score,
                        soft_preference_penalty,
                        -score,
                        overage_cost,
                        fatigue_penalty,
                        projected_same_category_count,
                        projected_same_category_streak,
                        projected_night_count,
                        projected_split_count,
                        projected_balance,
                        candidate_priority(connection, employee, date_string, week_start_date),
                    ),
                    employee,
                    assignment_templates,
                    score,
                ))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0])
    return candidates[0][1], candidates[0][2], candidates[0][3]


def insert_generated_entry(cursor, employee: dict, position_id: int, date_string: str, template: dict, created_entries: list[dict]):
    cursor.execute(
        """
        INSERT INTO schedule_entries (employee_id, position_id, date, shift_template_id)
        VALUES (?, ?, ?, ?)
        """,
        (employee["id"], position_id, date_string, template["id"]),
    )
    created_entries.append(
        {
            "id": cursor.lastrowid,
            "employee_id": employee["id"],
            "employee_name": employee["full_name"],
            "date": date_string,
            "shift_template_name": template["name"],
            "shift_category": template["category"],
        }
    )


def insert_generated_assignment(cursor, employee: dict, position_id: int, date_string: str, templates: list[dict], created_entries: list[dict]):
    for template in templates:
        insert_generated_entry(cursor, employee, position_id, date_string, template, created_entries)


def count_candidate_options_for_slot(
    connection,
    employees: list[dict],
    templates: list[dict],
    position_id: int,
    date_string: str,
    week_start_date: str,
    slot: dict,
    fatigue_relaxation: int = 0,
) -> int:
    count = 0
    for employee in employees:
        for template in templates:
            if not template_covers_slot(template, slot):
                continue
            if any(
                build_valid_assignment_previews(
                    connection,
                    employee,
                    assignment_templates,
                    position_id,
                    date_string,
                    week_start_date,
                    fatigue_relaxation=fatigue_relaxation,
                )
                is not None
                for assignment_templates in build_template_assignment_options(template, templates)
            ):
                count += 1
    return count


def format_slot_time(slot: dict) -> str:
    return f"{slot['start'] // 60:02d}:{slot['start'] % 60:02d}-{slot['end'] // 60 % 24:02d}:{slot['end'] % 60:02d}"


def slot_to_report(slot: dict) -> dict:
    return {
        "start": f"{slot['start'] // 60:02d}:{slot['start'] % 60:02d}",
        "end": f"{slot['end'] // 60 % 24:02d}:{slot['end'] % 60:02d}",
        "required_total": slot["required_total"],
        "required_female_min": slot["required_female_min"],
        "required_male_min": slot["required_male_min"],
    }


def summarize_reasons(reason_counts: dict[str, int], limit: int = 4) -> str:
    if not reason_counts:
        return "no available employees found"
    ordered = sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))
    return "; ".join(f"{reason} ({count})" for reason, count in ordered[:limit])


def explain_unfilled_interval_slot(
    connection,
    employees: list[dict],
    templates: list[dict],
    position_id: int,
    date_string: str,
    week_start_date: str,
    slot: dict,
    require_female: bool = False,
    require_male: bool = False,
) -> str:
    covering_templates = [template for template in templates if template_covers_slot(template, slot)]
    if not covering_templates:
        return "no active shift template covers this time interval"

    reason_counts: dict[str, int] = {}
    for employee in employees:
        if require_female and employee["sex"] != "female":
            reason_counts["not enough female employees available"] = reason_counts.get("not enough female employees available", 0) + 1
            continue
        if require_male and employee["sex"] != "male":
            reason_counts["not enough male employees available"] = reason_counts.get("not enough male employees available", 0) + 1
            continue

        employee_had_relevant_template = False
        for template in covering_templates:
            for assignment_templates in build_template_assignment_options(template, templates):
                staged_entries: list[dict] = []
                option_reason = None
                for assignment_template in assignment_templates:
                    reason = explain_employee_template_rejection(
                        connection,
                        employee,
                        position_id,
                        date_string,
                        assignment_template,
                        week_start_date,
                        fatigue_relaxation=1,
                        staged_entries=staged_entries,
                    )
                    if reason:
                        option_reason = reason
                        break
                    staged_entries.append(create_entry_preview(employee, position_id, date_string, assignment_template))

                if option_reason is None:
                    employee_had_relevant_template = True
                    break
                reason_counts[option_reason] = reason_counts.get(option_reason, 0) + 1

            if employee_had_relevant_template:
                break

    if not reason_counts:
        return "candidates existed, but they did not improve coverage without overfilling other intervals"

    return summarize_reasons(reason_counts)


def build_interval_underfilled_message(
    connection,
    employees: list[dict],
    templates: list[dict],
    position_id: int,
    week_start_date: str,
    date_string: str,
    slot: dict,
    total: int,
    female: int,
    male: int,
) -> str:
    require_female = female < slot["required_female_min"]
    require_male = male < slot["required_male_min"]
    reasons = explain_unfilled_interval_slot(
        connection,
        employees,
        templates,
        position_id,
        date_string,
        week_start_date,
        slot,
        require_female=require_female,
        require_male=require_male,
    )
    return (
        f"{date_string} {format_slot_time(slot)} underfilled: "
        f"staff {total}/{slot['required_total']}, women {female}/{slot['required_female_min']}, "
        f"men {male}/{slot['required_male_min']}. "
        f"Reasons: {reasons}"
    )


def build_interval_underfilled_report(
    connection,
    employees: list[dict],
    templates: list[dict],
    position_id: int,
    week_start_date: str,
    date_string: str,
    slot: dict,
    total: int,
    female: int,
    male: int,
) -> dict:
    require_female = female < slot["required_female_min"]
    require_male = male < slot["required_male_min"]
    reasons = explain_unfilled_interval_slot(
        connection,
        employees,
        templates,
        position_id,
        date_string,
        week_start_date,
        slot,
        require_female=require_female,
        require_male=require_male,
    )
    return {
        "kind": "interval",
        "date": date_string,
        "slot": slot_to_report(slot),
        "actual": {
            "total": total,
            "female": female,
            "male": male,
        },
        "missing": {
            "total": max(0, slot["required_total"] - total),
            "female": max(0, slot["required_female_min"] - female),
            "male": max(0, slot["required_male_min"] - male),
        },
        "reasons": reasons,
    }


def build_legacy_underfilled_report(
    connection,
    employees: list[dict],
    templates: list[dict],
    position_id: int,
    week_start_date: str,
    date_string: str,
    requirement: dict,
    total: int,
    female: int,
    male: int,
) -> dict:
    require_female = female < requirement["required_female_min"]
    require_male = male < requirement["required_male_min"]
    reasons = explain_unfilled_legacy_category(
        connection,
        employees,
        templates,
        position_id,
        date_string,
        week_start_date,
        requirement["shift_category"],
        require_female=require_female,
        require_male=require_male,
    )
    return {
        "kind": "legacy_category",
        "date": date_string,
        "shift_category": requirement["shift_category"],
        "actual": {
            "total": total,
            "female": female,
            "male": male,
        },
        "missing": {
            "total": max(0, requirement["required_total"] - total),
            "female": max(0, requirement["required_female_min"] - female),
            "male": max(0, requirement["required_male_min"] - male),
        },
        "reasons": reasons,
    }


def explain_unfilled_legacy_category(
    connection,
    employees: list[dict],
    templates: list[dict],
    position_id: int,
    date_string: str,
    week_start_date: str,
    category: str,
    require_female: bool = False,
    require_male: bool = False,
) -> str:
    category_templates = [template for template in templates if template["category"] == category]
    if not category_templates:
        return f"no active {category} templates"

    reason_counts: dict[str, int] = {}
    for employee in employees:
        if require_female and employee["sex"] != "female":
            reason_counts["not enough female employees available"] = reason_counts.get("not enough female employees available", 0) + 1
            continue
        if require_male and employee["sex"] != "male":
            reason_counts["not enough male employees available"] = reason_counts.get("not enough male employees available", 0) + 1
            continue

        for template in category_templates:
            reason = explain_employee_template_rejection(
                connection,
                employee,
                position_id,
                date_string,
                template,
                week_start_date,
                fatigue_relaxation=1,
            )
            if reason is None:
                break
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

    return summarize_reasons(reason_counts)


def build_week_shortage_queue(
    connection,
    employees: list[dict],
    templates: list[dict],
    position_id: int,
    week_start_date: str,
    week_dates: list[str],
    slots: list[dict],
) -> list[dict]:
    queue = []
    for date_index, date_string in enumerate(week_dates):
        entries = get_schedule_entries(connection, position_id=position_id, dates=[date_string])
        for slot in slots:
            total, female, male = count_slot_coverage(entries, slot)
            missing_total = max(0, slot["required_total"] - total)
            missing_female = max(0, slot["required_female_min"] - female)
            missing_male = max(0, slot["required_male_min"] - male)
            if missing_total <= 0 and missing_female <= 0 and missing_male <= 0:
                continue

            strict_candidates = count_candidate_options_for_slot(
                connection,
                employees,
                templates,
                position_id,
                date_string,
                week_start_date,
                slot,
                fatigue_relaxation=0,
            )
            emergency_candidates = strict_candidates or count_candidate_options_for_slot(
                connection,
                employees,
                templates,
                position_id,
                date_string,
                week_start_date,
                slot,
                fatigue_relaxation=1,
            )
            scarcity = strict_candidates if strict_candidates > 0 else emergency_candidates + 1000
            queue.append(
                {
                    "date": date_string,
                    "date_index": date_index,
                    "slot": slot,
                    "is_night_slot": slot["start"] >= 23 * 60 or slot["end"] <= 7 * 60 or slot["end"] > 24 * 60,
                    "missing_total": missing_total,
                    "missing_female": missing_female,
                    "missing_male": missing_male,
                    "strict_candidates": strict_candidates,
                    "emergency_candidates": emergency_candidates,
                    "scarcity": scarcity,
                }
            )

    queue.sort(
        key=lambda item: (
            -int(item["is_night_slot"]),
            item["scarcity"],
            -item["date_index"],
            -item["missing_total"],
            -item["missing_female"],
            -item["missing_male"],
            item["slot"]["start"],
        )
    )
    return queue


def build_generation_feasibility_report(
    connection,
    employees: list[dict],
    templates: list[dict],
    coverage_requirements: list[dict],
    legacy_requirements: list[dict],
    position_id: int,
    week_start_date: str,
    week_dates: list[str],
) -> dict:
    issues: list[dict] = []
    employee_count = len(employees)
    female_count = sum(1 for employee in employees if employee["sex"] == "female")
    male_count = sum(1 for employee in employees if employee["sex"] == "male")

    if coverage_requirements:
        slots = build_atomic_slots(coverage_requirements, templates)
        if not slots:
            issues.append({
                "severity": "blocking",
                "kind": "coverage",
                "message": "No active coverage slots can be built from coverage requirements.",
            })

        for slot in slots:
            covering_templates = [template for template in templates if template_covers_slot(template, slot)]
            if not covering_templates:
                issues.append({
                    "severity": "blocking",
                    "kind": "template",
                    "slot": slot_to_report(slot),
                    "message": "No active shift template covers this required interval.",
                })
            if slot["required_total"] > employee_count:
                issues.append({
                    "severity": "blocking",
                    "kind": "staff",
                    "slot": slot_to_report(slot),
                    "message": "Required staff is greater than employees assigned to the position.",
                })
            if slot["required_female_min"] > female_count:
                issues.append({
                    "severity": "blocking",
                    "kind": "female_staff",
                    "slot": slot_to_report(slot),
                    "message": "Required female staff is greater than available female employees.",
                })
            if slot["required_male_min"] > male_count:
                issues.append({
                    "severity": "blocking",
                    "kind": "male_staff",
                    "slot": slot_to_report(slot),
                    "message": "Required male staff is greater than available male employees.",
                })

        for date_string in week_dates:
            for slot in slots:
                strict_candidates = count_candidate_options_for_slot(
                    connection,
                    employees,
                    templates,
                    position_id,
                    date_string,
                    week_start_date,
                    slot,
                    fatigue_relaxation=0,
                )
                emergency_candidates = strict_candidates or count_candidate_options_for_slot(
                    connection,
                    employees,
                    templates,
                    position_id,
                    date_string,
                    week_start_date,
                    slot,
                    fatigue_relaxation=1,
                )
                if emergency_candidates == 0:
                    issues.append({
                        "severity": "blocking",
                        "kind": "candidate",
                        "date": date_string,
                        "slot": slot_to_report(slot),
                        "message": "No eligible employee/template candidate can cover this interval.",
                    })
                elif strict_candidates == 0:
                    issues.append({
                        "severity": "warning",
                        "kind": "emergency_relaxation",
                        "date": date_string,
                        "slot": slot_to_report(slot),
                        "message": "This interval is only coverable with emergency fatigue relaxation.",
                    })
    else:
        for requirement in legacy_requirements:
            category_templates = [template for template in templates if template["category"] == requirement["shift_category"]]
            if not category_templates:
                issues.append({
                    "severity": "blocking",
                    "kind": "template",
                    "shift_category": requirement["shift_category"],
                    "message": "No active template exists for this legacy shift requirement.",
                })
            if requirement["required_total"] > employee_count:
                issues.append({
                    "severity": "blocking",
                    "kind": "staff",
                    "shift_category": requirement["shift_category"],
                    "message": "Required staff is greater than employees assigned to the position.",
                })
            if requirement["required_female_min"] > female_count:
                issues.append({
                    "severity": "blocking",
                    "kind": "female_staff",
                    "shift_category": requirement["shift_category"],
                    "message": "Required female staff is greater than available female employees.",
                })
            if requirement["required_male_min"] > male_count:
                issues.append({
                    "severity": "blocking",
                    "kind": "male_staff",
                    "shift_category": requirement["shift_category"],
                    "message": "Required male staff is greater than available male employees.",
                })

    for issue in issues:
        issue["constraint_type"] = "hard" if issue["severity"] == "blocking" else "soft"

    hard_constraints = [issue for issue in issues if issue["constraint_type"] == "hard"]
    soft_constraints = [issue for issue in issues if issue["constraint_type"] == "soft"]

    return {
        "status": "blocking" if hard_constraints else "ok",
        "issues": issues,
        "hard_constraints": hard_constraints,
        "soft_constraints": soft_constraints,
    }


def format_feasibility_issue(issue: dict) -> str:
    parts = []
    if issue.get("date"):
        parts.append(str(issue["date"]))
    if issue.get("slot"):
        slot = issue["slot"]
        parts.append(f"{slot['start']}-{slot['end']}")
    if issue.get("shift_category"):
        parts.append(str(issue["shift_category"]))

    prefix = " ".join(parts)
    if prefix:
        return f"Pre-check {issue['severity']}: {prefix}: {issue['message']}"
    return f"Pre-check {issue['severity']}: {issue['message']}"


def fill_week_by_interval_coverage(
    connection,
    cursor,
    employees: list[dict],
    templates: list[dict],
    requirements: list[dict],
    position_id: int,
    week_start_date: str,
    week_dates: list[str],
    created_entries: list[dict],
    errors: list[str],
    unfilled_reports: list[dict],
):
    slots = build_atomic_slots(requirements, templates)
    if not slots:
        errors.append("No active coverage slots for this week")
        return

    guard = 0
    while guard < 1500:
        guard += 1
        queue = build_week_shortage_queue(
            connection,
            employees,
            templates,
            position_id,
            week_start_date,
            week_dates,
            slots,
        )
        if not queue:
            break

        assigned = False
        for shortage in queue:
            current_entries = get_schedule_entries(connection, position_id=position_id, dates=[shortage["date"]])
            for fatigue_relaxation in (0, 1):
                candidate = choose_best_interval_candidate(
                    connection=connection,
                    employees=employees,
                    templates=templates,
                    position_id=position_id,
                    date_string=shortage["date"],
                    week_start_date=week_start_date,
                    current_entries=current_entries,
                    slots=slots,
                    fatigue_relaxation=fatigue_relaxation,
                    target_slot=shortage["slot"],
                )
                if candidate is None:
                    continue

                employee, assignment_templates, _score = candidate
                insert_generated_assignment(cursor, employee, position_id, shortage["date"], assignment_templates, created_entries)
                if fatigue_relaxation == 1:
                    errors.append(f"{shortage['date']}: emergency fatigue relaxation was used to cover a slot")
                assigned = True
                break

            if assigned:
                break

        if not assigned:
            break

    for date_string in week_dates:
        final_entries = get_schedule_entries(connection, position_id=position_id, dates=[date_string])
        for slot in slots:
            total, female, male = count_slot_coverage(final_entries, slot)
            if total < slot["required_total"] or female < slot["required_female_min"] or male < slot["required_male_min"]:
                unfilled_reports.append(build_interval_underfilled_report(
                    connection,
                    employees,
                    templates,
                    position_id,
                    week_start_date,
                    date_string,
                    slot,
                    total,
                    female,
                    male,
                ))
                errors.append(build_interval_underfilled_message(
                    connection,
                    employees,
                    templates,
                    position_id,
                    week_start_date,
                    date_string,
                    slot,
                    total,
                    female,
                    male,
                ))


def fill_day_by_interval_coverage(
    connection,
    cursor,
    employees: list[dict],
    templates: list[dict],
    requirements: list[dict],
    position_id: int,
    week_start_date: str,
    date_string: str,
    created_entries: list[dict],
    errors: list[str],
    unfilled_reports: list[dict],
):
    slots = build_atomic_slots(requirements, templates)
    if not slots:
        errors.append(f"No active coverage slots for {date_string}")
        return

    guard = 0
    while guard < 200:
        guard += 1
        current_entries = get_schedule_entries(connection, position_id=position_id, dates=[date_string])
        if coverage_shortage(current_entries, slots) == 0:
            break
        candidate = None
        for fatigue_relaxation in (0, 1):
            candidate = choose_best_interval_candidate(
                connection=connection,
                employees=employees,
                templates=templates,
                position_id=position_id,
                date_string=date_string,
                week_start_date=week_start_date,
                current_entries=current_entries,
                slots=slots,
                fatigue_relaxation=fatigue_relaxation,
            )
            if candidate is not None:
                if fatigue_relaxation == 1:
                    errors.append(f"{date_string}: emergency fatigue relaxation was used to cover a slot")
                break
        if candidate is None:
            break
        employee, assignment_templates, _score = candidate
        insert_generated_assignment(cursor, employee, position_id, date_string, assignment_templates, created_entries)

    final_entries = get_schedule_entries(connection, position_id=position_id, dates=[date_string])
    remaining = coverage_shortage(final_entries, slots)
    if remaining > 0:
        for slot in slots:
            total, female, male = count_slot_coverage(final_entries, slot)
            if total < slot["required_total"] or female < slot["required_female_min"] or male < slot["required_male_min"]:
                unfilled_reports.append(build_interval_underfilled_report(
                    connection,
                    employees,
                    templates,
                    position_id,
                    week_start_date,
                    date_string,
                    slot,
                    total,
                    female,
                    male,
                ))
                errors.append(build_interval_underfilled_message(
                    connection,
                    employees,
                    templates,
                    position_id,
                    week_start_date,
                    date_string,
                    slot,
                    total,
                    female,
                    male,
                ))


def fill_day_by_legacy_categories(
    connection,
    cursor,
    employees: list[dict],
    templates: list[dict],
    requirements: list[dict],
    position_id: int,
    week_start_date: str,
    date_string: str,
    created_entries: list[dict],
    errors: list[str],
    unfilled_reports: list[dict],
):
    app_settings = get_position_app_settings(connection, position_id)
    for requirement in requirements:
        category = requirement["shift_category"]
        category_templates = [template for template in templates if template["category"] == category]
        while True:
            entries = [
                entry for entry in get_schedule_entries(connection, position_id=position_id, dates=[date_string])
                if entry["shift_category"] == category
            ]
            female_count = sum(1 for entry in entries if entry["employee_sex"] == "female")
            male_count = sum(1 for entry in entries if entry["employee_sex"] == "male")
            if (
                len(entries) >= requirement["required_total"]
                and female_count >= requirement["required_female_min"]
                and male_count >= requirement["required_male_min"]
            ):
                break

            require_female = female_count < requirement["required_female_min"]
            require_male = male_count < requirement["required_male_min"]
            candidates = []
            for fatigue_relaxation in (0, 1):
                for employee in employees:
                    if require_female and employee["sex"] != "female":
                        continue
                    if require_male and employee["sex"] != "male":
                        continue
                    for template in category_templates:
                        if can_employee_take_template(
                            connection,
                            employee,
                            position_id,
                            date_string,
                            template,
                            week_start_date,
                            fatigue_relaxation=fatigue_relaxation,
                        ):
                            fatigue_penalty = get_fatigue_penalty(connection, employee["id"], date_string, template)
                            preview = create_entry_preview(employee, position_id, date_string, template)
                            projected_entries = [
                                *get_employee_entries_for_date(connection, employee["id"], date_string),
                                preview,
                            ]
                            soft_preference_penalty = soft_recurring_preference_penalty(
                                connection,
                                employee["id"],
                                date_string,
                                [template],
                                projected_entries,
                            )
                            projected_same_category_count, projected_same_category_streak = get_projected_category_metrics(
                                connection,
                                employee,
                                week_start_date,
                                [preview],
                                [template["category"]],
                            )
                            projected_night_count, projected_split_count = get_projected_assignment_counts(
                                connection,
                                employee,
                                week_start_date,
                                [preview],
                            )
                            projected_balance = get_projected_assignment_score(
                                connection,
                                employee,
                                week_start_date,
                                [preview],
                                app_settings,
                            )
                            candidates.append((
                                soft_preference_penalty,
                                fatigue_penalty,
                                projected_same_category_count,
                                projected_same_category_streak,
                                projected_night_count,
                                projected_split_count,
                                projected_balance,
                                candidate_priority(connection, employee, date_string, week_start_date),
                                employee,
                                template,
                            ))
                if candidates:
                    if fatigue_relaxation == 1:
                        errors.append(f"{date_string} {category}: emergency fatigue relaxation was used to cover a slot")
                    break
            if not candidates:
                report = build_legacy_underfilled_report(
                    connection,
                    employees,
                    templates,
                    position_id,
                    week_start_date,
                    date_string,
                    requirement,
                    len(entries),
                    female_count,
                    male_count,
                )
                unfilled_reports.append(report)
                errors.append(
                    f"{date_string} {category} underfilled: staff {len(entries)}/{requirement['required_total']}, "
                    f"women {female_count}/{requirement['required_female_min']}, "
                    f"men {male_count}/{requirement['required_male_min']}. "
                    f"Reasons: {report['reasons']}"
                )
                break
            candidates.sort()
            _, _, _, _, _, _, _, _, employee, template = candidates[0]
            insert_generated_entry(cursor, employee, position_id, date_string, template, created_entries)


def max_consecutive_in_week(connection, employee_id: int, week_dates: list[str], predicate) -> int:
    best = 0
    current = 0

    for date_string in week_dates:
        if predicate(connection, employee_id, date_string):
            current += 1
            best = max(best, current)
        else:
            current = 0

    return best


def append_fatigue_summary_warnings(
    connection,
    employees: list[dict],
    position_id: int,
    week_dates: list[str],
    week_start_date: str,
    errors: list[str],
) -> None:
    app_settings = get_position_app_settings(connection, position_id)
    for employee in employees:
        worked_days = len(get_employee_week_worked_dates(connection, employee["id"], week_start_date))
        if worked_days > app_settings["max_work_days_per_week"]:
            errors.append(
                f"{employee['full_name']} has {worked_days} worked days in the week; mandatory weekly day off is violated"
            )

        max_nights = max_consecutive_in_week(connection, employee["id"], week_dates, employee_has_night_on_date)
        if max_nights > app_settings["max_consecutive_nights"]:
            errors.append(
                f"{employee['full_name']} has {max_nights} consecutive night days; normal limit is {app_settings['max_consecutive_nights']}"
            )

        max_splits = max_consecutive_in_week(connection, employee["id"], week_dates, employee_has_split_day)
        if max_splits > app_settings["max_consecutive_split_days"]:
            errors.append(
                f"{employee['full_name']} has {max_splits} consecutive split days; normal limit is {app_settings['max_consecutive_split_days']}"
            )


def get_employee_week_entries(
    connection,
    employee_id: int,
    week_start_date: str,
    exclude_entry_ids: set[int] | None = None,
    staged_entries: list[dict] | None = None,
) -> list[dict]:
    exclude_entry_ids = exclude_entry_ids or set()
    staged_entries = staged_entries or []

    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT
            se.id,
            se.employee_id,
            se.position_id,
            se.date,
            se.shift_template_id,
            se.no_show,
            st.name AS shift_template_name,
            st.category,
            st.start_time,
            st.end_time,
            st.is_overnight,
            st.is_split_only
        FROM schedule_entries se
        JOIN shift_templates st ON st.id = se.shift_template_id
        WHERE se.employee_id = ?
          AND se.date >= ?
          AND se.date <= ?
          AND se.no_show = 0
        """,
        (employee_id, week_start_date, get_week_end_date(week_start_date)),
    )

    entries = [dict(row) for row in cursor.fetchall() if row["id"] not in exclude_entry_ids]
    entries.extend(staged_entries)
    return entries


def max_consecutive_projected(entries: list[dict], week_dates: list[str], predicate) -> int:
    entries_by_date: dict[str, list[dict]] = {}
    for entry in entries:
        entries_by_date.setdefault(entry["date"], []).append(entry)

    best = 0
    current = 0
    for date_string in week_dates:
        if predicate(entries_by_date.get(date_string, [])):
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def projected_employee_score(employee: dict, entries: list[dict], week_dates: list[str], app_settings: dict) -> int:
    week_count = len(entries)
    worked_dates = {entry["date"] for entry in entries}
    night_count = sum(1 for entry in entries if entry_category(entry) == "night")
    split_day_count = sum(
        1
        for date_string in week_dates
        if {"morning", "evening"}.issubset({entry_category(entry) for entry in entries if entry["date"] == date_string})
    )
    max_nights = max_consecutive_projected(
        entries,
        week_dates,
        lambda day_entries: any(entry_category(entry) == "night" for entry in day_entries),
    )
    max_splits = max_consecutive_projected(
        entries,
        week_dates,
        lambda day_entries: {"morning", "evening"}.issubset({entry_category(entry) for entry in day_entries}),
    )

    score = 0
    score += max(0, employee["min_shifts_per_week"] - week_count) * app_settings["balance_missing_min_weight"]
    score += abs(employee["target_shifts_per_week"] - week_count) * app_settings["balance_target_distance_weight"]
    score += max(0, week_count - employee["target_shifts_per_week"]) * app_settings["balance_over_target_weight"]
    score += max(0, week_count - employee["max_shifts_per_week"]) * app_settings["balance_over_max_weight"]
    score += len(worked_dates) * app_settings["balance_worked_day_weight"]
    score += max(0, len(worked_dates) - app_settings["max_work_days_per_week"]) * app_settings["balance_over_max_weight"]
    score += night_count * app_settings["balance_night_weight"]
    score += split_day_count * app_settings["balance_split_weight"]
    score += max_nights * app_settings["balance_consecutive_night_weight"]
    score += max_splits * app_settings["balance_consecutive_split_weight"]
    score += max(0, max_nights - app_settings["max_consecutive_nights"]) * app_settings["balance_excess_night_weight"]
    score += max(0, max_splits - app_settings["max_consecutive_split_days"]) * app_settings["balance_excess_split_weight"]
    return score


def get_projected_assignment_score(
    connection,
    employee: dict,
    week_start_date: str,
    staged_entries: list[dict],
    app_settings: dict,
) -> int:
    week_dates = build_week_dates(week_start_date)
    projected_entries = get_employee_week_entries(
        connection,
        employee["id"],
        week_start_date,
        staged_entries=staged_entries,
    )
    return projected_employee_score(employee, projected_entries, week_dates, app_settings)


def get_projected_assignment_counts(
    connection,
    employee: dict,
    week_start_date: str,
    staged_entries: list[dict],
) -> tuple[int, int]:
    week_dates = build_week_dates(week_start_date)
    projected_entries = get_employee_week_entries(
        connection,
        employee["id"],
        week_start_date,
        staged_entries=staged_entries,
    )
    projected_night_count = sum(1 for entry in projected_entries if entry_category(entry) == "night")
    projected_split_count = sum(
        1
        for date_string in week_dates
        if {"morning", "evening"}.issubset({entry_category(entry) for entry in projected_entries if entry["date"] == date_string})
    )
    return projected_night_count, projected_split_count


def get_projected_category_metrics(
    connection,
    employee: dict,
    week_start_date: str,
    staged_entries: list[dict],
    categories: list[str],
) -> tuple[int, int]:
    week_dates = build_week_dates(week_start_date)
    projected_entries = get_employee_week_entries(
        connection,
        employee["id"],
        week_start_date,
        staged_entries=staged_entries,
    )
    target_categories = set(categories)
    projected_category_count = sum(1 for entry in projected_entries if entry_category(entry) in target_categories)
    projected_category_streak = max_consecutive_projected(
        projected_entries,
        week_dates,
        lambda day_entries: any(entry_category(entry) in target_categories for entry in day_entries),
    )
    return projected_category_count, projected_category_streak


def row_to_template_for_assignment(row: dict) -> dict:
    return {
        "id": row["shift_template_id"],
        "name": row["shift_template_name"],
        "category": entry_category(row),
        "start_time": row["start_time"],
        "end_time": row["end_time"],
        "is_overnight": bool(row["is_overnight"]),
        "is_active": True,
        "is_split_only": bool(row["is_split_only"]),
    }


def build_generated_assignment_groups(connection, created_entries: list[dict], position_id: int) -> list[list[dict]]:
    created_ids = [entry["id"] for entry in created_entries if entry.get("id")]
    if not created_ids:
        return []

    placeholders = ",".join(["?"] * len(created_ids))
    cursor = connection.cursor()
    cursor.execute(
        f"""
        SELECT
            se.id,
            se.employee_id,
            se.position_id,
            se.date,
            se.shift_template_id,
            st.name AS shift_template_name,
            st.category,
            st.start_time,
            st.end_time,
            st.is_overnight,
            st.is_split_only
        FROM schedule_entries se
        JOIN shift_templates st ON st.id = se.shift_template_id
        WHERE se.id IN ({placeholders})
          AND se.position_id = ?
        ORDER BY se.date, se.employee_id, st.start_time
        """,
        [*created_ids, position_id],
    )
    rows = [dict(row) for row in cursor.fetchall()]
    rows_by_id = {row["id"]: row for row in rows}
    visited: set[int] = set()
    groups: list[list[dict]] = []

    for row in rows:
        if row["id"] in visited:
            continue

        if row["category"] in {"morning", "evening"}:
            group = [
                candidate
                for candidate in rows
                if candidate["employee_id"] == row["employee_id"]
                and candidate["position_id"] == row["position_id"]
                and candidate["date"] == row["date"]
                and candidate["category"] in {"morning", "evening"}
            ]
        else:
            group = [row]

        group = [item for item in group if item["id"] in rows_by_id and item["id"] not in visited]
        if not group:
            continue
        for item in group:
            visited.add(item["id"])
        groups.append(sorted(group, key=lambda item: time_to_minutes(item["start_time"])))

    return groups


def post_optimize_generated_schedule(
    connection,
    cursor,
    employees: list[dict],
    position_id: int,
    week_start_date: str,
    week_dates: list[str],
    created_entries: list[dict],
    errors: list[str],
) -> int:
    app_settings = get_position_app_settings(connection, position_id)
    employee_by_id = {employee["id"]: employee for employee in employees}
    groups = build_generated_assignment_groups(connection, created_entries, position_id)
    moved_count = 0

    for group in groups:
        if not group:
            continue

        original_employee = employee_by_id.get(group[0]["employee_id"])
        if original_employee is None:
            continue

        date_string = group[0]["date"]
        entry_ids = {entry["id"] for entry in group}
        assignment_templates = [row_to_template_for_assignment(entry) for entry in group]
        original_entries_before = get_employee_week_entries(connection, original_employee["id"], week_start_date)
        original_entries_after = get_employee_week_entries(
            connection,
            original_employee["id"],
            week_start_date,
            exclude_entry_ids=entry_ids,
        )
        original_score_before = projected_employee_score(original_employee, original_entries_before, week_dates, app_settings)
        original_score_after = projected_employee_score(original_employee, original_entries_after, week_dates, app_settings)

        best_employee = None
        best_improvement = 0
        for candidate in employees:
            if candidate["id"] == original_employee["id"]:
                continue

            previews = build_valid_assignment_previews(
                connection,
                candidate,
                assignment_templates,
                position_id,
                date_string,
                week_start_date,
                fatigue_relaxation=0,
            )
            if previews is None:
                continue

            candidate_entries_before = get_employee_week_entries(connection, candidate["id"], week_start_date)
            candidate_entries_after = get_employee_week_entries(
                connection,
                candidate["id"],
                week_start_date,
                staged_entries=previews,
            )
            before_score = original_score_before + projected_employee_score(
                candidate,
                candidate_entries_before,
                week_dates,
                app_settings,
            )
            after_score = original_score_after + projected_employee_score(
                candidate,
                candidate_entries_after,
                week_dates,
                app_settings,
            )
            improvement = before_score - after_score

            if improvement > best_improvement:
                best_improvement = improvement
                best_employee = candidate

        if best_employee is None or best_improvement < 80:
            continue

        cursor.execute(
            f"""
            UPDATE schedule_entries
            SET employee_id = ?
            WHERE id IN ({','.join(['?'] * len(entry_ids))})
            """,
            [best_employee["id"], *entry_ids],
        )
        for created_entry in created_entries:
            if created_entry.get("id") in entry_ids:
                created_entry["employee_id"] = best_employee["id"]
                created_entry["employee_name"] = best_employee["full_name"]
        moved_count += len(entry_ids)

    return moved_count


def run_auto_generate_for_position(connection, position_id: int, week_start_date: str) -> dict:
    cursor = connection.cursor()
    position_row = fetch_one_or_404(cursor, "SELECT * FROM positions WHERE id = ?", (position_id,), "Position not found")
    position = row_to_position_dict(position_row)
    week_dates = build_week_dates(week_start_date)
    employees = load_position_employees(connection, position_id)
    if not employees:
        raise HTTPException(status_code=400, detail="No employees assigned to this position")

    templates_list = load_active_templates(connection, position_id)
    if not templates_list:
        raise HTTPException(status_code=400, detail="No active shift templates found")

    coverage_requirements = load_coverage_requirements_for_position(connection, position_id)
    legacy_requirements = load_legacy_shift_requirements(connection, position_id)
    if not coverage_requirements and not legacy_requirements:
        raise HTTPException(status_code=400, detail="No coverage or shift requirements found for this position")

    created_entries: list[dict] = []
    errors: list[str] = []
    unfilled_reports: list[dict] = []
    feasibility_report = build_generation_feasibility_report(
        connection,
        employees,
        templates_list,
        coverage_requirements,
        legacy_requirements,
        position_id,
        week_start_date,
        week_dates,
    )
    for issue in feasibility_report["issues"]:
        errors.append(format_feasibility_issue(issue))

    if coverage_requirements:
        fill_week_by_interval_coverage(
            connection,
            cursor,
            employees,
            templates_list,
            coverage_requirements,
            position_id,
            week_start_date,
            week_dates,
            created_entries,
            errors,
            unfilled_reports,
        )
    else:
        for date_string in week_dates:
            fill_day_by_legacy_categories(
                connection,
                cursor,
                employees,
                templates_list,
                legacy_requirements,
                position_id,
                week_start_date,
                date_string,
                created_entries,
                errors,
                unfilled_reports,
            )

    optimization_moved_count = post_optimize_generated_schedule(
        connection,
        cursor,
        employees,
        position_id,
        week_start_date,
        week_dates,
        created_entries,
        errors,
    )

    append_fatigue_summary_warnings(connection, employees, position_id, week_dates, week_start_date, errors)
    day_off_count = sync_generated_day_off_statuses(
        connection,
        cursor,
        employees,
        position_id,
        week_dates,
    )

    return {
        "message": "Auto-generation finished",
        "position_id": position_id,
        "position_name": position["name"],
        "created_count": len(created_entries),
        "created_entries": created_entries,
        "day_off_count": day_off_count,
        "optimization_moved_count": optimization_moved_count,
        "feasibility_report": feasibility_report,
        "unfilled_reports": unfilled_reports,
        "errors": errors,
    }


@app.post("/api/schedule/auto-generate", tags=["Schedule"])
def auto_generate_schedule(
    request_data: AutoGenerateScheduleRequest,
    _access: dict | None = Depends(require_schedule_edit_if_auth_initialized),
):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        organization_id = _access["membership"]["organization_id"] if _access else 1
        require_license_capability(cursor, "can_generate_schedule", organization_id)
        pull_cloud_preferences_for_desktop_generation(connection)
        result = run_auto_generate_for_position(connection, request_data.position_id, request_data.week_start_date)
        connection.commit()
        return result
    finally:
        connection.close()


@app.post("/api/schedule/auto-generate-all", tags=["Schedule"])
def auto_generate_all_schedules(
    request_data: AutoGenerateAllScheduleRequest,
    _access: dict | None = Depends(require_schedule_edit_if_auth_initialized),
):
    connection = get_connection()
    try:
        organization_id = _access["membership"]["organization_id"] if _access else 1
        cursor = connection.cursor()
        require_license_capability(cursor, "can_generate_schedule", organization_id)
        pull_cloud_preferences_for_desktop_generation(connection)
        cursor.execute("SELECT id, name FROM positions ORDER BY id")
        positions = [dict(row) for row in cursor.fetchall()]
        if not positions:
            raise HTTPException(status_code=400, detail="No positions found")

        results: list[dict] = []
        failures: list[dict] = []
        total_created_count = 0
        total_day_off_count = 0
        total_optimization_moved_count = 0

        for position in positions:
            savepoint_name = f"auto_generate_position_{position['id']}"
            cursor.execute(f"SAVEPOINT {savepoint_name}")
            try:
                result = run_auto_generate_for_position(connection, position["id"], request_data.week_start_date)
            except HTTPException as exc:
                cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                failures.append({
                    "position_id": position["id"],
                    "position_name": position["name"],
                    "detail": exc.detail,
                    "status_code": exc.status_code,
                })
                continue

            cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            results.append(result)
            total_created_count += result["created_count"]
            total_day_off_count += result["day_off_count"]
            total_optimization_moved_count += result["optimization_moved_count"]

        connection.commit()
        return {
            "message": "Auto-generation for all positions finished",
            "week_start_date": request_data.week_start_date,
            "generated_positions": len(results),
            "failed_positions": len(failures),
            "total_created_count": total_created_count,
            "total_day_off_count": total_day_off_count,
            "total_optimization_moved_count": total_optimization_moved_count,
            "results": results,
            "failures": failures,
        }
    finally:
        connection.close()


@app.get("/api/schedule/export-excel", tags=["Schedule"])
def export_schedule_excel(
    week_start_date: str,
    position_id: int,
    lang: str = "en",
    access_context: dict | None = Depends(require_schedule_view_if_auth_initialized),
    current_user: dict | None = Depends(get_optional_current_user),
):
    connection = get_connection()
    try:
        if lang not in {"en", "ru", "he"}:
            lang = "en"
        week_dates = build_week_dates(week_start_date)
        cursor = connection.cursor()
        position_row = fetch_one_or_404(cursor, "SELECT * FROM positions WHERE id = ?", (position_id,), "Position not found")
        position = row_to_position_dict(position_row)
        employee_scope = employee_scope_from_access(access_context)
        employees = [
            employee for employee in load_position_employees(connection, position_id)
            if employee_scope is None or employee["id"] == employee_scope
        ]
        employee_ids = {employee["id"] for employee in employees}
        entries = [
            entry
            for entry in get_schedule_entries(connection, dates=week_dates, employee_id=employee_scope)
            if entry["employee_id"] in employee_ids
        ]
        day_status_map = get_employee_day_status_map(connection, [employee["id"] for employee in employees], week_dates)
        output = build_schedule_export_workbook(
            position=position,
            week_start_date=week_start_date,
            week_dates=week_dates,
            employees=employees,
            entries=entries,
            day_status_map=day_status_map,
            lang=lang,
        )
        safe_position_name = position["name"].replace(" ", "_")
        filename = f"schedule_{safe_position_name}_{week_start_date}.xlsx"
        user_id, organization_id = audit_context_from_user(current_user)
        write_auth_audit_event_record(
            "schedule_exported",
            user_id=user_id,
            organization_id=organization_id,
            metadata={
                "format": "excel",
                "scope": "position",
                "week_start_date": week_start_date,
                "position_id": position_id,
                "lang": lang,
                "filename": filename,
            },
        )
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    finally:
        connection.close()


@app.get("/api/schedule/export-excel-all", tags=["Schedule"])
def export_all_schedules_excel(
    week_start_date: str,
    lang: str = "en",
    access_context: dict | None = Depends(require_schedule_view_if_auth_initialized),
    current_user: dict | None = Depends(get_optional_current_user),
):
    connection = get_connection()
    try:
        if lang not in {"en", "ru", "he"}:
            lang = "en"
        week_dates = build_week_dates(week_start_date)
        cursor = connection.cursor()
        employee_scope = employee_scope_from_access(access_context)
        if employee_scope is not None:
            cursor.execute(
                """
                SELECT p.*, ep.is_primary, ep.priority_score, ep.is_fallback_only
                FROM positions p
                JOIN employee_positions ep ON ep.position_id = p.id
                WHERE ep.employee_id = ?
                ORDER BY ep.is_primary DESC, ep.is_fallback_only ASC, ep.priority_score DESC, p.id
                """,
                (employee_scope,),
            )
        else:
            cursor.execute("SELECT * FROM positions ORDER BY id")
        positions = [row_to_position_dict(row) for row in cursor.fetchall()]
        employees_by_position = {
            position["id"]: [
                employee for employee in load_position_employees(connection, position["id"])
                if employee_scope is None or employee["id"] == employee_scope
            ]
            for position in positions
        }
        employee_ids = sorted({
            employee["id"]
            for employees in employees_by_position.values()
            for employee in employees
        })
        entries = get_schedule_entries(connection, dates=week_dates, employee_id=employee_scope)
        day_status_map = get_employee_day_status_map(connection, employee_ids, week_dates) if employee_ids else {}
        output = build_all_schedule_export_workbook(
            positions=positions,
            week_start_date=week_start_date,
            week_dates=week_dates,
            employees_by_position=employees_by_position,
            entries=entries,
            day_status_map=day_status_map,
            lang=lang,
        )
        filename = f"schedule_all_{week_start_date}.xlsx"
        user_id, organization_id = audit_context_from_user(current_user)
        write_auth_audit_event_record(
            "schedule_exported",
            user_id=user_id,
            organization_id=organization_id,
            metadata={
                "format": "excel",
                "scope": "all",
                "week_start_date": week_start_date,
                "lang": lang,
                "filename": filename,
            },
        )
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    finally:
        connection.close()


@app.get("/api/schedule/export-word", tags=["Schedule"])
def export_schedule_word(
    week_start_date: str,
    position_id: int,
    lang: str = "en",
    access_context: dict | None = Depends(require_schedule_view_if_auth_initialized),
    current_user: dict | None = Depends(get_optional_current_user),
):
    connection = get_connection()
    try:
        if lang not in {"en", "ru", "he"}:
            lang = "en"
        week_dates = build_week_dates(week_start_date)
        cursor = connection.cursor()
        position_row = fetch_one_or_404(cursor, "SELECT * FROM positions WHERE id = ?", (position_id,), "Position not found")
        position = row_to_position_dict(position_row)
        employee_scope = employee_scope_from_access(access_context)
        employees = [
            employee for employee in load_position_employees(connection, position_id)
            if employee_scope is None or employee["id"] == employee_scope
        ]
        employee_ids = {employee["id"] for employee in employees}
        entries = [
            entry
            for entry in get_schedule_entries(connection, dates=week_dates, employee_id=employee_scope)
            if entry["employee_id"] in employee_ids
        ]
        day_status_map = get_employee_day_status_map(connection, [employee["id"] for employee in employees], week_dates)
        output = build_schedule_export_document(
            position=position,
            week_start_date=week_start_date,
            week_dates=week_dates,
            employees=employees,
            entries=entries,
            day_status_map=day_status_map,
            lang=lang,
        )
        safe_position_name = position["name"].replace(" ", "_")
        filename = f"schedule_{safe_position_name}_{week_start_date}.docx"
        user_id, organization_id = audit_context_from_user(current_user)
        write_auth_audit_event_record(
            "schedule_exported",
            user_id=user_id,
            organization_id=organization_id,
            metadata={
                "format": "word",
                "scope": "position",
                "week_start_date": week_start_date,
                "position_id": position_id,
                "lang": lang,
                "filename": filename,
            },
        )
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    finally:
        connection.close()


@app.get("/api/schedule/export-word-all", tags=["Schedule"])
def export_all_schedules_word(
    week_start_date: str,
    lang: str = "en",
    access_context: dict | None = Depends(require_schedule_view_if_auth_initialized),
    current_user: dict | None = Depends(get_optional_current_user),
):
    connection = get_connection()
    try:
        if lang not in {"en", "ru", "he"}:
            lang = "en"
        week_dates = build_week_dates(week_start_date)
        cursor = connection.cursor()
        employee_scope = employee_scope_from_access(access_context)
        if employee_scope is not None:
            cursor.execute(
                """
                SELECT p.*, ep.is_primary, ep.priority_score, ep.is_fallback_only
                FROM positions p
                JOIN employee_positions ep ON ep.position_id = p.id
                WHERE ep.employee_id = ?
                ORDER BY ep.is_primary DESC, ep.is_fallback_only ASC, ep.priority_score DESC, p.id
                """,
                (employee_scope,),
            )
        else:
            cursor.execute("SELECT * FROM positions ORDER BY id")
        positions = [row_to_position_dict(row) for row in cursor.fetchall()]
        employees_by_position = {
            position["id"]: [
                employee for employee in load_position_employees(connection, position["id"])
                if employee_scope is None or employee["id"] == employee_scope
            ]
            for position in positions
        }
        employee_ids = sorted({
            employee["id"]
            for employees in employees_by_position.values()
            for employee in employees
        })
        entries = get_schedule_entries(connection, dates=week_dates, employee_id=employee_scope)
        day_status_map = get_employee_day_status_map(connection, employee_ids, week_dates) if employee_ids else {}
        output = build_all_schedule_export_document(
            positions=positions,
            week_start_date=week_start_date,
            week_dates=week_dates,
            employees_by_position=employees_by_position,
            entries=entries,
            day_status_map=day_status_map,
            lang=lang,
        )
        filename = f"schedule_all_{week_start_date}.docx"
        user_id, organization_id = audit_context_from_user(current_user)
        write_auth_audit_event_record(
            "schedule_exported",
            user_id=user_id,
            organization_id=organization_id,
            metadata={
                "format": "word",
                "scope": "all",
                "week_start_date": week_start_date,
                "lang": lang,
                "filename": filename,
            },
        )
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    finally:
        connection.close()

