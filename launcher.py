import threading
import time
import socket
import traceback
import webview
import uvicorn

try:
    from main import app
except Exception as error:
    print("ERROR while importing app from main.py:")
    print(error)
    traceback.print_exc()
    input("Press Enter to close...")
    raise


HOST = "127.0.0.1"
PORT = 8000


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
        print("Starting uvicorn server...")
        uvicorn.run(
            app,
            host=HOST,
            port=PORT,
            reload=False,
            log_level="info"
        )
    except Exception as error:
        print("ERROR while running server:")
        print(error)
        traceback.print_exc()
        input("Press Enter to close...")


if __name__ == "__main__":
    try:
        print("Launching application...")

        server_thread = threading.Thread(target=run_server, daemon=False)
        server_thread.start()

        print("Waiting for server...")
        if not wait_for_server(HOST, PORT, timeout=20):
            raise RuntimeError("Server did not start in time")

        print("Server is ready. Opening window...")
        webview.create_window(
            "Schedule App",
            f"http://{HOST}:{PORT}",
            width=1200,
            height=800
        )
        webview.start()

    except Exception as error:
        print("APPLICATION ERROR:")
        print(error)
        traceback.print_exc()
        input("Press Enter to close...")