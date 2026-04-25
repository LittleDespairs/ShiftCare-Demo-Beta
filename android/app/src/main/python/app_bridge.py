import socket
import sys
import threading
import time
from pathlib import Path

import uvicorn


SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8765
_server_thread = None
_runtime_backend_dir = None


def _backend_dir() -> Path:
    if _runtime_backend_dir:
        return Path(_runtime_backend_dir)
    return Path(__file__).resolve().parent / "schedule_app_backend"


def _ensure_backend_on_path() -> None:
    backend_dir = str(_backend_dir())
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)


def _is_port_open() -> bool:
    try:
        with socket.create_connection((SERVER_HOST, SERVER_PORT), timeout=0.25):
            return True
    except OSError:
        return False


def _run_server() -> None:
    _ensure_backend_on_path()
    from main import app

    uvicorn.run(
        app,
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=False,
        log_level="warning",
    )


def start_server(backend_path: str | None = None) -> str:
    global _server_thread, _runtime_backend_dir

    if backend_path:
        _runtime_backend_dir = backend_path

    if _server_thread and _server_thread.is_alive():
        return get_url()

    _server_thread = threading.Thread(target=_run_server, daemon=True)
    _server_thread.start()

    deadline = time.time() + 30
    while time.time() < deadline:
        if _is_port_open():
            return get_url()
        time.sleep(0.2)

    raise RuntimeError("Schedule App backend did not start within 30 seconds")


def get_url() -> str:
    return f"http://{SERVER_HOST}:{SERVER_PORT}/"
