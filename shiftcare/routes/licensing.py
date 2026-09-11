"""Routes: licensing for ShiftCare."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from schemas import LicenseActivationCodeRequest
from schemas import LicenseImportRequest
from shiftcare.services import access as services_access
from shiftcare.services import audit as services_audit
from shiftcare.services import authentication as services_authentication
from shiftcare.services import licensing as services_licensing
import database
import license_runtime

router = APIRouter()


@router.get("/api/license/status", tags=["Licensing"])
def get_license_status():
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        return services_licensing.build_license_status_payload(cursor)
    finally:
        connection.close()


@router.post("/api/license/import-file", tags=["Licensing"])
def import_license_file(
    request_data: LicenseImportRequest,
    admin_context: dict | None = Depends(services_access.require_database_admin_if_auth_initialized),
):
    services_licensing.require_not_demo("License import")
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        payload = services_licensing.import_license_certificate(cursor, request_data.certificate, source="imported")
        connection.commit()
        return {"message": "License imported", "license": payload}
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.post("/api/license/activate-code", tags=["Licensing"])
def activate_license_code(
    request_data: LicenseActivationCodeRequest,
    admin_context: dict | None = Depends(services_access.require_database_admin_if_auth_initialized),
):
    services_licensing.require_not_demo("License activation")
    activation_hash = services_authentication.hash_session_token(request_data.activation_code)
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO license_activation_attempts (organization_id, activation_code_hash, status, error)
            VALUES (1, ?, 'success', NULL)
            """,
            (activation_hash,),
        )
        certificate = license_runtime.decode_activation_code(request_data.activation_code)
        payload = services_licensing.import_license_certificate(cursor, certificate, source="activation_code")
        services_audit.write_license_event(
            cursor,
            "license_activation_succeeded",
            metadata={"source": "activation_code"},
            license_id=certificate["license_id"],
        )
        connection.commit()
        return {"message": "License activated", "license": payload}
    except license_runtime.LicenseValidationError as exc:
        connection.rollback()
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO license_activation_attempts (organization_id, activation_code_hash, status, error)
            VALUES (1, ?, 'failed', ?)
            """,
            (activation_hash, str(exc)),
        )
        services_audit.write_license_event(
            cursor,
            "license_activation_failed",
            metadata={"reason": str(exc), "source": "activation_code"},
        )
        connection.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.post("/api/license/refresh", tags=["Licensing"])
def refresh_license(
    admin_context: dict | None = Depends(services_access.require_database_admin_if_auth_initialized),
):
    services_licensing.require_not_demo("License refresh")
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        services_audit.write_license_event(
            cursor,
            "license_refresh_skipped",
            metadata={"reason": "cloud_license_backend_not_configured"},
        )
        connection.commit()
        return {
            "message": "Cloud license backend is not configured yet",
            "license": services_licensing.build_license_status_payload(cursor),
        }
    finally:
        connection.close()
