"""Routes: backups for ShiftCare."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from schemas import DatabaseBackupCreateRequest
from schemas import DatabaseRestoreRequest
from shiftcare import config as app_constants
from shiftcare.services import access as services_access
from shiftcare.services import audit as services_audit
from shiftcare.services import licensing as services_licensing
import database as database_module
import sqlite3

router = APIRouter()


@router.get("/api/database/backups", tags=["Settings"])
def get_database_backups(admin_context: dict | None = Depends(services_access.require_database_admin_if_auth_initialized)):
    return {"backups": database_module.list_database_backups()}


@router.post("/api/database/backups", tags=["Settings"])
def create_database_backup_endpoint(
    request_data: DatabaseBackupCreateRequest,
    admin_context: dict | None = Depends(services_access.require_database_admin_if_auth_initialized),
):
    services_licensing.require_not_demo("Database backup")
    if not database_module.is_sqlite_runtime():
        raise HTTPException(
            status_code=409,
            detail="File backups are disabled for PostgreSQL/Cloud SQL runtime. Use Cloud SQL managed backups.",
        )
    user_id, organization_id = services_licensing.audit_context_from_admin(admin_context)
    backup_path = database_module.create_schedule_backup(
        request_data.label,
        app_version=app_constants.APP_VERSION,
        schema_version=database_module.CURRENT_SCHEMA_VERSION,
        organization_id=organization_id or 1,
        created_by=user_id,
    )
    services_audit.write_auth_audit_event_record(
        "database_backup_created",
        user_id=user_id,
        organization_id=organization_id,
        metadata={"backup_name": backup_path.name, "label": request_data.label},
    )
    return {
        "message": "Database backup created successfully",
        "backup_name": backup_path.name,
    }


@router.post("/api/database/restore", tags=["Settings"])
def restore_database_backup_endpoint(
    request_data: DatabaseRestoreRequest,
    admin_context: dict | None = Depends(services_access.require_database_admin_if_auth_initialized),
):
    services_licensing.require_not_demo("Database restore")
    if not database_module.is_sqlite_runtime():
        raise HTTPException(
            status_code=409,
            detail="File restore is disabled for PostgreSQL/Cloud SQL runtime. Use Cloud SQL point-in-time recovery.",
        )
    try:
        result = database_module.restore_database_backup(request_data.backup_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Backup not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except sqlite3.Error as exc:
        raise HTTPException(status_code=409, detail="Database restore could not complete; retry after other operations finish") from exc
    user_id, organization_id = services_licensing.audit_context_from_admin(admin_context)
    # A backup can predate the account performing the restore. Audit the
    # operation without referencing identities that do not exist in that DB.
    with database_module.get_connection() as connection:
        if user_id and not connection.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone():
            user_id = None
            result["requires_login"] = True
        if organization_id and not connection.execute("SELECT 1 FROM organizations WHERE id = ?", (organization_id,)).fetchone():
            organization_id = None
    services_audit.write_auth_audit_event_record(
        "database_backup_restored",
        user_id=user_id,
        organization_id=organization_id,
        metadata=result,
    )
    return {"message": "Database restored successfully", **result}
