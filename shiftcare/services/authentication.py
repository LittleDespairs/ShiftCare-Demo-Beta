"""Services: authentication for ShiftCare."""
from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import HTTPException
from fastapi import Header
from fastapi import Request
from shiftcare import config as app_constants
from shiftcare.services import common as services_common
from shiftcare.services import runtime as services_runtime
from time import monotonic
from typing import Any
import auth_repository
import database
import hashlib
import hmac
import os
import re
import secrets

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
    with app_constants.AUTH_LOGIN_ATTEMPTS_LOCK:
        entry = app_constants.AUTH_LOGIN_ATTEMPTS.get(key)
        if not entry:
            return False
        locked_until = float(entry.get("locked_until") or 0)
        if locked_until > now:
            return True
        failures = [
            timestamp
            for timestamp in entry.get("failures", [])
            if now - timestamp <= app_constants.AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS
        ]
        if failures:
            entry["failures"] = failures
            entry["locked_until"] = 0
        else:
            app_constants.AUTH_LOGIN_ATTEMPTS.pop(key, None)
        return False


def record_login_failure(identifier: str, request: Request) -> bool:
    now = monotonic()
    key = login_rate_limit_key(identifier, request)
    with app_constants.AUTH_LOGIN_ATTEMPTS_LOCK:
        entry = app_constants.AUTH_LOGIN_ATTEMPTS.setdefault(key, {"failures": [], "locked_until": 0})
        entry["failures"] = [
            timestamp
            for timestamp in entry["failures"]
            if now - timestamp <= app_constants.AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS
        ]
        entry["failures"].append(now)
        if len(entry["failures"]) >= app_constants.AUTH_LOGIN_RATE_LIMIT_ATTEMPTS:
            entry["locked_until"] = now + app_constants.AUTH_LOGIN_RATE_LIMIT_LOCK_SECONDS
            return True
    return False


def clear_login_failures(identifier: str, request: Request) -> None:
    key = login_rate_limit_key(identifier, request)
    with app_constants.AUTH_LOGIN_ATTEMPTS_LOCK:
        app_constants.AUTH_LOGIN_ATTEMPTS.pop(key, None)


def is_feedback_rate_limited(current_user: dict, request: Request) -> bool:
    now = monotonic()
    key = f"{current_user.get('id') or 'anonymous'}|{get_request_ip(request)}"
    with app_constants.FEEDBACK_ATTEMPTS_LOCK:
        attempts = [
            timestamp
            for timestamp in app_constants.FEEDBACK_ATTEMPTS.get(key, [])
            if now - timestamp <= app_constants.FEEDBACK_RATE_LIMIT_WINDOW_SECONDS
        ]
        if len(attempts) >= app_constants.FEEDBACK_RATE_LIMIT_ATTEMPTS:
            app_constants.FEEDBACK_ATTEMPTS[key] = attempts
            return True
        attempts.append(now)
        app_constants.FEEDBACK_ATTEMPTS[key] = attempts
        return False


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


def get_demo_user_context() -> dict:
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT id FROM users WHERE lower(email) = ?", (database.DEMO_USER_EMAIL,))
        user_row = cursor.fetchone()
        if user_row:
            return get_user_context(cursor, int(user_row["id"]))
    finally:
        connection.close()

    now = services_common.current_utc_timestamp()
    return {
        "id": 0,
        "email": database.DEMO_USER_EMAIL,
        "full_name": "Demo Administrator",
        "status": "active",
        "email_verified": True,
        "created_at": now,
        "updated_at": now,
        "last_login_at": None,
        "memberships": [
            {
                "organization_id": 1,
                "organization_public_id": "shiftcare-demo-center",
                "organization_name": "ShiftCare Demo Center",
                "role": "owner",
                "status": "active",
                "employee_id": None,
            }
        ],
    }


def build_demo_auth_response() -> dict:
    expires_at = (
        datetime.now(UTC) + timedelta(days=3650)
    ).replace(tzinfo=None).isoformat(timespec="seconds")
    return {
        "access_token": app_constants.DEMO_ACCESS_TOKEN,
        "token_type": "bearer",
        "expires_at": expires_at,
        "user": get_demo_user_context(),
    }


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if services_runtime.is_demo_mode_enabled():
        return get_demo_user_context()
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        user_id = auth_repository.get_session_user_id(
            cursor,
            hash_session_token(token),
            services_common.current_utc_timestamp(),
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


def get_optional_current_user(authorization: str | None = Header(default=None)) -> dict | None:
    if not authorization:
        return None
    try:
        return get_current_user(authorization)
    except HTTPException:
        return None
