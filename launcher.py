import threading
import time
import socket
import sys
import traceback
import webbrowser
from pathlib import Path
import uvicorn


HOST = "127.0.0.1"
PORT = 8000


def get_log_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().with_suffix(".log")
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
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] {message}\n")


def show_error(title: str, message: str) -> None:
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
    except Exception:
        pass


try:
    from main import app
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


def wait_for_server(host: str, port: int, timeout: int = 20) -> bool:
    start = time.time()

    while time.time() - start < timeout:
        if is_server_ready(host, port):
            return True
        time.sleep(0.2)

    return False


def run_server():
    try:
        write_log("Starting uvicorn server...")
        uvicorn.run(
            app,
            host=HOST,
            port=PORT,
            reload=False,
            log_level="info",
            log_config=UVICORN_LOG_CONFIG,
        )
    except Exception:
        write_log(f"ERROR while running server:\n{traceback.format_exc()}")


if __name__ == "__main__":
    try:
        write_log("Launching application...")

        server_thread = threading.Thread(target=run_server, daemon=False)
        server_thread.start()

        write_log("Waiting for server...")
        if not wait_for_server(HOST, PORT, timeout=30):
            raise RuntimeError(f"Server did not start in time. See log: {LOG_PATH}")

        url = f"http://{HOST}:{PORT}"
        write_log(f"Server is ready. Opening browser: {url}")
        webbrowser.open(url)

        server_thread.join()

    except Exception:
        write_log(f"APPLICATION ERROR:\n{traceback.format_exc()}")
        show_error(
            "Schedule App",
            f"Application failed to start.\n\nDetails were saved to:\n{LOG_PATH}",
        )
        sys.exit(1)
