import sys
import tempfile
from pathlib import Path

import database

_TEMP_DIR = tempfile.TemporaryDirectory()
database.DATABASE_PATH = Path(_TEMP_DIR.name) / "schedule_app_test.db"
database.init_db()

import main  # noqa: E402


__all__ = ["database", "main"]
