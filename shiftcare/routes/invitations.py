"""Routes: invitations for ShiftCare."""
from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from schemas import AuthInvitationAcceptRequest
from schemas import OrganizationInvitationCreate
from shiftcare import config as app_constants
from shiftcare.services import audit as services_audit
from shiftcare.services import authentication as services_authentication
from shiftcare.services import cloud_client as services_cloud_client
from shiftcare.services import common as services_common
from shiftcare.services import memberships as services_memberships
from shiftcare.services import runtime as services_runtime
import database
import email_service
import secrets
import sqlite3

router = APIRouter()


@router.post("/api/auth/accept-invitation", tags=["Auth"])
def accept_invitation(request_data: AuthInvitationAcceptRequest):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        now = services_common.current_utc_timestamp()
        token_hash = services_authentication.hash_session_token(request_data.token)
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
            if existing_user["password_hash"] and not services_authentication.verify_password(request_data.password, existing_user["password_hash"]):
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
                    services_authentication.hash_password(request_data.password),
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
        services_audit.write_auth_audit_event(
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
        auth_response = services_authentication.build_auth_response(connection, user_id)
        connection.commit()
        return auth_response
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.get("/api/auth/invitation-preview", tags=["Auth"])
def get_invitation_preview(token: str):
    connection = database.get_connection()
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
            (services_authentication.hash_session_token(token), services_common.current_utc_timestamp()),
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


@router.get("/api/organizations/{organization_id}/invitations", tags=["Auth"])
def get_organization_invitations(organization_id: int, current_user: dict = Depends(services_authentication.get_current_user)):
    services_authentication.require_organization_role(current_user, organization_id, {"owner", "admin"})
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        if services_cloud_client.is_desktop_sqlite_runtime():
            settings = services_cloud_client.read_desktop_cloud_sync_settings(cursor, organization_id)
            if services_cloud_client.desktop_cloud_sync_is_ready(settings):
                return services_cloud_client.request_cloud_json(
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


@router.post("/api/organizations/{organization_id}/invitations", tags=["Auth"])
def create_organization_invitation(
    organization_id: int,
    request_data: OrganizationInvitationCreate,
    request: Request,
    current_user: dict = Depends(services_authentication.get_current_user),
):
    actor_membership = services_authentication.require_organization_role(current_user, organization_id, {"owner", "admin"})
    if request_data.role in app_constants.OWNER_MANAGED_ROLES and actor_membership["role"] != "owner":
        raise HTTPException(status_code=403, detail="Only owners can invite owners or administrators")
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        organization = services_common.fetch_one_or_404(
            cursor,
            "SELECT id, name FROM organizations WHERE id = ?",
            (organization_id,),
            "Organization not found",
        )
        email = str(request_data.email).strip().lower()
        purged_count = services_memberships.purge_disabled_organization_accounts(cursor, organization_id)
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
        employee_name = ""
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
                SELECT id, public_id, full_name
                FROM employees
                WHERE id = ? AND organization_id = ?
                """,
                (employee_id, organization_id),
            )
            employee_row = cursor.fetchone()
            if not employee_row:
                raise HTTPException(status_code=404, detail="Employee not found in this organization")
            employee_public_id = employee_row["public_id"]
            employee_name = str(employee_row["full_name"] or "")
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

        if services_cloud_client.is_desktop_sqlite_runtime() and services_cloud_client.is_desktop_invitation_request(request):
            settings = services_cloud_client.read_desktop_cloud_sync_settings(cursor, organization_id)
            if services_cloud_client.desktop_cloud_sync_is_ready(settings):
                cloud_payload = {
                    "email": email,
                    "employee_public_id": employee_public_id,
                    "role": request_data.role,
                    "expires_in_days": request_data.expires_in_days,
                }
                cloud_response = services_cloud_client.request_cloud_json(
                    settings["cloud_api_base_url"],
                    f"/api/organizations/{int(settings['cloud_organization_id'])}/invitations",
                    method="POST",
                    payload=cloud_payload,
                    token=settings["desktop_cloud_access_token"],
                )
                cloud_invitation = cloud_response.get("invitation") or {}
                cloud_token = cloud_response.get("invitation_token") or secrets.token_urlsafe(32)
                now = services_common.current_utc_timestamp()
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
                        services_authentication.hash_session_token(cloud_token),
                        expires_at,
                        current_user["id"],
                        now,
                    ),
                )
                local_invitation_id = cursor.lastrowid
                services_audit.write_auth_audit_event(
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
                if purged_count:
                    services_audit.write_auth_audit_event(
                        cursor,
                        "disabled_member_accounts_purged",
                        user_id=current_user["id"],
                        organization_id=organization_id,
                        metadata={"purged_count": purged_count},
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
                    "invitation_url": cloud_response.get("invitation_url") or services_runtime.build_invitation_url_for_request(request, cloud_token),
                    "email_status": cloud_response.get("email_status") or {"status": "sent_by_cloud"},
                }
            raise HTTPException(
                status_code=409,
                detail="Cloud invitation link is not available. Sign in with a cloud organization before inviting employees.",
            )

        now = services_common.current_utc_timestamp()
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
                services_authentication.hash_session_token(invitation_token),
                expires_at,
                current_user["id"],
                now,
            ),
        )
        invitation_id = cursor.lastrowid
        services_audit.write_auth_audit_event(
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
        if purged_count:
            services_audit.write_auth_audit_event(
                cursor,
                "disabled_member_accounts_purged",
                user_id=current_user["id"],
                organization_id=organization_id,
                metadata={"purged_count": purged_count},
            )
        invitation_url = services_runtime.build_invitation_url_for_request(request, invitation_token)
        connection.commit()
        email_result = email_service.send_invitation_email(
            to_email=email,
            invitation_url=invitation_url,
            organization_name=str(organization["name"] or "ShiftCare"),
            role=request_data.role,
            expires_at=expires_at,
            employee_name=employee_name,
        )
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
            "invitation_url": invitation_url,
            "email_status": email_service.public_email_status(email_result),
        }
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise HTTPException(status_code=409, detail="Invitation already exists or token collision") from exc
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.delete("/api/organizations/{organization_id}/invitations/{invitation_id}", tags=["Auth"])
def revoke_organization_invitation(
    organization_id: int,
    invitation_id: int,
    request: Request,
    current_user: dict = Depends(services_authentication.get_current_user),
):
    services_authentication.require_organization_role(current_user, organization_id, {"owner", "admin"})
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        if services_cloud_client.is_desktop_sqlite_runtime() and services_cloud_client.is_desktop_invitation_request(request):
            settings = services_cloud_client.read_desktop_cloud_sync_settings(cursor, organization_id)
            if services_cloud_client.desktop_cloud_sync_is_ready(settings):
                return services_cloud_client.request_cloud_json(
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

        now = services_common.current_utc_timestamp()
        cursor.execute(
            """
            UPDATE organization_invitations
            SET status = 'revoked'
            WHERE id = ? AND organization_id = ? AND status = 'pending'
            """,
            (invitation_id, organization_id),
        )
        services_audit.write_auth_audit_event(
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


@router.post("/api/organizations/{organization_id}/invitations/{invitation_id}/regenerate-token", tags=["Auth"])
def regenerate_organization_invitation_token(
    organization_id: int,
    invitation_id: int,
    request: Request,
    current_user: dict = Depends(services_authentication.get_current_user),
):
    services_authentication.require_organization_role(current_user, organization_id, {"owner", "admin"})
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        if services_cloud_client.is_desktop_sqlite_runtime() and services_cloud_client.is_desktop_invitation_request(request):
            settings = services_cloud_client.read_desktop_cloud_sync_settings(cursor, organization_id)
            if services_cloud_client.desktop_cloud_sync_is_ready(settings):
                return services_cloud_client.request_cloud_json(
                    settings["cloud_api_base_url"],
                    f"/api/organizations/{int(settings['cloud_organization_id'])}/invitations/{invitation_id}/regenerate-token",
                    method="POST",
                    token=settings["desktop_cloud_access_token"],
                )

        cursor.execute(
            """
            SELECT oi.id, oi.email, oi.employee_id, oi.role, oi.status,
                   e.full_name AS employee_name,
                   o.name AS organization_name
            FROM organization_invitations oi
            LEFT JOIN employees e ON e.id = oi.employee_id
            JOIN organizations o ON o.id = oi.organization_id
            WHERE oi.id = ? AND oi.organization_id = ?
            """,
            (invitation_id, organization_id),
        )
        invitation = cursor.fetchone()
        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found")
        if invitation["status"] != "pending":
            raise HTTPException(status_code=409, detail="Only pending invitations can receive a new link")

        now = services_common.current_utc_timestamp()
        expires_at = (datetime.now(UTC) + timedelta(days=7)).replace(tzinfo=None).isoformat(timespec="seconds")
        invitation_token = secrets.token_urlsafe(32)
        cursor.execute(
            """
            UPDATE organization_invitations
            SET token_hash = ?, expires_at = ?
            WHERE id = ? AND organization_id = ? AND status = 'pending'
            """,
            (services_authentication.hash_session_token(invitation_token), expires_at, invitation_id, organization_id),
        )
        services_audit.write_auth_audit_event(
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
        invitation_url = services_runtime.build_invitation_url_for_request(request, invitation_token)
        connection.commit()
        email_result = email_service.send_invitation_email(
            to_email=str(invitation["email"]),
            invitation_url=invitation_url,
            organization_name=str(invitation["organization_name"] or "ShiftCare"),
            role=str(invitation["role"]),
            expires_at=expires_at,
            employee_name=str(invitation["employee_name"] or ""),
        )
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
            "invitation_url": invitation_url,
            "email_status": email_service.public_email_status(email_result),
        }
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise HTTPException(status_code=409, detail="Invitation token collision") from exc
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()
