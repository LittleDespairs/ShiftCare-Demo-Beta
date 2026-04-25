import threading
import time
import socket
import sys
import traceback
import os
from pathlib import Path
import uvicorn


HOST = "127.0.0.1"
DEFAULT_PORT = 8000
APP_WINDOW_TITLE = "Schedule App"
APP_WINDOW_WIDTH = 1440
APP_WINDOW_HEIGHT = 900
APP_WINDOW_MIN_SIZE = (1100, 720)
SERVER = None


def get_windows_app_data_dir() -> Path:
    app_data_root = os.environ.get("LOCALAPPDATA")
    if app_data_root:
        app_data_dir = Path(app_data_root) / "Schedule App"
    else:
        app_data_dir = Path.home() / "AppData" / "Local" / "Schedule App"

    app_data_dir.mkdir(parents=True, exist_ok=True)
    return app_data_dir


def get_log_path() -> Path:
    if getattr(sys, "frozen", False):
        return get_windows_app_data_dir() / "ScheduleApp.log"
    return Path(__file__).resolve().with_suffix(".log")


LOG_PATH = get_log_path()
UVICORN_LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "default": {
            "class": "logging.NullHandler",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.access": {"handlers": ["default"], "level": "INFO", "propagate": False},
    },
}


def write_log(message: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] {message}\n")


def show_error(title: str, message: str) -> None:
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
    except Exception:
        pass


def get_requested_port() -> int:
    raw_port = os.environ.get("SCHEDULE_APP_PORT", "").strip()
    if not raw_port:
        return DEFAULT_PORT

    try:
        port = int(raw_port)
    except ValueError:
        write_log(f"Invalid SCHEDULE_APP_PORT value: {raw_port!r}. Falling back to {DEFAULT_PORT}.")
        return DEFAULT_PORT

    if not 1 <= port <= 65535:
        write_log(f"SCHEDULE_APP_PORT is out of range: {port}. Falling back to {DEFAULT_PORT}.")
        return DEFAULT_PORT

    return port


try:
    from main import app
    from main import APP_TITLE
except Exception:
    error_text = f"ERROR while importing app from main.py:\n{traceback.format_exc()}"
    write_log(error_text)
    show_error(
        "Schedule App",
        f"Application failed to start.\n\nDetails were saved to:\n{LOG_PATH}",
    )
    sys.exit(1)


def is_server_ready(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def find_available_port(host: str, preferred_port: int) -> int:
    if not is_server_ready(host, preferred_port):
        return preferred_port

    for port in range(preferred_port + 1, preferred_port + 100):
        if not is_server_ready(host, port):
            write_log(f"Port {preferred_port} is busy. Using {port}.")
            return port

    raise RuntimeError("Could not find a free local port for the desktop server.")


def wait_for_server(host: str, port: int, timeout: int = 20) -> bool:
    start = time.time()

    while time.time() - start < timeout:
        if is_server_ready(host, port):
            return True
        time.sleep(0.2)

    return False


def run_server(port: int):
    global SERVER

    try:
        write_log(f"Starting uvicorn server on {HOST}:{port}...")
        config = uvicorn.Config(
            app,
            host=HOST,
            port=port,
            reload=False,
            log_level="info",
            log_config=UVICORN_LOG_CONFIG,
        )
        SERVER = uvicorn.Server(config)
        SERVER.run()
    except Exception:
        write_log(f"ERROR while running server:\n{traceback.format_exc()}")


def stop_server() -> None:
    if SERVER is not None:
        write_log("Stopping uvicorn server...")
        SERVER.should_exit = True


def get_icon_path() -> str | None:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    icon_path = base_path / "static" / "icons" / "app-icon.ico"
    if icon_path.exists():
        return str(icon_path)
    return None


def open_desktop_window(url: str) -> None:
    try:
        import webview
    except Exception:
        write_log(f"ERROR while importing pywebview:\n{traceback.format_exc()}")
        show_error(
            APP_WINDOW_TITLE,
            "Desktop window engine is not installed.\n\nRun: pip install -r requirements.txt",
        )
        raise

    write_log(f"Opening desktop window: {url}")
    webview.create_window(
        title=APP_TITLE,
        url=url,
        width=APP_WINDOW_WIDTH,
        height=APP_WINDOW_HEIGHT,
        min_size=APP_WINDOW_MIN_SIZE,
        resizable=True,
        text_select=True,
    )
    webview.start(private_mode=False, storage_path=str(get_runtime_dir()), icon=get_icon_path())


def get_runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return get_windows_app_data_dir()
    return Path(__file__).resolve().parent


if __name__ == "__main__":
    try:
        write_log("Launching application...")
        port = find_available_port(HOST, get_requested_port())

        server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
        server_thread.start()

        write_log("Waiting for server...")
        if not wait_for_server(HOST, port, timeout=30):
            raise RuntimeError(f"Server did not start in time. See log: {LOG_PATH}")

        url = f"http://{HOST}:{port}"
        write_log(f"Server is ready. Opening desktop window: {url}")
        open_desktop_window(url)

        stop_server()
        server_thread.join(timeout=5)

    except Exception:
        stop_server()
        write_log(f"APPLICATION ERROR:\n{traceback.format_exc()}")
        show_error(
            "Schedule App",
            f"Application failed to start.\n\nDetails were saved to:\n{LOG_PATH}",
        )
        sys.exit(1)
