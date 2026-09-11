"""Services: access for ShiftCare."""
from __future__ import annotations

from fastapi import Depends
from fastapi import HTTPException
from fastapi import Header
from shiftcare.services import audit as services_audit
from shiftcare.services import authentication as services_authentication
from shiftcare.services import memberships as services_memberships
from shiftcare.services import runtime as services_runtime
import auth_repository
import database

def active_user_count(cursor) -> int:
    return auth_repository.active_user_count(cursor)


def require_database_admin_if_auth_initialized(authorization: str | None = Header(default=None)) -> dict | None:
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        has_active_users = active_user_count(cursor) > 0
    finally:
        connection.close()

    if not has_active_users:
        return None

    current_user = services_authentication.get_current_user(authorization)
    membership = services_authentication.find_any_membership_with_role(current_user, {"owner", "admin"})
    if not membership:
        raise HTTPException(status_code=403, detail="Owner or admin permissions are required")
    return {"user": current_user, "membership": membership}


def require_developer_support_access(current_user: dict = Depends(services_authentication.get_current_user)) -> dict:
    if not services_runtime.is_developer_mode_enabled():
        raise HTTPException(status_code=404, detail="Developer support mode is disabled")
    membership = services_authentication.find_any_membership_with_role(current_user, {"owner", "admin"})
    if not membership:
        raise HTTPException(status_code=403, detail="Owner or admin permissions are required")
    return {"user": current_user, "membership": membership}


def require_preference_access_if_auth_initialized(authorization: str | None = Header(default=None)) -> dict | None:
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        has_active_users = active_user_count(cursor) > 0
    finally:
        connection.close()

    if not has_active_users:
        return None

    current_user = services_authentication.get_current_user(authorization)
    admin_membership = services_authentication.find_any_membership_with_role(current_user, {"owner", "admin", "scheduler", "manager"})
    if admin_membership:
        return {"user": current_user, "membership": admin_membership, "scope": "all"}

    employee_membership = services_authentication.find_any_membership_with_role(current_user, {"employee"})
    if employee_membership and not employee_membership.get("employee_id"):
        connection = database.get_connection()
        try:
            cursor = connection.cursor()
            repaired = services_memberships.repair_employee_membership_links(cursor, current_user)
            if repaired:
                services_audit.write_auth_audit_event(
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
    connection = database.get_connection()
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

    current_user = services_authentication.get_current_user(authorization)
    membership = services_authentication.find_any_membership_with_role(current_user, allowed_roles)
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


def require_week_preference_approval_if_auth_initialized(authorization: str | None = Header(default=None)) -> dict | None:
    return require_roles_if_auth_initialized({"owner", "admin", "scheduler", "manager"}, authorization)
