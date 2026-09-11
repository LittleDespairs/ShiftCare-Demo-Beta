"""Routes: system for ShiftCare."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from shiftcare import config as app_constants
from shiftcare import web as web
from shiftcare.services import runtime as services_runtime
import app_config
import cloud_sql
import database
import os
import json

router = APIRouter()


@router.get("/manifest.webmanifest", include_in_schema=False)
def web_manifest():
    manifest = json.loads((web.BASE_PATH / "static" / "manifest.webmanifest").read_text(encoding="utf-8"))
    manifest.update(name=app_constants.APP_NAME, short_name=app_constants.APP_NAME)
    return JSONResponse(manifest, media_type="application/manifest+json", headers={"Cache-Control": "no-cache"})


@router.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(web.FAVICON_PATH, media_type="image/x-icon")


@router.get("/docs", include_in_schema=False)
def swagger_ui_html() -> HTMLResponse:
    return HTMLResponse(
        f"""
        <!DOCTYPE html>
        <html>
        <head>
            <link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
            <title>{app_constants.APP_TITLE} - API docs</title>
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
            <script>
            (function () {{
                const tokenKey = "schedule_app_auth_token";
                function storedToken() {{
                    return window.localStorage.getItem(tokenKey) || "";
                }}
                function isApiRequest(request) {{
                    try {{
                        const url = new URL(request.url, window.location.origin);
                        return url.pathname.startsWith("/api/");
                    }} catch (error) {{
                        return String(request.url || "").startsWith("/api/");
                    }}
                }}

                const ui = SwaggerUIBundle({{
                    url: "/openapi.json",
                    dom_id: "#swagger-ui",
                    deepLinking: true,
                    persistAuthorization: true,
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIBundle.SwaggerUIStandalonePreset
                    ],
                    layout: "BaseLayout",
                    requestInterceptor: function (request) {{
                        const token = storedToken();
                        if (token && isApiRequest(request)) {{
                            request.headers = request.headers || {{}};
                            if (!request.headers.Authorization) {{
                                request.headers.Authorization = "Bearer " + token;
                            }}
                        }}
                        return request;
                    }}
                }});

                window.ui = ui;
                const token = storedToken();
                if (token && typeof ui.preauthorizeApiKey === "function") {{
                    window.setTimeout(function () {{
                        try {{
                            ui.preauthorizeApiKey("{app_constants.OPENAPI_BEARER_AUTH_SCHEME}", token);
                        }} catch (error) {{
                            // The request interceptor above still applies the active session token.
                        }}
                    }}, 0);
                }}
            }})();
            </script>
        </body>
        </html>
        """
    )


@router.get("/service-worker.js", include_in_schema=False)
async def service_worker():
    return FileResponse(
        web.BASE_PATH / "static" / "service-worker.js",
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/api/health/live", tags=["Health"])
def health_live():
    return {
        "status": "ok",
        "app_version": app_constants.APP_VERSION,
        "environment": app_config.get_app_config().app_env,
    }


@router.get("/api/health/ready", tags=["Health"])
def health_ready():
    config = app_config.get_app_config()
    runtime = app_config.validate_runtime_config()
    database_status = "ok"
    database_error = None
    if config.database_engine in {"postgres", "postgresql"}:
        postgres_check = cloud_sql.check_postgres_connection(config)
        database_status = postgres_check["status"]
        database_error = postgres_check.get("error")
        if postgres_check["status"] != "ok":
            runtime["issues"].append("PostgreSQL connection check failed")
            runtime["status"] = "blocked"
    else:
        try:
            connection = database.get_connection()
            try:
                connection.execute("SELECT 1")
            finally:
                connection.close()
        except Exception as exc:
            database_status = "error"
            database_error = str(exc)
            runtime["issues"].append("Database connection check failed")
            runtime["status"] = "blocked"

    payload = {
        "status": "ok" if runtime["status"] == "ok" and database_status == "ok" else "blocked",
        "app_version": app_constants.APP_VERSION,
        "runtime": runtime,
        "database": {
            "status": database_status,
            "error": database_error,
        },
    }
    if payload["status"] != "ok":
        raise HTTPException(status_code=503, detail=payload)
    return payload


@router.get("/api/client-config", tags=["Health"])
def client_config():
    public_app_base_url = services_runtime.get_public_app_base_url()
    return {
        "app_version": app_constants.APP_VERSION,
        "default_api_base_url": os.environ.get("SCHEDULE_APP_DEFAULT_API_BASE_URL", app_constants.DEFAULT_CLOUD_API_BASE_URL).strip(),
        "local_api_base_url": "",
        "public_app_base_url": public_app_base_url,
        "employee_portal_url": f"{public_app_base_url}/login" if public_app_base_url else "",
        "employee_invitation_url_base": f"{public_app_base_url}/accept-invitation" if public_app_base_url else "",
        "environment": app_config.get_app_config().app_env,
        "developer_mode": services_runtime.is_developer_mode_enabled(),
        "cloud_employee_portal_mode": services_runtime.is_cloud_employee_portal_mode(),
    }
