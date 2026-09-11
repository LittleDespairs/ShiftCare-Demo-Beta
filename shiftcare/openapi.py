"""Openapi for ShiftCare."""
from __future__ import annotations

from fastapi import FastAPI
from shiftcare import config as app_constants

def build_openapi_schema(app: FastAPI) -> dict:
    from fastapi.openapi.utils import get_openapi

    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app_constants.tags_metadata,
    )
    components = openapi_schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})
    security_schemes[app_constants.OPENAPI_BEARER_AUTH_SCHEME] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": f"{app_constants.APP_NAME} session token",
        "description": f"Use the access_token returned by /api/auth/login or your active {app_constants.APP_NAME} browser session.",
    }

    for path_item in openapi_schema.get("paths", {}).values():
        for method in ("get", "put", "post", "delete", "options", "head", "patch", "trace"):
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue

            parameters = operation.get("parameters") or []
            has_authorization_header = any(
                str(parameter.get("name", "")).lower() == "authorization"
                and str(parameter.get("in", "")).lower() == "header"
                for parameter in parameters
            )
            if not has_authorization_header:
                continue

            filtered_parameters = [
                parameter
                for parameter in parameters
                if not (
                    str(parameter.get("name", "")).lower() == "authorization"
                    and str(parameter.get("in", "")).lower() == "header"
                )
            ]
            if filtered_parameters:
                operation["parameters"] = filtered_parameters
            else:
                operation.pop("parameters", None)

            security = operation.setdefault("security", [])
            if not any(app_constants.OPENAPI_BEARER_AUTH_SCHEME in entry for entry in security):
                security.insert(0, {app_constants.OPENAPI_BEARER_AUTH_SCHEME: []})

    app.openapi_schema = openapi_schema
    return app.openapi_schema
