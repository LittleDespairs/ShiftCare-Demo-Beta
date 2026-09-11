"""Services: backups for ShiftCare."""
from __future__ import annotations

from fastapi import HTTPException
from shiftcare.services import runtime as services_runtime
import database as database_module

def create_recovery_backup(label: str) -> str:
    if services_runtime.is_demo_mode_enabled():
        return ""
    if not database_module.is_sqlite_runtime():
        return "cloud_sql_managed_backup"
    try:
        return database_module.create_database_backup(label).name
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create safety backup: {exc}") from exc
