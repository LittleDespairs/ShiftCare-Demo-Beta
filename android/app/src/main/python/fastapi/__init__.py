import inspect
from typing import Any, get_type_hints

from pydantic import BaseModel
from starlette.applications import Starlette
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: Any = None):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class FastAPI:
    def __init__(self, *args, **kwargs):
        self.title = kwargs.get("title", "")
        self.description = kwargs.get("description", "")
        self.version = kwargs.get("version", "")
        self.routes = []
        self._app = Starlette()

    def mount(self, path: str, app, name: str | None = None):
        self._app.mount(path, app, name=name)

    def get(self, path: str, **options):
        return self._route(path, ["GET"])

    def post(self, path: str, **options):
        return self._route(path, ["POST"])

    def put(self, path: str, **options):
        return self._route(path, ["PUT"])

    def patch(self, path: str, **options):
        return self._route(path, ["PATCH"])

    def delete(self, path: str, **options):
        return self._route(path, ["DELETE"])

    def _route(self, path: str, methods: list[str]):
        def decorator(func):
            endpoint = self._make_endpoint(func)
            route = Route(path, endpoint, methods=methods)
            self.routes.append(route)
            self._app.routes.append(route)
            return func

        return decorator

    def _make_endpoint(self, func):
        signature = inspect.signature(func)
        type_hints = get_type_hints(func)

        async def endpoint(request: Request):
            try:
                kwargs = {}
                body_data = None

                for name, param in signature.parameters.items():
                    annotation = type_hints.get(name, param.annotation)

                    if annotation is Request:
                        kwargs[name] = request
                        continue

                    if inspect.isclass(annotation) and issubclass(annotation, BaseModel):
                        if body_data is None:
                            body_data = await request.json()
                        kwargs[name] = annotation(**body_data)
                        continue

                    if name in request.path_params:
                        raw_value = request.path_params[name]
                    elif name in request.query_params:
                        raw_value = request.query_params[name]
                    elif param.default is not inspect._empty:
                        raw_value = param.default
                    else:
                        raise HTTPException(status_code=422, detail=f"Missing parameter: {name}")

                    kwargs[name] = _convert_param(raw_value, annotation)

                result = func(**kwargs)
                if inspect.isawaitable(result):
                    result = await result
                return _to_response(result)
            except HTTPException as exc:
                return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
            except StarletteHTTPException as exc:
                return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
            except ValueError as exc:
                return JSONResponse({"detail": str(exc)}, status_code=422)

        return endpoint

    async def __call__(self, scope, receive, send):
        await self._app(scope, receive, send)


def _convert_param(value: Any, annotation: Any) -> Any:
    if annotation is inspect._empty:
        return value
    if annotation is bool:
        return str(value).lower() in {"1", "true", "yes", "on"}
    if annotation is int:
        return int(value)
    if annotation is float:
        return float(value)
    return value


def _to_response(result: Any):
    if isinstance(result, Response):
        return result
    return JSONResponse(result)
