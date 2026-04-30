from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app_config import AppConfig


def is_postgres_engine(engine: str) -> bool:
    return engine.strip().lower() in {"postgres", "postgresql"}


def _postgres_host(config: AppConfig) -> str:
    if config.database_host:
        return config.database_host
    if config.cloud_sql_connection_name:
        return f"/cloudsql/{config.cloud_sql_connection_name}"
    return ""


def _rewrite_sql_for_postgres(sql: str) -> str:
    rewritten = sql.replace("?", "%s")
    rewritten = re.sub(r"ON\s+CONFLICT\(([^)]+)\)", r"ON CONFLICT (\1)", rewritten, flags=re.IGNORECASE)
    return rewritten


def _is_postgres_integrity_error(exc: Exception) -> bool:
    if not exc.__class__.__module__.startswith("psycopg.errors"):
        return False
    sqlstate = str(getattr(exc, "sqlstate", "") or "")
    return sqlstate.startswith("23") or exc.__class__.__name__ in {
        "IntegrityError",
        "ForeignKeyViolation",
        "RestrictViolation",
        "UniqueViolation",
        "NotNullViolation",
        "CheckViolation",
        "ExclusionViolation",
    }


@dataclass
class CompatRow(Mapping):
    _columns: list[str]
    _values: tuple[Any, ...]

    def __getitem__(self, key: int | str) -> Any:
        if isinstance(key, int):
            return self._values[key]
        return self._values[self._columns.index(key)]

    def __iter__(self) -> Iterator[Any]:
        return iter(self._columns)

    def __len__(self) -> int:
        return len(self._columns)

    def keys(self) -> list[str]:
        return list(self._columns)

    def items(self):
        return zip(self._columns, self._values)


class PostgresCursorAdapter:
    def __init__(self, cursor, *, track_lastrowid: bool = True):
        self._cursor = cursor
        self._track_lastrowid = track_lastrowid
        self.lastrowid: int | None = None

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    def execute(self, sql: str, params: Sequence[Any] | None = None):
        self.lastrowid = None
        rewritten = _rewrite_sql_for_postgres(sql)
        try:
            self._cursor.execute(rewritten, params)
        except Exception as exc:
            if _is_postgres_integrity_error(exc):
                raise sqlite3.IntegrityError(str(exc)) from exc
            raise
        if self._track_lastrowid and rewritten.lstrip().upper().startswith("INSERT "):
            try:
                row = self._cursor.connection.execute("SELECT lastval()").fetchone()
                self.lastrowid = int(row[0]) if row else None
            except Exception:
                self.lastrowid = None
        return self

    def executemany(self, sql: str, params_seq):
        self.lastrowid = None
        try:
            self._cursor.executemany(_rewrite_sql_for_postgres(sql), params_seq)
        except Exception as exc:
            if _is_postgres_integrity_error(exc):
                raise sqlite3.IntegrityError(str(exc)) from exc
            raise
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        return self._wrap_row(row)

    def fetchall(self):
        return [self._wrap_row(row) for row in self._cursor.fetchall()]

    def _wrap_row(self, row):
        if row is None:
            return None
        columns = [column.name for column in self._cursor.description or []]
        return CompatRow(columns, tuple(row))

    def close(self) -> None:
        self._cursor.close()

    def __iter__(self):
        for row in self._cursor:
            yield self._wrap_row(row)


class PostgresConnectionAdapter:
    engine = "postgresql"

    def __init__(self, connection):
        self._connection = connection

    def cursor(self, *, track_lastrowid: bool = True) -> PostgresCursorAdapter:
        return PostgresCursorAdapter(self._connection.cursor(), track_lastrowid=track_lastrowid)

    def execute(self, sql: str, params: Sequence[Any] | None = None):
        cursor = self.cursor()
        cursor.execute(sql, params)
        return cursor

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()


def connect_postgres(config: AppConfig) -> PostgresConnectionAdapter:
    import psycopg

    connection = psycopg.connect(
        dbname=config.database_name,
        user=config.database_user,
        password=config.database_password,
        host=_postgres_host(config),
        port=config.database_port,
        sslmode=config.database_ssl_mode if config.database_host else "disable",
        connect_timeout=10,
    )
    return PostgresConnectionAdapter(connection)


def apply_postgres_schema(connection: PostgresConnectionAdapter, schema_path: Path) -> None:
    sql = schema_path.read_text(encoding="utf-8")
    cursor = connection.cursor(track_lastrowid=False)
    for statement in [part.strip() for part in sql.split(";") if part.strip()]:
        try:
            cursor.execute(statement)
        except Exception as exc:
            connection.rollback()
            preview = " ".join(statement.split())[:240]
            raise RuntimeError(f"PostgreSQL schema statement failed: {preview}") from exc
    connection.commit()
