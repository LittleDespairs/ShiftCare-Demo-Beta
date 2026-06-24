import base64
import hashlib
import hmac
import json
import os
from datetime import UTC, date as Date, datetime, timedelta
from typing import Any


TRIAL_DAYS = 30
TRIAL_EMPLOYEE_LIMIT = 15
DEFAULT_GRACE_DAYS = 30
DEVELOPER_BYPASS_EMPLOYEE_LIMIT = 9999
LICENSE_SIGNATURE_PAYLOAD_KEYS = {
    "branch_id",
    "cloud_organization_id",
    "customer_legal_name",
    "desktop_license_expires_at",
    "employee_limit",
    "features",
    "grace_ends_at",
    "issued_at",
    "key_id",
    "license_id",
    "organization_public_id",
    "plan_code",
    "revoked_at",
    "support_cloud_expires_at",
    "trial_expires_at",
    "trial_started_at",
    "updated_at",
}
BLOCKING_LICENSE_STATUSES = {"expired", "revoked"}
ACTIVATION_CODE_PREFIX = "SCAC1."


class LicenseValidationError(ValueError):
    pass


def current_utc_date() -> Date:
    return datetime.now(UTC).date()


def parse_date(value: str | None) -> Date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return Date.fromisoformat(str(value)[:10])
        except ValueError as exc:
            raise LicenseValidationError(f"Invalid license date: {value}") from exc


def normalize_certificate(raw_certificate: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw_certificate, dict):
        raise LicenseValidationError("License certificate must be a JSON object")
    certificate = dict(raw_certificate)
    required = {"license_id", "organization_public_id", "plan_code", "employee_limit", "issued_at"}
    missing = sorted(key for key in required if not certificate.get(key))
    if missing:
        raise LicenseValidationError("License certificate is missing required fields: " + ", ".join(missing))
    try:
        certificate["employee_limit"] = int(certificate["employee_limit"])
    except (TypeError, ValueError) as exc:
        raise LicenseValidationError("employee_limit must be an integer") from exc
    if certificate["employee_limit"] < 1:
        raise LicenseValidationError("employee_limit must be greater than zero")
    certificate.setdefault("features", [])
    if not isinstance(certificate["features"], list):
        raise LicenseValidationError("features must be a list")
    certificate.setdefault("status", "active")
    if certificate["status"] not in {"trial", "active", "payment_due", "grace", "expired", "revoked"}:
        raise LicenseValidationError("Unsupported license status")
    return certificate


def canonical_signature_payload(certificate: dict[str, Any]) -> bytes:
    payload = {
        key: certificate.get(key)
        for key in sorted(LICENSE_SIGNATURE_PAYLOAD_KEYS)
        if key in certificate
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def verify_hmac_signature(certificate: dict[str, Any]) -> bool:
    secret = os.environ.get("SCHEDULE_APP_LICENSE_SIGNING_SECRET", "").strip()
    if not secret:
        return False
    expected = hmac_signature(certificate, secret)
    actual = str(certificate.get("signature") or "")
    return hmac.compare_digest(actual, expected)


def hmac_signature(certificate: dict[str, Any], secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), canonical_signature_payload(certificate), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def verify_certificate_signature(certificate: dict[str, Any], *, developer_mode: bool = False) -> None:
    scheme = str(certificate.get("signature_scheme") or "").strip().lower()
    signature = str(certificate.get("signature") or "").strip()
    if not signature:
        raise LicenseValidationError("License certificate is missing signature")
    if scheme == "hmac-sha256-v1" and verify_hmac_signature(certificate):
        return
    if scheme == "unsigned-dev-v1" and developer_mode:
        return
    raise LicenseValidationError("License signature is invalid or unsupported")


def encode_activation_code(certificate: dict[str, Any]) -> str:
    payload = json.dumps(certificate, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    return ACTIVATION_CODE_PREFIX + encoded


def decode_activation_code(activation_code: str) -> dict[str, Any]:
    value = str(activation_code or "").strip()
    if not value.startswith(ACTIVATION_CODE_PREFIX):
        raise LicenseValidationError("Unsupported activation code format")
    encoded = value[len(ACTIVATION_CODE_PREFIX):]
    padding = "=" * (-len(encoded) % 4)
    try:
        raw = base64.urlsafe_b64decode((encoded + padding).encode("ascii"))
        certificate = json.loads(raw.decode("utf-8"))
    except (ValueError, json.JSONDecodeError) as exc:
        raise LicenseValidationError("Activation code is invalid") from exc
    return normalize_certificate(certificate)


def calculate_certificate_status(certificate: dict[str, Any], today: Date | None = None) -> str:
    today = today or current_utc_date()
    if certificate.get("revoked_at") or certificate.get("status") == "revoked":
        return "revoked"
    explicit_status = certificate.get("status")
    if explicit_status == "expired":
        return "expired"
    grace_ends_at = parse_date(certificate.get("grace_ends_at"))
    support_cloud_expires_at = parse_date(certificate.get("support_cloud_expires_at"))
    desktop_license_expires_at = parse_date(certificate.get("desktop_license_expires_at"))
    paid_expiry = desktop_license_expires_at or support_cloud_expires_at
    if paid_expiry and today > paid_expiry:
        if grace_ends_at and today <= grace_ends_at:
            return "grace"
        return "expired"
    if explicit_status in {"payment_due", "grace"}:
        return explicit_status
    return "active"


def calculate_trial_status(organization_created_at: str | None, today: Date | None = None) -> dict[str, Any]:
    today = today or current_utc_date()
    started_at = parse_date(organization_created_at) or today
    expires_at = started_at + timedelta(days=TRIAL_DAYS)
    grace_ends_at = expires_at + timedelta(days=DEFAULT_GRACE_DAYS)
    if today <= expires_at:
        status = "trial"
    elif today <= grace_ends_at:
        status = "grace"
    else:
        status = "expired"
    return {
        "status": status,
        "source": "trial",
        "trial_started_at": started_at.isoformat(),
        "trial_expires_at": expires_at.isoformat(),
        "grace_ends_at": grace_ends_at.isoformat(),
        "employee_limit": TRIAL_EMPLOYEE_LIMIT,
        "plan_code": "trial",
        "license_id": None,
        "support_cloud_expires_at": None,
        "features": ["desktop"],
    }


def build_developer_bypass_status() -> dict[str, Any]:
    return {
        "status": "active",
        "source": "developer_bypass",
        "license_id": "developer-bypass",
        "plan_code": "developer",
        "employee_limit": DEVELOPER_BYPASS_EMPLOYEE_LIMIT,
        "trial_started_at": None,
        "trial_expires_at": None,
        "support_cloud_expires_at": None,
        "grace_ends_at": None,
        "features": ["desktop", "employee_portal", "developer_bypass"],
        "developer_bypass": True,
        "message": "Developer license bypass enabled",
    }


def build_enforcement(status: str, employee_limit: int, employee_count: int) -> dict[str, Any]:
    is_blocked = status in BLOCKING_LICENSE_STATUSES
    employee_limit_reached = employee_count >= employee_limit
    return {
        "can_generate_schedule": not is_blocked,
        "can_create_schedule": not is_blocked,
        "can_create_shift": not is_blocked,
        "can_add_employee": not is_blocked and not employee_limit_reached,
        "employee_limit_reached": employee_limit_reached,
        "blocking_reason": status if is_blocked else None,
    }
