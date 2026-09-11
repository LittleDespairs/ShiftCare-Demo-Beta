"""Routes: settings for ShiftCare."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from schemas import AppSettingsUpdate
from shiftcare.services import access as services_access
import app_settings_service
import database

router = APIRouter()


@router.get("/api/app-settings", tags=["Requirements"])
def get_app_settings_api(access_context: dict | None = Depends(services_access.require_schedule_view_if_auth_initialized)):
    organization_id = access_context["membership"]["organization_id"] if access_context else 1
    connection = database.get_connection()
    try:
        return app_settings_service.get_app_settings(connection, organization_id=organization_id)
    finally:
        connection.close()


@router.put("/api/app-settings", tags=["Requirements"])
def update_app_settings(
    settings: AppSettingsUpdate,
    _access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized),
):
    organization_id = _access["membership"]["organization_id"] if _access else 1
    connection = database.get_connection()
    try:
        app_settings_service.save_app_settings(connection, settings, organization_id=organization_id)
        connection.commit()
        return {
            "message": "Application settings updated successfully",
            "settings": app_settings_service.get_app_settings(connection, organization_id=organization_id),
        }
    finally:
        connection.close()


@router.post("/api/app-settings/reset-colors", tags=["Requirements"])
def reset_app_visual_colors(_access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized)):
    organization_id = _access["membership"]["organization_id"] if _access else 1
    connection = database.get_connection()
    try:
        updated_positions = app_settings_service.reset_visual_color_settings(connection, organization_id=organization_id)
        connection.commit()
        return {
            "message": "Visual colors reset successfully",
            "settings": app_settings_service.get_app_settings(connection, organization_id=organization_id),
            "updated_positions": updated_positions,
            "default_position_color": app_settings_service.DEFAULT_POSITION_COLOR,
        }
    finally:
        connection.close()
