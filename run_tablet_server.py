import os
import socket

import uvicorn

from main import app


HOST = os.getenv("SCHEDULE_APP_HOST", "0.0.0.0")
PORT = int(os.getenv("SCHEDULE_APP_PORT", "8000"))


def get_lan_addresses() -> list[str]:
    addresses: set[str] = set()
    try:
        hostname = socket.gethostname()
        for item in socket.getaddrinfo(hostname, None, socket.AF_INET):
            address = item[4][0]
            if not address.startswith("127."):
                addresses.add(address)
    except OSError:
        pass
    return sorted(addresses)


if __name__ == "__main__":
    print("Schedule App tablet server")
    print("Keep this window open while using the app on the tablet.")
    for address in get_lan_addresses():
        print(f"Open on tablet: http://{address}:{PORT}")
    if not get_lan_addresses():
        print(f"Open on this device: http://127.0.0.1:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT, reload=False)
