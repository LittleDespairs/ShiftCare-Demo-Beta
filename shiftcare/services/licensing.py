"""Services: licensing for ShiftCare."""
from __future__ import annotations

from fastapi import HTTPException
from shiftcare import config as app_constants
from shiftcare.services import audit as services_audit
from shiftcare.services import common as services_common
from shiftcare.services import runtime as services_runtime
from typing import Any
import json
import license_runtime

def demo_restriction_detail(feature: str) -> dict:
    return {
        "message": f"{feature} is disabled in ShiftCare Demo",
        "demo_mode": True,
        "employee_limit": app_constants.DEMO_EMPLOYEE_LIMIT,
        "schedule_entry_limit": app_constants.DEMO_SCHEDULE_ENTRY_LIMIT,
    }


def require_not_demo(feature: str) -> None:
    if services_runtime.is_demo_mode_enabled():
        raise HTTPException(status_code=403, detail=demo_restriction_detail(feature))


def require_demo_schedule_entry_slot(cursor) -> None:
    if not services_runtime.is_demo_mode_enabled():
        return
    current_count = services_common.fetch_count(cursor, "SELECT COUNT(*) FROM schedule_entries")
    if current_count >= app_constants.DEMO_SCHEDULE_ENTRY_LIMIT:
        detail = demo_restriction_detail("Manual schedule editing")
        detail["current_schedule_entries"] = current_count
        raise HTTPException(status_code=403, detail=detail)


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
    if services_runtime.is_demo_mode_enabled():
        employee_limit_reached = employee_count >= app_constants.DEMO_EMPLOYEE_LIMIT
        return {
            "status": "demo",
            "source": "demo",
            "license_id": "shiftcare-demo",
            "plan_code": "demo",
            "employee_limit": app_constants.DEMO_EMPLOYEE_LIMIT,
            "employee_count": employee_count,
            "organization_id": organization_id,
            "organization_public_id": organization["public_id"],
            "organization_name": organization["name"],
            "trial_started_at": None,
            "trial_expires_at": None,
            "support_cloud_expires_at": None,
            "grace_ends_at": None,
            "features": ["desktop", "demo"],
            "key_id": "demo",
            "last_verified_at": None,
            "imported_at": None,
            "demo_mode": True,
            "message": "ShiftCare Demo mode",
            "enforcement": {
                "can_generate_schedule": True,
                "can_create_schedule": True,
                "can_create_shift": True,
                "can_add_employee": not employee_limit_reached,
                "employee_limit_reached": employee_limit_reached,
                "blocking_reason": "demo",
            },
        }
    if services_runtime.is_license_bypass_enabled():
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
    raise HTTPException(status_code=403 if services_runtime.is_demo_mode_enabled() else 402, detail=detail)


def import_license_certificate(cursor, certificate_data: dict[str, Any], organization_id: int = 1, source: str = "imported") -> dict:
    organization = get_default_organization_row(cursor, organization_id)
    certificate = license_runtime.normalize_certificate(certificate_data)
    if certificate["organization_public_id"] != organization["public_id"]:
        raise HTTPException(status_code=400, detail="License certificate belongs to a different organization")
    try:
        license_runtime.verify_certificate_signature(certificate, developer_mode=services_runtime.is_developer_mode_enabled())
    except license_runtime.LicenseValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    status = license_runtime.calculate_certificate_status(certificate)
    now = services_common.current_utc_timestamp()
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
    services_audit.write_license_event(
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
