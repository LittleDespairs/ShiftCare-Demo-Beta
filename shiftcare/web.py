"""Web for ShiftCare."""
from __future__ import annotations

from fastapi.templating import Jinja2Templates
from pathlib import Path
import sys

def get_base_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]


BASE_PATH = get_base_path()


FAVICON_PATH = BASE_PATH / "static" / "icons" / "app-icon.ico"


templates = Jinja2Templates(directory=str(BASE_PATH / "templates"))
