"""Routes: pages for ShiftCare."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import RedirectResponse
from shiftcare import web as web
from shiftcare.services import runtime as services_runtime
from shiftcare.services import updates as services_updates
import update_service

router = APIRouter()


def desktop_only_page_or_404(template_name: str, request: Request):
    if services_runtime.is_cloud_employee_portal_mode():
        raise HTTPException(status_code=404, detail="This page is available only in the desktop app")
    return web.templates.TemplateResponse(request=request, name=template_name, context={})


@router.get("/", tags=["Pages"])
def home_page(request: Request):
    if services_runtime.is_cloud_employee_portal_mode():
        return web.templates.TemplateResponse(request=request, name="schedule.html", context={})
    return web.templates.TemplateResponse(request=request, name="index.html", context={})


@router.get("/login", tags=["Pages"])
def login_page(request: Request):
    if services_runtime.is_demo_mode_enabled():
        return RedirectResponse("/", status_code=302, headers=update_service.no_store_headers())
    return web.templates.TemplateResponse(request=request, name="login.html", context={})


@router.get("/api/download/latest", tags=["Download"])
def latest_download_metadata():
    return services_updates.get_latest_download_payload()


@router.get("/api/download/demo/latest", tags=["Download"])
def latest_demo_download_metadata():
    return services_updates.get_latest_demo_download_payload()


@router.get("/download/latest", tags=["Download"])
def redirect_latest_download():
    payload = services_updates.get_latest_download_payload()
    return RedirectResponse(
        payload["latest"]["download_url"],
        status_code=302,
        headers=update_service.no_store_headers(),
    )


@router.get("/download/demo/latest", tags=["Download"])
def redirect_latest_demo_download():
    payload = services_updates.get_latest_demo_download_payload()
    return RedirectResponse(
        payload["latest"]["download_url"],
        status_code=302,
        headers=update_service.no_store_headers(),
    )


@router.get("/download", tags=["Pages"])
@router.get("/download-shiftcare", tags=["Pages"], include_in_schema=False)
@router.get("/download/shiftcare", tags=["Pages"], include_in_schema=False)
def download_page(request: Request):
    payload = services_updates.get_latest_download_payload()
    try:
        payload["demo_latest"] = services_updates.get_latest_demo_download_payload()["latest"]
    except HTTPException:
        payload["demo_latest"] = None
    return web.templates.TemplateResponse(
        request=request,
        name="download.html",
        context=payload,
        headers=update_service.no_store_headers(),
    )


@router.get("/organization", tags=["Pages"])
def organization_page(request: Request):
    return web.templates.TemplateResponse(request=request, name="organization.html", context={})


@router.get("/organizations", tags=["Pages"], include_in_schema=False)
def organizations_page_alias(request: Request):
    return web.templates.TemplateResponse(request=request, name="organization.html", context={})


@router.get("/support", tags=["Pages"])
def support_page(request: Request):
    if not services_runtime.is_developer_mode_enabled():
        raise HTTPException(status_code=404, detail="Developer support mode is disabled")
    return web.templates.TemplateResponse(request=request, name="support.html", context={})


@router.get("/feedback", tags=["Pages"])
def feedback_page(request: Request):
    return web.templates.TemplateResponse(request=request, name="feedback.html", context={})


@router.get("/accept-invitation", tags=["Pages"])
def accept_invitation_page(request: Request):
    return web.templates.TemplateResponse(request=request, name="accept_invitation.html", context={})


@router.get("/reset-password", tags=["Pages"])
def reset_password_page(request: Request):
    return web.templates.TemplateResponse(request=request, name="reset_password.html", context={})


@router.get("/verify-email", tags=["Pages"])
def verify_email_page(request: Request):
    return web.templates.TemplateResponse(request=request, name="verify_email.html", context={})


@router.get("/employees", tags=["Pages"])
def employees_page(request: Request):
    return desktop_only_page_or_404("employees.html", request)


@router.get("/positions", tags=["Pages"])
def positions_page(request: Request):
    return desktop_only_page_or_404("positions.html", request)


@router.get("/departments", tags=["Pages"])
def departments_page(request: Request):
    return desktop_only_page_or_404("departments.html", request)


@router.get("/employee-positions", tags=["Pages"])
def employee_positions_page(request: Request):
    return desktop_only_page_or_404("employee_positions.html", request)


@router.get("/shift-templates", tags=["Pages"])
def shift_templates_page(request: Request):
    return desktop_only_page_or_404("shift_templates.html", request)


@router.get("/coverage-requirements", tags=["Pages"])
def coverage_requirements_page(request: Request):
    return desktop_only_page_or_404("coverage_requirements.html", request)


@router.get("/weekly-preferences", tags=["Pages"])
def weekly_preferences_page(request: Request):
    return web.templates.TemplateResponse(request=request, name="weekly_preferences.html", context={})


@router.get("/schedule", tags=["Pages"])
def schedule_page(request: Request):
    return web.templates.TemplateResponse(request=request, name="schedule.html", context={})


@router.get("/settings", tags=["Pages"])
def settings_page(request: Request):
    return desktop_only_page_or_404("settings.html", request)


@router.get("/guide", tags=["Pages"])
def guide_page(request: Request):
    return web.templates.TemplateResponse(request=request, name="guide.html", context={})
