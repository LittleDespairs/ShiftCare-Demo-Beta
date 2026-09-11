"""Routes: updates for ShiftCare."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi import HTTPException
from schemas import UpdateInstallRequest
from shiftcare import config as app_constants
from shiftcare.services import licensing as services_licensing
from shiftcare.services import updates as services_updates
import subprocess
import update_service

router = APIRouter()


@router.get("/api/updates/check", tags=["Settings"])
def check_for_updates():
    return services_updates.get_update_status()


@router.get("/api/updates/startup", tags=["Settings"])
def get_startup_update_state():
    if not services_updates.update_notifications_are_enabled():
        return {
            "current_version": app_constants.APP_VERSION,
            "updates_enabled": False,
            "post_update_changelog": None,
            "update_status": {
                "current_version": app_constants.APP_VERSION,
                "update_available": False,
            },
        }

    update_status = {
        "current_version": app_constants.APP_VERSION,
        "update_available": False,
    }
    update_error = None
    try:
        update_status = services_updates.get_update_status()
    except HTTPException as exc:
        update_error = exc.detail
    except Exception as exc:
        update_error = str(exc)

    if update_error:
        update_status = {
            "current_version": app_constants.APP_VERSION,
            "update_available": False,
            "error": update_error,
        }

    return {
        "current_version": app_constants.APP_VERSION,
        "updates_enabled": True,
        "post_update_changelog": services_updates.read_pending_update_changelog(),
        "update_status": update_status,
    }


@router.post("/api/updates/post-install-changelog/ack", tags=["Settings"])
def acknowledge_post_install_changelog():
    services_updates.mark_update_changelog_seen()
    return {"message": "Update changelog acknowledged.", "current_version": app_constants.APP_VERSION}


@router.post("/api/updates/install", tags=["Settings"])
def install_update(request_data: UpdateInstallRequest):
    services_licensing.require_not_demo("Update installation")
    status = services_updates.get_update_status()
    latest = status.get("latest")
    if not latest or not status.get("update_available"):
        return {
            "message": "No newer update is available.",
            "current_version": app_constants.APP_VERSION,
            "update_available": False,
        }

    if request_data.download_url != latest["download_url"] or request_data.asset_name != latest["asset_name"]:
        raise HTTPException(status_code=400, detail="Requested update does not match the latest release")

    installer_path = services_updates.download_update_installer(latest["download_url"], latest["asset_name"])
    update_service.verify_windows_installer_signature(installer_path)
    services_updates.remember_pending_update_changelog(latest)
    subprocess.Popen([str(installer_path), "/CLOSEAPPLICATIONS"], close_fds=True)
    update_service.schedule_desktop_shutdown()

    return {
        "message": "Update installer started.",
        "installer_path": str(installer_path),
        "latest": latest,
    }
