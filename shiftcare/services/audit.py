"""Services: audit for ShiftCare."""
from __future__ import annotations

from shiftcare.services import runtime as services_runtime
import auth_repository
import database
import json

def write_auth_audit_event(
    cursor,
    event_type: str,
    user_id: int | None = None,
    organization_id: int | None = None,
    metadata: dict | None = None,
) -> None:
    if services_runtime.is_demo_mode_enabled():
        return
    auth_repository.write_auth_audit_event(
        cursor,
        event_type,
        user_id=user_id,
        organization_id=organization_id,
        metadata=metadata,
    )


def write_auth_audit_event_record(
    event_type: str,
    user_id: int | None = None,
    organization_id: int | None = None,
    metadata: dict | None = None,
) -> None:
    if services_runtime.is_demo_mode_enabled():
        return
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        write_auth_audit_event(
            cursor,
            event_type,
            user_id=user_id,
            organization_id=organization_id,
            metadata=metadata,
        )
        connection.commit()
    finally:
        connection.close()


def write_license_event(
    cursor,
    event_type: str,
    organization_id: int = 1,
    license_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    if services_runtime.is_demo_mode_enabled():
        return
    cursor.execute(
        """
        INSERT INTO license_events (organization_id, license_id, event_type, metadata_json)
        VALUES (?, ?, ?, ?)
        """,
        (organization_id, license_id, event_type, json.dumps(metadata or {}, ensure_ascii=False)),
    )
