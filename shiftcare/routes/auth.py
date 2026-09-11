"""Routes: auth for ShiftCare."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Header
from fastapi import Request
from schemas import AuthBootstrapRequest
from schemas import AuthLoginRequest
from schemas import AuthOrganizationCreateRequest
from schemas import AuthProfileUpdateRequest
from shiftcare import config as app_constants
from shiftcare.services import audit as services_audit
from shiftcare.services import authentication as services_authentication
from shiftcare.services import common as services_common
from shiftcare.services import memberships as services_memberships
from shiftcare.services import runtime as services_runtime
import app_config
import database
import secrets
import sqlite3

router = APIRouter()


@router.post("/api/auth/bootstrap", tags=["Auth"])
def bootstrap_first_owner(request_data: AuthBootstrapRequest, request: Request):
    if services_runtime.is_cloud_employee_portal_mode() and not services_runtime.is_trusted_desktop_cloud_request(request):
        raise HTTPException(status_code=404, detail="Organization setup is available only in the desktop app")
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        active_user_count = services_common.fetch_count(cursor, "SELECT COUNT(*) FROM users WHERE status = 'active'")
        if active_user_count:
            raise HTTPException(status_code=409, detail="Application already has an active user")

        email = str(request_data.email).strip().lower()
        now = services_common.current_utc_timestamp()
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
            (email, request_data.full_name.strip(), services_authentication.hash_password(request_data.password), now, now),
        )
        user_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO organization_memberships (organization_id, user_id, role, status, created_at, updated_at)
            VALUES (1, ?, 'owner', 'active', ?, ?)
            """,
            (user_id, now, now),
        )
        services_audit.write_auth_audit_event(cursor, "bootstrap_owner_created", user_id=user_id, organization_id=1)
        auth_response = services_authentication.build_auth_response(connection, user_id)
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


@router.post("/api/auth/login", tags=["Auth"])
def login(request_data: AuthLoginRequest, request: Request):
    if services_runtime.is_demo_mode_enabled():
        return services_authentication.build_demo_auth_response()

    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        identifier = services_authentication.normalize_login_identifier(request_data.email)
        if services_authentication.is_login_rate_limited(identifier, request):
            services_audit.write_auth_audit_event(
                cursor,
                "login_rate_limited",
                metadata={"identifier": identifier, "ip": services_authentication.get_request_ip(request)},
            )
            connection.commit()
            raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")

        user_row = services_authentication.find_user_for_login(cursor, identifier)
        if not user_row or user_row["status"] != "active" or not services_authentication.verify_password(request_data.password, user_row["password_hash"]):
            user_id = user_row["id"] if user_row else None
            services_audit.write_auth_audit_event(
                cursor,
                "login_failed",
                user_id=user_id,
                metadata={"identifier": identifier, "ip": services_authentication.get_request_ip(request)},
            )
            connection.commit()
            if services_authentication.record_login_failure(identifier, request):
                services_audit.write_auth_audit_event_record(
                    "login_rate_limited",
                    user_id=user_id,
                    metadata={"identifier": identifier, "ip": services_authentication.get_request_ip(request)},
                )
                raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")
            raise HTTPException(status_code=401, detail="Invalid login or password")

        now = services_common.current_utc_timestamp()
        if not services_runtime.is_demo_mode_enabled():
            cursor.execute("UPDATE users SET last_login_at = ?, updated_at = ? WHERE id = ?", (now, now, user_row["id"]))
        services_audit.write_auth_audit_event(cursor, "login_success", user_id=user_row["id"])
        auth_response = services_authentication.build_auth_response(connection, user_row["id"])
        if services_memberships.repair_employee_membership_links(cursor, auth_response["user"]):
            services_audit.write_auth_audit_event(cursor, "employee_membership_link_repaired", user_id=user_row["id"])
            auth_response["user"] = services_authentication.get_user_context(cursor, user_row["id"])
        connection.commit()
        services_authentication.clear_login_failures(identifier, request)
        return auth_response
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.post("/api/auth/create-organization", tags=["Auth"])
def create_owner_organization(request_data: AuthOrganizationCreateRequest, request: Request):
    if services_runtime.is_cloud_employee_portal_mode() and not services_runtime.is_trusted_desktop_cloud_request(request):
        raise HTTPException(status_code=404, detail="Organization setup is available only in the desktop app")
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        email = str(request_data.email).strip().lower()
        now = services_common.current_utc_timestamp()
        cursor.execute("SELECT id, password_hash, status FROM users WHERE lower(email) = ?", (email,))
        user_row = cursor.fetchone()
        if user_row:
            if user_row["status"] != "active" or not services_authentication.verify_password(request_data.password, user_row["password_hash"]):
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
                (email, request_data.full_name.strip(), services_authentication.hash_password(request_data.password), now, now),
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
        services_audit.write_auth_audit_event(cursor, "organization_created", user_id=user_id, organization_id=organization_id)
        auth_response = services_authentication.build_auth_response(connection, user_id)
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


@router.get("/api/auth/me", tags=["Auth"])
def get_authenticated_user(current_user: dict = Depends(services_authentication.get_current_user)):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        if services_memberships.repair_employee_membership_links(cursor, current_user):
            services_audit.write_auth_audit_event(cursor, "employee_membership_link_repaired", user_id=current_user["id"])
            connection.commit()
            return {"user": services_authentication.get_user_context(cursor, current_user["id"])}
        return {"user": current_user}
    finally:
        connection.close()


@router.get("/api/auth/status", tags=["Auth"])
def auth_status():
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) AS user_count FROM users WHERE status = 'active'")
        user_count = cursor.fetchone()["user_count"]
        cursor.execute("SELECT COUNT(*) AS organization_count FROM organizations WHERE status = 'active'")
        organization_count = cursor.fetchone()["organization_count"]
        return {
            "app_version": app_constants.APP_VERSION,
            "app_name": app_constants.APP_NAME,
            "demo_mode": services_runtime.is_demo_mode_enabled(),
            "bootstrap_available": False if services_runtime.is_demo_mode_enabled() else user_count == 0,
            "active_user_count": user_count,
            "active_organization_count": organization_count,
            "environment": app_config.get_app_config().app_env,
            "demo_user": services_authentication.get_demo_user_context() if services_runtime.is_demo_mode_enabled() else None,
        }
    finally:
        connection.close()


@router.put("/api/auth/profile", tags=["Auth"])
def update_authenticated_profile(
    request_data: AuthProfileUpdateRequest,
    current_user: dict = Depends(services_authentication.get_current_user),
):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        now = services_common.current_utc_timestamp()
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
        services_audit.write_auth_audit_event(cursor, "profile_updated", user_id=current_user["id"])
        updated_user = services_authentication.get_user_context(cursor, current_user["id"])
        connection.commit()
        return {"user": updated_user}
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.post("/api/auth/logout", tags=["Auth"])
def logout(authorization: str | None = Header(default=None), current_user: dict = Depends(services_authentication.get_current_user)):
    if services_runtime.is_demo_mode_enabled():
        return {"message": "Demo session kept active", "demo_mode": True}

    token = authorization.split(" ", 1)[1].strip() if authorization else ""
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        now = services_common.current_utc_timestamp()
        cursor.execute(
            """
            UPDATE auth_sessions
            SET revoked_at = ?
            WHERE token_hash = ? AND revoked_at IS NULL
            """,
            (now, services_authentication.hash_session_token(token)),
        )
        services_audit.write_auth_audit_event(cursor, "logout", user_id=current_user["id"])
        connection.commit()
        return {"message": "Logged out successfully"}
    finally:
        connection.close()
