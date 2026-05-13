from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, model_validator

from schedule_time import build_week_dates, parse_date_string, parse_time_string


def _normalize_id_card(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))


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
            normalized_id_card = _normalize_id_card(self.id_card)
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
    allow_same_day_other_positions: bool = False
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
    min_rest_minutes_between_morning_and_evening: int | None = Field(default=None, ge=0, le=24 * 60)
    min_rest_minutes_after_night_before_evening: int | None = Field(default=None, ge=0, le=24 * 60)
    max_daily_work_minutes: int | None = Field(default=None, ge=60, le=24 * 60)
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
