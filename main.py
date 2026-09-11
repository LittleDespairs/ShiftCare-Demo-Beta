"""ASGI entrypoint for ShiftCare desktop, Cloud Run, and tablet servers."""
from release_config import APP_VERSION
from shiftcare.application import create_app

app = create_app()
