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
            # An INSERT into a table without a sequence can make lastval() fail.
            # Isolate this optional lookup so it cannot abort the caller's write.
            self._cursor.connection.execute("SAVEPOINT shiftcare_lastrowid")
            try:
                row = self._cursor.connection.execute("SELECT lastval()").fetchone()
                self.lastrowid = int(row[0]) if row else None
            except Exception:
                self._cursor.connection.execute("ROLLBACK TO SAVEPOINT shiftcare_lastrowid")
                self.lastrowid = None
            finally:
                self._cursor.connection.execute("RELEASE SAVEPOINT shiftcare_lastrowid")
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


def migrate_postgres_runtime_constraints(connection: PostgresConnectionAdapter) -> None:
    """Upgrade existing installations before baseline seed upserts use new keys."""
    cursor = connection.cursor(track_lastrowid=False)
    cursor.execute("SELECT to_regclass('app_settings') AS relation")
    if cursor.fetchone()["relation"] is not None:
        cursor.execute("""
            SELECT c.conname, c.contype,
                   ARRAY(SELECT a.attname FROM unnest(c.conkey) WITH ORDINALITY k(attnum, ordinal)
                         JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum
                         ORDER BY k.ordinal) AS columns
            FROM pg_constraint c
            WHERE c.conrelid = to_regclass('app_settings') AND c.contype IN ('p', 'u')
        """)
        constraints = cursor.fetchall()
        has_primary_key = False
        for constraint in constraints:
            columns = list(constraint["columns"])
            if columns == ["key"]:
                identifier = '"' + constraint["conname"].replace('"', '""') + '"'
                cursor.execute(f"ALTER TABLE app_settings DROP CONSTRAINT {identifier}")
            elif constraint["contype"] == "p":
                has_primary_key = columns == ["organization_id", "key"]
        if not has_primary_key:
            cursor.execute("ALTER TABLE app_settings ADD PRIMARY KEY (organization_id, key)")

    cursor.execute("SELECT to_regclass('organization_memberships') AS relation")
    if cursor.fetchone()["relation"] is not None:
        cursor.execute("""
            SELECT 1 FROM pg_attribute
            WHERE attrelid = to_regclass('organization_memberships')
              AND attname = 'department_access_mode' AND NOT attisdropped
        """)
        if cursor.fetchone() is None:
            cursor.execute("""
                ALTER TABLE organization_memberships
                ADD COLUMN department_access_mode TEXT NOT NULL DEFAULT 'all'
                CHECK (department_access_mode IN ('all', 'restricted'))
            """)
            cursor.execute("SELECT to_regclass('user_department_access') AS relation")
            if cursor.fetchone()["relation"] is not None:
                cursor.execute("""
                    UPDATE organization_memberships m SET department_access_mode = 'restricted'
                    WHERE EXISTS (SELECT 1 FROM user_department_access a
                                  WHERE a.organization_id = m.organization_id AND a.user_id = m.user_id)
                """)


def apply_postgres_schema(connection: PostgresConnectionAdapter, schema_path: Path) -> None:
    sql = schema_path.read_text(encoding="utf-8")
    cursor = connection.cursor(track_lastrowid=False)
    try:
        migrate_postgres_runtime_constraints(connection)
    except Exception:
        connection.rollback()
        raise
    for statement in [part.strip() for part in sql.split(";") if part.strip()]:
        try:
            cursor.execute(statement)
        except Exception as exc:
            connection.rollback()
            preview = " ".join(statement.split())[:240]
            raise RuntimeError(f"PostgreSQL schema statement failed: {preview}") from exc
    connection.commit()
