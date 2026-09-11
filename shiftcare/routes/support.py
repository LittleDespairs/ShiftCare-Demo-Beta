"""Routes: support for ShiftCare."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from schemas import FeedbackReportCreate
from shiftcare.services import access as services_access
from shiftcare.services import audit as services_audit
from shiftcare.services import authentication as services_authentication
from shiftcare.services import feedback as services_feedback
from typing import Any
import database
import email_service

router = APIRouter()


@router.get("/api/support/accounts", tags=["Support"])
def get_support_accounts(_support: dict = Depends(services_access.require_developer_support_access)):
    connection = database.get_connection()
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


@router.post("/api/feedback/reports", tags=["Feedback"])
def create_feedback_report(
    request_data: FeedbackReportCreate,
    request: Request,
    current_user: dict = Depends(services_authentication.get_current_user),
):
    if services_authentication.is_feedback_rate_limited(current_user, request):
        raise HTTPException(status_code=429, detail="Too many reports. Please try again later.")

    membership = services_feedback.feedback_membership_for_user(current_user, request_data.organization_id)
    connection = database.get_connection()
    report: dict[str, Any] | None = None
    notification: dict[str, Any] = {"status": "not_attempted"}
    try:
        cursor = connection.cursor()
        report = services_feedback.insert_feedback_report(cursor, request_data, request, current_user, membership)
        services_audit.write_auth_audit_event(
            cursor,
            "feedback_report_created",
            user_id=report["user_id"],
            organization_id=report["organization_id"],
            metadata={
                "public_id": report["public_id"],
                "report_type": report["report_type"],
                "severity": report["severity"],
                "area": report["area"],
            },
        )
        connection.commit()

        try:
            cloud_response = services_feedback.forward_desktop_feedback_to_cloud(cursor, report, request_data, membership)
            if cloud_response is not None:
                cloud_report = cloud_response.get("report") or {}
                cloud_notification = cloud_response.get("notification") or {}
                notification = {
                    "status": "forwarded",
                    "detail": (
                        f"Forwarded to cloud report {cloud_report.get('public_id') or '-'}; "
                        f"cloud notification: {cloud_notification.get('status') or 'unknown'}"
                    ),
                    "cloud_report_public_id": cloud_report.get("public_id"),
                    "cloud_notification": cloud_notification,
                }
                services_feedback.update_feedback_notification_status(
                    cursor,
                    report["public_id"],
                    "forwarded",
                    notification["detail"],
                    forwarded=True,
                )
            else:
                email_result = email_service.send_feedback_report_email(report=report)
                notification = email_result.as_public_dict()
                services_feedback.update_feedback_notification_status(
                    cursor,
                    report["public_id"],
                    email_result.status,
                    email_result.detail,
                )
            connection.commit()
        except Exception as exc:
            connection.rollback()
            notification = {"status": "failed", "detail": str(exc)[:500]}
            cursor = connection.cursor()
            services_feedback.update_feedback_notification_status(
                cursor,
                report["public_id"],
                "failed",
                notification["detail"],
            )
            connection.commit()

        return {
            "message": "Report submitted successfully",
            "report": {
                "id": report["id"],
                "public_id": report["public_id"],
                "status": report["status"],
                "type": report["report_type"],
            },
            "notification": notification,
        }
    except HTTPException:
        connection.rollback()
        raise
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
