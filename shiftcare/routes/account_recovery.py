"""Routes: account recovery for ShiftCare."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Header
from fastapi import Request
from schemas import AuthEmailVerificationRequest
from schemas import AuthPasswordChangeRequest
from schemas import AuthPasswordResetConfirmRequest
from schemas import AuthPasswordResetRequest
from shiftcare.services import audit as services_audit
from shiftcare.services import authentication as services_authentication
from shiftcare.services import common as services_common
from shiftcare.services import runtime as services_runtime
import database
import email_service
import secrets

router = APIRouter()


@router.post("/api/auth/change-password", tags=["Auth"])
def change_authenticated_password(
    request_data: AuthPasswordChangeRequest,
    authorization: str | None = Header(default=None),
    current_user: dict = Depends(services_authentication.get_current_user),
):
    token = authorization.split(" ", 1)[1].strip() if authorization else ""
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE id = ?", (current_user["id"],))
        user_row = cursor.fetchone()
        if not user_row or not services_authentication.verify_password(request_data.current_password, user_row["password_hash"]):
            raise HTTPException(status_code=401, detail="Current password is incorrect")

        now = services_common.current_utc_timestamp()
        cursor.execute(
            """
            UPDATE users
            SET password_hash = ?, updated_at = ?
            WHERE id = ?
            """,
            (services_authentication.hash_password(request_data.new_password), now, current_user["id"]),
        )
        cursor.execute(
            """
            UPDATE auth_sessions
            SET revoked_at = ?
            WHERE user_id = ?
              AND token_hash != ?
              AND revoked_at IS NULL
            """,
            (now, current_user["id"], services_authentication.hash_session_token(token)),
        )
        services_audit.write_auth_audit_event(cursor, "password_changed", user_id=current_user["id"])
        connection.commit()
        return {"message": "Password changed successfully"}
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.post("/api/auth/request-password-reset", tags=["Auth"])
def request_password_reset(request_data: AuthPasswordResetRequest, request: Request):
    connection = database.get_connection()
    reset_email = None
    reset_url = ""
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
                (user_row["id"], services_authentication.hash_session_token(reset_token), services_authentication.token_expiration(days=1)),
            )
            services_audit.write_auth_audit_event(
                cursor,
                "password_reset_requested",
                user_id=user_row["id"],
                metadata={"email": email, "ip": services_authentication.get_request_ip(request)},
            )
            reset_email = email
            reset_url = services_runtime.build_password_reset_url_for_request(request, reset_token)
        connection.commit()
        email_result = None
        if reset_email and reset_url:
            email_result = email_service.send_password_reset_email(to_email=reset_email, reset_url=reset_url)
        include_debug_token = not email_service.email_delivery_is_enabled()
        return {
            "message": "If the account exists, password reset instructions were created.",
            "reset_token": reset_token if include_debug_token else None,
            "email_status": email_service.public_email_status(email_result) if reset_token else {"status": "not_attempted"},
        }
    finally:
        connection.close()


@router.post("/api/auth/reset-password", tags=["Auth"])
def reset_password(request_data: AuthPasswordResetConfirmRequest):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        now = services_common.current_utc_timestamp()
        cursor.execute(
            """
            SELECT id, user_id
            FROM auth_password_reset_tokens
            WHERE token_hash = ?
              AND used_at IS NULL
              AND expires_at > ?
            """,
            (services_authentication.hash_session_token(request_data.token), now),
        )
        token_row = cursor.fetchone()
        if not token_row:
            raise HTTPException(status_code=404, detail="Password reset token not found or expired")

        cursor.execute(
            "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
            (services_authentication.hash_password(request_data.new_password), now, token_row["user_id"]),
        )
        cursor.execute(
            "UPDATE auth_password_reset_tokens SET used_at = ? WHERE id = ?",
            (now, token_row["id"]),
        )
        cursor.execute(
            "UPDATE auth_sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
            (now, token_row["user_id"]),
        )
        services_audit.write_auth_audit_event(cursor, "password_reset_completed", user_id=token_row["user_id"])
        connection.commit()
        return {"message": "Password reset successfully"}
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.post("/api/auth/request-email-verification", tags=["Auth"])
def request_email_verification(request: Request, current_user: dict = Depends(services_authentication.get_current_user)):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        verification_token = secrets.token_urlsafe(32)
        cursor.execute(
            """
            INSERT INTO auth_email_verification_tokens (user_id, token_hash, expires_at)
            VALUES (?, ?, ?)
            """,
            (current_user["id"], services_authentication.hash_session_token(verification_token), services_authentication.token_expiration(days=7)),
        )
        services_audit.write_auth_audit_event(cursor, "email_verification_requested", user_id=current_user["id"])
        connection.commit()
        verification_url = services_runtime.build_email_verification_url_for_request(request, verification_token)
        email_result = email_service.send_email_verification_email(
            to_email=str(current_user["email"]),
            verification_url=verification_url,
        )
        include_debug_token = not email_service.email_delivery_is_enabled()
        return {
            "message": "Email verification token created.",
            "verification_token": verification_token if include_debug_token else None,
            "email_status": email_service.public_email_status(email_result),
        }
    finally:
        connection.close()


@router.post("/api/auth/verify-email", tags=["Auth"])
def verify_email(request_data: AuthEmailVerificationRequest):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        now = services_common.current_utc_timestamp()
        cursor.execute(
            """
            SELECT id, user_id
            FROM auth_email_verification_tokens
            WHERE token_hash = ?
              AND used_at IS NULL
              AND expires_at > ?
            """,
            (services_authentication.hash_session_token(request_data.token), now),
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
        services_audit.write_auth_audit_event(cursor, "email_verified", user_id=token_row["user_id"])
        connection.commit()
        return {"message": "Email verified successfully"}
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()
