"""Routes: members for ShiftCare."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from schemas import OrganizationMemberDepartmentAccessUpdate
from schemas import OrganizationMemberEmployeeLinkUpdate
from schemas import OrganizationMemberRoleUpdate
from shiftcare import config as app_constants
from shiftcare.services import audit as services_audit
from shiftcare.services import authentication as services_authentication
from shiftcare.services import cloud_client as services_cloud_client
from shiftcare.services import common as services_common
from shiftcare.services import memberships as services_memberships
import database

router = APIRouter()


@router.get("/api/organizations/{organization_id}/members", tags=["Auth"])
def get_organization_members(organization_id: int, current_user: dict = Depends(services_authentication.get_current_user)):
    services_authentication.require_organization_role(current_user, organization_id, {"owner", "admin", "scheduler", "manager"})
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        if services_cloud_client.is_desktop_sqlite_runtime():
            settings = services_cloud_client.read_desktop_cloud_sync_settings(cursor, organization_id)
            if services_cloud_client.desktop_cloud_sync_is_ready(settings):
                cloud_response = services_cloud_client.request_cloud_json(
                    settings["cloud_api_base_url"],
                    f"/api/organizations/{int(settings['cloud_organization_id'])}/members",
                    token=settings["desktop_cloud_access_token"],
                )
                cloud_response["members"] = [
                    member
                    for member in cloud_response.get("members") or []
                    if member.get("membership_status") == "active"
                ]
                return cloud_response
        repaired_count = services_memberships.repair_organization_employee_membership_links(cursor, organization_id)
        purged_count = services_memberships.purge_disabled_organization_accounts(cursor, organization_id)
        if repaired_count:
            services_audit.write_auth_audit_event(
                cursor,
                "organization_employee_membership_links_repaired",
                user_id=current_user["id"],
                organization_id=organization_id,
                metadata={"repaired_count": repaired_count},
            )
        if purged_count:
            services_audit.write_auth_audit_event(
                cursor,
                "disabled_member_accounts_purged",
                user_id=current_user["id"],
                organization_id=organization_id,
                metadata={"purged_count": purged_count},
            )
        if repaired_count or purged_count:
            connection.commit()
        cursor.execute(
            """
            SELECT u.id, u.email, u.full_name, u.status AS user_status, u.email_verified,
                   e.full_name AS employee_name,
                   e.public_id AS employee_public_id,
                   om.role, om.status AS membership_status, om.employee_id, om.created_at, om.updated_at,
                   om.department_access_mode
            FROM organization_memberships om
            JOIN users u ON u.id = om.user_id
            LEFT JOIN employees e ON e.id = om.employee_id
            WHERE om.organization_id = ?
              AND om.status = 'active'
            ORDER BY CASE om.status WHEN 'active' THEN 0 WHEN 'invited' THEN 1 ELSE 2 END, u.full_name, u.email
            """,
            (organization_id,),
        )
        member_rows = cursor.fetchall()
        department_access_by_user = services_memberships.build_member_department_access(cursor, organization_id)
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
                    "department_access": department_access_by_user.get(int(row["id"]), []),
                    "department_access_mode": row["department_access_mode"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                for row in member_rows
            ]
        }
    finally:
        connection.close()


@router.put("/api/organizations/{organization_id}/members/{user_id}/department-access", tags=["Auth"])
def update_organization_member_department_access(
    organization_id: int,
    user_id: int,
    request_data: OrganizationMemberDepartmentAccessUpdate,
    current_user: dict = Depends(services_authentication.get_current_user),
):
    actor_membership = services_authentication.require_organization_role(current_user, organization_id, {"owner", "admin"})
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="You cannot change your own department access")

    connection = database.get_connection()
    try:
        cursor = connection.cursor()
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

        target_role = str(target["role"])
        actor_role = str(actor_membership["role"])
        if target_role == "owner":
            raise HTTPException(status_code=400, detail="Owners always have access to all departments")
        if target_role == "admin" and actor_role != "owner":
            raise HTTPException(status_code=403, detail="Only owners can change administrator department access")
        if target_role not in app_constants.DEPARTMENT_ACCESS_LIMITED_ROLES:
            raise HTTPException(status_code=400, detail="Department access can be limited only for administrators and schedule viewers")

        department_ids = request_data.department_ids
        access_mode = request_data.access_mode or ("restricted" if department_ids else "all")
        if department_ids:
            placeholders = ",".join(["?"] * len(department_ids))
            cursor.execute(
                f"""
                SELECT id
                FROM departments
                WHERE organization_id = ?
                  AND id IN ({placeholders})
                """,
                (organization_id, *department_ids),
            )
            existing_department_ids = {int(row["id"]) for row in cursor.fetchall()}
            missing_department_ids = sorted(set(department_ids) - existing_department_ids)
            if missing_department_ids:
                raise HTTPException(status_code=404, detail="Department not found")

        now = services_common.current_utc_timestamp()
        cursor.execute(
            "UPDATE organization_memberships SET department_access_mode = ? WHERE organization_id = ? AND user_id = ?",
            (access_mode, organization_id, user_id),
        )
        cursor.execute(
            """
            DELETE FROM user_department_access
            WHERE organization_id = ? AND user_id = ?
            """,
            (organization_id, user_id),
        )
        for department_id in department_ids:
            cursor.execute(
                """
                INSERT INTO user_department_access (
                    organization_id, user_id, department_id, created_at, updated_at, updated_by
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (organization_id, user_id, department_id, now, now, current_user["id"]),
            )

        services_audit.write_auth_audit_event(
            cursor,
            "member_department_access_updated",
            user_id=current_user["id"],
            organization_id=organization_id,
            metadata={
                "target_user_id": user_id,
                "target_email": target["email"],
                "target_role": target_role,
                "department_ids": department_ids,
                "access_mode": access_mode,
            },
        )
        connection.commit()
        department_access_by_user = services_memberships.build_member_department_access(cursor, organization_id)
        return {
            "message": "Organization member department access updated",
            "user_id": user_id,
            "department_access": department_access_by_user.get(user_id, []),
            "department_access_mode": access_mode,
        }
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.delete("/api/organizations/{organization_id}/members/{user_id}", tags=["Auth"])
def remove_organization_member(
    organization_id: int,
    user_id: int,
    request: Request,
    current_user: dict = Depends(services_authentication.get_current_user),
):
    actor_membership = services_authentication.require_organization_role(current_user, organization_id, {"owner", "admin"})

    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        if services_cloud_client.is_desktop_sqlite_runtime() and services_cloud_client.is_desktop_invitation_request(request):
            settings = services_cloud_client.read_desktop_cloud_sync_settings(cursor, organization_id)
            if services_cloud_client.desktop_cloud_sync_is_ready(settings):
                return services_cloud_client.request_cloud_json(
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

        now = services_common.current_utc_timestamp()
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
        purged_count = services_memberships.purge_disabled_organization_accounts(cursor, organization_id)
        services_audit.write_auth_audit_event(
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
        if purged_count:
            services_audit.write_auth_audit_event(
                cursor,
                "disabled_member_accounts_purged",
                user_id=current_user["id"],
                organization_id=organization_id,
                metadata={"purged_count": purged_count},
            )
        connection.commit()
        return {"message": "Organization member access removed", "purged_user_accounts": purged_count}
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.put("/api/organizations/{organization_id}/members/{user_id}/role", tags=["Auth"])
def update_organization_member_role(
    organization_id: int,
    user_id: int,
    request_data: OrganizationMemberRoleUpdate,
    request: Request,
    current_user: dict = Depends(services_authentication.get_current_user),
):
    actor_membership = services_authentication.require_organization_role(current_user, organization_id, {"owner", "admin"})
    actor_role = actor_membership["role"]
    new_role = request_data.role

    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="You cannot change your own organization role")
    if actor_role != "owner" and new_role in app_constants.OWNER_MANAGED_ROLES:
        raise HTTPException(status_code=403, detail="Only owners can assign owner or administrator roles")

    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        employee_id = request_data.employee_id
        employee_public_id = request_data.employee_public_id

        if services_cloud_client.is_desktop_sqlite_runtime() and services_cloud_client.is_desktop_invitation_request(request):
            settings = services_cloud_client.read_desktop_cloud_sync_settings(cursor, organization_id)
            if services_cloud_client.desktop_cloud_sync_is_ready(settings):
                return services_cloud_client.request_cloud_json(
                    settings["cloud_api_base_url"],
                    f"/api/organizations/{int(settings['cloud_organization_id'])}/members/{user_id}/role",
                    method="PUT",
                    payload={
                        "role": new_role,
                        "employee_id": None,
                        "employee_public_id": employee_public_id,
                    },
                    token=settings["desktop_cloud_access_token"],
                )

        cursor.execute(
            """
            SELECT om.role, om.status, om.employee_id, u.email, u.full_name
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
        if target_role in app_constants.OWNER_MANAGED_ROLES and actor_role != "owner":
            raise HTTPException(status_code=403, detail="Only owners can change owners or administrators")

        if target_role == "owner" and new_role != "owner":
            cursor.execute(
                """
                SELECT COUNT(*) AS owner_count
                FROM organization_memberships
                WHERE organization_id = ? AND role = 'owner' AND status = 'active'
                """,
                (organization_id,),
            )
            if cursor.fetchone()["owner_count"] <= 1:
                raise HTTPException(status_code=409, detail="Cannot demote the last active owner")

        if new_role == "employee":
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

            if employee_id is not None:
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
        else:
            employee_id = None

        now = services_common.current_utc_timestamp()
        cursor.execute(
            """
            UPDATE organization_memberships
            SET role = ?, employee_id = ?, updated_at = ?
            WHERE organization_id = ? AND user_id = ? AND status = 'active'
            """,
            (new_role, employee_id, now, organization_id, user_id),
        )
        if new_role not in app_constants.DEPARTMENT_ACCESS_LIMITED_ROLES:
            cursor.execute(
                """
                DELETE FROM user_department_access
                WHERE organization_id = ? AND user_id = ?
                """,
                (organization_id, user_id),
            )
        cursor.execute(
            """
            UPDATE auth_sessions
            SET revoked_at = ?
            WHERE user_id = ? AND revoked_at IS NULL
            """,
            (now, user_id),
        )
        services_audit.write_auth_audit_event(
            cursor,
            "member_role_updated",
            user_id=current_user["id"],
            organization_id=organization_id,
            metadata={
                "target_user_id": user_id,
                "target_email": target["email"],
                "old_role": target_role,
                "new_role": new_role,
                "employee_id": employee_id,
            },
        )
        connection.commit()
        return {
            "message": "Organization member role updated",
            "member": {
                "user_id": user_id,
                "email": target["email"],
                "full_name": target["full_name"],
                "role": new_role,
                "employee_id": employee_id,
                "membership_status": "active",
            },
        }
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.put("/api/organizations/{organization_id}/members/{user_id}/employee-link", tags=["Auth"])
def update_organization_member_employee_link(
    organization_id: int,
    user_id: int,
    request_data: OrganizationMemberEmployeeLinkUpdate,
    request: Request,
    current_user: dict = Depends(services_authentication.get_current_user),
):
    services_authentication.require_organization_role(current_user, organization_id, {"owner", "admin"})
    connection = database.get_connection()
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

        if services_cloud_client.is_desktop_sqlite_runtime() and services_cloud_client.is_desktop_invitation_request(request):
            settings = services_cloud_client.read_desktop_cloud_sync_settings(cursor, organization_id)
            if services_cloud_client.desktop_cloud_sync_is_ready(settings):
                return services_cloud_client.request_cloud_json(
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

        now = services_common.current_utc_timestamp()
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
        services_audit.write_auth_audit_event(
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
